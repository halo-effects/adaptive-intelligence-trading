"""Check 3D death cross for ETH - why is it never True?"""
import sys, os, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd, numpy as np

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'
db = sqlite3.connect(DB)
df = pd.read_sql("SELECT timestamp, close FROM candles_daily WHERE symbol='ETH/USDT' ORDER BY timestamp", db)
db.close()
df['dt'] = pd.to_datetime(df['timestamp'], unit='ms')
df = df.set_index('dt').sort_index()
df = df[~df.index.duplicated(keep='last')]
print(f"ETH daily: {len(df)} rows, {df.index[0]} to {df.index[-1]}")

# 3D resampling
d3 = df['close'].resample('3D').last().dropna()
s50 = d3.rolling(50).mean()
s200 = d3.rolling(200).mean()
in_dx = s50 < s200

print(f"\n3D candles: {len(d3)}, SMA200 valid from: {s200.first_valid_index()}")
print(f"Any death cross True? {in_dx.any()}")

# Show periods where death cross is True
dx_periods = in_dx[in_dx == True]
if len(dx_periods):
    print(f"\n3D Death cross periods ({len(dx_periods)} candles):")
    for dt in dx_periods.index[:20]:
        print(f"  {dt.strftime('%Y-%m-%d')} SMA50={s50.loc[dt]:.2f} SMA200={s200.loc[dt]:.2f}")
else:
    # Show SMA50 vs SMA200 gap around Jun 2025
    print("\nSMA50 vs SMA200 around Jun 2025:")
    for dt in d3.index:
        if pd.Timestamp('2025-04-01') <= dt <= pd.Timestamp('2025-08-01'):
            if not pd.isna(s50.loc[dt]) and not pd.isna(s200.loc[dt]):
                gap = (s50.loc[dt] - s200.loc[dt]) / s200.loc[dt] * 100
                print(f"  {dt.strftime('%Y-%m-%d')} SMA50=${s50.loc[dt]:,.0f} SMA200=${s200.loc[dt]:,.0f} gap={gap:+.1f}%")
