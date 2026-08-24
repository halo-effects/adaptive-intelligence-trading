import re

with open('trading/spot/collect_scanner_candles.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract all tuples from UNIVERSE
pattern = r'\("([^"]+)",\s*"([^"]+)"\)'
pairs = re.findall(pattern, content)

print("Collector mapping (DB symbol -> HL symbol):")
print("%-20s -> %s" % ("DB (Binance)", "Hyperliquid"))
print("-" * 55)
for db_sym, hl_sym in pairs:
    print("%-20s -> %s" % (db_sym, hl_sym))

print("\nTotal pairs: %d" % len(pairs))

# Identify quote currency mismatches
print("\n=== Quote currency analysis ===")
usdt_db = [p for p in pairs if '/USDT' in p[0]]
usdc_db = [p for p in pairs if '/USDC' in p[0]]
print("DB symbols using USDT: %d" % len(usdt_db))
print("DB symbols using USDC: %d" % len(usdc_db))

# All HL symbols use USDC:USDC perps
hl_usdc = [p for p in pairs if 'USDC:USDC' in p[1]]
print("HL symbols using USDC perps: %d" % len(hl_usdc))

# So the pattern is: Binance candles in USDT, HL trades in USDC perps
# The scanner uses Binance for history, HL for live trading
