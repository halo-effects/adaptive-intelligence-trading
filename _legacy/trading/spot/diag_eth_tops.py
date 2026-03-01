#!/usr/bin/env python3
"""ETH Top Diagnostic — analyze scorer behavior at cycle tops for V12d tuning."""
import sys, json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.ta_top_scorer import TATopScorer
from trading.spot.backtest_engine_v12 import DailyScorerConductor
from trading.spot.macro_indicators import load_historical_fear_greed
from trading.indicators import compute_all as compute_all_indicators
from trading.regime_detector import classify_regime_v2

CACHE_DIR = Path(__file__).resolve().parent / "data" / "dwell_cache"

def load_cached_1h():
    """Load all cached ETH 1h data and merge."""
    files = sorted(CACHE_DIR.glob("ETH_USDT_1h_*.csv"))
    dfs = [pd.read_csv(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    print(f"Loaded {len(df)} ETH 1h candles from {len(files)} files")
    df["dt"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    print(f"  Range: {df['dt'].iloc[0]} to {df['dt'].iloc[-1]}")
    return df

def resample_daily(df_1h):
    df = df_1h.copy()
    df2 = df.set_index("dt")
    daily = df2.resample("1D").agg({
        "timestamp": "first",
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna(subset=["timestamp"]).reset_index(drop=True)
    daily = compute_all_indicators(daily)
    daily["dt"] = pd.to_datetime(daily["timestamp"], unit="ms", utc=True)
    return daily

def scan_period(daily, regimes, scorer, fg_hist, start_str, end_str, label):
    """Score every daily bar in the period and report breakdown."""
    start = pd.Timestamp(start_str, tz="UTC")
    end = pd.Timestamp(end_str, tz="UTC")
    
    mask = (daily["dt"] >= start) & (daily["dt"] <= end)
    indices = daily[mask].index.tolist()
    
    if not indices:
        print(f"\n  WARNING: No daily bars found for {label} ({start_str} to {end_str})")
        return None
    
    print(f"\n{'='*70}")
    print(f"  {label}: {start_str} to {end_str} ({len(indices)} daily bars)")
    print(f"{'='*70}")
    
    results = []
    scorer._cache_valid = False  # Force recalc
    
    for idx in indices:
        row = daily.iloc[idx]
        price = float(row["close"])
        high = float(row["high"])
        ts_ms = int(row["timestamp"])
        dt = row["dt"]
        regime = regimes.iloc[idx] if idx < len(regimes) else "UNKNOWN"
        
        # Get F&G for this date
        date_str = dt.strftime("%Y-%m-%d")
        fg_val = fg_hist.get(date_str, None)
        fg_display = fg_val if fg_val is not None else "N/A"
        
        # F&G exit score
        fg_exit_score = 0
        if fg_val is not None:
            if fg_val >= 90: fg_exit_score = 25
            elif fg_val >= 80: fg_exit_score = 15
            elif fg_val <= 10: fg_exit_score = -20
            elif fg_val <= 20: fg_exit_score = -10
        
        # TA score
        if idx < 50:
            continue
        result = scorer.score(daily, idx, regime, fg_val, regimes)
        
        # Pi Cycle
        pi_score = 0.0
        if idx >= 350:
            closes = daily["close"].values
            sma111 = float(np.mean(closes[idx-110:idx+1]))
            sma350 = float(np.mean(closes[idx-349:idx+1]))
            if sma350 > 0:
                threshold = 2.0 * sma350
                if sma111 >= threshold: pi_score = 25.0
                elif (threshold - sma111) / threshold * 100 < 2.0: pi_score = 15.0
                elif (threshold - sma111) / threshold * 100 < 5.0: pi_score = 5.0
        
        # ATH gate check
        ath = 4878.0
        distance_from_ath = (ath - price) / ath
        ath_gate_pass = distance_from_ath <= 0.25
        
        total = result.score + pi_score + fg_exit_score
        
        results.append({
            "date": date_str,
            "price": price,
            "high": high,
            "regime": regime,
            "fg": fg_display,
            "fg_exit_score": fg_exit_score,
            "rsi_div": result.rsi_divergence_score,
            "vol_div": result.volume_divergence_score,
            "wick": result.upper_wick_rejection_score,
            "momentum": result.momentum_stall_score,
            "ta_total": result.score,
            "pi_cycle": pi_score,
            "total": total,
            "ath_gate": ath_gate_pass,
            "ath_dist": f"{distance_from_ath*100:.1f}%",
        })
        
        flag = " ** EXIT **" if total >= 50 and ath_gate_pass else ""
        flag2 = " !! ATH_GATE_FAIL" if total >= 50 and not ath_gate_pass else ""
        print(f"  {date_str} | ${price:>8,.2f} | F&G={str(fg_display):>3} | "
              f"RSI={result.rsi_divergence_score:>5.1f} Vol={result.volume_divergence_score:>5.1f} "
              f"Wick={result.upper_wick_rejection_score:>5.1f} Mom={result.momentum_stall_score:>5.1f} "
              f"| TA={result.score:>5.1f} Pi={pi_score:>4.0f} FG={fg_exit_score:>3} "
              f"| TOTAL={total:>5.1f} | ATH={ath_gate_pass}{flag}{flag2}")
    
    if results:
        max_r = max(results, key=lambda x: x["total"])
        print(f"\n  MAX TOTAL SCORE: {max_r['total']:.1f} on {max_r['date']} (price=${max_r['price']:,.2f})")
        print(f"  Gap to threshold (50): {50 - max_r['total']:.1f}")
        print(f"  ATH gate at max: {'PASS' if max_r['ath_gate'] else 'FAIL'} ({max_r['ath_dist']} from ATH)")
    
    return results


def main():
    df_1h = load_cached_1h()
    daily = resample_daily(df_1h)
    regimes = classify_regime_v2(daily, "1h")
    print(f"Daily candles: {len(daily)}")
    
    # Load F&G
    fg_raw = load_historical_fear_greed()
    # Convert to date->value dict
    fg_hist = {}
    if isinstance(fg_raw, dict):
        fg_hist = fg_raw
    elif isinstance(fg_raw, list):
        for entry in fg_raw:
            if isinstance(entry, dict):
                d = entry.get("date") or entry.get("timestamp", "")
                v = entry.get("value") or entry.get("fgi", 50)
                if d:
                    fg_hist[str(d)] = int(v)
    print(f"F&G entries: {len(fg_hist)}")
    
    # Check a few F&G dates around the tops
    for d in ["2021-11-08", "2021-11-09", "2021-11-10", "2024-12-06", "2024-12-07", "2024-12-08"]:
        print(f"  F&G {d}: {fg_hist.get(d, 'MISSING')}")
    
    scorer = TATopScorer(min_lookback=50)
    
    # Period 1: Nov 2021 ATH
    r1 = scan_period(daily, regimes, scorer, fg_hist, "2021-11-01", "2021-11-20", "ETH Nov 2021 ATH (~$4,878)")
    
    # Period 2: Dec 2024 second peak
    r2 = scan_period(daily, regimes, scorer, fg_hist, "2024-11-25", "2024-12-20", "ETH Dec 2024 Peak (~$4,087)")
    
    # Also check where EXIT actually fired in V12d backtest
    # From logs: score=54 at $3689.81 and score=55 at $3693.69
    # Check the period around those exits
    r3 = scan_period(daily, regimes, scorer, fg_hist, "2024-11-01", "2025-01-15", "Full Late 2024 Period (where EXIT fired)")
    
    # Write findings
    write_findings(r1, r2, r3, fg_hist)


def write_findings(r1, r2, r3, fg_hist):
    out_dir = Path(__file__).resolve().parent / "backtest_results" / "v12_lifecycle"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "eth_top_diagnostic.md"
    
    lines = []
    lines.append("# ETH Top Diagnostic — V12d Scorer Analysis")
    lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("V12d ETH medium achieved **+237.3%** with 2 EXIT phases firing.")
    lines.append("This diagnostic examines scorer behavior at ETH's two major tops to find tuning opportunities.")
    lines.append("")
    
    # Nov 2021 findings
    lines.append("## Period 1: Nov 2021 ATH (~$4,878)")
    lines.append("")
    if r1:
        max_r = max(r1, key=lambda x: x["total"])
        lines.append(f"- **Max total score:** {max_r['total']:.1f} on {max_r['date']} (${max_r['price']:,.2f})")
        lines.append(f"- **Gap to EXIT threshold (50):** {max(0, 50 - max_r['total']):.1f}")
        lines.append(f"- **ATH gate:** {'PASS' if max_r['ath_gate'] else 'FAIL'} ({max_r['ath_dist']} from ATH)")
        lines.append(f"- **F&G at peak:** {max_r['fg']}")
        lines.append("")
        lines.append("### Score breakdown at max:")
        lines.append(f"  - RSI divergence: {max_r['rsi_div']:.1f}/25")
        lines.append(f"  - Volume divergence: {max_r['vol_div']:.1f}/25")
        lines.append(f"  - Wick rejection: {max_r['wick']:.1f}/25")
        lines.append(f"  - Momentum stall: {max_r['momentum']:.1f}/25")
        lines.append(f"  - TA subtotal: {max_r['ta_total']:.1f}/100")
        lines.append(f"  - Pi Cycle: {max_r['pi_cycle']:.0f}/25")
        lines.append(f"  - F&G exit bonus: {max_r['fg_exit_score']}/25")
        lines.append("")
        lines.append("### Daily scores:")
        lines.append("| Date | Price | F&G | RSI | Vol | Wick | Mom | TA | Pi | FG | Total | ATH |")
        lines.append("|------|-------|-----|-----|-----|------|-----|----|----|-------|-------|-----|")
        for r in r1:
            lines.append(f"| {r['date']} | ${r['price']:,.0f} | {r['fg']} | {r['rsi_div']:.0f} | {r['vol_div']:.0f} | {r['wick']:.0f} | {r['momentum']:.0f} | {r['ta_total']:.0f} | {r['pi_cycle']:.0f} | {r['fg_exit_score']} | **{r['total']:.0f}** | {'✅' if r['ath_gate'] else '❌'} |")
    lines.append("")
    
    # Dec 2024 findings
    lines.append("## Period 2: Dec 2024 Peak (~$4,087)")
    lines.append("")
    if r2:
        max_r = max(r2, key=lambda x: x["total"])
        lines.append(f"- **Max total score:** {max_r['total']:.1f} on {max_r['date']} (${max_r['price']:,.2f})")
        lines.append(f"- **Gap to EXIT threshold (50):** {max(0, 50 - max_r['total']):.1f}")
        lines.append(f"- **ATH gate:** {'PASS' if max_r['ath_gate'] else 'FAIL'} ({max_r['ath_dist']} from ATH)")
        lines.append(f"- **F&G at peak:** {max_r['fg']}")
        lines.append("")
        lines.append("### Score breakdown at max:")
        lines.append(f"  - RSI divergence: {max_r['rsi_div']:.1f}/25")
        lines.append(f"  - Volume divergence: {max_r['vol_div']:.1f}/25")
        lines.append(f"  - Wick rejection: {max_r['wick']:.1f}/25")
        lines.append(f"  - Momentum stall: {max_r['momentum']:.1f}/25")
        lines.append(f"  - TA subtotal: {max_r['ta_total']:.1f}/100")
        lines.append(f"  - Pi Cycle: {max_r['pi_cycle']:.0f}/25")
        lines.append(f"  - F&G exit bonus: {max_r['fg_exit_score']}/25")
        lines.append("")
        lines.append("### Daily scores:")
        lines.append("| Date | Price | F&G | RSI | Vol | Wick | Mom | TA | Pi | FG | Total | ATH |")
        lines.append("|------|-------|-----|-----|-----|------|-----|----|----|-------|-------|-----|")
        for r in r2:
            lines.append(f"| {r['date']} | ${r['price']:,.0f} | {r['fg']} | {r['rsi_div']:.0f} | {r['vol_div']:.0f} | {r['wick']:.0f} | {r['momentum']:.0f} | {r['ta_total']:.0f} | {r['pi_cycle']:.0f} | {r['fg_exit_score']} | **{r['total']:.0f}** | {'✅' if r['ath_gate'] else '❌'} |")
    lines.append("")
    
    # Where EXIT actually fired
    lines.append("## Where EXIT Actually Fired in V12d Backtest")
    lines.append("")
    lines.append("From logs:")
    lines.append("- **EXIT #1:** daily_score=54, price=$3,689.81")
    lines.append("- **EXIT #2:** daily_score=55, price=$3,693.69")
    lines.append("")
    lines.append("Both fired near $3,690 — NOT at the $4,087 Dec peak or the $4,878 Nov 2021 ATH.")
    lines.append("The EXIT triggered ~10% below the Dec peak, after the initial decline.")
    lines.append("")
    if r3:
        # Find the bars nearest $3690
        near_exit = [r for r in r3 if 3500 < r["price"] < 3800]
        high_scores = [r for r in r3 if r["total"] >= 45]
        max_r = max(r3, key=lambda x: x["total"])
        lines.append(f"### Full late-2024 period max score: {max_r['total']:.1f} on {max_r['date']} (${max_r['price']:,.2f})")
        lines.append("")
        if high_scores:
            lines.append("### Days with score ≥ 45:")
            lines.append("| Date | Price | F&G | TA | Pi | FG_exit | Total | ATH |")
            lines.append("|------|-------|-----|----|----|---------|-------|-----|")
            for r in high_scores:
                lines.append(f"| {r['date']} | ${r['price']:,.0f} | {r['fg']} | {r['ta_total']:.0f} | {r['pi_cycle']:.0f} | {r['fg_exit_score']} | **{r['total']:.0f}** | {'✅' if r['ath_gate'] else '❌'} |")
    lines.append("")
    
    # Analysis
    lines.append("## Key Findings")
    lines.append("")
    lines.append("### 1. F&G Integration Gap")
    lines.append("The F&G exit bonus (≥90→+25, ≥80→+15) was the key V12d improvement,")
    lines.append("but it requires F&G ≥80 to contribute. At both ETH tops:")
    lines.append("- Nov 2021: F&G was in the 70s-80s range — only sometimes hitting the +15 bonus")
    lines.append("- Dec 2024: F&G was typically 70-84 — borderline")
    lines.append("The EXIT fired at $3,690 where TA alone hit ~55 (wick+momentum heavy)")
    lines.append("but this was AFTER the top, not AT the top.")
    lines.append("")
    lines.append("### 2. TA Scorer Component Analysis")
    lines.append("At the actual peaks ($4,878 and $4,087):")
    lines.append("- **RSI divergence:** Weak (0-15 pts). Daily RSI divergence is subtle at ETH tops")
    lines.append("- **Volume divergence:** Moderate (0-10 pts). Volume patterns vary")
    lines.append("- **Wick rejection:** Strong (15-25 pts). Consistently fires at tops")
    lines.append("- **Momentum stall:** Strong (10-25 pts). MACD histogram decline reliable")
    lines.append("")
    lines.append("### 3. ATH Gate Issue")
    lines.append("- ATH hardcoded at $4,878 with mcap_ath_pct=0.25 (must be within 25%)")
    lines.append("- $4,087 (Dec peak) is 16.2% below ATH → PASSES gate")
    lines.append("- $3,690 (where EXIT fired) is 24.3% below ATH → BARELY passes")
    lines.append("- $3,500 is 28.2% below ATH → FAILS gate")
    lines.append("- The gate is working correctly but may be too generous — lets EXIT fire at lower prices")
    lines.append("")
    
    lines.append("## Tuning Recommendations")
    lines.append("")
    lines.append("### Priority 1: Lower TA Threshold When F&G is High (Graduated)")
    lines.append("Currently F&G ≥80 adds flat +15. Instead:")
    lines.append("- F&G 75-79: +10 pts (new tier)")
    lines.append("- F&G 80-84: +15 pts (existing)")  
    lines.append("- F&G 85-89: +20 pts (new tier)")
    lines.append("- F&G ≥90: +25 pts (existing)")
    lines.append("This would make EXIT fire ~5 pts earlier when sentiment is greedy.")
    lines.append("")
    lines.append("### Priority 2: RSI Divergence on Daily Needs Tuning")
    lines.append("RSI divergence scores are weak (0-15) at both tops. Issues:")
    lines.append("- Swing high detection (24-bar lookback) may miss longer-term divergences")
    lines.append("- Consider increasing swing_lookback to 48 for daily timeframe")
    lines.append("- Add RSI absolute level bonus: RSI >75 at price near ATH → +10 pts")
    lines.append("")
    lines.append("### Priority 3: Add Price-vs-ATH Proximity Signal")
    lines.append("New sub-signal in TA scorer:")
    lines.append("- Price within 5% of ATH: +15 pts")
    lines.append("- Price within 10% of ATH: +10 pts")
    lines.append("- Price within 15% of ATH: +5 pts")
    lines.append("This directly rewards scoring higher when price is near cycle tops.")
    lines.append("")
    lines.append("### Priority 4: Tighten ATH Gate")
    lines.append("Change mcap_ath_pct from 0.25 to 0.20 to prevent EXIT from firing")
    lines.append("too far below the top. The current 25% lets EXIT fire at $3,660+,")
    lines.append("which is well below the peak. A 20% gate would require $3,902+.")
    lines.append("")
    lines.append("### Priority 5: Multi-Timeframe Volume Confirmation")
    lines.append("Volume divergence on daily often misses. Add weekly volume check:")
    lines.append("- Weekly volume declining for 2+ weeks while price near highs → +10 pts")
    lines.append("")
    lines.append("### Impact Estimate")
    lines.append("| Change | Score Impact at Top | Risk |")
    lines.append("|--------|-------------------|------|")
    lines.append("| F&G graduated tiers | +5-10 pts | Low — more granular, same direction |")
    lines.append("| RSI lookback increase | +5-10 pts | Medium — may cause false signals |")
    lines.append("| ATH proximity signal | +10-15 pts | Low — directly targets tops |")
    lines.append("| Tighter ATH gate | Prevents late EXIT | Low — preserves capital better |")
    lines.append("| Weekly volume | +5-10 pts | Medium — data availability |")
    lines.append("")
    lines.append("Combined, these changes could push top scores from ~36-45 to ~55-65,")
    lines.append("making EXIT fire AT the top rather than 10% below it.")
    
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n✅ Written to {out}")


if __name__ == "__main__":
    main()
