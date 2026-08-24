"""Final verification of collector + scanner changes."""
import re

# 1. Syntax check both files
for fname in ['trading/spot/collect_scanner_candles.py', 'trading/spot/v14_cycle_scanner.py']:
    with open(fname, 'r', encoding='utf-8') as f:
        src = f.read()
    try:
        compile(src, fname, 'exec')
        print(f"{fname.split('/')[-1]}: compiles OK")
    except SyntaxError as e:
        print(f"{fname.split('/')[-1]}: SYNTAX ERROR line {e.lineno}: {e.msg}")

# 2. Scanner COINS verification
with open('trading/spot/v14_cycle_scanner.py', 'r', encoding='utf-8') as f:
    scanner = f.read()

coins_match = re.search(r'COINS\s*=\s*\[(.*?)\]', scanner, re.DOTALL)
coins_block = coins_match.group(1) if coins_match else ''

# Extract actual symbols (ignore comments)
scanner_syms = re.findall(r"'([A-Z]+/USD[TC])'", coins_block)

print(f"\nScanner COINS: {len(scanner_syms)} symbols")
print(f"  Symbols: {scanner_syms}")

checks = {
    'GRAM/USDT present': 'GRAM/USDT' in scanner_syms,
    'TON/USDT absent': 'TON/USDT' not in scanner_syms,
    'HYPE/USDT present': 'HYPE/USDT' in scanner_syms,
    'HYPE/USDC absent': 'HYPE/USDC' not in scanner_syms,
    'MKR/USDT absent': 'MKR/USDT' not in scanner_syms,
    'ASTER/USDT present': 'ASTER/USDT' in scanner_syms,
    'Watchlist comment': 'collect_scanner_candles.py' in scanner,
}

print("\nScanner checks:")
for label, ok in checks.items():
    print(f"  {'OK' if ok else 'FAIL'}: {label}")

# 3. Collector ACTIVE_UNIVERSE verification
with open('trading/spot/collect_scanner_candles.py', 'r', encoding='utf-8') as f:
    collector = f.read()

# Count active universe entries (non-commented tuples before WATCHLIST variable)
au_match = re.search(r'ACTIVE_UNIVERSE\s*=\s*\[(.*?)\]', collector, re.DOTALL)
au_block = au_match.group(1) if au_match else ''
au_pairs = re.findall(r'^\s*\("([^"]+)",\s*"([^"]+)"\)', au_block, re.MULTILINE)

wl_match = re.search(r'WATCHLIST\s*=\s*\[(.*?)\]', collector, re.DOTALL)
wl_block = wl_match.group(1) if wl_match else ''
wl_pairs = re.findall(r'^\s*\("([^"]+)",\s*"([^"]+)"\)', wl_block, re.MULTILINE)

uc_match = re.search(r'USDC_COINS\s*=\s*\[(.*?)\]', collector, re.DOTALL)
uc_block = uc_match.group(1) if uc_match else ''
uc_pairs = re.findall(r'^\s*\("([^"]+)",\s*"([^"]+)"\)', uc_block, re.MULTILINE)

print(f"\nCollector counts:")
print(f"  ACTIVE_UNIVERSE: {len(au_pairs)} pairs")
print(f"  WATCHLIST: {len(wl_pairs)} pairs")
print(f"  USDC_COINS: {len(uc_pairs)} pairs")

au_coins = set(p[0].split('/')[0] for p in au_pairs)
wl_coins = set(p[0].split('/')[0] for p in wl_pairs)

collector_checks = {
    'GRAM/USDT in active': any(p[0] == 'GRAM/USDT' for p in au_pairs),
    'TON/USDT not in active': not any(p[0] == 'TON/USDT' for p in au_pairs),
    'HYPE/USDT in active': any(p[0] == 'HYPE/USDT' for p in au_pairs),
    'HYPE/USDC in USDC_COINS': any(p[0] == 'HYPE/USDC' for p in uc_pairs),
    'TRUMP/USDC in USDC_COINS': any(p[0] == 'TRUMP/USDC' for p in uc_pairs),
    'APT in watchlist': 'APT' in wl_coins,
    'JTO in watchlist': 'JTO' in wl_coins,
    'BERA in watchlist': 'BERA' in wl_coins,
    'No overlap active/watchlist': len(au_coins & wl_coins) == 0,
    'main() uses ACTIVE_UNIVERSE': 'ACTIVE_UNIVERSE + WATCHLIST + USDC_COINS' in collector,
}

print("\nCollector checks:")
for label, ok in collector_checks.items():
    print(f"  {'OK' if ok else 'FAIL'}: {label}")

# 4. Cross-check: scanner COINS base coins should match collector ACTIVE_UNIVERSE base coins
# (minus ASTER which is on a different exchange)
scanner_coins = set(s.split('/')[0] for s in scanner_syms)
scanner_no_aster = scanner_coins - {'ASTER'}
au_no_aster = au_coins

only_scanner = scanner_no_aster - au_no_aster
only_collector = au_no_aster - scanner_no_aster

print(f"\nCross-check (ignoring ASTER):")
print(f"  Scanner-only: {sorted(only_scanner) if only_scanner else 'None'}")
print(f"  Collector-only: {sorted(only_collector) if only_collector else 'None'}")
if not only_scanner and not only_collector:
    print("  MATCH: Scanner and collector active universes are aligned")
