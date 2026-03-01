"""Fetch LINK/USDT 1h candles from Binance back to 2023-06-01."""
import ccxt
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB_PATH = Path('trading/spot/data/candles.db')

def main():
    target_start = datetime(2023, 6, 1)
    target_start_ms = int(target_start.timestamp() * 1000)
    
    ex = ccxt.binance({'enableRateLimit': True})
    db = sqlite3.connect(str(DB_PATH))
    
    # Check existing
    r = db.execute("SELECT MIN(timestamp), COUNT(*) FROM candles WHERE symbol='LINK/USDT'").fetchone()
    existing_min = r[0] if r[1] > 0 else None
    print(f"Existing: {r[1]} candles, earliest: {datetime.fromtimestamp(existing_min/1000) if existing_min else 'none'}")
    
    # Fetch from target start to existing start (or to now if none)
    fetch_until = existing_min if existing_min else int(datetime.now().timestamp() * 1000)
    since_ms = target_start_ms
    total = 0
    
    while since_ms < fetch_until:
        candles = ex.fetch_ohlcv('LINK/USDT', '1h', since=since_ms, limit=1000)
        if not candles:
            break
        # Filter to before existing data
        if existing_min:
            candles = [c for c in candles if c[0] < existing_min]
        if not candles:
            break
        
        for c in candles:
            db.execute(
                "INSERT OR IGNORE INTO candles (symbol, timestamp, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
                ('LINK/USDT', c[0], c[1], c[2], c[3], c[4], c[5]))
        db.commit()
        total += len(candles)
        latest = datetime.fromtimestamp(candles[-1][0]/1000)
        print(f"  Fetched {total} new candles, latest: {latest.date()}")
        since_ms = candles[-1][0] + 1
        if len(candles) < 1000:
            break
        time.sleep(0.3)
    
    # Also fetch LINK/USDC if available
    print(f"\nTotal new LINK/USDT candles: {total}")
    
    # Final count
    r = db.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol='LINK/USDT'").fetchone()
    print(f"Final: {r[0]} candles, {datetime.fromtimestamp(r[1]/1000).date()} -> {datetime.fromtimestamp(r[2]/1000).date()}")
    
    db.close()
    print("\nNow run build_daily_candles.py to rebuild daily table.")

if __name__ == '__main__':
    main()
