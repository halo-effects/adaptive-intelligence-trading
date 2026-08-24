import sqlite3, json
from datetime import datetime, timezone

conn = sqlite3.connect('trading/spot/data/candles.db')
cur = conn.cursor()

# Load scanner results to get the active 45-coin universe
cur.execute("SELECT DISTINCT symbol FROM scanner_results")
scanner_symbols = set(r[0] for r in cur.fetchall())
print(f"Scanner DB universe: {len(scanner_symbols)} coins")

# Also check the cycle_scanner.json for approved/active coins
try:
    with open('docs/data/v14/cycle_scanner.json', 'r') as f:
        scanner_data = json.load(f)
    scanner_coins_json = set()
    if 'results' in scanner_data:
        for r in scanner_data['results']:
            scanner_coins_json.add(r.get('symbol', ''))
    elif isinstance(scanner_data, list):
        for r in scanner_data:
            scanner_coins_json.add(r.get('symbol', ''))
    print(f"cycle_scanner.json coins: {len(scanner_coins_json)}")
except Exception as e:
    print(f"Could not read cycle_scanner.json: {e}")
    scanner_coins_json = set()

# Get all stale 1h symbols
stale_cutoff = 1751673600  # 2026-07-05 00:00 UTC
cur.execute("""
    SELECT symbol, MAX(timestamp) as latest, COUNT(*) as candles
    FROM candles
    WHERE timeframe = '1h'
    GROUP BY symbol
    ORDER BY symbol
""")
all_symbols = cur.fetchall()

stale = []
current = []
for sym, latest, count in all_symbols:
    if latest > 1e12:
        ts = latest / 1000
    else:
        ts = latest
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    
    # Extract coin name from symbol
    coin = sym.split('/')[0]
    
    in_scanner_db = sym in scanner_symbols or any(s.startswith(coin + '/') for s in scanner_symbols)
    in_scanner_json = sym in scanner_coins_json or any(s.startswith(coin + '/') for s in scanner_coins_json)
    
    if ts < stale_cutoff:
        stale.append({
            'symbol': sym,
            'last_date': dt.strftime('%Y-%m-%d'),
            'candles': count,
            'in_scanner_db': in_scanner_db,
            'in_scanner_json': in_scanner_json,
            'days_stale': (datetime(2026, 7, 5, tzinfo=timezone.utc) - dt).days
        })

print(f"\nTotal symbols in DB: {len(all_symbols)}")
print(f"Stale symbols: {len(stale)}")

print(f"\n{'Symbol':<20} {'Last Date':>12} {'Days Stale':>12} {'Candles':>10} {'In Scanner?':>12} {'In JSON?':>10}")
print("-" * 80)
for s in sorted(stale, key=lambda x: x['days_stale'], reverse=True):
    print(f"{s['symbol']:<20} {s['last_date']:>12} {s['days_stale']:>12} {s['candles']:>10,} {'YES':>12 if s['in_scanner_db'] else 'no':>12} {'YES':>10 if s['in_scanner_json'] else 'no':>10}")

# Now check what the collector config looks like
print("\n=== Cross-reference with V14PM status.json symbols ===")
try:
    with open('trading/spot/live/v14pm/status.json', 'r') as f:
        pm_status = json.load(f)
    pm_symbols = pm_status.get('symbols', [])
    approved = pm_status.get('approved_symbols', [])
    print(f"V14PM tracked symbols: {pm_symbols}")
    print(f"V14PM approved symbols: {approved}")
    
    # Check which PM symbols are stale
    stale_syms = set(s['symbol'] for s in stale)
    pm_stale = [s for s in pm_symbols if s in stale_syms]
    if pm_stale:
        print(f"\n⚠️  STALE symbols in V14PM active universe: {pm_stale}")
    else:
        print(f"\n✅ No stale symbols in V14PM active universe")
except Exception as e:
    print(f"Could not read V14PM status: {e}")

# Check collector config if it exists
import glob
collector_files = glob.glob('trading/**/collector*', recursive=True) + glob.glob('trading/**/collect*', recursive=True)
print(f"\nCollector-related files: {collector_files[:10]}")

conn.close()
