"""Backfill 15m candles from Binance for DCA parameter testing.

Coins: ETH, BTC, SOL, LINK, XRP (USDC pairs, fallback USDT)
Period: Jan 2023 → present
Target: ~70K candles per coin at 15m
"""
import sqlite3
import time
import requests
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'candles.db'

COINS = [
    ('ETHUSDC', 'ETH/USDC'),
    ('BTCUSDC', 'BTC/USDC'),
    ('SOLUSDC', 'SOL/USDC'),
    ('LINKUSDC', 'LINK/USDC'),
    ('XRPUSDC', 'XRP/USDC'),
]

# Fallbacks if USDC pair doesn't exist on Binance
FALLBACKS = {
    'LINKUSDC': ('LINKUSDT', 'LINK/USDC'),  # Store as USDC even if fetched from USDT
    'XRPUSDC': ('XRPUSDT', 'XRP/USDC'),
}

START_MS = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
TIMEFRAME = '15m'
LIMIT = 1000  # Binance max per request
MS_PER_CANDLE = 15 * 60 * 1000


def fetch_candles(symbol, start_ms, timeframe='15m', limit=1000):
    """Fetch candles from Binance."""
    url = 'https://api.binance.com/api/v3/klines'
    params = {
        'symbol': symbol,
        'interval': timeframe,
        'startTime': start_ms,
        'limit': limit,
    }
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code == 400:
        return None  # Symbol doesn't exist
    resp.raise_for_status()
    return resp.json()


def backfill_coin(binance_sym, db_sym, conn):
    """Backfill one coin's 15m candles."""
    # Check existing data
    existing = conn.execute(
        'SELECT MAX(timestamp) FROM candles WHERE symbol=? AND timeframe=?',
        (db_sym, TIMEFRAME)
    ).fetchone()[0]

    if existing and existing > START_MS:
        start = existing + MS_PER_CANDLE
        print(f"  Resuming from {datetime.fromtimestamp(start/1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M')}")
    else:
        start = START_MS
        print(f"  Starting fresh from 2023-01-01")

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    total_inserted = 0
    current = start

    while current < now_ms:
        try:
            data = fetch_candles(binance_sym, current, TIMEFRAME, LIMIT)
        except Exception as e:
            # Try fallback
            if binance_sym in FALLBACKS:
                fb_sym, _ = FALLBACKS[binance_sym]
                print(f"  Trying fallback {fb_sym}...")
                try:
                    data = fetch_candles(fb_sym, current, TIMEFRAME, LIMIT)
                except Exception as e2:
                    print(f"  Fallback also failed: {e2}")
                    return total_inserted
            else:
                print(f"  Error: {e}")
                return total_inserted

        if data is None:
            # Try fallback for 400 errors
            if binance_sym in FALLBACKS:
                fb_sym, _ = FALLBACKS[binance_sym]
                print(f"  {binance_sym} not found, trying {fb_sym}...")
                data = fetch_candles(fb_sym, current, TIMEFRAME, LIMIT)
                if data is None:
                    print(f"  Fallback {fb_sym} also not found")
                    return total_inserted
                # Switch to fallback for remaining requests
                binance_sym = fb_sym
            else:
                print(f"  Symbol {binance_sym} not found on Binance")
                return total_inserted

        if not data:
            break

        rows = []
        for c in data:
            ts = c[0]
            rows.append((db_sym, TIMEFRAME, ts, float(c[1]), float(c[2]),
                         float(c[3]), float(c[4]), float(c[5])))

        conn.executemany(
            'INSERT OR REPLACE INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?,?)',
            rows
        )
        conn.commit()

        total_inserted += len(rows)
        last_ts = data[-1][0]
        current = last_ts + MS_PER_CANDLE

        # Progress
        pct = min(100, (current - START_MS) / (now_ms - START_MS) * 100)
        date_str = datetime.fromtimestamp(last_ts/1000, tz=timezone.utc).strftime('%Y-%m-%d')
        print(f"  {date_str} ({pct:.0f}%) - {total_inserted:,} candles", end='\r')

        if len(data) < LIMIT:
            break

        time.sleep(0.15)  # Rate limit

    print(f"  Done: {total_inserted:,} candles inserted" + " " * 30)
    return total_inserted


def main():
    conn = sqlite3.connect(DB_PATH)

    # Ensure table exists
    conn.execute('''CREATE TABLE IF NOT EXISTS candles (
        symbol TEXT, timeframe TEXT, timestamp INTEGER,
        open REAL, high REAL, low REAL, close REAL, volume REAL,
        PRIMARY KEY (symbol, timeframe, timestamp)
    )''')

    print(f"Backfilling 15m candles: Jan 2023 -> present")
    print(f"DB: {DB_PATH}\n")

    for binance_sym, db_sym in COINS:
        print(f"\n{db_sym}:")
        n = backfill_coin(binance_sym, db_sym, conn)

    # Also backfill 5m for comparison test (just ETH to start)
    print(f"\n\nAlso backfilling 5m ETH/USDC for noise comparison:")
    existing_5m = conn.execute(
        "SELECT COUNT(*) FROM candles WHERE symbol='ETH/USDC' AND timeframe='5m'"
    ).fetchone()[0]
    if existing_5m > 50000:
        print(f"  Already have {existing_5m:,} 5m candles, skipping")
    else:
        # Quick 5m backfill for ETH only
        start = START_MS
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        total = 0
        current = start
        ms_5m = 5 * 60 * 1000
        while current < now_ms:
            data = fetch_candles('ETHUSDC', current, '5m', LIMIT)
            if not data:
                break
            rows = [(
                'ETH/USDC', '5m', c[0], float(c[1]), float(c[2]),
                float(c[3]), float(c[4]), float(c[5])
            ) for c in data]
            conn.executemany(
                'INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?,?)',
                rows
            )
            conn.commit()
            total += len(rows)
            last_ts = data[-1][0]
            current = last_ts + ms_5m
            pct = min(100, (current - START_MS) / (now_ms - START_MS) * 100)
            date_str = datetime.fromtimestamp(last_ts/1000, tz=timezone.utc).strftime('%Y-%m-%d')
            print(f"  {date_str} ({pct:.0f}%) - {total:,} candles", end='\r')
            if len(data) < LIMIT:
                break
            time.sleep(0.15)
        print(f"  Done: {total:,} 5m candles" + " " * 30)

    # Summary
    print(f"\n\nSUMMARY:")
    for _, db_sym in COINS:
        for tf in ['15m', '5m']:
            r = conn.execute(
                'SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol=? AND timeframe=?',
                (db_sym, tf)
            ).fetchone()
            if r[0] > 0:
                mn = datetime.fromtimestamp(r[1]/1000, tz=timezone.utc).strftime('%Y-%m-%d')
                mx = datetime.fromtimestamp(r[2]/1000, tz=timezone.utc).strftime('%Y-%m-%d')
                print(f"  {db_sym} {tf}: {r[0]:,} candles ({mn} to {mx})")

    conn.close()


if __name__ == '__main__':
    main()
