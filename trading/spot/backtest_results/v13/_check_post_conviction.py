"""Check price action after conviction triggers - did we flip long too early?"""
import sqlite3
import pandas as pd
from datetime import datetime

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
conn = sqlite3.connect(DB)

triggers = [
    ("ETH", "2025-06-22", 2111.89),
    ("SOL", "2026-02-11", None),
    ("LINK", "2026-02-05", None),
]

for coin, tdate, tprice in triggers:
    sym = f"{coin}/USDT"
    td = datetime.strptime(tdate, "%Y-%m-%d")
    td_ms = int(td.timestamp() * 1000)
    
    df = pd.read_sql_query(
        "SELECT timestamp, close FROM candles_daily WHERE symbol=? AND timestamp>=? ORDER BY timestamp LIMIT 30",
        conn, params=[sym, td_ms]
    )
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    
    if len(df) == 0:
        print(f"{coin}: No data after {tdate}")
        continue
    
    entry_price = tprice if tprice else df["close"].iloc[0]
    print(f"\n{coin} - Conviction fired {tdate} @ ${entry_price:.2f}")
    print(f"  {'Date':12} {'Price':>10} {'From Entry':>10}")
    print(f"  {'-'*35}")
    
    for _, row in df.iterrows():
        p = row["close"]
        pct = (p / entry_price - 1) * 100
        print(f"  {row['date'].strftime('%Y-%m-%d'):12} ${p:>9.2f} {pct:+8.1f}%")
    
    # Max drawdown from entry
    prices = df["close"].values
    min_after = prices.min()
    max_dd = (min_after / entry_price - 1) * 100
    current = prices[-1]
    current_pct = (current / entry_price - 1) * 100
    print(f"  Max drawdown from entry: {max_dd:+.1f}%")
    print(f"  Current: {current_pct:+.1f}%")

conn.close()
