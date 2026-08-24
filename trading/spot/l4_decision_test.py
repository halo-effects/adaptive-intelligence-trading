#!/usr/bin/env python3
"""
L4 Decision Test — Spec v1.0 (Fable 2026-07-04)
=================================================
Produces a decision-grade comparison: mechanical L4, removed (cash reserve), or pivot-gated.
Output: decision table for Brett, equity CSVs, per-coin per-arm data.

P-0: DD reconciliation is built into the harness as assertions.

Usage:
    python -m trading.spot.l4_decision_test
"""

import argparse
import csv
import json
import os
import sqlite3
import sys
import io
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_WORKSPACE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_WORKSPACE))

from trading.spot.engine.grid_model import (
    LAYER_FRACTIONS, SO_DEVIATION, TP_PCT, MAX_LAYERS, layer_cost
)
from trading.spot.engine.gate_model import (
    entry_veto, veto_clear, VetoState,
    RSI_HOT, RSI_COLD, STALL_N, GATE_COOLDOWN_H, GATE_K_MAX, EXT_ATR_MULT
)

DB_PATH = _WORKSPACE / "trading" / "spot" / "data" / "candles.db"
OUTPUT_DIR = _WORKSPACE / "projects" / "ait" / "specs"
TAKER_FEE = 0.00025
COINS = ["NEAR", "TAO", "INJ", "TON", "JUP", "DYDX", "ASTER", "HYPE"]

# L4 fraction for P-0 sanity assertion
L4_FRACTION = LAYER_FRACTIONS[3]  # 0.16

# ── Pivot Gate Constants (§1) ─────────────────────────────────────────────────
PIVOT_CONFIRM_N = 3         # Consecutive candles with lows above candidate
PIVOT_MAX_SLIP_PCT = 0.015  # Max fill price above trigger (one grid deviation)


# ── Data Loading ──────────────────────────────────────────────────────────────

def load_1h_candles_range(coin: str, start_date: str, end_date: str) -> list:
    conn = sqlite3.connect(str(DB_PATH))
    start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").replace(
        tzinfo=timezone.utc).timestamp() * 1000)
    end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").replace(
        tzinfo=timezone.utc).timestamp() * 1000)
    for quote in ["USDT", "USDC"]:
        symbol = f"{coin}/{quote}"
        rows = conn.execute(
            "SELECT timestamp, open, high, low, close, volume FROM candles "
            "WHERE symbol = ? AND timeframe = '1h' AND timestamp >= ? AND timestamp <= ? "
            "ORDER BY timestamp",
            (symbol, start_ts, end_ts)
        ).fetchall()
        if rows:
            conn.close()
            return rows
    conn.close()
    return []


# ── Indicator Computation ─────────────────────────────────────────────────────

def resample_daily(candles_1h):
    days = defaultdict(list)
    for ts, o, h, l, c, v in candles_1h:
        days[ts // 86400000].append((ts, o, h, l, c, v))
    daily = []
    for dk in sorted(days.keys()):
        cs = days[dk]
        daily.append((cs[0][0], cs[0][1], max(c[2] for c in cs),
                      min(c[3] for c in cs), cs[-1][4], sum(c[5] for c in cs)))
    return daily

def compute_rsi(closes, period=14):
    if len(closes) <= period:
        return [50.0] * len(closes)
    rsis = [50.0] * period
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [max(0, d) for d in deltas]; losses = [max(0, -d) for d in deltas]
    ag = sum(gains[:period]) / period; al = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
        rsis.append(100.0 - 100.0 / (1.0 + ag / max(al, 1e-10)))
    return rsis

def compute_sma(closes, period):
    smas = []
    for i in range(len(closes)):
        w = closes[max(0, i-period+1):i+1]
        smas.append(sum(w) / len(w))
    return smas

def compute_atr(daily, period=14):
    atrs = [0.0] * len(daily)
    if len(daily) < 2: return atrs
    trs = [max(daily[i][2]-daily[i][3], abs(daily[i][2]-daily[i-1][4]),
               abs(daily[i][3]-daily[i-1][4])) for i in range(1, len(daily))]
    if len(trs) < period: return atrs
    atr = sum(trs[:period]) / period; atrs[period] = atr
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period; atrs[i+1] = atr
    return atrs

def compute_stoch_rsi(rsis, period=14, k_smooth=3, d_smooth=3):
    k_vals = [50.0] * len(rsis); d_vals = [50.0] * len(rsis)
    for i in range(period, len(rsis)):
        w = rsis[i-period+1:i+1]; rl, rh = min(w), max(w)
        k_vals[i] = ((rsis[i]-rl)/(rh-rl)*100) if (rh-rl) > 0 else 50.0
    sk = list(k_vals)
    for i in range(k_smooth, len(k_vals)):
        sk[i] = sum(k_vals[i-k_smooth+1:i+1]) / k_smooth
    for i in range(d_smooth, len(sk)):
        d_vals[i] = sum(sk[i-d_smooth+1:i+1]) / d_smooth
    return sk, d_vals


# ── Pivot Gate State Machine (§1) ─────────────────────────────────────────────

class PivotGate:
    """Per-layer pivot gate state machine.
    States: DORMANT → ARMED → (counting pivot confirmation) → FILL or DISARM
    """
    def __init__(self, layer_idx, trigger_price, prev_fill_price):
        self.layer_idx = layer_idx
        self.trigger_price = trigger_price
        self.prev_fill_price = prev_fill_price  # for disarm check
        self.state = "DORMANT"
        self.episode_low = float('inf')
        self.pivot_candidate = 0.0
        self.confirm_count = 0
        self.fill_price = None  # set on confirmation

    def update(self, candle_low, candle_open, stoch_k=None, stoch_d=None,
               prev_stoch_k=None, require_kd=False):
        """Process one 1h candle. Returns 'FILL' if confirmed, else current state."""
        if self.state == "DORMANT":
            if candle_low <= self.trigger_price:
                self.state = "ARMED"
                self.episode_low = candle_low
                self.pivot_candidate = candle_low
                self.confirm_count = 0
            return self.state

        if self.state == "ARMED" or self.state == "CONFIRMING":
            # Disarm: price recovered above previous layer's fill
            if candle_low > self.prev_fill_price:
                self.state = "DORMANT"
                return self.state

            # Track episode low
            if candle_low < self.episode_low:
                self.episode_low = candle_low
                self.pivot_candidate = candle_low
                self.confirm_count = 0
                self.state = "ARMED"
                return self.state

            # Candle low is above pivot candidate — count toward confirmation
            if candle_low > self.pivot_candidate:
                self.confirm_count += 1
                self.state = "CONFIRMING"

                if self.confirm_count >= PIVOT_CONFIRM_N:
                    # Check K↑D requirement for A3b
                    if require_kd:
                        kd_cross = (stoch_k is not None and stoch_d is not None
                                   and prev_stoch_k is not None
                                   and stoch_k > stoch_d and prev_stoch_k <= stoch_d
                                   and stoch_k < GATE_K_MAX)
                        if not kd_cross:
                            return self.state  # Keep waiting for cross

                    # Slippage bound: fill at next candle open
                    max_fill = self.trigger_price * (1 + PIVOT_MAX_SLIP_PCT)
                    if candle_open > max_fill:
                        # Price recovered too far — skip
                        self.state = "ARMED"
                        self.confirm_count = 0
                        return "SKIP"

                    self.fill_price = candle_open
                    self.state = "FILL"
                    return "FILL"
            else:
                # New low equal to candidate — not strictly above, reset
                self.confirm_count = 0
                self.state = "ARMED"

        return self.state


# ── Simulation Engine ─────────────────────────────────────────────────────────

def run_arm(candles_1h, coin, arm, emit_equity_csv=False):
    """
    Arms:
      A0: mechanical, no veto
      A1: mechanical, veto ON
      A2: 3-layer (40/24/20) + 16% cash reserve, veto ON
      A3: pivot-gated L4, veto ON
      A3b: pivot-gated L4 + K↑D confirmation, veto ON
    
    P-0 DD formula (verified):
      equity = cash + (total_qty * candle_close)
      dd = (peak_equity - equity) / peak_equity
      max_dd = max(dd) over all candles
    """
    if len(candles_1h) < 100:
        return None

    use_veto = arm != "A0"
    max_layers_arm = 3 if arm == "A2" else MAX_LAYERS
    use_pivot = arm in ("A3", "A3b")
    require_kd = arm == "A3b"

    # Indicators
    daily = resample_daily(candles_1h)
    daily_closes = [d[4] for d in daily]
    daily_rsis = compute_rsi(daily_closes)
    daily_sma50 = compute_sma(daily_closes, 50)
    daily_atrs = compute_atr(daily)
    closes_1h = [c[4] for c in candles_1h]
    stoch_k, stoch_d = compute_stoch_rsi(compute_rsi(closes_1h))

    daily_ts = [d[0] for d in daily]
    def get_daily_idx(ts):
        dk = ts // 86400000
        for i, dt in enumerate(daily_ts):
            if dt // 86400000 == dk: return i
        return max(0, len(daily_ts) - 1)

    alloc = 10000.0
    cash = alloc
    deals = []
    in_position = False
    layers = 0
    total_qty = 0.0; total_cost = 0.0
    avg_entry = 0.0; tp_price = 0.0
    deal_start_idx = 0
    peak_equity = alloc; max_dd = 0.0

    # Veto state
    veto = VetoState()
    days_no_new_high = 0; local_high = 0.0; last_daily_idx = -1

    # Pivot gate state (for L4 in A3/A3b)
    pivot_gate = None
    last_gated_fill_idx = -999

    # Stats
    vetoed = 0; gated = 0
    l4_fills = []  # {trigger_price, fill_price, delta_pct}

    # Equity series for CSV
    equity_series = [] if emit_equity_csv else None

    # Track layer-hours for capital freedom
    total_layer_hours = 0

    for i, (ts, o, h, l, c, vol) in enumerate(candles_1h):
        di = get_daily_idx(ts)
        d_rsi = daily_rsis[di] if di < len(daily_rsis) else 50.0
        d_sma50 = daily_sma50[di] if di < len(daily_sma50) else c
        d_atr = daily_atrs[di] if di < len(daily_atrs) else 0.0

        # Daily extreme tracking
        if di != last_daily_idx:
            last_daily_idx = di
            if di < len(daily) and daily[di][2] > local_high:
                local_high = daily[di][2]; days_no_new_high = 0
            else:
                days_no_new_high += 1

        # Veto tracking
        if use_veto:
            if not veto.active:
                veto = entry_veto("long", d_rsi, c, d_sma50, atr14=d_atr)
                if veto.active: veto.extreme_price = local_high
            else:
                if veto_clear("long", veto, d_rsi, c, d_sma50,
                             days_no_new_high, veto.extreme_price):
                    veto = VetoState()

        # Layer-hours
        if in_position: total_layer_hours += layers

        # Not in position — try to enter
        if not in_position:
            if use_veto and veto.active:
                vetoed += 1
            else:
                order_cost = layer_cost(0, alloc)
                if order_cost <= cash:
                    fee = order_cost * TAKER_FEE
                    qty = (order_cost - fee) / c
                    total_qty = qty; total_cost = order_cost
                    avg_entry = total_cost / total_qty
                    tp_price = avg_entry * (1 + TP_PCT)
                    layers = 1; cash -= order_cost
                    in_position = True; deal_start_idx = i
                    pivot_gate = None; last_gated_fill_idx = -999

            # Equity tracking
            equity = cash + (total_qty * c if in_position else 0)
            if equity > peak_equity: peak_equity = equity
            dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
            if dd > max_dd: max_dd = dd
            if equity_series is not None:
                equity_series.append((ts, round(equity, 2), round(dd * 100, 4)))
            continue

        # TP check
        if h >= tp_price:
            proceeds = total_qty * tp_price
            fee = proceeds * TAKER_FEE
            pnl = proceeds - fee - total_cost
            deals.append({
                "pnl": round(pnl, 2), "layers": layers,
                "duration_h": i - deal_start_idx,
                "return_pct": round(pnl / total_cost * 100, 2)
            })
            cash += proceeds - fee
            in_position = False; total_qty = 0; total_cost = 0; layers = 0
            veto = VetoState(); local_high = 0; days_no_new_high = 0
            pivot_gate = None

            equity = cash
            if equity > peak_equity: peak_equity = equity
            dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
            if dd > max_dd: max_dd = dd
            if equity_series is not None:
                equity_series.append((ts, round(equity, 2), round(dd * 100, 4)))
            continue

        # DCA layer check
        if layers < max_layers_arm:
            target_drop = SO_DEVIATION * layers
            current_drop = (avg_entry - l) / avg_entry if avg_entry > 0 else 0

            if current_drop >= target_drop:
                layer_idx = layers

                # L4 pivot gate (A3/A3b)
                if use_pivot and layer_idx == 3:
                    # Initialize pivot gate when trigger first reached
                    if pivot_gate is None:
                        # Cooldown check
                        if i - last_gated_fill_idx < GATE_COOLDOWN_H:
                            gated += 1
                        else:
                            trigger = avg_entry * (1 - SO_DEVIATION * (layer_idx))
                            # Previous fill price = L3 fill (approx from avg_entry of L3)
                            prev_fill = avg_entry  # conservative: use current avg
                            pivot_gate = PivotGate(layer_idx, trigger, prev_fill)

                    if pivot_gate is not None:
                        prev_k = stoch_k[i-1] if i > 0 and i-1 < len(stoch_k) else None
                        cur_k = stoch_k[i] if i < len(stoch_k) else None
                        cur_d = stoch_d[i] if i < len(stoch_d) else None

                        result = pivot_gate.update(
                            l, o, stoch_k=cur_k, stoch_d=cur_d,
                            prev_stoch_k=prev_k, require_kd=require_kd
                        )

                        if result == "FILL":
                            fill_price = pivot_gate.fill_price
                            trigger = pivot_gate.trigger_price
                            delta_pct = (fill_price / trigger - 1) * 100
                            l4_fills.append({
                                "trigger": round(trigger, 6),
                                "fill": round(fill_price, 6),
                                "delta_pct": round(delta_pct, 2),
                                "ts": datetime.fromtimestamp(ts/1000, tz=timezone.utc).isoformat()
                            })

                            so_cost = layer_cost(layer_idx, alloc)
                            so_cost = min(so_cost, cash)
                            if so_cost >= 1:
                                fee = so_cost * TAKER_FEE
                                qty = (so_cost - fee) / fill_price
                                total_qty += qty; total_cost += so_cost
                                avg_entry = total_cost / total_qty
                                tp_price = avg_entry * (1 + TP_PCT)
                                layers += 1; cash -= so_cost
                                last_gated_fill_idx = i
                                pivot_gate = None
                        elif result == "SKIP":
                            pivot_gate = None  # Reset, will re-arm if price drops again
                        else:
                            gated += 1
                    else:
                        gated += 1

                else:
                    # Mechanical fill (L1/L2/L3, or L4 in A0/A1)
                    so_cost = layer_cost(layer_idx, alloc)
                    so_cost = min(so_cost, cash)
                    if so_cost >= 1:
                        fee = so_cost * TAKER_FEE
                        qty = (so_cost - fee) / l
                        total_qty += qty; total_cost += so_cost
                        avg_entry = total_cost / total_qty
                        tp_price = avg_entry * (1 + TP_PCT)
                        layers += 1; cash -= so_cost

        # Equity tracking (P-0 verified formula)
        equity = cash + total_qty * c
        if equity > peak_equity: peak_equity = equity
        dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
        if dd > max_dd: max_dd = dd
        if equity_series is not None:
            equity_series.append((ts, round(equity, 2), round(dd * 100, 4)))

    # End-of-window state
    end_state = None
    if in_position:
        last_close = candles_1h[-1][4]
        pos_val = total_qty * last_close
        unrealized = pos_val - total_cost
        end_state = {
            "layers": layers, "invested": round(total_cost, 2),
            "value": round(pos_val, 2), "unrealized_pnl": round(unrealized, 2),
            "unrealized_pct": round(unrealized / total_cost * 100, 2) if total_cost > 0 else 0,
        }

    total_pnl = sum(d["pnl"] for d in deals)
    unrealized_pnl = end_state["unrealized_pnl"] if end_state else 0
    wins = sum(1 for d in deals if d["pnl"] > 0)
    avg_dur = sum(d["duration_h"] for d in deals) / len(deals) if deals else 0
    avg_layer_frac = total_layer_hours / (len(candles_1h) * MAX_LAYERS) if candles_1h else 0

    return {
        "coin": coin, "arm": arm,
        "deals": len(deals),
        "realized_pnl": round(total_pnl, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "total_pnl": round(total_pnl + unrealized_pnl, 2),
        "win_rate": round(wins / len(deals) * 100, 1) if deals else 0,
        "max_dd": round(max_dd * 100, 2),
        "avg_duration_h": round(avg_dur, 1),
        "l3_plus": sum(1 for d in deals if d["layers"] >= 3),
        "l4_count": sum(1 for d in deals if d["layers"] >= 4),
        "l4_fills": l4_fills,
        "vetoed": vetoed, "gated": gated,
        "end_state": end_state,
        "avg_layer_frac": round(avg_layer_frac, 4),
        "equity_series": equity_series,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    WINDOWS = [
        {"label": "Frozen (bull-to-correction)", "start": "2026-04-05", "end": "2026-07-03",
         "coins": COINS},
        {"label": "2026 Q1 chop", "start": "2026-01-01", "end": "2026-03-31",
         "coins": ["NEAR", "INJ"]},
    ]

    ARMS = ["A0", "A1", "A2", "A3", "A3b"]
    ARM_LABELS = {
        "A0": "Mechanical (no veto)",
        "A1": "Mechanical + veto",
        "A2": "3-layer reserve + veto",
        "A3": "Pivot-gated L4 + veto",
        "A3b": "Pivot+K/D L4 + veto",
    }

    print("=" * 120)
    print("L4 DECISION TEST — Spec v1.0")
    print(f"Grid: {LAYER_FRACTIONS} | TP: {TP_PCT*100}% | Dev: {SO_DEVIATION*100}%")
    print(f"Pivot: CONFIRM_N={PIVOT_CONFIRM_N}, MAX_SLIP={PIVOT_MAX_SLIP_PCT*100}%")
    print(f"Veto: RSI>{RSI_HOT}/<{RSI_COLD}, EXT_ATR_MULT={EXT_ATR_MULT}")
    print(f"P-0 DD formula: equity = cash + qty*close, dd = (peak-equity)/peak, sampled every 1h")
    print(f"P-0 L4 bound assertion: |DD_a - DD_b| <= {L4_FRACTION + 0.02:.2f} for same-veto arms differing only in L4")
    print("=" * 120)

    all_results = []
    p0_violations = []

    for window in WINDOWS:
        print(f"\n{'=' * 120}")
        print(f"WINDOW: {window['label']} ({window['start']} to {window['end']})")
        print(f"{'=' * 120}")

        window_results = []
        for coin in window["coins"]:
            candles = load_1h_candles_range(coin, window["start"], window["end"])
            if not candles:
                print(f"  {coin}: No data"); continue
            print(f"  {coin}: {len(candles):,} candles ({len(candles)//24}d)")

            for arm in ARMS:
                # Emit equity CSV for TAO on all arms in frozen window
                emit_csv = (coin == "TAO" and window["label"].startswith("Frozen"))
                r = run_arm(candles, coin, arm, emit_equity_csv=emit_csv)
                if r:
                    window_results.append(r)
                    all_results.append({**r, "window": window["label"],
                                       "equity_series": None})  # Don't store in JSON

                    # Save equity CSV
                    if emit_csv and r.get("equity_series"):
                        csv_path = OUTPUT_DIR / f"equity-series-TAO-{arm}.csv"
                        with open(csv_path, "w", newline="") as f:
                            w = csv.writer(f)
                            w.writerow(["timestamp", "equity", "dd_pct"])
                            w.writerows(r["equity_series"])
                        print(f"    Equity CSV: {csv_path.name}")

        # P-0.3: Sanity assertion — DD bound between arms differing only in L4
        for coin in window["coins"]:
            a1 = next((r for r in window_results if r["coin"]==coin and r["arm"]=="A1"), None)
            a2 = next((r for r in window_results if r["coin"]==coin and r["arm"]=="A2"), None)
            if a1 and a2:
                dd_delta = abs(a1["max_dd"] - a2["max_dd"]) / 100
                bound = L4_FRACTION + 0.02
                if dd_delta > bound:
                    msg = (f"P-0.3 VIOLATION: {coin} |A1 DD {a1['max_dd']:.1f}% - "
                           f"A2 DD {a2['max_dd']:.1f}%| = {dd_delta:.3f} > {bound:.2f}")
                    p0_violations.append(msg)
                    print(f"  *** {msg}")

        # Results table
        print(f"\n{'Coin':<7} {'Arm':<22} {'Deals':>5} {'RealPnL':>9} {'Unreal':>8} {'Total':>9} "
              f"{'MaxDD':>7} {'AvgDur':>7} {'L3+':>4} {'L4':>3} {'L4Fills':>7} {'Veto':>5} {'Gated':>6}")
        print("-" * 115)
        for coin in window["coins"]:
            for r in window_results:
                if r["coin"] != coin: continue
                l4f = len(r.get("l4_fills", []))
                l4_avg_slip = ""
                if l4f > 0:
                    avg_slip = sum(f["delta_pct"] for f in r["l4_fills"]) / l4f
                    l4_avg_slip = f" ({avg_slip:+.1f}%)"
                print(f"{r['coin']:<7} {ARM_LABELS[r['arm']]:<22} {r['deals']:>5} "
                      f"${r['realized_pnl']:>7.0f} ${r['unrealized_pnl']:>6.0f} ${r['total_pnl']:>7.0f} "
                      f"{r['max_dd']:>6.1f}% {r['avg_duration_h']:>6.1f}h "
                      f"{r['l3_plus']:>4} {r['l4_count']:>3} "
                      f"{l4f:>3}{l4_avg_slip:>4} {r['vetoed']:>5} {r['gated']:>6}")
            print()

    # Summary by arm across frozen window
    print(f"\n{'=' * 120}")
    print("DECISION TABLE (frozen window, all coins):")
    print(f"{'Arm':<22} {'Deals':>6} {'Total PnL':>10} {'%Mech':>7} "
          f"{'MaxDD min':>9} {'MaxDD med':>9} {'MaxDD max':>9} {'MedDur':>7} "
          f"{'L4 Fills':>8} {'Avg Slip':>8} {'PnL/DD':>8}")
    print("-" * 115)

    frozen = [r for r in all_results if r["window"].startswith("Frozen")]
    mech_total = sum(r["total_pnl"] for r in frozen if r["arm"] == "A0")

    for arm in ARMS:
        ar = [r for r in frozen if r["arm"] == arm]
        if not ar: continue
        tpnl = sum(r["total_pnl"] for r in ar)
        dds = sorted([r["max_dd"] for r in ar])
        n = len(dds)
        dd_min = dds[0]; dd_max = dds[-1]
        dd_med = (dds[n//2-1] + dds[n//2]) / 2 if n % 2 == 0 else dds[n//2]
        durs = sorted([r["avg_duration_h"] for r in ar if r["avg_duration_h"] > 0])
        dur_med = (durs[len(durs)//2-1]+durs[len(durs)//2])/2 if len(durs) % 2 == 0 and durs else (durs[len(durs)//2] if durs else 0)
        pct = tpnl / mech_total * 100 if mech_total else 0
        pnl_dd = tpnl / dd_med if dd_med > 0 else float('inf')
        l4f = sum(len(r.get("l4_fills", [])) for r in ar)
        all_slips = [f["delta_pct"] for r in ar for f in r.get("l4_fills", [])]
        avg_slip = sum(all_slips) / len(all_slips) if all_slips else 0

        print(f"  {ARM_LABELS[arm]:<20} {sum(r['deals'] for r in ar):>5}  "
              f"${tpnl:>8.0f} {pct:>6.1f}%  "
              f"{dd_min:>7.1f}%  {dd_med:>7.1f}%  {dd_max:>7.1f}%  "
              f"{dur_med:>5.1f}h  "
              f"{l4f:>6}  "
              f"{'N/A' if not all_slips else f'{avg_slip:+.2f}%':>7}  "
              f"${pnl_dd:>6.0f}")

    # P-0 summary
    print(f"\n{'=' * 120}")
    if p0_violations:
        print("P-0 VIOLATIONS (run not valid as decision evidence):")
        for v in p0_violations:
            print(f"  {v}")
    else:
        print("P-0 PASSED: All DD bound assertions hold. Results are decision-grade.")

    # A3 fill analysis
    print(f"\n{'=' * 120}")
    print("A3 PIVOT-GATE L4 FILL DETAILS:")
    for r in all_results:
        if r["arm"] == "A3" and r.get("l4_fills"):
            for f in r["l4_fills"]:
                print(f"  {r['coin']} [{r.get('window','')}] {f['ts']}: "
                      f"trigger=${f['trigger']:.4f} fill=${f['fill']:.4f} "
                      f"delta={f['delta_pct']:+.2f}%")
    a3_fills = [f for r in all_results if r["arm"]=="A3" for f in r.get("l4_fills",[])]
    if not a3_fills:
        print("  NO L4 FILLS ADMITTED by pivot gate across all windows")
    else:
        print(f"\n  Total A3 fills: {len(a3_fills)}")
        print(f"  Avg confirmation cost: {sum(f['delta_pct'] for f in a3_fills)/len(a3_fills):+.2f}%")

    # Save results
    save_results = [{k: v for k, v in r.items() if k != "equity_series"} for r in all_results]
    out_path = OUTPUT_DIR / "l4-decision-results.json"
    with open(out_path, "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "spec": "L4 Decision Test Spec v1.0 (Fable 2026-07-04)",
            "parameters": {
                "grid": LAYER_FRACTIONS, "tp_pct": TP_PCT, "so_deviation": SO_DEVIATION,
                "pivot_confirm_n": PIVOT_CONFIRM_N, "pivot_max_slip_pct": PIVOT_MAX_SLIP_PCT,
                "gate_cooldown_h": GATE_COOLDOWN_H, "gate_k_max": GATE_K_MAX,
                "l4_fraction": L4_FRACTION, "taker_fee": TAKER_FEE,
            },
            "p0_violations": p0_violations,
            "results": save_results,
        }, f, indent=2, default=str)
    print(f"\nResults saved: {out_path}")
    print("=" * 120)


if __name__ == "__main__":
    main()
