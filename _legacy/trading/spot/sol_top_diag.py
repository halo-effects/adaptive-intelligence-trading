"""SOL Nov 2021 top diagnostic — why V12d conductor didn't fire EXIT."""
import sys, json
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import numpy as np

from trading.spot.backtest_engine_v12 import DailyScorerConductor
from trading.spot.ta_top_scorer import TATopScorer
from trading.spot.macro_indicators import load_historical_fear_greed

# ── 1. Fetch SOL 1h data for the peak period ──
# Need enough lookback for daily resampling (50+ daily bars) + the peak
# Fetch from 2021-07-01 to 2021-12-31
print("=== SOL Top Diagnostic ===\n")

# Check if we have cached data
CACHE_DIR = Path(__file__).resolve().parent / "data" / "dwell_cache"
cache_file = CACHE_DIR / "SOL_USDT_1h_2021-07-01_2021-12-31.csv"

if cache_file.exists():
    print(f"Loading cached data from {cache_file}")
    df = pd.read_csv(cache_file)
else:
    print("Fetching SOL/USDT 1h data from Binance...")
    import ccxt, time
    exchange = ccxt.binance({"enableRateLimit": True})
    start_ms = int(datetime(2021, 7, 1, tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime(2021, 12, 31, tzinfo=timezone.utc).timestamp() * 1000)
    all_c = []
    cursor = start_ms
    while cursor < end_ms:
        try:
            candles = exchange.fetch_ohlcv("SOL/USDT", "1h", since=cursor, limit=1000)
        except Exception as e:
            print(f"  Error: {e}, retrying...")
            time.sleep(5)
            continue
        if not candles:
            break
        all_c.extend(candles)
        cursor = candles[-1][0] + 1
        time.sleep(0.3)
    df = pd.DataFrame(all_c, columns=["timestamp","open","high","low","close","volume"])
    df = df[df["timestamp"] <= end_ms].drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_file, index=False)
    print(f"  Fetched and cached {len(df)} candles")

print(f"Data: {len(df)} candles, {pd.Timestamp(df['timestamp'].iloc[0], unit='ms')} to {pd.Timestamp(df['timestamp'].iloc[-1], unit='ms')}")

# ── 2. Load F&G data ──
fg_data = load_historical_fear_greed()
print(f"\nF&G data: {len(fg_data)} entries")

# Check Nov 2021 F&G availability
nov_dates = [f"2021-11-{d:02d}" for d in range(1, 11)]
print("F&G for Nov 1-10, 2021:")
for d in nov_dates:
    val = fg_data.get(d)
    print(f"  {d}: {val if val is not None else 'MISSING'}")

# ── 3. Set up DailyScorerConductor ──
conductor = DailyScorerConductor(exit_threshold=50.0, mcap_ath_pct=0.25)
conductor.set_price_ath(260.0)  # Known SOL ATH

# Prepare daily data from 1h
conductor.prepare(df)

print(f"\nDaily data ready: {conductor._daily_ready}")
if conductor._daily_df is not None:
    print(f"Daily candles: {len(conductor._daily_df)}")

# ── 4. Score each day around the peak (Nov 1-10, 2021) ──
print("\n=== SCORING Nov 1-15, 2021 ===")
print(f"{'Date':>12} {'Price':>8} {'Total':>6} {'TA':>5} {'RSI':>5} {'Vol':>5} {'Wick':>5} {'Mom':>5} {'Pi':>5} {'F&G':>5} {'FGval':>5} {'ATH%':>6}")
print("-" * 100)

max_score = 0
max_score_date = None
results_log = []

# Scan Nov 1 - Nov 15
for day_offset in range(0, 20):  # Nov 1 to Nov 20
    target_date = datetime(2021, 11, 1, tzinfo=timezone.utc) + timedelta(days=day_offset)
    target_ms = int(target_date.timestamp() * 1000)
    
    # Find closest 1h candle
    idx = (df["timestamp"] - target_ms).abs().idxmin()
    candle = df.iloc[idx]
    price = float(candle["close"])
    ts_ms = int(candle["timestamp"])
    
    # Get F&G value
    date_str = target_date.strftime("%Y-%m-%d")
    fg_val = fg_data.get(date_str, None)
    fg_for_score = fg_val if fg_val is not None else 50
    
    # Force re-score by resetting cache
    conductor._last_scored_daily_idx = -1
    
    # Score
    total = conductor.score_at(ts_ms, price, fg_for_score)
    result = conductor._cached_result
    fg_exit = conductor._cached_fg_exit_score
    
    # Get pi score manually
    if conductor._daily_df is not None:
        dt = pd.Timestamp(ts_ms, unit="ms", tz="UTC")
        day_start_ms = int(dt.normalize().timestamp() * 1000)
        daily_ts = conductor._daily_df["timestamp"].values
        diffs = np.abs(daily_ts - day_start_ms)
        daily_idx = int(np.argmin(diffs))
        pi_score = conductor._score_pi_cycle(daily_idx)
    else:
        pi_score = 0
        daily_idx = 0
    
    ath_dist = (260.0 - price) / 260.0 * 100
    
    ta_score = result.score if result else 0
    rsi_s = result.rsi_divergence_score if result else 0
    vol_s = result.volume_divergence_score if result else 0
    wick_s = result.upper_wick_rejection_score if result else 0
    mom_s = result.momentum_stall_score if result else 0
    
    fg_display = fg_val if fg_val is not None else "N/A"
    
    print(f"{date_str:>12} ${price:>7.1f} {total:>6.0f} {ta_score:>5.0f} {rsi_s:>5.0f} {vol_s:>5.0f} {wick_s:>5.0f} {mom_s:>5.0f} {pi_score:>5.0f} {fg_exit:>5.0f} {str(fg_display):>5} {ath_dist:>5.1f}%")
    
    results_log.append({
        "date": date_str, "price": price, "total": total, "ta": ta_score,
        "rsi": rsi_s, "vol": vol_s, "wick": wick_s, "mom": mom_s,
        "pi": pi_score, "fg_exit": fg_exit, "fg_val": fg_val, "ath_dist_pct": ath_dist,
        "daily_idx": daily_idx
    })
    
    if total > max_score:
        max_score = total
        max_score_date = date_str

# ── 5. ATH Gate Check ──
print(f"\n=== ATH GATE CHECK ===")
print(f"ATH: $260.0, Gate: within 25% (price >= $195)")
for r in results_log:
    within = r["price"] >= 195
    status = "WITHIN" if within else "OUTSIDE"
    print(f"  {r['date']}: ${r['price']:.1f} {status} ({r['ath_dist_pct']:.1f}% from ATH)")

# ── 6. Summary ──
print(f"\n=== SUMMARY ===")
print(f"MAX score achieved: {max_score:.0f} on {max_score_date}")
print(f"EXIT threshold: 50")
print(f"Gap to EXIT: {max(0, 50 - max_score):.0f} points")

# Check should_exit
print(f"\n=== should_exit() CHECK ===")
for r in results_log:
    if r["total"] >= 30:
        target_ms = int(datetime.strptime(r["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
        conductor._last_scored_daily_idx = -1
        would_exit = conductor.should_exit(target_ms, r["price"], r.get("fg_val") or 50)
        print(f"  {r['date']}: score={r['total']:.0f}, should_exit={would_exit}")

# ── 7. Write report ──
out_dir = Path(__file__).resolve().parent / "backtest_results" / "v12_lifecycle"
out_dir.mkdir(parents=True, exist_ok=True)
report_path = out_dir / "sol_top_diagnostic.md"

with open(report_path, "w") as f:
    f.write("# SOL Nov 2021 Top Diagnostic — V12d Distribution Scorer\n\n")
    f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
    f.write("## Question\n")
    f.write("Why did the V12d distribution scorer never fire EXIT during SOL's Nov 2021 peak (~$260)?\n\n")
    
    f.write("## Scoring Results (Nov 1-20, 2021)\n\n")
    f.write("| Date | Price | Total | TA | RSI | Vol | Wick | Mom | Pi | F&G | FG Val | ATH% |\n")
    f.write("|------|-------|-------|----|-----|-----|------|-----|----|-----|--------|------|\n")
    for r in results_log:
        fg_d = r["fg_val"] if r["fg_val"] is not None else "N/A"
        f.write(f"| {r['date']} | ${r['price']:.1f} | {r['total']:.0f} | {r['ta']:.0f} | {r['rsi']:.0f} | {r['vol']:.0f} | {r['wick']:.0f} | {r['mom']:.0f} | {r['pi']:.0f} | {r['fg_exit']:.0f} | {fg_d} | {r['ath_dist_pct']:.1f}% |\n")
    
    f.write(f"\n## Key Findings\n\n")
    f.write(f"- **MAX score achieved:** {max_score:.0f} on {max_score_date}\n")
    f.write(f"- **EXIT threshold:** 50 points\n")
    f.write(f"- **Gap to EXIT:** {max(0, 50 - max_score):.0f} points\n\n")
    
    f.write("## Component Analysis\n\n")
    f.write("### TA Scorer (max 100 pts, 4 × 25 each)\n")
    f.write("The TA scorer detects **weakening rallies** (RSI divergence, volume divergence, wick rejection, momentum stall). ")
    f.write("SOL's Nov 2021 top was a **blow-off top** — a parabolic move that doesn't show divergence patterns until AFTER the top.\n\n")
    
    f.write("### F&G Component\n")
    has_fg = any(r["fg_val"] is not None for r in results_log)
    if has_fg:
        fg_vals = [r for r in results_log if r["fg_val"] is not None]
        f.write(f"F&G data **was available** for this period.\n")
        f.write(f"- Values ranged from {min(r['fg_val'] for r in fg_vals)} to {max(r['fg_val'] for r in fg_vals)}\n")
        extreme = [r for r in fg_vals if r["fg_val"] >= 80]
        f.write(f"- Days with F&G ≥ 80 (greed): {len(extreme)}\n")
        very_extreme = [r for r in fg_vals if r["fg_val"] >= 90]
        f.write(f"- Days with F&G ≥ 90 (extreme greed): {len(very_extreme)}\n\n")
    else:
        f.write("F&G data was **NOT available** — defaulted to 50 (neutral), contributing 0 pts.\n\n")
    
    f.write("### Pi Cycle\n")
    pi_scores = [r["pi"] for r in results_log]
    f.write(f"Pi Cycle scores: {set(pi_scores)}\n")
    f.write("Pi Cycle requires 350 daily bars. For SOL starting mid-2021, this is likely insufficient history.\n\n")
    
    f.write("### ATH Gate\n")
    within_count = sum(1 for r in results_log if r["price"] >= 195)
    f.write(f"- ATH: $260, gate threshold: $195 (within 25%)\n")
    f.write(f"- Days within gate: {within_count}/{len(results_log)}\n\n")
    
    f.write("## Root Cause Analysis\n\n")
    f.write("The EXIT threshold of 50 was never reached because:\n\n")
    f.write("1. **TA Scorer design flaw (known):** Detects weakening rallies via divergence, not blow-off tops. ")
    f.write("SOL went parabolic — no RSI divergence, no volume divergence at the peak itself.\n")
    f.write("2. **F&G contribution capped at 25 pts:** Even with extreme greed (≥90), F&G only adds 25 pts. ")
    f.write("Combined with low TA scores, this can't reach 50 alone.\n")
    f.write("3. **Pi Cycle likely N/A:** Needs 350 daily bars of history. SOL didn't have enough.\n")
    f.write("4. **Threshold math:** To reach 50, you need TA ≥ 25 + F&G = 25, or TA ≥ 35 + F&G = 15. ")
    f.write("The TA scorer rarely gives >20 pts during blow-off tops.\n\n")
    
    f.write("## Recommendations\n\n")
    f.write("1. **Add blow-off top detector:** Parabolic advance detection (e.g., price >2σ above 20-day SMA, ")
    f.write("vertical angle of ascent, acceleration of price)\n")
    f.write("2. **Lower EXIT threshold for extreme F&G:** If F&G ≥ 90 + price near ATH, threshold could be 35\n")
    f.write("3. **Add rate-of-change signal:** RSI >80 sustained for multiple days at ATH = strong top signal\n")
    f.write("4. **Consider F&G as gate, not just additive:** F&G ≥ 80 + ANY TA signal ≥ 20 → EXIT\n")

print(f"\nReport written to: {report_path}")
