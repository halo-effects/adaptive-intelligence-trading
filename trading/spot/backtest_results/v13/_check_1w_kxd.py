"""Check 1W StochRSI K/D around ETH Jun 2025 conviction date."""
import sqlite3
import pandas as pd
import numpy as np

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"

conn = sqlite3.connect(DB)
df = pd.read_sql_query(
    "SELECT timestamp, close FROM candles_daily WHERE symbol='ETH/USDT' ORDER BY timestamp", conn)
conn.close()
df['dt'] = pd.to_datetime(df['timestamp'], unit='ms')
df = df.set_index('dt').sort_index()

for tf_label, tf_rule in [('1W', 'W'), ('2W', '2W')]:
    w = df['close'].resample(tf_rule).last().dropna()
    
    # RSI(14)
    delta = w.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    # StochRSI(3,3,14,14)
    rsi_low = rsi.rolling(14).min()
    rsi_high = rsi.rolling(14).max()
    stoch = ((rsi - rsi_low) / (rsi_high - rsi_low).replace(0, np.nan)) * 100
    k = stoch.rolling(3).mean()
    d = k.rolling(3).mean()
    
    # Show around Jun 2025
    mask = (k.index >= '2025-04-01') & (k.index <= '2025-08-01')
    print(f"\nETH {tf_label} StochRSI around Jun 2025:")
    print(f"  {'Date':12} {'Close':>10} {'K':>8} {'D':>8} {'K>D':>5}")
    print(f"  {'-'*45}")
    for dt in k.index[mask]:
        kv = k.loc[dt]
        dv = d.loc[dt]
        cross = 'YES' if kv > dv else 'no'
        print(f"  {dt.strftime('%Y-%m-%d'):12} ${w.loc[dt]:>9.2f} {kv:>8.1f} {dv:>8.1f} {cross:>5}")

    # Show current
    print(f"\n  Current (last 5):")
    for dt in k.index[-5:]:
        kv = k.loc[dt]
        dv = d.loc[dt]
        cross = 'YES' if kv > dv else 'no'
        print(f"  {dt.strftime('%Y-%m-%d'):12} ${w.loc[dt]:>9.2f} {kv:>8.1f} {dv:>8.1f} {cross:>5}")
