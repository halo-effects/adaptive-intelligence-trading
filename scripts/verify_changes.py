"""Verify collector ↔ scanner symbol consistency and check for issues."""
import re
import sys
import sqlite3

# 1. Extract collector ACTIVE_UNIVERSE coins
with open('trading/spot/collect_scanner_candles.py', 'r', encoding='utf-8') as f:
    collector_src = f.read()

# Split at WATCHLIST to only get ACTIVE_UNIVERSE
active_section = collector_src.split('WATCHLIST')[0]
collector_active = set()
collector_active_pairs = []
for m in re.finditer(r'\("([^"]+)",\s*"([^"]+)"\)', active_section):
    line_start = active_section.rfind('\n', 0, m.start())
    line = active_section[line_start:m.start()]
    if '#' not in line:  # not commented out
        db_sym, hl_sym = m.group(1), m.group(2)
        collector_active.add(db_sym.split('/')[0])
        collector_active_pairs.append((db_sym, hl_sym))

# 2. Extract collector WATCHLIST coins
watch_section = collector_src.split('WATCHLIST')[1].split('USDC_COINS')[0] if 'WATCHLIST' in collector_src else ''
collector_watch = set()
for m in re.finditer(r'\("([^"]+)",\s*"([^"]+)"\)', watch_section):
    line_start = watch_section.rfind('\n', 0, m.start())
    line = watch_section[line_start:m.start()]
    if '#' not in line:
        collector_watch.add(m.group(1).split('/')[0])

# 3. Extract scanner COINS
with open('trading/spot/v14_cycle_scanner.py', 'r', encoding='utf-8') as f:
    scanner_src = f.read()

scanner_coins = set()
scanner_symbols = []
coins_match = re.search(r'COINS\s*=\s*\[(.*?)\]', scanner_src, re.DOTALL)
if coins_match:
    block = coins_match.group(1)
    for m in re.finditer(r"'([^']+)'", block):
        sym = m.group(1)
        scanner_coins.add(sym.split('/')[0])
        scanner_symbols.append(sym)

print("=== Symbol Counts ===")
print(f"Collector ACTIVE_UNIVERSE: {len(collector_active)} coins")
print(f"Collector WATCHLIST: {len(collector_watch)} coins")
print(f"Scanner COINS: {len(scanner_coins)} coins")

# 4. Cross-check
only_collector = collector_active - scanner_coins
only_scanner = scanner_coins - collector_active
print(f"\nIn collector active but NOT scanner: {sorted(only_collector) if only_collector else 'None'}")
print(f"In scanner but NOT collector active: {sorted(only_scanner) if only_scanner else 'None'}")

# 5. Check specific fixes
print("\n=== Fix Verification ===")

# TON → GRAM
has_ton_collector = 'TON/USDT' in collector_src.split('#')[0]  # rough check
has_gram_collector = 'GRAM/USDT' in collector_src
has_ton_scanner = "'TON/USDT'" in scanner_src
has_gram_scanner = "'GRAM/USDT'" in scanner_src
print(f"TON in collector (should be gone): {'FAIL - still there' if has_ton_collector else 'OK - removed'}")
print(f"GRAM in collector (should exist):  {'OK' if has_gram_collector else 'FAIL - missing'}")
print(f"TON in scanner (should be gone):   {'FAIL - still there' if has_ton_scanner else 'OK - removed'}")
print(f"GRAM in scanner (should exist):    {'OK' if has_gram_scanner else 'FAIL - missing'}")

# HYPE quote currency
hype_usdt_active = any(db == 'HYPE/USDT' for db, _ in collector_active_pairs)
hype_usdc_scanner = "'HYPE/USDC'" in scanner_src
hype_usdt_scanner = "'HYPE/USDT'" in scanner_src
print(f"\nHYPE/USDT in collector active:     {'OK' if hype_usdt_active else 'FAIL'}")
print(f"HYPE/USDT in scanner:              {'OK' if hype_usdt_scanner else 'FAIL'}")
print(f"HYPE/USDC in scanner (should not): {'FAIL' if hype_usdc_scanner else 'OK'}")

# HYPE/USDC in USDC_COINS
usdc_section = collector_src.split('USDC_COINS')[1] if 'USDC_COINS' in collector_src else ''
hype_usdc_preserved = 'HYPE/USDC' in usdc_section
print(f"HYPE/USDC in USDC_COINS (history): {'OK' if hype_usdc_preserved else 'MISSING - need to preserve history'}")

# 6. Check V14PM runner for TON references that need updating
with open('trading/spot/run_v14_portfolio_live_aster.py', 'r', encoding='utf-8') as f:
    runner_src = f.read()

ton_in_runner = 'TON' in runner_src and 'TON/' in runner_src
print(f"\n=== V14PM Runner TON References ===")
if ton_in_runner:
    lines = runner_src.split('\n')
    for i, line in enumerate(lines):
        if 'TON/' in line and '#' not in line[:line.index('TON/')]:
            print(f"  L{i+1}: {line.strip()}")
else:
    print("  No TON references found (symbols come from exchange/config at runtime)")

# 7. Check for syntax errors via import
print("\n=== Syntax Check ===")
try:
    compile(collector_src, 'collect_scanner_candles.py', 'exec')
    print("Collector: syntax OK")
except SyntaxError as e:
    print(f"Collector: SYNTAX ERROR at line {e.lineno}: {e.msg}")

try:
    compile(scanner_src, 'v14_cycle_scanner.py', 'exec')
    print("Scanner: syntax OK")
except SyntaxError as e:
    print(f"Scanner: SYNTAX ERROR at line {e.lineno}: {e.msg}")

# 8. Check DB: does GRAM/USDT or HYPE/USDT have any existing candles?
print("\n=== DB State ===")
conn = sqlite3.connect('trading/spot/data/candles.db')
cur = conn.cursor()
for sym in ['GRAM/USDT', 'HYPE/USDT', 'HYPE/USDC', 'TON/USDT']:
    cur.execute("SELECT COUNT(*) FROM candles WHERE symbol = ? AND timeframe = '1h'", (sym,))
    count = cur.fetchone()[0]
    print(f"  {sym}: {count:,} candles in DB")
conn.close()

# 9. Quote currency consistency with V14PM
print("\n=== V14PM Symbol Consistency ===")
import json
with open('trading/spot/live/v14pm/status.json', 'r', encoding='utf-8') as f:
    pm = json.load(f)
pm_symbols = pm.get('symbols', [])
print(f"V14PM tracked symbols: {pm_symbols}")
# Check which PM symbols are in collector active (by full symbol)
collector_active_syms = set(db for db, _ in collector_active_pairs)
for sym in pm_symbols:
    in_active = sym in collector_active_syms
    coin = sym.split('/')[0]
    in_watch = coin in collector_watch
    tag = "ACTIVE" if in_active else ("WATCHLIST" if in_watch else "MISSING")
    print(f"  {sym}: {tag}")
