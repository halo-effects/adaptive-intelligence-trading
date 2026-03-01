"""Extract monthly ETH prices from cached data for chart."""
import pandas as pd
from pathlib import Path

cache = Path(__file__).parent / "data" / "dwell_cache"
all_data = []

for f in sorted(cache.glob("ETH_USDT_15m_*")):
    df = pd.read_csv(f)
    all_data.append(df)

if not all_data:
    print("No ETH data found")
    exit()

combined = pd.concat(all_data).drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
combined["date"] = pd.to_datetime(combined["timestamp"], unit="ms")

# Monthly OHLC summary
monthly = combined.set_index("date").resample("ME").agg({
    "open": "first", "high": "max", "low": "min", "close": "last"
})

# Key dates for Wyckoff phases
print("=== ETH Monthly Prices ===")
for idx, row in monthly.iterrows():
    print(f"{idx.strftime('%Y-%m')}: O={row['open']:.0f} H={row['high']:.0f} L={row['low']:.0f} C={row['close']:.0f}")

# Key Wyckoff markers
print("\n=== Key Price Points ===")
print(f"2022-06 start: ${combined.iloc[0]['close']:.0f}")

# Find approximate highs and lows
for year in [2022, 2023, 2024, 2025]:
    yr_data = combined[combined["date"].dt.year == year]
    if yr_data.empty:
        continue
    high_idx = yr_data["high"].idxmax()
    low_idx = yr_data["low"].idxmin()
    high_date = yr_data.loc[high_idx, "date"]
    low_date = yr_data.loc[low_idx, "date"]
    print(f"{year} High: ${yr_data.loc[high_idx, 'high']:.0f} ({high_date.strftime('%Y-%m-%d')})")
    print(f"{year} Low:  ${yr_data.loc[low_idx, 'low']:.0f} ({low_date.strftime('%Y-%m-%d')})")
