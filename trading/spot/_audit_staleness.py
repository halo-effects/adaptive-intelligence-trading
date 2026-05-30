#!/usr/bin/env python3
"""Audit: Check data staleness."""
import sqlite3, sys, io
from datetime import datetime, timezone
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

db = sqlite3.connect(r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db')

now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
day_ms = 86400000
fresh_cutoff = now_ms - (2 * day_ms)

fresh = []
stale = []
q = "SELECT symbol, MAX(timestamp) FROM candles WHERE timeframe='1h' GROUP BY symbol"
for sym, latest in db.execute(q).fetchall():
    age_days = (now_ms - latest) / day_ms
    if latest >= fresh_cutoff:
        fresh.append((sym, age_days))
    else:
        stale.append((sym, age_days))

print(f'FRESH (< 2 days old): {len(fresh)} coins')
print(f'STALE (> 2 days old): {len(stale)} coins')
print()
if stale:
    print('Stale coins:')
    for sym, age in sorted(stale, key=lambda x: -x[1]):
        print(f'  {sym:15s}: {age:.1f} days old')

scanner_coins = set(['BTC','ETH','SOL','XRP','LINK','DOGE','ADA','LTC','AVAX','DOT',
    'UNI','ATOM','NEAR','HBAR','INJ','FIL','RUNE','CRV','SNX','COMP','MKR',
    'ENS','DYDX','LDO','ARB','OP','STX','SEI','RENDER','SUI','FET','TAO',
    'TON','JUP','KAS','PENDLE','PYTH','TIA','ONDO','ENA','EIGEN','W','ZRO','HYPE','AAVE'])

stale_scanner = [(s, a) for s, a in stale if s.split('/')[0] in scanner_coins]
fresh_scanner = [(s, a) for s, a in fresh if s.split('/')[0] in scanner_coins]
print(f'\nScanner universe (45 coins):')
print(f'  Fresh: {len(fresh_scanner)}')
print(f'  Stale: {len(stale_scanner)}')
if stale_scanner:
    print('  Stale scanner coins:')
    for sym, age in sorted(stale_scanner, key=lambda x: -x[1]):
        print(f'    {sym:15s}: {age:.1f} days old')

db.close()
