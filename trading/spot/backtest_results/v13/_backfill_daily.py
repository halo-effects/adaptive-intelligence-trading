"""Backfill daily candles from Binance for ETH/BTC (and SOL gap-fill) into candles_daily."""
import sqlite3, time, requests
from datetime import datetime, timezone

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
BINANCE = "https://api.binance.com/api/v3/klines"

COINS = {
    "ETH/USDT": "ETHUSDT",
    "BTC/USDT": "BTCUSDT",
    "SOL/USDT": "SOLUSDT",
}

# Start from Jan 1 2019 (or coin launch)
START = int(datetime(2019, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)

def backfill(symbol, binance_symbol, conn):
    cur = conn.cursor()
    # Find earliest existing
    row = cur.execute("SELECT MIN(timestamp) FROM candles_daily WHERE symbol=?", (symbol,)).fetchone()
    end_ts = row[0] if row[0] else int(datetime.now(timezone.utc).timestamp() * 1000)
    
    start_ts = START
    total = 0
    
    print(f"\n{symbol}: backfilling from {datetime.fromtimestamp(start_ts/1000, tz=timezone.utc).date()} to {datetime.fromtimestamp(end_ts/1000, tz=timezone.utc).date()}")
    
    while start_ts < end_ts:
        params = {
            "symbol": binance_symbol,
            "interval": "1d",
            "startTime": start_ts,
            "endTime": end_ts,
            "limit": 1000,
        }
        resp = requests.get(BINANCE, params=params, timeout=30)
        resp.raise_for_status()
        candles = resp.json()
        
        if not candles:
            break
        
        rows = []
        for c in candles:
            ts = c[0]  # open time
            dt = datetime.fromtimestamp(ts/1000, tz=timezone.utc).strftime('%Y-%m-%d')
            rows.append((symbol, dt, ts, float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])))
        
        cur.executemany(
            "INSERT OR IGNORE INTO candles_daily (symbol, date, timestamp, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?,?)",
            rows
        )
        conn.commit()
        total += len(rows)
        
        last_ts = candles[-1][0]
        if last_ts <= start_ts:
            break
        start_ts = last_ts + 86400000  # next day
        
        print(f"  {total} candles so far (through {datetime.fromtimestamp(last_ts/1000, tz=timezone.utc).date()})")
        time.sleep(0.2)
    
    # Verify
    cnt = cur.execute("SELECT COUNT(*) FROM candles_daily WHERE symbol=?", (symbol,)).fetchone()[0]
    mn = cur.execute("SELECT MIN(timestamp) FROM candles_daily WHERE symbol=?", (symbol,)).fetchone()[0]
    mx = cur.execute("SELECT MAX(timestamp) FROM candles_daily WHERE symbol=?", (symbol,)).fetchone()[0]
    print(f"  DONE: {cnt} total candles, {datetime.fromtimestamp(mn/1000, tz=timezone.utc).date()} to {datetime.fromtimestamp(mx/1000, tz=timezone.utc).date()}")
    return total

if __name__ == "__main__":
    conn = sqlite3.connect(DB)
    for sym, bsym in COINS.items():
        backfill(sym, bsym, conn)
    conn.close()
    print("\nAll done.")
