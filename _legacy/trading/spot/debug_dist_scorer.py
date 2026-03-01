"""Debug: what distribution scores does the scorer produce on ETH 2024 data?"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
from trading.spot.distribution_scorer import DistributionScorer, DistributionPhase
from trading.spot.macro_indicators import load_historical_fear_greed
from trading.regime_detector import classify_regime_v2

fg = load_historical_fear_greed()
print(f"F&G entries: {len(fg)}")

# Load ETH chunk 6 (Jan-May 2024, includes the $4K top)
cache = Path(__file__).parent / "data" / "dwell_cache"
df = pd.read_csv(cache / "ETH_USDT_15m_2024-01-14_2024-05-21.csv")
print(f"Candles: {len(df)}")

regimes = classify_regime_v2(df, "15m")

scorer = DistributionScorer()
max_score = 0
max_result = None
max_i = 0

# Sample every 96 candles (1 day)
for i in range(100, len(df), 96):
    ts = df.iloc[i]["timestamp"]
    from datetime import datetime, timezone
    dt = datetime.fromtimestamp(ts/1000, tz=timezone.utc)
    date_str = dt.strftime("%Y-%m-%d")
    fg_val = fg.get(date_str)
    regime = regimes.iloc[i] if i < len(regimes) else "UNKNOWN"

    result = scorer.score(df, i, regime, fg_val, regimes)

    if result.score > 0 or fg_val and fg_val > 60:
        print(f"{date_str}: score={result.score:.0f} phase={result.phase.value} "
              f"fg={fg_val} regime={regime} "
              f"[fg_s={result.fg_sustained_score:.0f} pi={result.pi_cycle_score:.0f} "
              f"dist={result.distribution_regime_score:.0f} vol={result.volume_divergence_score:.0f} "
              f"wlh={result.weekly_lower_highs_score:.0f}]")

    if result.score > max_score:
        max_score = result.score
        max_result = result
        max_i = i

print(f"\nMax score: {max_score:.0f} at candle {max_i}")
if max_result:
    print(f"  Phase: {max_result.phase.value}")
    print(f"  Components: fg={max_result.fg_sustained_score:.0f} pi={max_result.pi_cycle_score:.0f} "
          f"dist={max_result.distribution_regime_score:.0f} vol={max_result.volume_divergence_score:.0f} "
          f"wlh={max_result.weekly_lower_highs_score:.0f}")
