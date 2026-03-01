"""Backfill LINK and XRP 1h candles from Binance, then build daily candles.
Same approach as backfill_deep.py — get 1h candles then aggregate to daily.
"""
import sqlite3
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'candles.db'

def fetch_binance_klines(symbol, interval='1h', start_ms=None, end_ms=None, limit=1000):
    url = 'https://api.binance.com/api/v3/klines'
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    if start_ms: params['startTime'] = start_ms
    if end_ms: params['endTime'] = end_ms
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.json()

def backfill_1h(binance_symbol, db_symbol, start_date, end_date):
    """Fetch 1h candles from Binance and store in DB."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    start_ms = int(start_date.timestamp() * 1000)
    end_ms = int(end_date.timestamp() * 1000)
    
    total = 0
    current_ms = start_ms
    
    while current_ms < end_ms:
        try:
            data = fetch_binance_klines(binance_symbol, '1h', current_ms, end_ms)
        except Exception as e:
            print(f"  Error at {datetime.fromtimestamp(current_ms/1000)}: {e}")
            time.sleep(5)
            continue
        
        if not data:
            break
        
        for k in data:
            ts = k[0]
            c.execute("""INSERT OR REPLACE INTO candles 
                        (symbol, timeframe, timestamp, open, high, low, close, volume)
                        VALUES (?, '1h', ?, ?, ?, ?, ?, ?)""",
                     (db_symbol, ts, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])))
            total += 1
        
        current_ms = data[-1][0] + 1
        conn.commit()
        
        if len(data) < 1000:
            break
        time.sleep(0.1)
    
    conn.commit()
    conn.close()
    print(f"  {db_symbol}: {total} 1h candles stored")
    return total

def build_daily(symbol):
    """Aggregate 1h candles to daily."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get 1h candles
    rows = c.execute("""SELECT timestamp, open, high, low, close, volume 
                       FROM candles WHERE symbol=? AND timeframe='1h' ORDER BY timestamp""", (symbol,)).fetchall()
    
    if not rows:
        print(f"  No 1h candles for {symbol}")
        conn.close()
        return 0
    
    # Group by date
    from collections import defaultdict
    daily = defaultdict(list)
    for ts, o, h, l, cl, v in rows:
        day = datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d')
        daily[day].append((ts, o, h, l, cl, v))
    
    count = 0
    for day, candles in sorted(daily.items()):
        if len(candles) < 20:  # Skip incomplete days
            continue
        open_price = candles[0][1]
        high_price = max(c[2] for c in candles)
        low_price = min(c[3] for c in candles)
        close_price = candles[-1][4]
        volume = sum(c[5] for c in candles)
        
        c.execute("""INSERT OR REPLACE INTO candles_daily 
                    (symbol, date, open, high, low, close, volume, candle_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                 (symbol, day, open_price, high_price, low_price, close_price, volume, len(candles)))
        count += 1
    
    conn.commit()
    conn.close()
    print(f"  {symbol}: {count} daily candles built")
    return count

def compute_indicators(symbol):
    """Compute indicators for daily candles."""
    import pandas as pd
    import numpy as np
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM candles_daily WHERE symbol=? ORDER BY date", conn, params=(symbol,)
    )
    
    if df.empty:
        conn.close()
        return
    
    # SMAs
    df['sma20'] = df['close'].rolling(20).mean()
    df['sma50'] = df['close'].rolling(50).mean()
    df['sma200'] = df['close'].rolling(200).mean()
    
    # Bollinger Bands
    bb_std = df['close'].rolling(20).std()
    df['bb_width'] = (4 * bb_std / df['sma20'] * 100).where(df['sma20'] > 0)
    df['bb_pct'] = ((df['close'] - (df['sma20'] - 2*bb_std)) / (4*bb_std)).where(bb_std > 0)
    
    # ATR
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift()).abs(),
        (df['low'] - df['close'].shift()).abs()
    ], axis=1).max(axis=1)
    df['atr14'] = tr.rolling(14).mean()
    df['atr_pct'] = (df['atr14'] / df['close'] * 100)
    
    # ADX
    plus_dm = df['high'].diff()
    minus_dm = -df['low'].diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    atr_smooth = tr.ewm(alpha=1/14, min_periods=14).mean()
    df['plus_di'] = 100 * (plus_dm.ewm(alpha=1/14, min_periods=14).mean() / atr_smooth)
    df['minus_di'] = 100 * (minus_dm.ewm(alpha=1/14, min_periods=14).mean() / atr_smooth)
    dx = 100 * (df['plus_di'] - df['minus_di']).abs() / (df['plus_di'] + df['minus_di']).replace(0, np.nan)
    df['adx'] = dx.ewm(alpha=1/14, min_periods=14).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0.0).ewm(alpha=1/14, min_periods=14).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/14, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi14'] = 100 - (100 / (1 + rs))
    
    # Structure streaks
    hh = df['high'] > df['high'].shift(1)
    hl = df['low'] > df['low'].shift(1)
    lh = df['high'] < df['high'].shift(1)
    ll = df['low'] < df['low'].shift(1)
    
    hh_hl_streak = pd.Series(0, index=df.index, dtype=int)
    lh_ll_streak = pd.Series(0, index=df.index, dtype=int)
    for i in range(1, len(df)):
        if hh.iloc[i] and hl.iloc[i]:
            hh_hl_streak.iloc[i] = hh_hl_streak.iloc[i-1] + 1
        if lh.iloc[i] and ll.iloc[i]:
            lh_ll_streak.iloc[i] = lh_ll_streak.iloc[i-1] + 1
    df['consec_hh_hl'] = hh_hl_streak
    df['consec_lh_ll'] = lh_ll_streak
    
    # SMA slopes
    df['sma50_slope'] = df['sma50'].pct_change(5) * 100
    df['sma200_slope'] = df['sma200'].pct_change(20) * 100
    
    # Price vs SMAs
    df['price_vs_sma50'] = ((df['close'] - df['sma50']) / df['sma50'] * 100).where(df['sma50'] > 0)
    df['price_vs_sma200'] = ((df['close'] - df['sma200']) / df['sma200'] * 100).where(df['sma200'] > 0)
    
    # Update DB
    c = conn.cursor()
    for _, row in df.iterrows():
        c.execute("""UPDATE candles_daily SET 
                    sma20=?, sma50=?, sma200=?, bb_width=?, bb_pct=?,
                    atr14=?, atr_pct=?, adx=?, plus_di=?, minus_di=?,
                    rsi14=?, consec_hh_hl=?, consec_lh_ll=?,
                    sma50_slope=?, sma200_slope=?, price_vs_sma50=?, price_vs_sma200=?
                    WHERE symbol=? AND date=?""",
                 (row['sma20'], row['sma50'], row['sma200'], row['bb_width'], row['bb_pct'],
                  row['atr14'], row['atr_pct'], row['adx'], row['plus_di'], row['minus_di'],
                  row['rsi14'], row['consec_hh_hl'], row['consec_lh_ll'],
                  row['sma50_slope'], row['sma200_slope'], row['price_vs_sma50'], row['price_vs_sma200'],
                  symbol, row['date']))
    
    conn.commit()
    conn.close()
    print(f"  {symbol}: indicators computed for {len(df)} rows")


if __name__ == '__main__':
    # Start from Jan 2019 for warmup (same as BTC/ETH)
    start = datetime(2019, 1, 1)
    end = datetime(2026, 2, 27)
    
    pairs = [
        ('LINKUSDT', 'LINK/USDT'),
        ('LINKUSDC', 'LINK/USDC'),
        ('XRPUSDT', 'XRP/USDT'),
        ('XRPUSDC', 'XRP/USDC'),
    ]
    
    for binance_sym, db_sym in pairs:
        print(f"\nBackfilling {db_sym} from Binance...")
        try:
            backfill_1h(binance_sym, db_sym, start, end)
        except Exception as e:
            print(f"  FAILED: {e}")
    
    # Build daily candles
    for db_sym in ['LINK/USDT', 'LINK/USDC', 'XRP/USDT', 'XRP/USDC']:
        print(f"\nBuilding daily candles for {db_sym}...")
        build_daily(db_sym)
    
    # Merge USDT into USDC if USDC has less data (same as SOL approach)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    for coin in ['LINK', 'XRP']:
        usdc_count = c.execute("SELECT COUNT(*) FROM candles_daily WHERE symbol=?", (f"{coin}/USDC",)).fetchone()[0]
        usdt_count = c.execute("SELECT COUNT(*) FROM candles_daily WHERE symbol=?", (f"{coin}/USDT",)).fetchone()[0]
        print(f"\n{coin}: USDC={usdc_count}, USDT={usdt_count}")
        
        if usdt_count > usdc_count:
            # Copy USDT rows that don't exist in USDC
            c.execute(f"""INSERT OR IGNORE INTO candles_daily 
                        (symbol, date, open, high, low, close, volume, candle_count,
                         sma20, sma50, sma200, bb_width, bb_pct, atr14, atr_pct,
                         adx, plus_di, minus_di, rsi14, consec_hh_hl, consec_lh_ll,
                         sma50_slope, sma200_slope, price_vs_sma50, price_vs_sma200)
                        SELECT '{coin}/USDC', date, open, high, low, close, volume, candle_count,
                               NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL
                        FROM candles_daily 
                        WHERE symbol='{coin}/USDT' 
                        AND date NOT IN (SELECT date FROM candles_daily WHERE symbol='{coin}/USDC')""")
            new_count = c.execute("SELECT COUNT(*) FROM candles_daily WHERE symbol=?", (f"{coin}/USDC",)).fetchone()[0]
            print(f"  Merged: {coin}/USDC now has {new_count} rows")
    
    conn.commit()
    conn.close()
    
    # Recompute indicators on merged data
    for sym in ['LINK/USDC', 'XRP/USDC']:
        print(f"\nComputing indicators for {sym}...")
        compute_indicators(sym)
    
    # Final check
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for s in ['LINK/USDC', 'XRP/USDC']:
        r = c.execute('SELECT COUNT(*), MIN(date), MAX(date) FROM candles_daily WHERE symbol=?', (s,)).fetchone()
        print(f"\nFINAL: {s}: {r[0]} rows, {r[1]} to {r[2]}")
    conn.close()
