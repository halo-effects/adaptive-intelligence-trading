"""Check what floor BTC would have triggered at."""
import sqlite3, pandas as pd

conn = sqlite3.connect("C:/Users/Never/.openclaw/workspace/trading/spot/data/candles.db")
start_ts = int(pd.Timestamp("2024-10-01").timestamp() * 1000)
end_ts = int(pd.Timestamp("2025-03-01").timestamp() * 1000)
df = pd.read_sql_query(
    "SELECT timestamp, low, close FROM candles WHERE symbol='BTC/USDC' AND timestamp>=? AND timestamp<=? ORDER BY timestamp",
    conn, params=(start_ts, end_ts))
df["low"] = pd.to_numeric(df["low"])
df["close"] = pd.to_numeric(df["close"])

exit_entry = 62906.0
low_price = df["low"].min()
low_idx = df["low"].idxmin()
low_date = pd.Timestamp(int(df.loc[low_idx, "timestamp"]), unit="ms")
max_discount = (exit_entry - low_price) / exit_entry * 100

print(f"EXIT entry price: ${exit_entry:,.0f}")
print(f"Lowest price in window: ${low_price:,.0f} on {low_date}")
print(f"Maximum discount from exit: {max_discount:.1f}%")
print()
print("Floor thresholds:")
for floor in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
    trigger_price = exit_entry * (1 - floor / 100)
    triggered = low_price <= trigger_price
    print(f"  {floor:>2}% floor = ${trigger_price:>9,.0f} -> {'YES' if triggered else 'NO'}")
conn.close()
