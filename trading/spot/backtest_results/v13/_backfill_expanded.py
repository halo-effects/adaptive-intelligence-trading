"""Backfill daily candles from Binance for expanded coin universe."""
import sqlite3, time, requests
from datetime import datetime, timezone

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
BINANCE = "https://api.binance.com/api/v3/klines"

# Coins needing backfill (symbol → Binance symbol, start date)
COINS = {
    "AAVE/USDT": ("AAVEUSDT", "2020-10-01"),    # AAVE launched Oct 2020
    "ADA/USDT": ("ADAUSDT", "2019-01-01"),       # ADA since 2017
    "BNB/USDT": ("BNBUSDT", "2019-01-01"),       # BNB since 2017
    "AVAX/USDT": ("AVAXUSDT", "2020-09-01"),     # AVAX launched Sep 2020
    "DOT/USDT": ("DOTUSDT", "2020-08-01"),       # DOT launched Aug 2020
    "UNI/USDT": ("UNIUSDT", "2020-09-01"),       # UNI launched Sep 2020
    "NEAR/USDT": ("NEARUSDT", "2020-10-01"),     # NEAR on Binance Oct 2020
    "LTC/USDT": ("LTCUSDT", "2019-01-01"),       # LTC since forever
    "ATOM/USDT": ("ATOMUSDT", "2019-04-01"),     # ATOM launched Apr 2019
}

START_DEFAULT = "2019-01-01"

def backfill(symbol, binance_symbol, start_date, conn):
    cur = conn.cursor()
    start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    # Check existing
    existing = cur.execute("SELECT COUNT(*) FROM candles_daily WHERE symbol=?", (symbol,)).fetchone()[0]
    
    total = 0
    print(f"\n{symbol}: backfilling from {start_date} (existing: {existing})")
    
    while start_ts < end_ts:
        params = {
            "symbol": binance_symbol,
            "interval": "1d",
            "startTime": start_ts,
            "endTime": end_ts,
            "limit": 1000,
        }
        try:
            resp = requests.get(BINANCE, params=params, timeout=30)
            resp.raise_for_status()
            candles = resp.json()
        except Exception as e:
            print(f"  Error: {e}")
            break
        
        if not candles:
            break
        
        rows = []
        for c in candles:
            ts = c[0]
            dt = datetime.fromtimestamp(ts/1000, tz=timezone.utc).strftime('%Y-%m-%d')
            rows.append((symbol, dt, ts, float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])))
        
        cur.executemany(
            "INSERT OR REPLACE INTO candles_daily (symbol, date, timestamp, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?,?)",
            rows
        )
        conn.commit()
        total += len(rows)
        
        last_ts = candles[-1][0]
        if last_ts <= start_ts:
            break
        start_ts = last_ts + 86400000
        
        time.sleep(0.2)  # Rate limit
    
    final = cur.execute("SELECT COUNT(*) FROM candles_daily WHERE symbol=?", (symbol,)).fetchone()[0]
    print(f"  Done: +{total} rows, total={final}")

conn = sqlite3.connect(DB)
for symbol, (bsym, start) in COINS.items():
    backfill(symbol, bsym, start, conn)
conn.close()

# Verify all
print("\n" + "=" * 60)
print("FINAL DATA CHECK")
print("=" * 60)
conn = sqlite3.connect(DB)
for coin in ['BTC', 'ETH', 'SOL', 'LINK', 'XRP', 'HBAR', 'AAVE', 'ADA', 'BNB', 'AVAX', 'DOT', 'UNI', 'NEAR', 'LTC', 'ATOM']:
    best = 0
    best_sym = ''
    for q in ['USDC', 'USDT']:
        sym = f'{coin}/{q}'
        cnt = conn.execute("SELECT COUNT(*) FROM candles_daily WHERE symbol=?", (sym,)).fetchone()[0]
        if cnt > best:
            best = cnt
            best_sym = sym
    ok = "OK" if best >= 600 else "SHORT"
    print(f"  {coin:<6} {best:>5}d ({best_sym:<12}) 3D_SMA200={ok}")
conn.close()
