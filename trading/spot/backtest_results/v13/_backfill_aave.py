"""Backfill AAVE daily candles from 1h data, plus check BTC/other coin readiness."""
import sys, os, sqlite3
import pandas as pd
import numpy as np

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'

def backfill_daily_from_1h(symbol_1h, symbol_daily=None):
    """Build daily candles from 1h data and insert into candles_daily."""
    if symbol_daily is None:
        symbol_daily = symbol_1h
    
    db = sqlite3.connect(DB)
    
    # Load 1h candles
    df = pd.read_sql(
        "SELECT timestamp, open, high, low, close, volume FROM candles WHERE symbol=? AND timeframe='1h' ORDER BY timestamp",
        db, params=[symbol_1h]
    )
    print(f"{symbol_1h}: {len(df)} 1h candles")
    if len(df) == 0:
        db.close()
        return
    
    df['dt'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('dt').sort_index()
    
    # Resample to daily
    daily = df.resample('1D').agg({
        'timestamp': 'first',
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    print(f"  -> {len(daily)} daily candles ({daily.index[0].date()} to {daily.index[-1].date()})")
    
    # Check existing
    existing = pd.read_sql(
        "SELECT COUNT(*) as cnt FROM candles_daily WHERE symbol=?",
        db, params=[symbol_daily]
    ).iloc[0]['cnt']
    print(f"  Existing daily rows for {symbol_daily}: {existing}")
    
    # Insert (replace existing)
    if existing > 0:
        db.execute("DELETE FROM candles_daily WHERE symbol=?", (symbol_daily,))
        print(f"  Deleted {existing} existing rows")
    
    rows = []
    for dt, row in daily.iterrows():
        rows.append((
            symbol_daily,
            int(row['timestamp']),
            float(row['open']),
            float(row['high']),
            float(row['low']),
            float(row['close']),
            float(row['volume'])
        ))
    
    db.executemany(
        "INSERT INTO candles_daily (symbol, timestamp, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
        rows
    )
    db.commit()
    
    # Verify
    final = db.execute("SELECT COUNT(*) FROM candles_daily WHERE symbol=?", (symbol_daily,)).fetchone()[0]
    print(f"  Final: {final} daily rows for {symbol_daily}")
    db.close()

# Backfill AAVE
backfill_daily_from_1h('AAVE/USDT')

# Check all candidate coins
print("\n" + "=" * 60)
print("COIN DATA READINESS CHECK")
print("=" * 60)
db = sqlite3.connect(DB)
candidates = ['BTC', 'ETH', 'SOL', 'LINK', 'XRP', 'HBAR', 'AAVE', 'ADA', 'BNB', 'AVAX', 'DOT', 'UNI', 'NEAR', 'LTC', 'ATOM', 'MKR', 'MATIC']
for coin in candidates:
    best_daily = 0
    best_sym = ''
    for q in ['USDC', 'USDT']:
        sym = f'{coin}/{q}'
        cnt = db.execute("SELECT COUNT(*) FROM candles_daily WHERE symbol=?", (sym,)).fetchone()[0]
        h1 = db.execute("SELECT COUNT(*) FROM candles WHERE symbol=? AND timeframe='1h'", (sym,)).fetchone()[0]
        if cnt > best_daily:
            best_daily = cnt
            best_sym = sym
        if cnt > 0 or h1 > 0:
            pass  # just tracking
    
    # Get best
    all_syms = []
    for q in ['USDC', 'USDT']:
        sym = f'{coin}/{q}'
        cnt = db.execute("SELECT COUNT(*) FROM candles_daily WHERE symbol=?", (sym,)).fetchone()[0]
        h1 = db.execute("SELECT COUNT(*) FROM candles WHERE symbol=? AND timeframe='1h'", (sym,)).fetchone()[0]
        if cnt > 0 or h1 > 0:
            all_syms.append(f"{sym}: {cnt}d/{h1}h")
    
    sma200_ok = best_daily >= 600
    sma3d_ok = best_daily >= 200  # 3D resample + SMA200 needs ~600 3D candles = 1800 days, but 200 3D = 600 days
    status = "OK" if best_daily >= 600 else "NEED BACKFILL" if best_daily < 600 else "?"
    print(f"  {coin:<6} best={best_daily:>5}d  3D_SMA200={'Y' if best_daily >= 600 else 'N'}  {' | '.join(all_syms)}")

db.close()
