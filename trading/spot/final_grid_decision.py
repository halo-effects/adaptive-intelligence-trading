#!/usr/bin/env python3
"""
Final Grid Decision — Test Run Spec v1.0 (Fable 2026-07-04)
============================================================
One run, one table, one decision: the production grid.
Arms: G-A1 (40/24/20/16), G-A2 (40/24/20+reserve), G-SPLIT (48/32/20), G-FAT (56/24/20)

Usage:
    python -m trading.spot.final_grid_decision
"""

import csv
import json
import sqlite3
import sys
import io
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32" and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_WORKSPACE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_WORKSPACE))

from trading.spot.engine.grid_model import SO_DEVIATION, TP_PCT, MAX_LAYERS
from trading.spot.engine.gate_model import (
    entry_veto, veto_clear, VetoState, EXT_ATR_MULT
)

DB_PATH = _WORKSPACE / "trading" / "spot" / "data" / "candles.db"
OUTPUT_DIR = _WORKSPACE / "projects" / "ait" / "specs"
TAKER_FEE = 0.00025
COINS = ["NEAR", "TAO", "INJ", "TON", "JUP", "DYDX", "ASTER", "HYPE"]

# Grid definitions
GRIDS = {
    "G-A1": {"fracs": [0.40, 0.24, 0.20, 0.16], "layers": 4, "label": "40/24/20/16 (4L)"},
    "G-A2": {"fracs": [0.40, 0.24, 0.20], "layers": 3, "label": "40/24/20 + 16% rsv (3L)"},
    "G-SPLIT": {"fracs": [0.48, 0.32, 0.20], "layers": 3, "label": "48/32/20 (3L)"},
    "G-FAT": {"fracs": [0.56, 0.24, 0.20], "layers": 3, "label": "56/24/20 (3L)"},
}

# Validate fracs sum
for arm, g in GRIDS.items():
    s = sum(g["fracs"])
    assert abs(s - 1.0) < 0.001 or (arm == "G-A2" and abs(s - 0.84) < 0.001), \
        f"{arm} fracs sum to {s}, expected 1.0 (or 0.84 for reserve)"

WINDOWS = [
    {"label": "Frozen", "start": "2026-04-05", "end": "2026-07-03", "coins": COINS},
    {"label": "Q1 chop", "start": "2026-01-01", "end": "2026-03-31", "coins": ["NEAR", "INJ"]},
]


# ── Data + Indicators ─────────────────────────────────────────────────────────

def load_candles(coin, start, end):
    conn = sqlite3.connect(str(DB_PATH))
    s_ts = int(datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    e_ts = int(datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    for q in ["USDT", "USDC"]:
        rows = conn.execute(
            "SELECT timestamp, open, high, low, close, volume FROM candles "
            "WHERE symbol=? AND timeframe='1h' AND timestamp>=? AND timestamp<=? ORDER BY timestamp",
            (f"{coin}/{q}", s_ts, e_ts)).fetchall()
        if rows: conn.close(); return rows
    conn.close(); return []

def resample_daily(c1h):
    d = defaultdict(list)
    for r in c1h: d[r[0]//86400000].append(r)
    return [(v[0][0], v[0][1], max(x[2] for x in v), min(x[3] for x in v),
             v[-1][4], sum(x[5] for x in v)) for v in [d[k] for k in sorted(d)]]

def compute_rsi(cl, p=14):
    if len(cl)<=p: return [50.0]*len(cl)
    r=[50.0]*p; dl=[cl[i]-cl[i-1] for i in range(1,len(cl))]
    g=[max(0,x) for x in dl]; ls=[max(0,-x) for x in dl]
    ag=sum(g[:p])/p; al=sum(ls[:p])/p
    for i in range(p,len(dl)):
        ag=(ag*(p-1)+g[i])/p; al=(al*(p-1)+ls[i])/p
        r.append(100-100/(1+ag/max(al,1e-10)))
    return r

def compute_sma(cl, p):
    return [sum(cl[max(0,i-p+1):i+1])/min(i+1,p) for i in range(len(cl))]

def compute_atr(daily, p=14):
    a=[0.0]*len(daily)
    if len(daily)<2: return a
    tr=[max(daily[i][2]-daily[i][3],abs(daily[i][2]-daily[i-1][4]),
            abs(daily[i][3]-daily[i-1][4])) for i in range(1,len(daily))]
    if len(tr)<p: return a
    v=sum(tr[:p])/p; a[p]=v
    for i in range(p,len(tr)): v=(v*(p-1)+tr[i])/p; a[i+1]=v
    return a


# ── Simulation ────────────────────────────────────────────────────────────────

def run_arm(candles_1h, coin, arm, emit_csv=False):
    grid = GRIDS[arm]
    fracs = grid["fracs"]
    max_l = grid["layers"]

    if len(candles_1h) < 100: return None

    daily = resample_daily(candles_1h)
    dc = [d[4] for d in daily]
    d_rsis = compute_rsi(dc); d_sma50 = compute_sma(dc, 50); d_atrs = compute_atr(daily)
    d_ts = [d[0] for d in daily]
    def di(ts):
        dk = ts//86400000
        for i,dt in enumerate(d_ts):
            if dt//86400000==dk: return i
        return max(0,len(d_ts)-1)

    alloc = 10000.0; cash = alloc
    deals = []; in_pos = False; layers = 0
    tq = 0.0; tc = 0.0; ae = 0.0; tp = 0.0
    ds_idx = 0; peak = alloc; mdd = 0.0

    veto = VetoState(); dnh = 0; lh = 0.0; ldi = -1
    vetoed = 0; tlh = 0
    eq_series = [] if emit_csv else None

    # E-3a: per-deal entry quality
    deal_entries = []  # {ext_atr, rsi, mae, duration, return_pct}
    deal_mae = 0.0  # max adverse excursion for current deal

    for i, (ts, o, h, l, c, vol) in enumerate(candles_1h):
        dix = di(ts)
        dr = d_rsis[dix] if dix < len(d_rsis) else 50.0
        ds = d_sma50[dix] if dix < len(d_sma50) else c
        da = d_atrs[dix] if dix < len(d_atrs) else 0.0

        if dix != ldi:
            ldi = dix
            if dix < len(daily) and daily[dix][2] > lh: lh = daily[dix][2]; dnh = 0
            else: dnh += 1

        if not veto.active:
            veto = entry_veto("long", dr, c, ds, atr14=da)
            if veto.active: veto.extreme_price = lh
        else:
            if veto_clear("long", veto, dr, c, ds, dnh, veto.extreme_price):
                veto = VetoState()

        if in_pos: tlh += layers

        if not in_pos:
            if veto.active:
                vetoed += 1
            else:
                oc = alloc * fracs[0]
                if oc <= cash:
                    fee = oc * TAKER_FEE; qty = (oc - fee) / c
                    tq = qty; tc = oc; ae = tc / tq; tp = ae * (1 + TP_PCT)
                    layers = 1; cash -= oc; in_pos = True; ds_idx = i
                    deal_mae = 0.0
                    # E-3a: record entry conditions (NULL on failure, never defaults)
                    if da > 0 and ds > 0 and dix >= 50:  # need warm-up for valid indicators
                        deal_entry_ext_atr = (c - ds) / da
                        deal_entry_rsi = dr
                    else:
                        deal_entry_ext_atr = None  # NULL — lookup failed
                        deal_entry_rsi = None

            eq = cash + (tq * c if in_pos else 0)
            if eq > peak: peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0
            if dd > mdd: mdd = dd
            if eq_series is not None: eq_series.append((ts, round(eq, 2), round(dd*100, 4)))
            continue

        # TP
        if h >= tp:
            pr = tq * tp; fee = pr * TAKER_FEE; pnl = pr - fee - tc
            dur = i - ds_idx
            deals.append({"pnl": round(pnl, 2), "layers": layers, "duration_h": dur,
                          "return_pct": round(pnl/tc*100, 2), "mae_pct": round(deal_mae*100, 2)})
            deal_entries.append({
                "ext_atr_at_entry": round(deal_entry_ext_atr, 3) if deal_entry_ext_atr is not None else "",
                "rsi_at_entry": round(deal_entry_rsi, 1) if deal_entry_rsi is not None else "",
                "max_adverse_pct": round(deal_mae*100, 2),
                "duration_h": dur,
                "return_pct": round(pnl/tc*100, 2),
                "layers": layers,
            })
            cash += pr - fee; in_pos = False; tq = 0; tc = 0; layers = 0
            veto = VetoState(); lh = 0; dnh = 0

            eq = cash
            if eq > peak: peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0
            if dd > mdd: mdd = dd
            if eq_series is not None: eq_series.append((ts, round(eq, 2), round(dd*100, 4)))
            continue

        # DCA
        if layers < max_l:
            td = SO_DEVIATION * layers
            cd = (ae - l) / ae if ae > 0 else 0
            if cd >= td:
                sc = alloc * fracs[layers]; sc = min(sc, cash)
                if sc >= 1:
                    fee = sc * TAKER_FEE; qty = (sc - fee) / l
                    tq += qty; tc += sc; ae = tc / tq; tp = ae * (1 + TP_PCT)
                    layers += 1; cash -= sc

        # DD + MAE
        eq = cash + tq * c
        if eq > peak: peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0
        if dd > mdd: mdd = dd
        if in_pos:
            adv = (ae - l) / ae if ae > 0 else 0
            if adv > deal_mae: deal_mae = adv
        if eq_series is not None: eq_series.append((ts, round(eq, 2), round(dd*100, 4)))

    # End state
    end = None
    if in_pos:
        lc = candles_1h[-1][4]; pv = tq * lc; ur = pv - tc
        end = {"layers": layers, "invested": round(tc, 2), "value": round(pv, 2),
               "unrealized_pnl": round(ur, 2),
               "unrealized_pct": round(ur/tc*100, 2) if tc > 0 else 0}

    rpnl = sum(d["pnl"] for d in deals)
    upnl = end["unrealized_pnl"] if end else 0
    wins = sum(1 for d in deals if d["pnl"] > 0)
    durations = [d["duration_h"] for d in deals]
    durations.sort()
    med_dur = (durations[len(durations)//2] if durations else 0)
    alf = tlh / (len(candles_1h) * max_l) if candles_1h else 0

    return {
        "coin": coin, "arm": arm, "grid": "/".join(f"{f*100:.0f}" for f in fracs),
        "layers": max_l,
        "deals": len(deals),
        "realized_pnl": round(rpnl, 2), "unrealized_pnl": round(upnl, 2),
        "total_pnl": round(rpnl + upnl, 2),
        "win_rate": round(wins/len(deals)*100, 1) if deals else 0,
        "max_dd": round(mdd * 100, 2),
        "med_duration_h": med_dur,
        "l3_plus": sum(1 for d in deals if d["layers"] >= 3),
        "vetoed": vetoed,
        "end_state": end,
        "avg_layer_frac": round(alf, 4),
        "equity_series": eq_series,
        "deal_entries": deal_entries,
    }


def main():
    # Load reference data from L4 test
    ref_path = OUTPUT_DIR / "l4-decision-results.json"
    ref_data = json.loads(ref_path.read_text()) if ref_path.exists() else None

    print("=" * 130)
    print("FINAL GRID DECISION — Test Run Spec v1.0")
    labels = ', '.join(f'{a}={GRIDS[a]["label"]}' for a in GRIDS)
    print(f"Grid menu: {labels}")
    print(f"P-0 discipline: verified DD formula, frozen edges, single run")
    print("=" * 130)

    all_results = []
    new_arms = ["G-SPLIT", "G-FAT"]
    ref_arms = ["G-A1", "G-A2"]

    for window in WINDOWS:
        print(f"\n{'=' * 130}")
        print(f"WINDOW: {window['label']} ({window['start']} to {window['end']})")
        print(f"{'=' * 130}")

        # Pull reference data if available
        if ref_data:
            ref_window_label = "Frozen (bull-to-correction)" if window["label"] == "Frozen" else "2026 Q1 chop"
            for arm in ref_arms:
                # Map arm names: A1→G-A1, A2→G-A2
                ref_arm = "A1" if arm == "G-A1" else "A2"
                for coin in window["coins"]:
                    ref_r = next((r for r in ref_data["results"]
                                 if r["coin"] == coin and r["arm"] == ref_arm
                                 and r.get("window", "").startswith(ref_window_label[:6])), None)
                    if ref_r:
                        all_results.append({
                            "coin": coin, "arm": arm,
                            "grid": GRIDS[arm]["label"],
                            "layers": GRIDS[arm]["layers"],
                            "deals": ref_r["deals"],
                            "realized_pnl": ref_r["realized_pnl"],
                            "unrealized_pnl": ref_r["unrealized_pnl"],
                            "total_pnl": ref_r["total_pnl"],
                            "win_rate": ref_r["win_rate"],
                            "max_dd": ref_r["max_dd"],
                            "med_duration_h": ref_r.get("avg_duration_h", 0),
                            "l3_plus": ref_r.get("l3_plus", 0),
                            "vetoed": ref_r.get("vetoed", 0),
                            "end_state": ref_r.get("end_state"),
                            "avg_layer_frac": ref_r.get("avg_layer_frac", 0),
                            "window": window["label"],
                            "source": "reference",
                        })

        # Run new arms
        for coin in window["coins"]:
            candles = load_candles(coin, window["start"], window["end"])
            if not candles:
                print(f"  {coin}: No data"); continue
            print(f"  {coin}: {len(candles):,} candles")

            for arm in new_arms:
                emit = (coin == "TAO" and window["label"] == "Frozen")
                r = run_arm(candles, coin, arm, emit_csv=emit)
                if r:
                    r["window"] = window["label"]
                    r["source"] = "new_run"
                    all_results.append({k: v for k, v in r.items() if k != "equity_series" and k != "deal_entries"})

                    # Save equity CSV
                    if emit and r.get("equity_series"):
                        cp = OUTPUT_DIR / f"equity-series-TAO-{arm}.csv"
                        with open(cp, "w", newline="") as f:
                            w = csv.writer(f); w.writerow(["timestamp", "equity", "dd_pct"])
                            w.writerows(r["equity_series"])
                        print(f"    Equity CSV: {cp.name}")

                    # Save E-3a deal entries
                    if r.get("deal_entries"):
                        dp = OUTPUT_DIR / f"e3a-deals-{coin}-{arm}-{window['label'].replace(' ','_')}.csv"
                        with open(dp, "w", newline="") as f:
                            w = csv.DictWriter(f, fieldnames=["ext_atr_at_entry","rsi_at_entry",
                                              "max_adverse_pct","duration_h","return_pct","layers"])
                            w.writeheader(); w.writerows(r["deal_entries"])

    # ── Results Table ─────────────────────────────────────────────────────────
    for window in WINDOWS:
        wl = window["label"]
        wr = [r for r in all_results if r.get("window") == wl]
        if not wr: continue

        print(f"\n{'=' * 130}")
        print(f"RESULTS: {wl}")
        print(f"{'Coin':<7} {'Arm':<10} {'Grid':<18} {'Deals':>5} {'RealPnL':>9} {'Unreal':>8} "
              f"{'Total':>9} {'MaxDD':>7} {'MedDur':>7} {'L3+':>4} {'Veto':>5}")
        print("-" * 100)
        for coin in (COINS if wl == "Frozen" else ["NEAR", "INJ"]):
            for arm in ["G-A1", "G-A2", "G-SPLIT", "G-FAT"]:
                r = next((x for x in wr if x["coin"]==coin and x["arm"]==arm), None)
                if not r: continue
                print(f"{r['coin']:<7} {r['arm']:<10} {GRIDS[arm]['label']:<18} {r['deals']:>5} "
                      f"${r['realized_pnl']:>7.0f} ${r['unrealized_pnl']:>6.0f} ${r['total_pnl']:>7.0f} "
                      f"{r['max_dd']:>6.1f}% {r['med_duration_h']:>5.0f}h {r['l3_plus']:>4} {r['vetoed']:>5}")
            print()

    # ── Decision Table (one page) ─────────────────────────────────────────────
    print(f"\n{'=' * 130}")
    print("DECISION TABLE")
    print(f"{'Arm':<10} {'Grid':<18} {'Window':<10} {'Deals':>6} {'Total PnL':>10} "
          f"{'DD min':>7} {'DD med':>7} {'DD max':>7} {'MedDur':>7} {'PnL/%DD':>8} {'Rule1':>7}")
    print("-" * 110)

    # Get G-A1 totals for Rule 1
    a1_frozen_total = sum(r["total_pnl"] for r in all_results if r["arm"]=="G-A1" and r.get("window")=="Frozen")
    a1_chop_total = sum(r["total_pnl"] for r in all_results if r["arm"]=="G-A1" and r.get("window")=="Q1 chop")

    for arm in ["G-A1", "G-A2", "G-SPLIT", "G-FAT"]:
        for wl in ["Frozen", "Q1 chop"]:
            wr = [r for r in all_results if r["arm"]==arm and r.get("window")==wl]
            if not wr: continue
            tpnl = sum(r["total_pnl"] for r in wr)
            dds = sorted([r["max_dd"] for r in wr])
            n = len(dds)
            dd_min = dds[0]; dd_max = dds[-1]
            dd_med = (dds[n//2-1]+dds[n//2])/2 if n%2==0 and n>1 else dds[n//2]
            durs = sorted([r["med_duration_h"] for r in wr if r["med_duration_h"]>0])
            dur_med = durs[len(durs)//2] if durs else 0
            pnl_dd = tpnl / dd_med if dd_med > 0 else float('inf')

            # Rule 1 check (chop window)
            rule1 = ""
            if wl == "Q1 chop":
                frozen_total = sum(r["total_pnl"] for r in all_results if r["arm"]==arm and r.get("window")=="Frozen")
                frozen_gain = frozen_total - a1_frozen_total
                chop_excess_loss = a1_chop_total - tpnl  # how much MORE this arm lost vs A1
                if chop_excess_loss > frozen_gain and frozen_gain > 0:
                    rule1 = "ELIM"
                elif chop_excess_loss > 0:
                    rule1 = f"+${chop_excess_loss:.0f}"
                else:
                    rule1 = "OK"

            print(f"  {arm:<8} {GRIDS[arm]['label']:<18} {wl:<10} {sum(r['deals'] for r in wr):>5} "
                  f"${tpnl:>8.0f} {dd_min:>6.1f}% {dd_med:>6.1f}% {dd_max:>6.1f}% "
                  f"{dur_med:>5.0f}h ${pnl_dd:>6.0f} {rule1:>7}")

    # ── Fable Predictions Scored ──────────────────────────────────────────────
    print(f"\n{'=' * 130}")
    print("FABLE PREDICTIONS SCORED:")
    frozen_pnls = {}; frozen_pnldd = {}
    for arm in ["G-A1", "G-A2", "G-SPLIT", "G-FAT"]:
        fr = [r for r in all_results if r["arm"]==arm and r.get("window")=="Frozen"]
        if fr:
            tpnl = sum(r["total_pnl"] for r in fr)
            dds = sorted([r["max_dd"] for r in fr])
            n = len(dds)
            dd_med = (dds[n//2-1]+dds[n//2])/2 if n%2==0 and n>1 else dds[n//2]
            frozen_pnls[arm] = tpnl
            frozen_pnldd[arm] = tpnl / dd_med if dd_med > 0 else 0

    p1 = "CORRECT" if frozen_pnls.get("G-FAT",0) > frozen_pnls.get("G-A1",0) else "WRONG"
    print(f"  1. G-FAT wins frozen PnL: {p1} (G-FAT=${frozen_pnls.get('G-FAT',0):.0f} vs G-A1=${frozen_pnls.get('G-A1',0):.0f})")

    p2 = "CORRECT" if frozen_pnldd.get("G-FAT",0) > frozen_pnldd.get("G-A1",0) else "WRONG"
    print(f"  2. G-FAT wins frozen PnL/%DD: {p2} (G-FAT=${frozen_pnldd.get('G-FAT',0):.0f} vs G-A1=${frozen_pnldd.get('G-A1',0):.0f})")

    between = (frozen_pnls.get("G-A1",0) < frozen_pnls.get("G-SPLIT",0) < frozen_pnls.get("G-FAT",0))
    print(f"  3. G-SPLIT between G-A1 and G-FAT on PnL: {'CORRECT' if between else 'WRONG'}")

    # Save
    save = [{k:v for k,v in r.items()} for r in all_results]
    out = OUTPUT_DIR / "final-grid-decision-results.json"
    with open(out, "w") as f:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(),
                   "spec": "Final Grid Decision Spec v1.0", "results": save}, f, indent=2, default=str)
    print(f"\nResults saved: {out}")
    print("=" * 130)


if __name__ == "__main__":
    main()
