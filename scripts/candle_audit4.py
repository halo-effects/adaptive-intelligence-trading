import sqlite3, json
from datetime import datetime, timezone

conn = sqlite3.connect('trading/spot/data/candles.db')
cur = conn.cursor()

# Get scanner universe from DB
cur.execute("SELECT DISTINCT symbol FROM scanner_results")
scanner_db = set(r[0] for r in cur.fetchall())
print(f"Scanner DB universe: {len(scanner_db)} coins")

# Load cycle_scanner.json properly
try:
    with open('docs/data/v14/cycle_scanner.json', 'r', encoding='utf-8') as f:
        scanner_data = json.load(f)
    # Navigate structure
    if isinstance(scanner_data, dict):
        results = scanner_data.get('results', scanner_data.get('coins', []))
        if not results and 'windows' in scanner_data:
            for w in scanner_data['windows']:
                for r in w.get('results', []):
                    results.append(r)
    else:
        results = scanner_data
    scanner_json_symbols = set(r.get('symbol', '') for r in results if r.get('symbol'))
    scanner_json_coins = set(r.get('coin', '') for r in results if r.get('coin'))
    print(f"cycle_scanner.json symbols: {len(scanner_json_symbols)}, coins: {len(scanner_json_coins)}")
    if scanner_json_coins:
        print(f"  Coins: {sorted(scanner_json_coins)}")
except Exception as e:
    print(f"cycle_scanner.json error: {e}")
    scanner_json_symbols = set()
    scanner_json_coins = set()

# Get all 1h candle stats
cur.execute("""
    SELECT symbol, MAX(timestamp) as latest, MIN(timestamp) as earliest, COUNT(*) as candles
    FROM candles
    WHERE timeframe = '1h'
    GROUP BY symbol
    ORDER BY symbol
""")
all_1h = cur.fetchall()

# Determine timestamp format from first row
sample_ts = all_1h[0][1]
is_ms = sample_ts > 1e12
print(f"\nTimestamp format: {'milliseconds' if is_ms else 'seconds'}")

today_ts = datetime(2026, 7, 5, tzinfo=timezone.utc).timestamp()
if is_ms:
    today_ts *= 1000

stale = []
for sym, latest, earliest, count in all_1h:
    ts = latest / 1000 if is_ms else latest
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    
    ts_e = earliest / 1000 if is_ms else earliest
    dt_e = datetime.fromtimestamp(ts_e, tz=timezone.utc)
    
    coin = sym.split('/')[0]
    in_scanner = sym in scanner_db
    in_json = sym in scanner_json_symbols or coin in scanner_json_coins
    
    days_stale = (datetime(2026, 7, 5, 15, 0, tzinfo=timezone.utc) - dt).days
    
    if days_stale >= 1:
        stale.append({
            'symbol': sym,
            'coin': coin,
            'last_date': dt.strftime('%Y-%m-%d'),
            'first_date': dt_e.strftime('%Y-%m-%d'),
            'candles': count,
            'in_scanner_db': in_scanner,
            'in_scanner_json': in_json,
            'days_stale': days_stale
        })

print(f"\nTotal 1h symbols: {len(all_1h)}")
print(f"Stale (>= 1 day old): {len(stale)}")

print(f"\n{'Symbol':<20} {'Last Date':>12} {'Stale Days':>10} {'Candles':>10} {'Scanner DB':>10} {'Active?':>8}")
print("-" * 75)
for s in sorted(stale, key=lambda x: x['days_stale'], reverse=True):
    marker = "WARN" if s['in_scanner_db'] else ""
    print(f"{s['symbol']:<20} {s['last_date']:>12} {s['days_stale']:>10} {s['candles']:>10,} {'YES' if s['in_scanner_db'] else 'no':>10} {marker:>8}")

# Check which stale coins are in the V14PM universe
print("\n=== V14PM cross-check ===")
with open('trading/spot/live/v14pm/status.json', 'r', encoding='utf-8') as f:
    pm = json.load(f)
pm_syms = pm.get('symbols', [])
stale_syms = set(s['symbol'] for s in stale)
pm_stale = [s for s in pm_syms if s in stale_syms]
print(f"V14PM symbols: {len(pm_syms)}")
print(f"V14PM stale: {pm_stale if pm_stale else 'None - all current'}")

# Check collector config
print("\n=== Collector config ===")
try:
    with open('trading/spot/collect_scanner_candles.py', 'r', encoding='utf-8') as f:
        content = f.read()
    # Find symbol list
    import re
    # Look for SYMBOLS or coins list
    for pattern in [r'SYMBOLS\s*=\s*\[([^\]]+)\]', r'coins\s*=\s*\[([^\]]+)\]', r'COINS\s*=\s*\[([^\]]+)\]', r'symbols\s*=\s*\[([^\]]+)\]']:
        m = re.search(pattern, content, re.DOTALL)
        if m:
            print(f"Found symbol list in collector:")
            syms = [s.strip().strip("'\"") for s in m.group(1).split(',') if s.strip().strip("'\"")]
            print(f"  {len(syms)} symbols configured")
            # Check if stale coins are in collector
            stale_coins = set(s['coin'] for s in stale)
            collector_coins = set(s.split('/')[0] for s in syms)
            missing = stale_coins & collector_coins
            removed = stale_coins - collector_coins
            if missing:
                print(f"  Stale BUT still in collector config: {missing}")
            if removed:
                print(f"  Stale AND removed from collector: {removed}")
            break
    else:
        print("  Could not find symbol list - checking file structure...")
        # Print first 50 lines
        lines = content.split('\n')[:80]
        for i, line in enumerate(lines):
            if 'symbol' in line.lower() or 'coin' in line.lower() or 'UNIVERSE' in line:
                print(f"  L{i+1}: {line.rstrip()}")
except Exception as e:
    print(f"Error reading collector: {e}")

# Check collector log for recent activity
print("\n=== Recent collector log ===")
try:
    with open('trading/spot/data/collector.log', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for line in lines[-15:]:
        print(f"  {line.rstrip()}")
except Exception as e:
    print(f"Error: {e}")

conn.close()
