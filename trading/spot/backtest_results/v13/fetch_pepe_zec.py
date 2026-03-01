"""Fetch PEPE and ZEC 1h candles from Binance into candles.db."""
import ccxt
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "candles.db"

def fetch_candles(exchange, symbol, timeframe='1h', since_ms=None, limit=1000):
    all_candles = []
    while True:
        candles = exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=limit)
        if not candles:
            break
        all_candles.extend(candles)
        print(f"  {len(all_candles)} candles, latest: {datetime.fromtimestamp(candles[-1][0]/1000).date()}")
        since_ms = candles[-1][0] + 1
        if len(candles) < limit:
            break
        time.sleep(0.3)
    return all_candles

def store_candles(db, symbol, candles, timeframe='1h'):
    inserted = 0
    for c in candles:
        try:
            db.execute(
                "INSERT OR REPLACE INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?,?)",
                (symbol, timeframe, c[0], c[1], c[2], c[3], c[4], c[5])
            )
            inserted += 1
        except Exception as e:
            if inserted == 0:
                print(f"  INSERT error: {e}")
            pass
    db.commit()
    print(f"  Stored {inserted} candles for {symbol}")

def main():
    # Need data from 2023-06-01 for SMA200 warmup
    target_start = datetime(2023, 6, 1)
    target_start_ms = int(target_start.timestamp() * 1000)
    
    # PEPE launched May 2023, ZEC has long history
    # Binance pairs: PEPE/USDT (high liquidity), ZEC/USDT
    symbols = {
        'NEAR/USDT': 'NEAR/USDT',
        'LINK/USDT': 'LINK/USDT',
    }
    
    ex = ccxt.binance({'enableRateLimit': True})
    db = sqlite3.connect(str(DB_PATH))
    
    for symbol, db_symbol in symbols.items():
        print(f"\n{'='*60}")
        print(f"Fetching {symbol} from {target_start.date()}")
        
        r = db.execute("SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM candles WHERE symbol=?", (db_symbol,)).fetchone()
        if r[2] > 0:
            print(f"  Existing: {datetime.fromtimestamp(r[0]/1000).date()} to {datetime.fromtimestamp(r[1]/1000).date()} ({r[2]} candles)")
            # Fetch any missing recent data
            candles = fetch_candles(ex, symbol, '1h', since_ms=r[1]+1, limit=1000)
            if candles:
                store_candles(db, db_symbol, candles)
            # Also backfill if needed
            if r[0] > target_start_ms:
                print(f"  Backfilling from {target_start.date()}")
                candles = fetch_candles(ex, symbol, '1h', since_ms=target_start_ms, limit=1000)
                candles = [c for c in candles if c[0] < r[0]]
                if candles:
                    store_candles(db, db_symbol, candles)
        else:
            print(f"  No existing data, fetching full range")
            candles = fetch_candles(ex, symbol, '1h', since_ms=target_start_ms, limit=1000)
            store_candles(db, db_symbol, candles)
    
    # Show final counts
    print(f"\n{'='*60}")
    print("Final counts:")
    for _, db_symbol in symbols.items():
        r = db.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol=?", (db_symbol,)).fetchone()
        if r[0] > 0:
            print(f"  {db_symbol}: {r[0]} candles, {datetime.fromtimestamp(r[1]/1000).date()} to {datetime.fromtimestamp(r[2]/1000).date()}")
    
    db.close()
    print("\nDone! Run build_daily_candles.py next.")

if __name__ == '__main__':
    main()
