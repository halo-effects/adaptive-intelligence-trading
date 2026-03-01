#!/usr/bin/env python3
"""Multi-Timeframe Top Scorer Diagnostic.

Tests the TA top scorer on 1h, 4h, daily, and weekly timeframes
around known ETH tops to find which signals fire and when.

Uses 1h data resampled to higher timeframes.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timezone
from trading.spot.ta_top_scorer import TATopScorer
from trading.indicators import compute_all as compute_all_indicators
from trading.regime_detector import classify_regime_v2


CACHE_DIR = Path(__file__).parent / "data" / "dwell_cache"

# Known ETH tops to test against
KNOWN_TOPS = {
    "Mar 2024": {"date": "2024-03-12", "price": 4093, "ath_pct": 0.16},  # 16% below $4,878 ATH
    "Dec 2024": {"date": "2024-12-16", "price": 4087, "ath_pct": 0.16},
}


def load_1h_data() -> pd.DataFrame:
    """Load and concatenate all 1h ETH data."""
    files = sorted(CACHE_DIR.glob("ETH_USDT_1h_*.csv"))
    dfs = []
    for f in files:
        df = pd.read_csv(f)
        dfs.append(df)
    
    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    print(f"Loaded {len(combined)} 1h candles")
    
    # Convert timestamp to datetime for resampling
    combined["dt"] = pd.to_datetime(combined["timestamp"], unit="ms", utc=True)
    return combined


def resample_ohlcv(df_1h: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample 1h OHLCV to higher timeframe."""
    df = df_1h.set_index("dt")
    
    resampled = df.resample(rule).agg({
        "timestamp": "first",
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna(subset=["timestamp"]).reset_index(drop=True)
    
    # Restore dt column
    resampled["dt"] = pd.to_datetime(resampled["timestamp"], unit="ms", utc=True)
    return resampled


def run_scorer_on_timeframe(df: pd.DataFrame, tf_label: str, top_name: str, top_info: dict):
    """Run TA scorer on a specific timeframe and report scores around a known top."""
    # Compute indicators
    df_ind = compute_all_indicators(df.copy())
    regimes = classify_regime_v2(df_ind, "1h")  # regime detector uses same logic
    
    scorer = TATopScorer()
    
    # Find the candle closest to the known top date
    top_ts = pd.Timestamp(top_info["date"], tz="UTC")
    df_ind["dt"] = pd.to_datetime(df_ind["timestamp"], unit="ms", utc=True)
    
    # Find closest index
    time_diffs = abs(df_ind["dt"] - top_ts)
    top_idx = time_diffs.idxmin()
    top_price = float(df_ind.iloc[top_idx]["close"])
    
    print(f"\n{'='*70}")
    print(f"  {tf_label} | {top_name} top (expected ~${top_info['price']})")
    print(f"  Closest candle: idx={top_idx}, price=${top_price:.0f}, ts={df_ind.iloc[top_idx]['dt']}")
    print(f"{'='*70}")
    
    # Determine window around top based on timeframe
    if "1h" in tf_label:
        window = 72  # 3 days before/after
    elif "4h" in tf_label:
        window = 36  # 6 days before/after  
    elif "1d" in tf_label or "daily" in tf_label.lower():
        window = 30  # 30 days before/after
    elif "1w" in tf_label or "weekly" in tf_label.lower():
        window = 12  # 12 weeks before/after
    else:
        window = 30
    
    start_idx = max(100, top_idx - window)
    end_idx = min(len(df_ind) - 1, top_idx + window)
    
    # Track max scores and when they fire
    max_score = 0
    max_score_idx = 0
    max_score_price = 0
    exit_candles = []
    
    print(f"\n  {'idx':>5} {'date':>16} {'price':>8} {'score':>6} {'phase':>10} {'RSI':>5} {'Vol':>5} {'Wick':>5} {'Mom':>5} {'regime':>12}")
    print(f"  {'-'*5} {'-'*16} {'-'*8} {'-'*6} {'-'*10} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*12}")
    
    for i in range(start_idx, end_idx + 1):
        price = float(df_ind.iloc[i]["close"])
        regime = regimes.iloc[i] if i < len(regimes) else "UNKNOWN"
        result = scorer.score(df_ind, i, regime, 0, regimes)
        
        dt = df_ind.iloc[i]["dt"]
        dt_str = dt.strftime("%Y-%m-%d %H:%M") if "1h" in tf_label or "4h" in tf_label else dt.strftime("%Y-%m-%d")
        
        # Always show if score >= 15, near top, or is the top itself
        is_top = (i == top_idx)
        is_high_score = (result.score >= 15)
        is_near_top = abs(i - top_idx) <= (window // 4)
        
        if is_top or is_high_score or (is_near_top and i % max(1, window // 10) == 0):
            marker = " <<<< TOP" if is_top else ""
            print(f"  {i:>5} {dt_str:>16} ${price:>7.0f} {result.score:>5.0f}  {result.phase.value:>10} "
                  f"{result.rsi_divergence_score:>5.1f} {result.volume_divergence_score:>5.1f} "
                  f"{result.upper_wick_rejection_score:>5.1f} {result.momentum_stall_score:>5.1f} "
                  f"{regime:>12}{marker}")
        
        if result.score > max_score:
            max_score = result.score
            max_score_idx = i
            max_score_price = price
        
        if result.phase.value == "EXIT":
            exit_candles.append((i, dt_str, price, result.score))
    
    # Summary
    print(f"\n  MAX SCORE: {max_score:.0f} at idx={max_score_idx} (${max_score_price:.0f})")
    if max_score_idx != top_idx:
        candle_diff = max_score_idx - top_idx
        direction = "AFTER" if candle_diff > 0 else "BEFORE"
        print(f"  Offset from top: {abs(candle_diff)} candles {direction}")
    
    if exit_candles:
        print(f"  EXIT signals fired: {len(exit_candles)}")
        for idx, dt, p, s in exit_candles[:5]:
            offset = idx - top_idx
            direction = "after" if offset > 0 else "before"
            print(f"    {dt} ${p:.0f} score={s:.0f} ({abs(offset)} candles {direction} top)")
    else:
        print(f"  EXIT signals: NONE (threshold=50)")
    
    return {
        "timeframe": tf_label,
        "top": top_name,
        "max_score": max_score,
        "max_score_candles_from_top": max_score_idx - top_idx,
        "exit_count": len(exit_candles),
        "first_exit_offset": exit_candles[0][0] - top_idx if exit_candles else None,
    }


def main():
    df_1h = load_1h_data()
    
    # Build all timeframes
    print("\nResampling to 4h...")
    df_4h = resample_ohlcv(df_1h, "4h")
    print(f"  {len(df_4h)} candles")
    
    print("Resampling to daily...")
    df_1d = resample_ohlcv(df_1h, "1D")
    print(f"  {len(df_1d)} candles")
    
    print("Resampling to weekly...")
    df_1w = resample_ohlcv(df_1h, "1W")
    print(f"  {len(df_1w)} candles")
    
    timeframes = [
        ("1h", df_1h),
        ("4h", df_4h),
        ("daily", df_1d),
        ("weekly", df_1w),
    ]
    
    all_results = []
    
    for top_name, top_info in KNOWN_TOPS.items():
        print(f"\n\n{'#'*70}")
        print(f"  KNOWN TOP: {top_name} — ${top_info['price']} on {top_info['date']}")
        print(f"{'#'*70}")
        
        for tf_label, df_tf in timeframes:
            try:
                result = run_scorer_on_timeframe(df_tf, tf_label, top_name, top_info)
                all_results.append(result)
            except Exception as e:
                print(f"\n  ERROR on {tf_label}: {e}")
                import traceback
                traceback.print_exc()
    
    # Final comparison table
    print(f"\n\n{'='*70}")
    print(f"  MULTI-TIMEFRAME COMPARISON")
    print(f"{'='*70}")
    print(f"  {'Top':>10} {'TF':>8} {'Max Score':>10} {'Offset':>10} {'EXIT?':>6}")
    print(f"  {'-'*10} {'-'*8} {'-'*10} {'-'*10} {'-'*6}")
    
    for r in all_results:
        offset_str = f"{r['max_score_candles_from_top']:+d}" if r['max_score_candles_from_top'] else "0"
        exit_str = f"Yes({r['exit_count']})" if r['exit_count'] > 0 else "No"
        print(f"  {r['top']:>10} {r['timeframe']:>8} {r['max_score']:>10.0f} {offset_str:>10} {exit_str:>6}")


if __name__ == "__main__":
    main()
