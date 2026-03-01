"""Debug 2W StochRSI for BTC around Nov 2021 ATH."""
import sys, pandas as pd, numpy as np
sys.path.insert(0, '.')
from v13_signals import V13SignalPack, load_daily, _stoch_rsi, resample_nweek

from pathlib import Path
DB = str(Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db')

daily = load_daily('BTC', DB)
sym = daily.attrs.get('symbol', '?')
print(f"Loaded: {sym}, {len(daily)} rows, {daily.index[0]} to {daily.index[-1]}")

# Check raw closes around BTC ATH
print("\nBTC daily closes Oct-Dec 2021 (sampled):")
mask = (daily.index >= '2021-10-01') & (daily.index <= '2021-12-15')
subset = daily[mask]
for i, (idx, row) in enumerate(subset.iterrows()):
    if i % 7 == 0:  # weekly samples
        print(f"  {idx.strftime('%Y-%m-%d')}: close={row['close']:.0f}")

# 2W resampled
resampled = resample_nweek(daily['close'], 2)
print(f"\n2W resampled periods: {len(resampled)}")
mask2 = (resampled.index >= '2021-08-01') & (resampled.index <= '2022-02-01')
print("\n2W closes Aug 2021 - Jan 2022:")
for idx, val in resampled[mask2].items():
    print(f"  {idx.strftime('%Y-%m-%d')}: {val:.0f}")

# StochRSI
k, d, rsi = _stoch_rsi(resampled)
print("\n2W StochRSI K values (full history through 2022):")
mask3 = (k.index >= '2021-01-01') & (k.index <= '2022-03-01')
for idx, val in k[mask3].items():
    rsi_val = rsi.loc[idx] if idx in rsi.index else float('nan')
    close_val = resampled.loc[idx] if idx in resampled.index else float('nan')
    flag = " <<<" if val > 90 else ""
    print(f"  {idx.strftime('%Y-%m-%d')}: K={val:6.1f}  RSI={rsi_val:5.1f}  close={close_val:.0f}{flag}")

# Count how many valid K values total
valid = k.dropna()
print(f"\nTotal K values: {len(k)}, valid: {len(valid)}, first valid: {valid.index[0].strftime('%Y-%m-%d')}")

# Check: what's the max K ever?
print(f"Max K ever: {k.max():.1f} on {k.idxmax().strftime('%Y-%m-%d')}")
