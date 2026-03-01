#!/usr/bin/env python3
"""Diagnostic: Run TA scorer on chunk 8 data to check scores near Dec 2024 peak."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import numpy as np
from trading.spot.ta_top_scorer import TATopScorer
from trading.indicators import compute_all as compute_all_indicators
from trading.regime_detector import classify_regime_v2

df = pd.read_csv('trading/spot/data/dwell_cache/ETH_USDT_1h_2024-09-10_2025-01-16.csv')
df = compute_all_indicators(df)
regimes = classify_regime_v2(df, '1h')
scorer = TATopScorer()

print(f"Data: {len(df)} candles, {df.iloc[0]['timestamp']} to {df.iloc[-1]['timestamp']}")
print(f"Price range: ${df['close'].min():.0f} - ${df['close'].max():.0f}")
print()

# Find the peak
peak_idx = df['close'].idxmax()
peak_price = df.iloc[peak_idx]['close']
peak_ts = df.iloc[peak_idx]['timestamp']
print(f"Peak: ${peak_price:.0f} at index {peak_idx}, ts={peak_ts}")
print()

# Check scores around peak and anywhere score >= 30
print(f"\n=== Scores around peak (index {peak_idx}) ===")
for i in range(max(100, peak_idx-50), min(len(df), peak_idx+50)):
    price = float(df.iloc[i]['close'])
    regime = regimes.iloc[i] if i < len(regimes) else 'UNKNOWN'
    result = scorer.score(df, i, regime, 0, regimes)
    ts = df.iloc[i]['timestamp']
    if isinstance(ts, (int, float)):
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(ts/1000, tz=timezone.utc)
        ts_str = dt.strftime('%Y-%m-%d %H:%M')
    else:
        ts_str = str(ts)
    # Show components
    comps = result.components if hasattr(result, 'components') else {}
    print(f"  i={i:>4} {ts_str} ${price:>7.0f} score={result.score:>3.0f} phase={result.phase.value:>10s} regime={regime:>12s} {comps}")

print("\n=== Scores >= 30 OR price > $3800 ===")
for i in range(100, len(df)):
    price = float(df.iloc[i]['close'])
    regime = regimes.iloc[i] if i < len(regimes) else 'UNKNOWN'
    result = scorer.score(df, i, regime, 0, regimes)
    if result.score >= 30 or price > 3800:
        ts = df.iloc[i]['timestamp']
        # Convert timestamp
        if isinstance(ts, (int, float)):
            from datetime import datetime, timezone
            dt = datetime.fromtimestamp(ts/1000, tz=timezone.utc)
            ts_str = dt.strftime('%Y-%m-%d %H:%M')
        else:
            ts_str = str(ts)
        print(f"  i={i:>4} {ts_str} ${price:>7.0f} score={result.score:>3.0f} phase={result.phase.value}")
