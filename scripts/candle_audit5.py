import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect('trading/spot/data/candles.db')
cur = conn.cursor()

# Check if removed coins have alternate USDC pairs that are current
removed = ['APT', 'S', 'ORCA', 'IP', 'BERA', 'MOVE', 'VIRTUAL', 'GRASS', 'INIT', 'JTO', 'TRUMP', 'PEPE']
print('=== Removed coins - any alternate current pairs? ===')
for coin in removed:
    cur.execute(
        "SELECT symbol, MAX(timestamp) as latest, COUNT(*) as candles "
        "FROM candles WHERE timeframe = '1h' AND symbol LIKE ? GROUP BY symbol",
        (coin + '/%',)
    )
    rows = cur.fetchall()
    for sym, latest, count in rows:
        dt = datetime.fromtimestamp(latest/1000, tz=timezone.utc)
        tag = 'CURRENT' if dt.date().isoformat() == '2026-07-05' else 'STALE ' + dt.date().isoformat()
        print('  %-20s %8d candles  %s' % (sym, count, tag))

# HYPE, TON, PEPE - in collector but USDT pair stale
for coin in ['HYPE', 'TON', 'PEPE', 'JTO']:
    print('\n=== %s pair status ===' % coin)
    cur.execute(
        "SELECT symbol, MAX(timestamp) as latest, COUNT(*) FROM candles "
        "WHERE timeframe='1h' AND symbol LIKE ? GROUP BY symbol",
        (coin + '/%',)
    )
    for sym, latest, count in cur.fetchall():
        dt = datetime.fromtimestamp(latest/1000, tz=timezone.utc)
        print('  %-20s last: %s  (%d candles)' % (sym, dt.strftime('%Y-%m-%d %H:%M'), count))

# Check what the V14PM bot actually uses for these coins
print('\n=== V14PM: which pair does each tracked coin use? ===')
import json
with open('trading/spot/live/v14pm/status.json', 'r', encoding='utf-8') as f:
    pm = json.load(f)
for sym in pm.get('symbols', []):
    coin_data = pm.get('coins', {}).get(sym, {})
    state = coin_data.get('state', '?')
    layers = coin_data.get('layers', 0)
    print('  %-20s state=%-12s layers=%d' % (sym, state, layers))

# Check collector's full symbol list
print('\n=== Collector configured symbols (current 45-coin universe) ===')
with open('trading/spot/collect_scanner_candles.py', 'r', encoding='utf-8') as f:
    content = f.read()
import re
m = re.search(r'(?:SYMBOLS|coins|COINS|symbols|UNIVERSE)\s*=\s*\[([^\]]+)\]', content, re.DOTALL)
if m:
    syms = [s.strip().strip("'\"") for s in m.group(1).split(',') if s.strip().strip("'\"")]
    print('  Total: %d symbols' % len(syms))
    # Group by coin to find which quote currencies
    from collections import defaultdict
    by_coin = defaultdict(list)
    for s in syms:
        parts = s.split('/')
        by_coin[parts[0]].append(s)
    for coin in sorted(by_coin):
        pairs = by_coin[coin]
        if len(pairs) > 1:
            print('  %s: %s' % (coin, pairs))
    
    # Which scanner coins don't have 1h candle data at all?
    cur.execute("SELECT DISTINCT symbol FROM candles WHERE timeframe='1h'")
    db_syms = set(r[0] for r in cur.fetchall())
    missing = [s for s in syms if s not in db_syms]
    if missing:
        print('\n  Missing from candle DB entirely: %s' % missing)

conn.close()
