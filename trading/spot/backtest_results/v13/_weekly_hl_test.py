"""
Weekly Higher Low candle close as bottom confirmation gate.
Test: after conviction score hits 3/4 + 3D DX, wait for weekly HL close.

HL = current week's low > previous week's low (higher low formed).
Also test: HL close = current week's close > previous week's close.

Check timing vs actual bottoms and vs 2W K>=5.
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
conn = sqlite3.connect(DB)

coins = ["ETH/USDT", "SOL/USDT", "LINK/USDT", "XRP/USDT", "BTC/USDT"]

# Known bottom dates (significant, from earlier analysis)
bottoms = {
    "ETH": [("2025-04-09", 1385.05), ("2025-06-22", 2111.89), ("2025-11-21", 2623.57)],
    "SOL": [("2025-04-07", 95.26), ("2025-12-18", 116.88)],
    "LINK": [("2025-04-07", 10.10), ("2025-10-10", 7.90)],
    "XRP": [("2025-04-07", 1.61), ("2025-12-19", 1.77)],
    "BTC": [("2025-04-07", 74508), ("2025-11-21", 80600)],
}

print("WEEKLY HIGHER-LOW CONFIRMATION GATE TEST")
print("=" * 75)
print("How long after true bottom does a weekly HL form?")
print("HL = week low > prev week low AND week close > prev week close")
print()

for sym in coins:
    base = sym.split("/")[0]
    df = pd.read_sql_query(
        "SELECT timestamp, open, high, low, close FROM candles_daily WHERE symbol=? ORDER BY timestamp",
        conn, params=[sym]
    )
    df["dt"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("dt").sort_index()
    
    # Resample to weekly
    weekly = df.resample("W").agg({
        "open": "first", "high": "max", "low": "min", "close": "last"
    }).dropna()
    
    weekly["prev_low"] = weekly["low"].shift(1)
    weekly["prev_close"] = weekly["close"].shift(1)
    weekly["hl_low"] = weekly["low"] > weekly["prev_low"]  # Higher low
    weekly["hl_close"] = weekly["close"] > weekly["prev_close"]  # Higher close
    weekly["hl_both"] = weekly["hl_low"] & weekly["hl_close"]  # Both
    
    print(f"\n{'='*75}")
    print(f"  {base}")
    print(f"{'='*75}")
    
    if base not in bottoms:
        continue
    
    for bdate_s, bprice in bottoms[base]:
        bdate = datetime.strptime(bdate_s, "%Y-%m-%d")
        
        # Find first weekly HL after bottom
        after = weekly[weekly.index >= bdate]
        
        for label, col in [("HL (low only)", "hl_low"), ("HL (low+close)", "hl_both")]:
            matches = after[after[col]]
            if len(matches) > 0:
                first = matches.index[0]
                days = (first - bdate).days
                price_at_hl = matches.iloc[0]["close"]
                pct_missed = (price_at_hl / bprice - 1) * 100
                print(f"  {bdate_s} ${bprice:>10.2f} -> {label:20} {first.strftime('%Y-%m-%d')} ({days:3d}d, {pct_missed:+.1f}%)")
            else:
                print(f"  {bdate_s} ${bprice:>10.2f} -> {label:20} NOT YET")
    
    # Show recent weekly candles
    print(f"\n  Recent weekly candles:")
    print(f"  {'Week':12} {'Open':>10} {'High':>10} {'Low':>10} {'Close':>10} {'HL_low':>6} {'HL_cls':>6}")
    print(f"  {'-'*68}")
    for _, row in weekly.tail(8).iterrows():
        hl_l = "Y" if row["hl_low"] else ""
        hl_c = "Y" if row["hl_close"] else ""
        print(f"  {_.strftime('%Y-%m-%d'):12} ${row['open']:>9.2f} ${row['high']:>9.2f} ${row['low']:>9.2f} ${row['close']:>9.2f} {hl_l:>6} {hl_c:>6}")

conn.close()
