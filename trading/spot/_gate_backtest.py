#!/usr/bin/env python3
"""
Signal-Aware Deployment Backtest Harness
========================================
Task 4.6: Runs the §8 backtest program from signal-aware-deployment.md v1.0.

Tests four arms per window: mechanical, veto-only, gate-only, veto+gate.
Uses GridModel (d) sizing and engine's linear-deviation-from-avg-entry trigger.

Usage:
    python -m trading.spot._gate_backtest
    python -m trading.spot._gate_backtest --coin NEAR --window 90
"""

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

_WORKSPACE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_WORKSPACE))

from trading.spot.engine.grid_model import (
    LAYER_FRACTIONS, SO_DEVIATION, TP_PCT, MAX_LAYERS, layer_cost
)
from trading.spot.engine.gate_model import (
    entry_veto, veto_clear, layer_gate_open, VetoState,
    RSI_HOT, RSI_COLD, EXT_PCT
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("gate_backtest")

DB_PATH = Path(_WORKSPACE / "trading" / "spot" / "data" / "candles.db")

# Coins to test (matches audit §3.4 analysis)
DEFAULT_COINS = ["NEAR", "TAO", "INJ", "HYPE", "ASTER", "TON", "JUP", "DYDX"]
TAKER_FEE = 0.00025


def load_daily_candles(coin: str, days: int = 90) -> list:
    """Load daily candles from candles_daily table."""
    conn = sqlite3.connect(str(DB_PATH))
    cutoff = datetime.utcnow() - timedelta(days=days)
    cutoff_ts = int(cutoff.timestamp() * 1000)

    # Try both USDT and USDC symbols
    for quote in ["USDT", "USDC"]:
        symbol = f"{coin}/{quote}"
        rows = conn.execute(
            "SELECT timestamp, open, high, low, close, volume FROM candles_daily "
            "WHERE symbol = ? AND timestamp >= ? ORDER BY timestamp",
            (symbol, cutoff_ts)
        ).fetchall()
        if rows:
            conn.close()
            return rows

    conn.close()
    return []


def compute_rsi(closes: list, period: int = 14) -> list:
    """Compute RSI(14) from a list of closes."""
    rsis = [50.0] * min(period, len(closes))
    if len(closes) <= period:
        return rsis

    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [max(0, d) for d in deltas]
    losses = [max(0, -d) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsis.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsis.append(100.0 - (100.0 / (1.0 + rs)))

    return rsis


def compute_sma(closes: list, period: int = 50) -> list:
    """Compute SMA from closes."""
    smas = [0.0] * len(closes)
    for i in range(len(closes)):
        if i < period - 1:
            smas[i] = sum(closes[:i+1]) / (i + 1)
        else:
            smas[i] = sum(closes[i-period+1:i+1]) / period
    return smas


def run_sim(candles: list, coin: str, use_veto: bool, use_gate: bool) -> dict:
    """Run DCA simulation with optional veto and gate.

    Returns dict with performance metrics.
    """
    if len(candles) < 30:
        return {"coin": coin, "deals": 0, "pnl": 0, "max_dd": 0, "avg_duration_h": 0,
                "arm": f"{'veto' if use_veto else ''}{'gate' if use_gate else ''}{'mech' if not use_veto and not use_gate else ''}"}

    alloc = 10000.0
    cash = alloc

    # Pre-compute indicators
    closes = [c[4] for c in candles]  # close price
    rsis = compute_rsi(closes)
    sma50s = compute_sma(closes, 50)

    # Track deals
    deals = []
    in_position = False
    layers = 0
    total_qty = 0.0
    total_cost = 0.0
    avg_entry = 0.0
    tp_price = 0.0
    deal_start_idx = 0
    peak_equity = alloc
    max_dd = 0.0

    # Veto state
    veto = VetoState()
    days_no_new_high = 0
    local_high = 0.0

    # Gate state
    last_gated_fill_idx = -999

    for i, (ts, o, h, l, c, vol) in enumerate(candles):
        rsi = rsis[i] if i < len(rsis) else 50.0
        sma50 = sma50s[i] if i < len(sma50s) else c

        # Update local high tracking for veto clear
        if c > local_high:
            local_high = c
            days_no_new_high = 0
        else:
            days_no_new_high += 1

        # Check veto (Part A)
        if use_veto and not in_position:
            if not veto.active:
                veto = entry_veto("long", rsi, c, sma50, False)
                if veto.active:
                    veto.extreme_price = local_high
            else:
                if veto_clear("long", veto, rsi, c, sma50,
                             days_no_new_high, veto.extreme_price):
                    veto = VetoState()

        if not in_position:
            # Check if we should enter
            if use_veto and veto.active:
                continue  # Vetoed

            # Open deal
            order_cost = layer_cost(0, alloc)
            if order_cost > cash:
                continue
            fee = order_cost * TAKER_FEE
            qty = (order_cost - fee) / c
            total_qty = qty
            total_cost = order_cost
            avg_entry = total_cost / total_qty
            tp_price = avg_entry * (1 + TP_PCT)
            layers = 1
            cash -= order_cost
            in_position = True
            deal_start_idx = i
            continue

        # In position — check TP
        if h >= tp_price:
            proceeds = total_qty * tp_price
            fee = proceeds * TAKER_FEE
            pnl = proceeds - fee - total_cost
            duration_h = (i - deal_start_idx) * 24  # Daily candles
            deals.append({"pnl": pnl, "layers": layers, "duration_h": duration_h,
                         "return_pct": pnl / total_cost * 100})
            cash += proceeds - fee
            in_position = False
            total_qty = 0
            total_cost = 0
            layers = 0
            local_high = 0
            days_no_new_high = 0
            veto = VetoState()

            equity = cash
            if equity > peak_equity:
                peak_equity = equity
            dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
            if dd > max_dd:
                max_dd = dd
            continue

        # Check DCA layers
        if layers < MAX_LAYERS:
            target_drop = SO_DEVIATION * layers
            current_drop = (avg_entry - l) / avg_entry if avg_entry > 0 else 0
            if current_drop >= target_drop:
                layer_idx = layers

                # Part B gate check
                if use_gate and layer_idx >= 2:
                    hours_since = (i - last_gated_fill_idx) * 24
                    # Simplified exhaustion evidence: look for stall after drop
                    # (In production this uses HVF + StochRSI; here we use RSI turning up)
                    has_stall = rsi > 35 and days_no_new_high >= 2
                    has_turn = i > 0 and i < len(rsis) and i-1 < len(rsis) and rsis[i] > rsis[i-1] and rsi < 45
                    gate_open, _ = layer_gate_open("long", layer_idx, has_stall, has_turn, hours_since)
                    if not gate_open:
                        continue

                so_cost = layer_cost(layer_idx, alloc)
                so_cost = min(so_cost, cash)
                if so_cost < 1:
                    continue
                fee = so_cost * TAKER_FEE
                qty = (so_cost - fee) / l
                total_qty += qty
                total_cost += so_cost
                avg_entry = total_cost / total_qty
                tp_price = avg_entry * (1 + TP_PCT)
                layers += 1
                cash -= so_cost
                if use_gate and layer_idx >= 2:
                    last_gated_fill_idx = i

        # Track drawdown
        position_value = total_qty * c
        equity = cash + position_value
        if equity > peak_equity:
            peak_equity = equity
        dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
        if dd > max_dd:
            max_dd = dd

    # Close any open position at last price
    if in_position:
        final_price = candles[-1][4]
        position_value = total_qty * final_price
        unrealized_pnl = position_value - total_cost

    arm_name = []
    if use_veto:
        arm_name.append("veto")
    if use_gate:
        arm_name.append("gate")
    if not arm_name:
        arm_name = ["mechanical"]

    total_pnl = sum(d["pnl"] for d in deals)
    avg_dur = sum(d["duration_h"] for d in deals) / len(deals) if deals else 0
    wins = sum(1 for d in deals if d["pnl"] > 0)

    return {
        "coin": coin,
        "arm": "+".join(arm_name),
        "deals": len(deals),
        "pnl": round(total_pnl, 2),
        "win_rate": round(wins / len(deals) * 100, 1) if deals else 0,
        "max_dd": round(max_dd * 100, 2),
        "avg_duration_h": round(avg_dur, 1),
        "avg_return_pct": round(sum(d["return_pct"] for d in deals) / len(deals), 2) if deals else 0,
        "l3_plus_deals": sum(1 for d in deals if d["layers"] >= 3),
        "max_layers_used": max((d["layers"] for d in deals), default=0),
    }


def main():
    parser = argparse.ArgumentParser(description="Signal-Aware Deployment Backtest")
    parser.add_argument("--coin", type=str, help="Test single coin")
    parser.add_argument("--window", type=int, default=90, help="Lookback days (default 90)")
    args = parser.parse_args()

    coins = [args.coin.upper()] if args.coin else DEFAULT_COINS
    window = args.window

    print(f"\n{'='*90}")
    print(f"  Signal-Aware Deployment Backtest — {len(coins)} coins, {window}d window")
    print(f"  Grid: {LAYER_FRACTIONS} | TP: {TP_PCT*100}% | Dev: {SO_DEVIATION*100}%")
    print(f"  Veto: RSI>{RSI_HOT}/{RSI_COLD}, Ext>{int(EXT_PCT*100)}%")
    print(f"{'='*90}\n")

    all_results = []
    for coin in coins:
        candles = load_daily_candles(coin, window)
        if not candles:
            print(f"  {coin}: No data")
            continue

        print(f"  {coin} ({len(candles)} daily candles)")

        for use_veto, use_gate in [(False, False), (True, False), (False, True), (True, True)]:
            result = run_sim(candles, coin, use_veto, use_gate)
            all_results.append(result)

    # Print results table
    print(f"\n{'='*90}")
    print(f"{'Coin':<8} {'Arm':<14} {'Deals':>6} {'PnL':>10} {'WR%':>6} {'MaxDD':>7} {'AvgDur':>8} {'AvgRet%':>8} {'L3+':>4}")
    print(f"{'-'*90}")

    for r in all_results:
        print(
            f"{r['coin']:<8} {r['arm']:<14} {r['deals']:>6} "
            f"${r['pnl']:>8.2f} {r['win_rate']:>5.1f}% {r['max_dd']:>6.2f}% "
            f"{r['avg_duration_h']:>7.1f}h {r['avg_return_pct']:>7.2f}% {r['l3_plus_deals']:>4}"
        )

    # Summary by arm
    arms = ["mechanical", "veto", "gate", "veto+gate"]
    print(f"\n{'='*90}")
    print("SUMMARY BY ARM:")
    for arm in arms:
        arm_results = [r for r in all_results if r["arm"] == arm]
        if not arm_results:
            continue
        total_pnl = sum(r["pnl"] for r in arm_results)
        total_deals = sum(r["deals"] for r in arm_results)
        avg_dd = sum(r["max_dd"] for r in arm_results) / len(arm_results)
        avg_dur = sum(r["avg_duration_h"] for r in arm_results) / len(arm_results) if arm_results else 0
        print(f"  {arm:<14} deals={total_deals:>4}  PnL=${total_pnl:>10.2f}  avgDD={avg_dd:>5.2f}%  avgDur={avg_dur:>6.1f}h")

    print(f"\n{'='*90}")
    print("NOTE: This uses daily candles with simplified exhaustion evidence.")
    print("Production uses 1h candles with HVF + StochRSI — results will differ.")
    print("Acceptance: veto+gate must be within 10% PnL of mechanical on chop windows.")
    print(f"{'='*90}")


if __name__ == "__main__":
    main()
