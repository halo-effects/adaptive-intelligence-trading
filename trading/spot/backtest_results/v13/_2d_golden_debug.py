"""Debug: check 2D SMA state for ETH/BTC/SOL — did they ever have a death cross to cross back from?"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import sqlite3, pandas as pd, numpy as np

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'

for coin in ['ETH/USDT', 'BTC/USDT', 'SOL/USDT', 'LINK/USDT', 'XRP/USDT']:
    conn = sqlite3.connect(DB)
    df = pd.read_sql("SELECT timestamp, close FROM candles_daily WHERE symbol=? ORDER BY timestamp", conn, params=[coin])
    conn.close()
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('date').sort_index()
    
    # Resample to 2D
    df2 = df.resample('2D').agg({'close': 'last'}).dropna()
    df2['sma50'] = df2['close'].rolling(50).mean()
    df2['sma200'] = df2['close'].rolling(200).mean()
    valid = df2.dropna(subset=['sma50', 'sma200'])
    
    name = coin.split('/')[0]
    print(f"\n{name}: {len(df2)} 2D candles, SMA200 valid from {valid.index[0].strftime('%Y-%m-%d') if len(valid) else 'N/A'}")
    
    if len(valid):
        # Check state at ETF era start
        etf = valid[valid.index >= '2023-01-01']
        if len(etf):
            first = etf.iloc[0]
            state = "GOLDEN" if first['sma50'] > first['sma200'] else "DEATH"
            print(f"  State at ETF era start: {state} (SMA50={first['sma50']:.2f}, SMA200={first['sma200']:.2f})")
            
            # Count crosses in ETF era
            above = etf['sma50'] > etf['sma200']
            crosses = (above != above.shift(1)) & above.notna() & above.shift(1).notna()
            gc = crosses & above  # golden crosses
            dc = crosses & ~above  # death crosses
            print(f"  ETF era: {gc.sum()} golden crosses, {dc.sum()} death crosses")
            
            # Show all cross dates
            for d in etf[gc].index:
                print(f"    GC: {d.strftime('%Y-%m-%d')}")
            for d in etf[dc].index:
                print(f"    DC: {d.strftime('%Y-%m-%d')}")
