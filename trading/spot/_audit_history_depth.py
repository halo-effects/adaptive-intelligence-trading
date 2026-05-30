#!/usr/bin/env python3
"""Audit: Check candle history depth for signal stack requirements."""
import sqlite3, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_PATH = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'
db = sqlite3.connect(DB_PATH)

# Signal stack minimum requirements:
# - SMA200: needs 200 daily candles minimum
# - StochRSI (3W): needs ~21 weeks = 147 days of resampled data + RSI lookback
#   RSI(14) needs 14 periods, StochRSI needs 14 more, K smooth 3, D smooth 3
#   On weekly data: 14 + 14 + 3 + 3 = 34 weeks = ~238 days minimum
# - BMSB (SMA20/EMA21 of weekly): needs 21 weeks = ~147 days
# - 2D divergence: needs swing detection lookback (~60 days)
# - Steve 3-Check: needs daily data
# Conservative minimum: 300 daily candles for full signal coverage

MIN_DAYS_FULL = 300  # Full signal stack
MIN_DAYS_BASIC = 200  # SMA200 minimum

# Scanner universe (45 coins the PM trades)
SCANNER_COINS = [
    'BTC','ETH','SOL','XRP','LINK','DOGE','ADA','LTC','AVAX','DOT',
    'UNI','ATOM','NEAR','HBAR','INJ','FIL','RUNE','CRV','SNX','COMP','MKR',
    'ENS','DYDX','LDO','ARB','OP','STX','SEI','RENDER','SUI','FET','TAO',
    'TON','JUP','KAS','PENDLE','PYTH','TIA','ONDO','ENA','EIGEN','W','ZRO','HYPE','AAVE'
]

# Also check coins the live bot has engines for
LIVE_BOT_COINS = ['TAO','HYPE','JTO','PEPE','DYDX','INJ','ENA','TON','JUP']

print("=" * 90)
print(f"{'COIN':>10} | {'SYMBOL':>15} | {'SOURCE':>12} | {'DAYS':>6} | {'OLDEST':>12} | {'NEWEST':>12} | STATUS")
print("=" * 90)

results = []
for coin in sorted(set(SCANNER_COINS + LIVE_BOT_COINS)):
    # Find all symbols for this coin in daily
    rows = db.execute(
        "SELECT symbol, COUNT(*) as cnt, MIN(timestamp), MAX(timestamp) "
        "FROM candles_daily WHERE symbol LIKE ? GROUP BY symbol",
        (f'{coin}/%',)
    ).fetchall()
    
    if not rows:
        results.append((coin, None, 0, 'MISSING', None, None))
        print(f"{coin:>10} | {'---':>15} | {'---':>12} | {'0':>6} | {'---':>12} | {'---':>12} | MISSING")
        continue
    
    # Pick the one with most data (same logic as load_daily)
    best = max(rows, key=lambda r: r[1])
    sym, cnt, oldest_ms, newest_ms = best
    
    oldest = datetime.fromtimestamp(oldest_ms/1000, tz=timezone.utc).strftime('%Y-%m-%d')
    newest = datetime.fromtimestamp(newest_ms/1000, tz=timezone.utc).strftime('%Y-%m-%d')
    
    # Determine data source by checking if it has hourly candles from Binance (pre-2025 data)
    # vs Hyperliquid/Aster (2025+ data)
    has_pre2024 = db.execute(
        "SELECT COUNT(*) FROM candles_daily WHERE symbol=? AND timestamp < 1704067200000",  # 2024-01-01
        (sym,)
    ).fetchone()[0]
    
    # Check if hourly data exists from multiple sources
    hourly_oldest = db.execute(
        "SELECT MIN(timestamp) FROM candles WHERE symbol=? AND timeframe='1h'",
        (sym,)
    ).fetchone()[0]
    
    if hourly_oldest:
        h_date = datetime.fromtimestamp(hourly_oldest/1000, tz=timezone.utc).strftime('%Y-%m-%d')
        if hourly_oldest < 1704067200000:  # pre-2024
            source = "Binance+HL"
        elif hourly_oldest < 1740700800000:  # pre-March 2025
            source = "HL backfill"
        else:
            source = "HL/Aster"
    else:
        h_date = "no hourly"
        source = "daily-only"
    
    if cnt >= MIN_DAYS_FULL:
        status = "OK"
    elif cnt >= MIN_DAYS_BASIC:
        status = "SMA200-OK"
    else:
        status = f"SHORT ({MIN_DAYS_FULL - cnt} needed)"
    
    in_scanner = "S" if coin in SCANNER_COINS else " "
    in_live = "L" if coin in LIVE_BOT_COINS else " "
    
    results.append((coin, sym, cnt, status, oldest, newest))
    print(f"{coin:>10} | {sym:>15} | {source:>12} | {cnt:>6} | {oldest:>12} | {newest:>12} | {status} {in_scanner}{in_live}")

print("=" * 90)

# Summary
ok = sum(1 for r in results if r[3] == 'OK')
sma_ok = sum(1 for r in results if r[3] == 'SMA200-OK')
short = sum(1 for r in results if 'SHORT' in str(r[3]) or r[3] == 'MISSING')
print(f"\nSummary: {ok} full coverage, {sma_ok} SMA200-only, {short} insufficient")

# List the problem coins
print("\n=== COINS WITH INSUFFICIENT HISTORY ===")
for coin, sym, cnt, status, oldest, newest in results:
    if 'SHORT' in str(status) or status == 'MISSING':
        in_scanner = coin in SCANNER_COINS
        in_live = coin in LIVE_BOT_COINS
        tags = []
        if in_scanner: tags.append("SCANNER")
        if in_live: tags.append("LIVE BOT")
        print(f"  {coin:>10}: {cnt} days ({status}) [{', '.join(tags)}]")

# Check specifically which coins came from Binance backfill
print("\n=== BINANCE BACKFILL COINS (pre-2024 data in DB) ===")
pre2024 = db.execute("""
    SELECT DISTINCT symbol FROM candles_daily 
    WHERE timestamp < 1704067200000
    ORDER BY symbol
""").fetchall()
for r in pre2024:
    cnt = db.execute("SELECT COUNT(*) FROM candles_daily WHERE symbol=?", (r[0],)).fetchone()[0]
    oldest = db.execute("SELECT MIN(timestamp) FROM candles_daily WHERE symbol=?", (r[0],)).fetchone()[0]
    dt = datetime.fromtimestamp(oldest/1000, tz=timezone.utc).strftime('%Y-%m-%d')
    print(f"  {r[0]:>15}: {cnt} days, from {dt}")

db.close()
