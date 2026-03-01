import sqlite3, pandas as pd
conn = sqlite3.connect("C:/Users/Never/.openclaw/workspace/trading/spot/data/candles.db")
df = pd.read_sql_query(
    "SELECT timestamp, close FROM candles WHERE symbol='BTC/USDC' AND timestamp >= 1728000000000 AND timestamp <= 1738368000000 ORDER BY timestamp",
    conn)
df["close"] = pd.to_numeric(df["close"])
df["date"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
daily = df.set_index("date").resample("1D")["close"].last().dropna()

print("BTC price action after Oct 10 2024 low ($58,946):")
print("Exit entry was $62,906")
print()
for dt, price in daily["2024-10-08":"2024-12-15"].items():
    marker = ""
    if dt.strftime("%Y-%m-%d") == "2024-10-10":
        marker = " <<<< LOW / Spring attempt"
    elif price > 100000:
        marker = " <<<< ABOVE $100K"
    print(f"  {dt.strftime('%Y-%m-%d')}: ${price:>9,.0f}{marker}")

low = 58946
peak = daily["2024-10-10":"2024-12-15"].max()
print(f"\nLow: ${low:,}")
print(f"Peak after: ${peak:,.0f}")
print(f"Rally: +{(peak - low) / low * 100:.0f}%")
conn.close()
