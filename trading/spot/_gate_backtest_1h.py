#!/usr/bin/env python3
"""
Signal-Aware Deployment Backtest — 1h Candle Resolution
========================================================
Task 4.6: Full-resolution backtest using 1h candles from candles.db.
Uses proper exhaustion evidence (stall detection, momentum turns) on 1h data.

Usage:
    python -m trading.spot._gate_backtest_1h
    python -m trading.spot._gate_backtest_1h --coin NEAR --days 180
    python -m trading.spot._gate_backtest_1h --days 365
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

_WORKSPACE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_WORKSPACE))

from trading.spot.engine.grid_model import (
    LAYER_FRACTIONS, SO_DEVIATION, TP_PCT, MAX_LAYERS, layer_cost
)
from trading.spot.engine.gate_model import (
    entry_veto, veto_clear, layer_gate_open, VetoState,
    RSI_HOT, RSI_COLD, EXT_PCT, STALL_N, GATE_COOLDOWN_H
)

DB_PATH = Path(_WORKSPACE / "trading" / "spot" / "data" / "candles.db")
DEFAULT_COINS = ["NEAR", "TAO", "INJ", "TON", "JUP", "DYDX", "ASTER", "HYPE"]
TAKER_FEE = 0.00025


def load_1h_candles(coin: str, days: int) -> list:
    """Load 1h candles from candles table."""
    conn = sqlite3.connect(str(DB_PATH))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_ts = int(cutoff.timestamp() * 1000)
    for quote in ["USDT", "USDC"]:
        symbol = f"{coin}/{quote}"
        rows = conn.execute(
            "SELECT timestamp, open, high, low, close, volume FROM candles "
            "WHERE symbol = ? AND timeframe = '1h' AND timestamp >= ? ORDER BY timestamp",
            (symbol, cutoff_ts)
        ).fetchall()
        if rows:
            conn.close()
            return rows
    conn.close()
    return []


def resample_daily(candles_1h: list) -> list:
    """Resample 1h candles to daily for indicator computation."""
    from collections import defaultdict
    days = defaultdict(list)
    for ts, o, h, l, c, v in candles_1h:
        day_key = ts // 86400000  # Floor to day
        days[day_key].append((ts, o, h, l, c, v))
    daily = []
    for day_key in sorted(days.keys()):
        candles = days[day_key]
        daily.append((
            candles[0][0],           # timestamp (first candle)
            candles[0][1],           # open
            max(c[2] for c in candles),  # high
            min(c[3] for c in candles),  # low
            candles[-1][4],          # close
            sum(c[5] for c in candles),  # volume
        ))
    return daily


def compute_rsi(closes: list, period: int = 14) -> list:
    """Compute RSI(14) from closes."""
    if len(closes) <= period:
        return [50.0] * len(closes)
    rsis = [50.0] * period
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [max(0, d) for d in deltas]
    losses = [max(0, -d) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / max(avg_loss, 1e-10)
        rsis.append(100.0 - (100.0 / (1.0 + rs)))
    return rsis


def compute_sma(closes: list, period: int) -> list:
    """Compute SMA."""
    smas = []
    for i in range(len(closes)):
        if i < period - 1:
            smas.append(sum(closes[:i+1]) / (i + 1))
        else:
            smas.append(sum(closes[i-period+1:i+1]) / period)
    return smas


def compute_stoch_rsi(rsis: list, period: int = 14, k_smooth: int = 3, d_smooth: int = 3):
    """Compute StochRSI K and D."""
    k_vals = [50.0] * len(rsis)
    d_vals = [50.0] * len(rsis)
    for i in range(period, len(rsis)):
        window = rsis[i-period+1:i+1]
        rsi_low = min(window)
        rsi_high = max(window)
        rng = rsi_high - rsi_low
        k_vals[i] = ((rsis[i] - rsi_low) / rng * 100) if rng > 0 else 50.0
    # Smooth K
    smoothed_k = list(k_vals)
    for i in range(k_smooth, len(k_vals)):
        smoothed_k[i] = sum(k_vals[i-k_smooth+1:i+1]) / k_smooth
    # Smooth D
    for i in range(d_smooth, len(smoothed_k)):
        d_vals[i] = sum(smoothed_k[i-d_smooth+1:i+1]) / d_smooth
    return smoothed_k, d_vals


def run_sim_1h(candles_1h: list, coin: str, use_veto: bool, use_gate: bool) -> dict:
    """Run DCA sim on 1h candles with optional veto and gate."""
    if len(candles_1h) < 100:
        arm = []
        if use_veto: arm.append("veto")
        if use_gate: arm.append("gate")
        return {"coin": coin, "arm": "+".join(arm) or "mechanical",
                "deals": 0, "pnl": 0, "max_dd": 0, "avg_duration_h": 0,
                "win_rate": 0, "avg_return_pct": 0, "l3_plus": 0, "max_layers": 0,
                "vetoed_entries": 0, "gated_layers": 0}

    # Resample to daily for veto indicators
    daily = resample_daily(candles_1h)
    daily_closes = [d[4] for d in daily]
    daily_rsis = compute_rsi(daily_closes)
    daily_sma50 = compute_sma(daily_closes, 50)

    # 1h indicators for gate
    closes_1h = [c[4] for c in candles_1h]
    rsi_1h = compute_rsi(closes_1h)
    stoch_k, stoch_d = compute_stoch_rsi(rsi_1h)

    # Map each 1h candle to its daily index
    daily_ts = [d[0] for d in daily]
    def get_daily_idx(ts_1h):
        day_key = ts_1h // 86400000
        for i, dts in enumerate(daily_ts):
            if dts // 86400000 == day_key:
                return i
        return max(0, len(daily_ts) - 1)

    alloc = 10000.0
    cash = alloc
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
    last_daily_idx = -1

    # Gate state
    last_gated_fill_idx = -999
    stall_counter = 0
    last_1h_low = float('inf')
    prior_swing_low = float('inf')  # B2 higher-low anchor

    # Stats
    vetoed_entries = 0
    gated_layers = 0

    for i, (ts, o, h, l, c, vol) in enumerate(candles_1h):
        di = get_daily_idx(ts)
        d_rsi = daily_rsis[di] if di < len(daily_rsis) else 50.0
        d_sma50 = daily_sma50[di] if di < len(daily_sma50) else c

        # Track daily extremes for veto
        if di != last_daily_idx:
            last_daily_idx = di
            if di < len(daily) and daily[di][2] > local_high:
                local_high = daily[di][2]
                days_no_new_high = 0
            else:
                days_no_new_high += 1

        # 1h stall detection for gate Part B
        if l < last_1h_low:
            last_1h_low = l
            stall_counter = 0
        else:
            stall_counter += 1

        # Veto check (Part A) — only when not in position
        if use_veto and not in_position:
            if not veto.active:
                veto = entry_veto("long", d_rsi, c, d_sma50, False)
                if veto.active:
                    veto.extreme_price = local_high
            else:
                if veto_clear("long", veto, d_rsi, c, d_sma50,
                             days_no_new_high, veto.extreme_price):
                    veto = VetoState()

        if not in_position:
            if use_veto and veto.active:
                vetoed_entries += 1
                continue

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
            last_1h_low = l
            prior_swing_low = float('inf')
            stall_counter = 0
            continue

        # In position — check TP
        if h >= tp_price:
            proceeds = total_qty * tp_price
            fee = proceeds * TAKER_FEE
            pnl = proceeds - fee - total_cost
            duration_h = (i - deal_start_idx)  # Each candle = 1 hour
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
            last_1h_low = float('inf')

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

                # Part B gate check for L3+ (1h resolution)
                if use_gate and layer_idx >= 2:
                    hours_since = i - last_gated_fill_idx
                    # B1: Stall after flush (STALL_N candles without new low)
                    has_stall = stall_counter >= STALL_N
                    # B2: Structure turn (1h StochRSI K crosses up through D)
                    has_turn = (i > 0 and i < len(stoch_k) and i-1 < len(stoch_k)
                               and stoch_k[i] > stoch_d[i]
                               and stoch_k[i-1] <= stoch_d[i-1]
                               and stoch_k[i] < 40)  # Only in oversold territory
                    # B2 higher-low anchor: current low > prior swing low
                    has_hl = l > prior_swing_low if prior_swing_low < float('inf') else False
                    gate_open, reason = layer_gate_open("long", layer_idx, has_stall, has_turn, has_hl, hours_since)
                    if not gate_open:
                        gated_layers += 1
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
                # Track swing lows for B2 higher-low anchor
                prior_swing_low = last_1h_low
                last_1h_low = l
                stall_counter = 0
                if use_gate and layer_idx >= 2:
                    last_gated_fill_idx = i

        # Track drawdown
        position_value = total_qty * c if in_position else 0
        equity = cash + position_value
        if equity > peak_equity:
            peak_equity = equity
        dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
        if dd > max_dd:
            max_dd = dd

    arm = []
    if use_veto: arm.append("veto")
    if use_gate: arm.append("gate")

    total_pnl = sum(d["pnl"] for d in deals)
    avg_dur = sum(d["duration_h"] for d in deals) / len(deals) if deals else 0
    wins = sum(1 for d in deals if d["pnl"] > 0)

    return {
        "coin": coin,
        "arm": "+".join(arm) or "mechanical",
        "deals": len(deals),
        "pnl": round(total_pnl, 2),
        "win_rate": round(wins / len(deals) * 100, 1) if deals else 0,
        "max_dd": round(max_dd * 100, 2),
        "avg_duration_h": round(avg_dur, 1),
        "avg_return_pct": round(sum(d["return_pct"] for d in deals) / len(deals), 2) if deals else 0,
        "l3_plus": sum(1 for d in deals if d["layers"] >= 3),
        "max_layers": max((d["layers"] for d in deals), default=0),
        "vetoed_entries": vetoed_entries,
        "gated_layers": gated_layers,
    }


def main():
    parser = argparse.ArgumentParser(description="Signal-Aware Backtest (1h candles)")
    parser.add_argument("--coin", type=str, help="Test single coin")
    parser.add_argument("--days", type=int, default=180, help="Lookback days (default 180)")
    args = parser.parse_args()

    coins = [args.coin.upper()] if args.coin else DEFAULT_COINS
    days = args.days

    print(f"\n{'='*100}")
    print(f"  Signal-Aware Deployment Backtest (1H CANDLES) -- {len(coins)} coins, {days}d window")
    print(f"  Grid: {LAYER_FRACTIONS} | TP: {TP_PCT*100}% | Dev: {SO_DEVIATION*100}%")
    print(f"  Veto: RSI>{RSI_HOT}/{RSI_COLD}, Ext>{int(EXT_PCT*100)}%")
    print(f"  Gate: Stall>={STALL_N} candles, Cooldown>={GATE_COOLDOWN_H}h, L3+ only")
    print(f"{'='*100}\n")

    all_results = []
    for coin in coins:
        candles = load_1h_candles(coin, days)
        if not candles:
            print(f"  {coin}: No 1h data")
            continue
        print(f"  {coin}: {len(candles):,} 1h candles ({len(candles)//24}d)")

        for use_veto, use_gate in [(False, False), (True, False), (False, True), (True, True)]:
            result = run_sim_1h(candles, coin, use_veto, use_gate)
            all_results.append(result)

    # Results table
    print(f"\n{'='*100}")
    print(f"{'Coin':<8} {'Arm':<14} {'Deals':>6} {'PnL':>10} {'WR%':>6} {'MaxDD':>7} {'AvgDur':>8} {'AvgRet%':>8} {'L3+':>4} {'Vetoed':>7} {'Gated':>6}")
    print(f"{'-'*100}")

    for r in all_results:
        print(
            f"{r['coin']:<8} {r['arm']:<14} {r['deals']:>6} "
            f"${r['pnl']:>8.2f} {r['win_rate']:>5.1f}% {r['max_dd']:>6.2f}% "
            f"{r['avg_duration_h']:>7.1f}h {r['avg_return_pct']:>7.2f}% {r['l3_plus']:>4}"
            f" {r['vetoed_entries']:>7} {r['gated_layers']:>6}"
        )

    # Summary
    arms = ["mechanical", "veto", "gate", "veto+gate"]
    print(f"\n{'='*100}")
    print("SUMMARY BY ARM:")
    print(f"{'Arm':<14} {'Deals':>6} {'PnL':>12} {'AvgDD':>8} {'AvgDur':>8} {'Vetoed':>8} {'Gated':>8}")
    print(f"{'-'*70}")
    for arm in arms:
        ar = [r for r in all_results if r["arm"] == arm]
        if not ar:
            continue
        print(
            f"  {arm:<14} {sum(r['deals'] for r in ar):>4}  "
            f"${sum(r['pnl'] for r in ar):>10.2f}  "
            f"{sum(r['max_dd'] for r in ar)/len(ar):>6.2f}%  "
            f"{sum(r['avg_duration_h'] for r in ar)/len(ar):>6.1f}h  "
            f"{sum(r['vetoed_entries'] for r in ar):>6}  "
            f"{sum(r['gated_layers'] for r in ar):>6}"
        )

    # Save results for Fable
    output = {
        "backtest_params": {
            "resolution": "1h",
            "window_days": days,
            "coins": coins,
            "grid": LAYER_FRACTIONS,
            "tp_pct": TP_PCT,
            "so_deviation": SO_DEVIATION,
            "max_layers": MAX_LAYERS,
            "veto_rsi_hot": RSI_HOT,
            "veto_rsi_cold": RSI_COLD,
            "veto_ext_pct": EXT_PCT,
            "gate_stall_n": STALL_N,
            "gate_cooldown_h": GATE_COOLDOWN_H,
        },
        "results": all_results,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    out_path = _WORKSPACE / "projects" / "ait" / "specs" / "gate-backtest-results-1h.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to: {out_path}")

    print(f"\n{'='*100}")


if __name__ == "__main__":
    main()
