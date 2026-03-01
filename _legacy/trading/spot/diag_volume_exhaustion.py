"""Diagnostic: Test volume exhaustion scorer on ETH Nov 2021 and Dec 2024 tops."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd
import numpy as np
from trading.spot.ta_top_scorer import TATopScorer
from trading.regime_detector import classify_regime_v2
from trading.indicators import compute_all as compute_all_indicators

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'data', 'dwell_cache')


def load_and_resample(path):
    """Load 1h CSV and resample to daily."""
    df = pd.read_csv(path)
    df['dt'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df = df.set_index('dt')
    daily = df.resample('1D').agg({
        'timestamp': 'first', 'open': 'first', 'high': 'max',
        'low': 'min', 'close': 'last', 'volume': 'sum',
    }).dropna(subset=['timestamp']).reset_index(drop=True)
    return daily


def find_date_index(df, target_date_str):
    dates = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    target = pd.Timestamp(target_date_str, tz='UTC')
    diffs = (dates - target).abs()
    return int(diffs.idxmin())


def score_window(df, center_idx, window, label):
    print(f"\n{'='*80}")
    print(f"  {label}")
    print(f"{'='*80}")

    df_ind = compute_all_indicators(df.copy())
    regimes = classify_regime_v2(df_ind, "1h")
    scorer = TATopScorer(rsi_period=14, swing_lookback=5, min_lookback=30)

    start = max(30, center_idx - window)
    end = min(len(df_ind), center_idx + window + 1)
    results = []

    for i in range(start, end):
        regime = regimes.iloc[i] if i < len(regimes) else "UNKNOWN"
        result = scorer.score(df_ind, i, regime, 50, regimes)
        price = float(df_ind.iloc[i]['close'])
        dt = pd.Timestamp(int(df_ind.iloc[i]['timestamp']), unit='ms', tz='UTC').strftime('%Y-%m-%d')
        marker = " <<<TOP" if i == center_idx else ""

        results.append({
            'date': dt, 'price': price, 'idx': i,
            'total': result.score,
            'rsi': result.rsi_divergence_score,
            'vol_exh': result.volume_exhaustion_score,
            'wick': result.upper_wick_rejection_score,
            'mom': result.momentum_stall_score,
            'marker': marker,
        })

        print(f"  {dt}  ${price:>8,.0f}  "
              f"TOTAL={result.score:5.1f}  "
              f"RSI={result.rsi_divergence_score:5.1f}  "
              f"VOL_EXH={result.volume_exhaustion_score:5.1f}  "
              f"WICK={result.upper_wick_rejection_score:5.1f}  "
              f"MOM={result.momentum_stall_score:5.1f}"
              f"{marker}")

    # Summary
    top_r = [r for r in results if r['marker']]
    if top_r:
        r = top_r[0]
        print(f"\n  >>> AT TOP: Total={r['total']:.1f}  "
              f"(RSI={r['rsi']:.1f} + VolExh={r['vol_exh']:.1f} + Wick={r['wick']:.1f} + Mom={r['mom']:.1f})")
    max_vol_exh = max(r['vol_exh'] for r in results) if results else 0
    print(f"  >>> Peak volume exhaustion in window: {max_vol_exh:.1f}")
    return results


def main():
    print("Volume Exhaustion Diagnostic — ETH Tops")
    print("=" * 80)

    # Nov 2021 top
    path_2021 = os.path.join(CACHE_DIR, 'ETH_USDT_1h_2021-10-01_2022-01-29.csv')
    # Dec 2024 top — use file spanning that period
    path_2024 = os.path.join(CACHE_DIR, 'ETH_USDT_1h_2024-09-10_2025-01-16.csv')

    all_results = {}

    if os.path.exists(path_2021):
        df_2021 = load_and_resample(path_2021)
        print(f"Loaded Nov 2021 data: {len(df_2021)} daily bars")
        idx = find_date_index(df_2021, '2021-11-10')
        all_results['ETH Nov 2021 Top ($4,878 ATH)'] = score_window(
            df_2021, idx, 10, "ETH Nov 2021 Top ($4,878 ATH)")
    else:
        print(f"Missing: {path_2021}")

    if os.path.exists(path_2024):
        df_2024 = load_and_resample(path_2024)
        print(f"\nLoaded Dec 2024 data: {len(df_2024)} daily bars")
        idx = find_date_index(df_2024, '2024-12-06')
        all_results['ETH Dec 2024 Top (~$4,100)'] = score_window(
            df_2024, idx, 10, "ETH Dec 2024 Top (~$4,100)")
    else:
        print(f"Missing: {path_2024}")

    # Write report
    report_dir = os.path.join(os.path.dirname(__file__), 'backtest_results', 'v12_lifecycle')
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, 'volume_exhaustion_diagnostic.md')

    with open(report_path, 'w') as f:
        f.write("# Volume Exhaustion Diagnostic Report\n\n")
        f.write("**Component:** `_score_volume_exhaustion()` replacing dead `_score_volume_divergence()`\n\n")
        f.write("**Problem:** Old volume divergence scored 0 at every ETH top because blow-off tops\n")
        f.write("have STRONG volume, not divergent volume.\n\n")
        f.write("**New approach:** Detect volume exhaustion patterns:\n")
        f.write("1. Volume climax (>3x avg spike near highs)\n")
        f.write("2. Spike fade (elevated >2x for 5+ bars, then drops below 1.5x)\n")
        f.write("3. Sustained elevation near highs (distribution signature)\n\n")

        for label, results in all_results.items():
            f.write(f"## {label}\n\n")
            f.write("| Date | Price | Total | RSI | VolExh | Wick | Mom |\n")
            f.write("|------|-------|-------|-----|--------|------|-----|\n")
            for r in results:
                mark = " **TOP**" if r['marker'] else ""
                f.write(f"| {r['date']}{mark} | ${r['price']:,.0f} | {r['total']:.1f} | "
                       f"{r['rsi']:.1f} | {r['vol_exh']:.1f} | {r['wick']:.1f} | {r['mom']:.1f} |\n")

            top_r = [r for r in results if r['marker']]
            if top_r:
                r = top_r[0]
                f.write(f"\n**At top:** Total={r['total']:.1f} "
                       f"(RSI={r['rsi']:.1f} + VolExh={r['vol_exh']:.1f} + Wick={r['wick']:.1f} + Mom={r['mom']:.1f})\n\n")

            max_ve = max(r['vol_exh'] for r in results) if results else 0
            f.write(f"**Peak volume exhaustion in window:** {max_ve:.1f}\n\n")

        f.write("## Summary\n\n")
        f.write("Old `_score_volume_divergence` scored **0** at all tops (25% of capacity wasted).\n\n")
        for label, results in all_results.items():
            top_r = [r for r in results if r['marker']]
            if top_r:
                f.write(f"- **{label}:** VolExh = {top_r[0]['vol_exh']:.1f}/25 pts\n")
        f.write("\n### ATH Proximity Bonus (added to DailyScorerConductor)\n\n")
        f.write("- Within 10% of ATH: +10 pts\n")
        f.write("- Within 15% of ATH: +5 pts\n")
        f.write("- ETH $4,878 ATH -> Nov 2021 top at $4,878 = +10 pts, Dec 2024 at ~$4,100 (16% below) = +0 pts\n")

    print(f"\n\nReport written to: {report_path}")


if __name__ == "__main__":
    main()
