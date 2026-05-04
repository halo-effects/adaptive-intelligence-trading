"""Backtest trailing stop configs against actual candle data."""
import sqlite3, json, sys
import numpy as np

sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")
DB_PATH = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
conn = sqlite3.connect(DB_PATH)

# Check schema
cols = conn.execute("PRAGMA table_info(candles)").fetchall()
print("candles columns:", [c[1] for c in cols])

# Check what coins exist
coins_avail = conn.execute(
    "SELECT DISTINCT symbol, COUNT(*) as cnt FROM candles GROUP BY symbol ORDER BY cnt DESC"
).fetchall()
print(f"\nCoins in DB: {len(coins_avail)}")
target_coins = ["TAO/USDT", "ZEC/USDT", "FET/USDT", "JTO/USDT", "HYPE/USDT"]
for sym, cnt in coins_avail:
    if any(t.replace("/USDT","") in sym for t in target_coins):
        print(f"  {sym}: {cnt:,} candles")

# Also show first few to understand format
sample = conn.execute("SELECT * FROM candles LIMIT 3").fetchall()
print(f"\nSample row: {sample[0]}")
