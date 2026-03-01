"""
Backfill 1h candles for indicator warmup before Oct 2020 backtest start.
Then rebuild daily candles with indicators from the extended history.

BTC/USDC: Jan 2020 → Sep 2020 (9 months warmup)
ETH/USDC: Jan 2020 → Sep 2020 (9 months warmup)  
SOL/USDT: Aug 2020 → Jun 2021 (fill gap before USDC existed Sep 2021)

Also backfill SOL/USDC Sep 2021 → Jun 2021 gap and rebuild all daily.
"""

import sys, os, time, sqlite3
import requests
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'candles.db')

def fetch_1h_candles(symbol, start_date, end_date):
    """Fetch 1h candles from Binance in batches of 1000."""
    start_ms = int(datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp() * 1000)
    
    all_candles = []
    current = start_ms
    binance_symbol = symbol.replace('/', '')
    
    while current < end_ms:
        params = {
            'symbol': binance_symbol,
            'interval': '1h',
            'startTime': current,
            'endTime': end_ms,
            'limit': 1000
        }
        r = requests.get('https://api.binance.com/api/v3/klines', params=params)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        
        all_candles.extend(batch)
        current = batch[-1][0] + 1  # Next ms after last candle
        
        print(f"  {symbol}: fetched {len(all_candles)} candles, latest {datetime.fromtimestamp(batch[-1][0]/1000).strftime('%Y-%m-%d')}")
        time.sleep(0.2)  # Rate limit
    
    return all_candles


def insert_1h_candles(conn, symbol, candles):
    """Insert 1h candles into DB, skip duplicates."""
    inserted = 0
    skipped = 0
    for c in candles:
        try:
            conn.execute(
                'INSERT INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (symbol, '1h', c[0], float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5]))
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1
    conn.commit()
    print(f"  {symbol}: inserted {inserted}, skipped {skipped} duplicates")
    return inserted


def rebuild_daily_from_1h(conn, symbol):
    """Rebuild ALL daily candles for a symbol from 1h data, with indicators."""
    import pandas as pd
    import numpy as np
    
    # Load all 1h candles
    rows = conn.execute(
        'SELECT timestamp, open, high, low, close, volume FROM candles WHERE symbol=? AND timeframe=? ORDER BY timestamp',
        (symbol, '1h')
    ).fetchall()
    
    if not rows:
        print(f"  {symbol}: no 1h candles found!")
        return 0
    
    df = pd.DataFrame(rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.strftime('%Y-%m-%d')
    
    # Aggregate to daily
    daily = df.groupby('date').agg({
        'timestamp': 'first',
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).reset_index()
    
    # Compute indicators
    daily = compute_indicators(daily)
    
    # Delete existing daily candles for this symbol
    conn.execute('DELETE FROM candles_daily WHERE symbol=?', (symbol,))
    
    # Insert
    for _, row in daily.iterrows():
        conn.execute(
            'INSERT INTO candles_daily (symbol, date, timestamp, open, high, low, close, volume, sma50, sma200, adx, atr, atr_pct, rsi, bbw, regime) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (symbol, row['date'], int(row['timestamp']),
             row['open'], row['high'], row['low'], row['close'], row['volume'],
             row.get('sma50'), row.get('sma200'), row.get('adx'), row.get('atr'),
             row.get('atr_pct'), row.get('rsi'), row.get('bbw'), row.get('regime'))
        )
    
    conn.commit()
    mn = daily['date'].min()
    mx = daily['date'].max()
    print(f"  {symbol}: rebuilt {len(daily)} daily candles ({mn} to {mx})")
    return len(daily)


def compute_indicators(df):
    """Compute technical indicators on daily OHLCV DataFrame."""
    import pandas as pd
    import numpy as np
    
    c = df['close'].astype(float)
    h = df['high'].astype(float)
    l = df['low'].astype(float)
    
    # SMA
    df['sma50'] = c.rolling(50).mean()
    df['sma200'] = c.rolling(200).mean()
    
    # RSI (14)
    delta = c.diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # ATR (14)
    tr = pd.concat([
        h - l,
        (h - c.shift(1)).abs(),
        (l - c.shift(1)).abs()
    ], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()
    df['atr_pct'] = df['atr'] / c * 100
    
    # ADX (14)
    plus_dm = h.diff()
    minus_dm = -l.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    
    atr14 = tr.rolling(14).mean()
    plus_di = 100 * (plus_dm.rolling(14).mean() / atr14.replace(0, np.nan))
    minus_di = 100 * (minus_dm.rolling(14).mean() / atr14.replace(0, np.nan))
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    df['adx'] = dx.rolling(14).mean()
    
    # BBW (20, 2)
    sma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    upper = sma20 + 2 * std20
    lower = sma20 - 2 * std20
    df['bbw'] = ((upper - lower) / sma20 * 100)
    
    # Regime
    def classify_regime(row):
        adx = row.get('adx')
        bbw = row.get('bbw')
        if pd.isna(adx) or pd.isna(bbw):
            return None
        if adx > 30 and bbw > 10:
            return 'EXTREME'
        elif adx > 25:
            return 'TRENDING'
        elif adx < 20:
            return 'RANGING'
        else:
            return 'MILD_TREND'
    
    df['regime'] = df.apply(classify_regime, axis=1)
    
    return df


def main():
    conn = sqlite3.connect(DB_PATH)
    
    # Check current state
    print("=== Current 1h candle ranges ===")
    for sym in ['BTC/USDC', 'ETH/USDC', 'SOL/USDC', 'SOL/USDT']:
        row = conn.execute(
            'SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM candles WHERE symbol=? AND timeframe=?',
            (sym, '1h')
        ).fetchone()
        if row[0]:
            mn = datetime.fromtimestamp(row[0]/1000).strftime('%Y-%m-%d')
            mx = datetime.fromtimestamp(row[1]/1000).strftime('%Y-%m-%d')
            print(f"  {sym}: {mn} to {mx} ({row[2]} rows)")
        else:
            print(f"  {sym}: no data")
    
    # Step 1: Backfill 1h candles
    backfills = [
        ('BTC/USDC', 'BTCUSDC', '2020-01-01', '2020-09-30'),
        ('ETH/USDC', 'ETHUSDC', '2020-01-01', '2020-09-30'),
        ('SOL/USDT', 'SOLUSDT', '2020-08-11', '2021-06-30'),  # SOL listed Aug 2020
    ]
    
    print("\n=== Backfilling 1h candles ===")
    for db_sym, binance_sym, start, end in backfills:
        print(f"\n{db_sym}: {start} → {end}")
        candles = fetch_1h_candles(db_sym, start, end)
        if candles:
            insert_1h_candles(conn, db_sym, candles)
    
    # Step 2: Rebuild daily candles from ALL 1h data
    print("\n=== Rebuilding daily candles with indicators ===")
    
    # For SOL we need to merge USDT + USDC into one daily series
    # Strategy: rebuild USDC daily, then also rebuild USDT daily
    # The signal pack's load_daily picks the one with more rows
    for sym in ['BTC/USDC', 'ETH/USDC', 'SOL/USDC', 'SOL/USDT']:
        rebuild_daily_from_1h(conn, sym)
    
    # Verify final state
    print("\n=== Final daily candle ranges ===")
    for sym in ['BTC/USDC', 'ETH/USDC', 'SOL/USDC', 'SOL/USDT']:
        row = conn.execute(
            'SELECT MIN(date), MAX(date), COUNT(*) FROM candles_daily WHERE symbol=?',
            (sym,)
        ).fetchone()
        if row[0]:
            print(f"  {sym}: {row[0]} to {row[1]} ({row[2]} rows)")
        else:
            print(f"  {sym}: no data")
    
    # Check 2W StochRSI warmup readiness
    print("\n=== 2W StochRSI warmup check ===")
    print("  Need ~28 weeks (196 days) before Oct 2020 for full warmup")
    for sym in ['BTC/USDC', 'ETH/USDC']:
        row = conn.execute('SELECT MIN(date) FROM candles_daily WHERE symbol=?', (sym,)).fetchone()
        if row[0]:
            start = datetime.strptime(row[0], '%Y-%m-%d')
            oct2020 = datetime(2020, 10, 1)
            warmup_days = (oct2020 - start).days
            print(f"  {sym}: starts {row[0]}, warmup = {warmup_days} days {'✓' if warmup_days >= 196 else '✗ INSUFFICIENT'}")
    
    conn.close()
    print("\nDone!")


if __name__ == '__main__':
    main()
