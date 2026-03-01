"""
Backfill daily candle data from Binance for ETH, SOL, BTC.
Target: Apr 2020 (warm-up) to present.
Downloads 1d candles and inserts into candles_daily table.
"""
import sqlite3
import requests
import time
from datetime import datetime, timezone
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / 'data' / 'candles.db'
BINANCE_URL = 'https://api.binance.com/api/v3/klines'

def fetch_daily_candles(symbol, start_ms, end_ms):
    """Fetch daily candles from Binance in batches of 1000."""
    all_candles = []
    current = start_ms
    
    while current < end_ms:
        params = {
            'symbol': symbol.replace('/', ''),
            'interval': '1d',
            'startTime': current,
            'endTime': end_ms,
            'limit': 1000
        }
        resp = requests.get(BINANCE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        
        for k in data:
            all_candles.append({
                'timestamp': k[0],  # open time
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5])
            })
        
        # Move past last candle
        current = data[-1][0] + 86400000  # +1 day in ms
        print(f'  Fetched {len(data)} candles, total {len(all_candles)}, '
              f'up to {datetime.fromtimestamp(data[-1][0]/1000, tz=timezone.utc).date()}')
        time.sleep(0.2)  # Rate limit
    
    return all_candles


def get_existing_range(db, symbol):
    """Get existing data range for a symbol."""
    row = db.execute(
        'SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM candles_daily WHERE symbol=?',
        (symbol,)
    ).fetchone()
    return row


def main():
    db = sqlite3.connect(str(DB))
    
    # Target: April 2020 for warm-up (200-day SMA needs ~200 days before Oct 2020 start)
    target_start = datetime(2020, 4, 1, tzinfo=timezone.utc)
    target_start_ms = int(target_start.timestamp() * 1000)
    
    coins = {
        'ETH/USDT': 'ETHUSDT',
        'SOL/USDT': 'SOLUSDT', 
        'BTC/USDT': 'BTCUSDT'
    }
    
    for db_symbol, binance_symbol in coins.items():
        print(f'\n{"="*60}')
        print(f'  {db_symbol}')
        print(f'{"="*60}')
        
        existing = get_existing_range(db, db_symbol)
        existing_min = existing[0]
        existing_count = existing[2]
        
        if existing_min and existing_min <= target_start_ms:
            print(f'  Already have data from {datetime.fromtimestamp(existing_min/1000, tz=timezone.utc).date()}, skipping')
            continue
        
        # Fetch from target start to existing start (or to now if no data)
        end_ms = existing_min if existing_min else int(datetime.now(timezone.utc).timestamp() * 1000)
        
        print(f'  Existing: {existing_count} rows, min ts={existing_min}')
        print(f'  Fetching: {target_start.date()} to {datetime.fromtimestamp(end_ms/1000, tz=timezone.utc).date()}')
        
        candles = fetch_daily_candles(binance_symbol, target_start_ms, end_ms)
        
        if not candles:
            print(f'  No candles returned!')
            continue
        
        # Filter out any that overlap with existing data
        if existing_min:
            candles = [c for c in candles if c['timestamp'] < existing_min]
        
        print(f'  Inserting {len(candles)} new daily candles...')
        
        for c in candles:
            db.execute(
                'INSERT OR IGNORE INTO candles_daily (symbol, timestamp, open, high, low, close, volume) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                (db_symbol, c['timestamp'], c['open'], c['high'], c['low'], c['close'], c['volume'])
            )
        
        db.commit()
        
        # Verify
        new_range = get_existing_range(db, db_symbol)
        new_min = datetime.fromtimestamp(new_range[0]/1000, tz=timezone.utc).date()
        new_max = datetime.fromtimestamp(new_range[1]/1000, tz=timezone.utc).date()
        print(f'  Done: {new_range[2]} total rows, {new_min} to {new_max}')
    
    db.close()
    print('\nBackfill complete!')


if __name__ == '__main__':
    main()
