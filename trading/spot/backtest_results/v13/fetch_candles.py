"""
Fetch historical 1h candles from Binance and store in candles.db.
Then rebuild daily candles for the fetched symbols.
"""
import ccxt
import sqlite3
import time
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "candles.db"

def fetch_candles(exchange, symbol, timeframe='1h', since_ms=None, limit=1000):
    """Fetch candles from exchange with pagination."""
    all_candles = []
    while True:
        candles = exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=limit)
        if not candles:
            break
        all_candles.extend(candles)
        print(f"  Fetched {len(all_candles)} candles, latest: {datetime.fromtimestamp(candles[-1][0]/1000).date()}")
        since_ms = candles[-1][0] + 1  # Next ms after last candle
        if len(candles) < limit:
            break
        time.sleep(0.5)  # Rate limit
    return all_candles


def store_candles(db, symbol, candles):
    """Store candles in the candles table."""
    # Create table if needed
    db.execute("""
        CREATE TABLE IF NOT EXISTS candles (
            symbol TEXT, timestamp INTEGER, open REAL, high REAL, low REAL, 
            close REAL, volume REAL,
            PRIMARY KEY (symbol, timestamp)
        )
    """)
    
    inserted = 0
    for c in candles:
        try:
            db.execute(
                "INSERT OR REPLACE INTO candles (symbol, timestamp, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
                (symbol, c[0], c[1], c[2], c[3], c[4], c[5])
            )
            inserted += 1
        except Exception as e:
            pass
    db.commit()
    print(f"  Stored {inserted} candles for {symbol}")


def main():
    # Target: get data from 2023-06-01 to have enough for SMA200 warmup + Sep 2024 start
    target_start = datetime(2023, 6, 1)
    target_start_ms = int(target_start.timestamp() * 1000)
    
    symbols = {
        'BNB/USDT': 'BNB/USDT',
        'XRP/USDT': 'XRP/USDT',
    }
    
    ex = ccxt.binance({'enableRateLimit': True})
    db = sqlite3.connect(str(DB_PATH))
    
    for symbol, db_symbol in symbols.items():
        print(f"\n{'='*60}")
        print(f"Fetching {symbol} from {target_start.date()}")
        
        # Check existing data
        r = db.execute("SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM candles WHERE symbol=?", (db_symbol,)).fetchone()
        if r[2] > 0:
            existing_start = datetime.fromtimestamp(r[0]/1000)
            existing_end = datetime.fromtimestamp(r[1]/1000)
            print(f"  Existing: {existing_start.date()} to {existing_end.date()} ({r[2]} candles)")
            
            # Fetch missing earlier data
            if r[0] > target_start_ms:
                print(f"  Fetching earlier data: {target_start.date()} to {existing_start.date()}")
                candles = fetch_candles(ex, symbol, '1h', since_ms=target_start_ms, limit=1000)
                # Filter to only before existing
                candles = [c for c in candles if c[0] < r[0]]
                if candles:
                    store_candles(db, db_symbol, candles)
            else:
                print(f"  Already have data from before target start")
        else:
            print(f"  No existing data, fetching full range")
            candles = fetch_candles(ex, symbol, '1h', since_ms=target_start_ms, limit=1000)
            store_candles(db, db_symbol, candles)
    
    # Show final counts
    print(f"\n{'='*60}")
    print("Final candle counts:")
    for _, db_symbol in symbols.items():
        r = db.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol=?", (db_symbol,)).fetchone()
        if r[0] > 0:
            print(f"  {db_symbol}: {r[0]} candles, {datetime.fromtimestamp(r[1]/1000).date()} to {datetime.fromtimestamp(r[2]/1000).date()}")
    
    db.close()
    print("\nDone! Now run build_daily_candles.py to rebuild daily table.")


if __name__ == '__main__':
    main()
