#!/usr/bin/env python3
"""
Backfill candles for V14-ETF coins: LTC, ADA, HBAR
Pulls 1h candles from Hyperliquid (perps) and daily from Binance.

Requirements:
  - LTC/USDT 1h: Jan 2024 → present (currently only Feb 2025+)
  - ADA/USDT 1h: Jan 2024 → present (currently only Feb 2025+)
  - HBAR/USDT 1h: catch up Mar 1-2 2026 (have Jan 2024 → Feb 28)
  - SOL/USDT 1h: already good (Aug 2020+)
  - XRP/USDT 1h: already good (Jan 2019+)
  - Daily candles for LTC, ADA: need from Jan 2023+ for SMA200 warmup
"""

import ccxt
import sqlite3
import time
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("AIT_CANDLES_DB", str(Path(__file__).parent / "data" / "candles.db")))

def init_db(conn):
    """Ensure tables exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candles (
            symbol TEXT, timeframe TEXT, timestamp INTEGER,
            open REAL, high REAL, low REAL, close REAL, volume REAL,
            PRIMARY KEY (symbol, timeframe, timestamp)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candles_daily (
            symbol TEXT, timestamp INTEGER,
            open REAL, high REAL, low REAL, close REAL, volume REAL,
            PRIMARY KEY (symbol, timestamp)
        )
    """)
    conn.commit()

def fetch_candles(exchange, symbol, timeframe, since_ms, limit=1000):
    """Fetch candles from exchange with rate limit handling."""
    all_candles = []
    current_since = since_ms
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    while current_since < now_ms:
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=limit)
            if not candles:
                break
            all_candles.extend(candles)
            last_ts = candles[-1][0]
            if last_ts <= current_since:
                break
            current_since = last_ts + 1
            print(f"  {symbol} {timeframe}: {len(all_candles)} candles, up to {datetime.fromtimestamp(last_ts/1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M')}")
            time.sleep(0.3)  # Rate limit
        except Exception as e:
            print(f"  Error fetching {symbol}: {e}")
            time.sleep(2)
            continue
    
    return all_candles

def store_candles(conn, symbol, timeframe, candles):
    """Store candles in DB, skip duplicates."""
    if timeframe == '1d':
        table = 'candles_daily'
        conn.executemany(
            f"INSERT OR IGNORE INTO {table} (symbol, timestamp, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(symbol, c[0], c[1], c[2], c[3], c[4], c[5]) for c in candles]
        )
    else:
        table = 'candles'
        conn.executemany(
            f"INSERT OR IGNORE INTO {table} (symbol, timeframe, timestamp, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(symbol, timeframe, c[0], c[1], c[2], c[3], c[4], c[5]) for c in candles]
        )
    conn.commit()
    print(f"  Stored {len(candles)} candles for {symbol} {timeframe}")

def main():
    conn = sqlite3.connect(str(DB_PATH))
    init_db(conn)
    
    # --- 1h candles from Hyperliquid (perps for price feed) ---
    print("=" * 60)
    print("STEP 1: 1h candles from Hyperliquid")
    print("=" * 60)
    
    hl = ccxt.hyperliquid()
    hl.load_markets()
    
    # Map: DB symbol -> Hyperliquid perp symbol
    hl_map = {
        "LTC/USDT": "LTC/USDC:USDC",
        "ADA/USDT": "ADA/USDC:USDC",
        "HBAR/USDT": "HBAR/USDC:USDC",
    }
    
    jan_2024_ms = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    mar_1_2026_ms = int(datetime(2026, 3, 1, tzinfo=timezone.utc).timestamp() * 1000)
    
    tasks_1h = [
        ("LTC/USDT", hl_map["LTC/USDT"], jan_2024_ms),
        ("ADA/USDT", hl_map["ADA/USDT"], jan_2024_ms),
        ("HBAR/USDT", hl_map["HBAR/USDT"], mar_1_2026_ms),  # Just catch-up
    ]
    
    for db_sym, hl_sym, since in tasks_1h:
        print(f"\nFetching 1h: {db_sym} (from {hl_sym})")
        candles = fetch_candles(hl, hl_sym, '1h', since)
        if candles:
            store_candles(conn, db_sym, '1h', candles)
        else:
            print(f"  WARNING: No candles returned for {hl_sym}")
    
    # --- Daily candles from Binance (longer history) ---
    print("\n" + "=" * 60)
    print("STEP 2: Daily candles from Binance")
    print("=" * 60)
    
    binance = ccxt.binance()
    binance.load_markets()
    
    jan_2023_ms = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    
    daily_tasks = [
        ("LTC/USDT", "LTC/USDT", jan_2023_ms),
        ("ADA/USDT", "ADA/USDT", jan_2023_ms),
    ]
    
    for db_sym, binance_sym, since in daily_tasks:
        print(f"\nFetching daily: {db_sym} (from Binance)")
        candles = fetch_candles(binance, binance_sym, '1d', since)
        if candles:
            store_candles(conn, db_sym, '1d', candles)
        else:
            print(f"  WARNING: No daily candles for {binance_sym}")
    
    # --- Also build daily from 1h for consistency check ---
    # (The engine uses candles_daily table)
    
    # --- Verify final state ---
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    coins = ['SOL/USDT', 'XRP/USDT', 'LTC/USDT', 'HBAR/USDT', 'ADA/USDT']
    for c in coins:
        cur = conn.execute(
            'SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM candles WHERE symbol=? AND timeframe=?',
            (c, '1h')
        )
        row = cur.fetchone()
        if row and row[2] > 0:
            mn = datetime.fromtimestamp(row[0]/1000, tz=timezone.utc).strftime('%Y-%m-%d')
            mx = datetime.fromtimestamp(row[1]/1000, tz=timezone.utc).strftime('%Y-%m-%d')
            print(f"  {c} 1h: {row[2]} candles, {mn} -> {mx}")
        else:
            print(f"  {c} 1h: NO DATA")
        
        cur2 = conn.execute(
            'SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM candles_daily WHERE symbol=?',
            (c,)
        )
        row2 = cur2.fetchone()
        if row2 and row2[2] > 0:
            mn2 = datetime.fromtimestamp(row2[0]/1000, tz=timezone.utc).strftime('%Y-%m-%d')
            mx2 = datetime.fromtimestamp(row2[1]/1000, tz=timezone.utc).strftime('%Y-%m-%d')
            print(f"  {c} daily: {row2[2]} rows, {mn2} -> {mx2}")
        else:
            print(f"  {c} daily: NO DATA")
    
    conn.close()
    print("\nDone!")

if __name__ == "__main__":
    main()
