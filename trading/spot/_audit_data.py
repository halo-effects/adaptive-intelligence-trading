#!/usr/bin/env python3
"""Phase 1 audit: Data pipeline integrity check."""
import sqlite3, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

db = sqlite3.connect(r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db')

print('=== 1h CANDLE FRESHNESS ===')
hourly = db.execute('''
    SELECT symbol, COUNT(*), MIN(timestamp), MAX(timestamp)
    FROM candles WHERE timeframe='1h'
    GROUP BY symbol ORDER BY symbol
''').fetchall()
for r in hourly:
    oldest = datetime.fromtimestamp(r[2]/1000, tz=timezone.utc).strftime('%Y-%m-%d')
    newest = datetime.fromtimestamp(r[3]/1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M')
    print(f'  {r[0]:15s} {r[1]:6d} candles  {oldest} to {newest}')
print(f'Total 1h symbols: {len(hourly)}')

print('\n=== DAILY CANDLE FRESHNESS ===')
daily = db.execute('''
    SELECT symbol, COUNT(*), MIN(timestamp), MAX(timestamp)
    FROM candles_daily GROUP BY symbol ORDER BY symbol
''').fetchall()
for r in daily:
    oldest = datetime.fromtimestamp(r[2]/1000, tz=timezone.utc).strftime('%Y-%m-%d')
    newest = datetime.fromtimestamp(r[3]/1000, tz=timezone.utc).strftime('%Y-%m-%d')
    print(f'  {r[0]:15s} {r[1]:6d} days  {oldest} to {newest}')
print(f'Total daily symbols: {len(daily)}')

# Cross-reference
hourly_syms = set(r[0] for r in hourly)
daily_syms = set(r[0] for r in daily)
print(f'\nHourly-only (no daily): {sorted(hourly_syms - daily_syms)}')
print(f'Daily-only (no hourly): {sorted(daily_syms - hourly_syms)}')

# Check collector COINS list manually (can't import due to missing os import in collector)
collector_syms = {
    'BTC/USDC','ETH/USDC','SOL/USDT','XRP/USDT','LINK/USDT','DOGE/USDT','ADA/USDT',
    'LTC/USDT','AVAX/USDT','DOT/USDT','UNI/USDT','ATOM/USDT','NEAR/USDT','HBAR/USDT',
    'INJ/USDT','FIL/USDT','RUNE/USDT','CRV/USDT','SNX/USDT','COMP/USDT','MKR/USDT',
    'ENS/USDT','DYDX/USDT','LDO/USDT','ARB/USDT','OP/USDT','STX/USDT','SEI/USDT',
    'RENDER/USDT','SUI/USDT','FET/USDT','TAO/USDT','TON/USDT','JUP/USDT','KAS/USDT',
    'PENDLE/USDT','PYTH/USDT','TIA/USDT','ONDO/USDT','ENA/USDT','EIGEN/USDT','W/USDT',
    'ZRO/USDT','HYPE/USDC','AAVE/USDT','LINK/USDC','XRP/USDC','SOL/USDC','ETH/USDC','BTC/USDC'
}
print(f'\nCollector universe: {len(collector_syms)} symbols')
print(f'In collector but not in hourly DB: {sorted(collector_syms - hourly_syms)}')
print(f'In hourly DB but not in collector: {sorted(hourly_syms - collector_syms)}')

# Data quality
print('\n=== DATA QUALITY ===')
for table in ['candles', 'candles_daily']:
    nulls = db.execute(f'SELECT COUNT(*) FROM {table} WHERE open IS NULL OR close IS NULL OR high IS NULL OR low IS NULL').fetchone()[0]
    zeros = db.execute(f'SELECT COUNT(*) FROM {table} WHERE close = 0').fetchone()[0]
    negs = db.execute(f'SELECT COUNT(*) FROM {table} WHERE close < 0 OR open < 0').fetchone()[0]
    total = db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    print(f'{table}: {total:,} rows, {nulls} NULL OHLC, {zeros} zero-close, {negs} negative')

# Check for duplicate timestamps
print('\n=== DUPLICATE CHECK ===')
dup_hourly = db.execute('''
    SELECT symbol, timestamp, COUNT(*) as cnt
    FROM candles WHERE timeframe='1h'
    GROUP BY symbol, timestamp HAVING cnt > 1
    LIMIT 5
''').fetchall()
print(f'Duplicate 1h candles: {len(dup_hourly)} found' + (f' (showing first 5: {dup_hourly})' if dup_hourly else ''))

dup_daily = db.execute('''
    SELECT symbol, timestamp, COUNT(*) as cnt
    FROM candles_daily
    GROUP BY symbol, timestamp HAVING cnt > 1
    LIMIT 5
''').fetchall()
print(f'Duplicate daily candles: {len(dup_daily)} found' + (f' (showing first 5: {dup_daily})' if dup_daily else ''))

# Check OHLC consistency (high should be >= open, close, low; low <= all)
print('\n=== OHLC CONSISTENCY ===')
bad_ohlc = db.execute('''
    SELECT COUNT(*) FROM candles
    WHERE high < open OR high < close OR low > open OR low > close
''').fetchone()[0]
print(f'candles: {bad_ohlc} rows with inconsistent OHLC (high < open/close or low > open/close)')

bad_daily = db.execute('''
    SELECT COUNT(*) FROM candles_daily
    WHERE high < open OR high < close OR low > open OR low > close
''').fetchone()[0]
print(f'candles_daily: {bad_daily} rows with inconsistent OHLC')

# Check candle_count field in daily (should be ~24 for complete days)
print('\n=== DAILY CANDLE COMPLETENESS ===')
sparse = db.execute('''
    SELECT symbol, date, candle_count
    FROM candles_daily
    WHERE candle_count > 0 AND candle_count < 20
    AND date < date('now', '-2 days')
    ORDER BY candle_count
    LIMIT 10
''').fetchall()
if sparse:
    print(f'Sparse days (< 20 candles, older than 2 days): {len(sparse)}')
    for s in sparse[:10]:
        print(f'  {s[0]} on {s[1]}: only {s[2]} candles')
else:
    print('No sparse days found (all have 20+ candles)')

# Check candle_count=0 (these came from pre-resample data, e.g. manual imports)
zero_count = db.execute('SELECT COUNT(*) FROM candles_daily WHERE candle_count = 0').fetchone()[0]
print(f'Daily rows with candle_count=0 (pre-resample imports): {zero_count}')

db.close()
print('\n=== AUDIT COMPLETE ===')
