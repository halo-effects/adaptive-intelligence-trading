"""Test that all collector symbols resolve on Hyperliquid."""
import ccxt

hl = ccxt.hyperliquid()
_orig = hl.fetch_spot_markets
def _safe(*a, **k):
    try:
        return _orig(*a, **k)
    except TypeError:
        return []
hl.fetch_spot_markets = _safe
hl.load_markets()

test_symbols = [
    ('GRAM/USDC:USDC', 'Active universe - was TON'),
    ('HYPE/USDC:USDC', 'Active universe + USDC_COINS'),
    ('APT/USDC:USDC', 'Watchlist'),
    ('JTO/USDC:USDC', 'Watchlist'),
    ('BERA/USDC:USDC', 'Watchlist'),
    ('TRUMP/USDC:USDC', 'Watchlist'),
    ('S/USDC:USDC', 'Watchlist'),
    ('VIRTUAL/USDC:USDC', 'Watchlist'),
    ('GRASS/USDC:USDC', 'Watchlist'),
    ('INIT/USDC:USDC', 'Watchlist'),
    ('MOVE/USDC:USDC', 'Watchlist'),
]

print('=== HL Symbol Resolution ===')
all_ok = True
for sym, note in test_symbols:
    exists = sym in hl.symbols
    status = 'OK' if exists else 'MISSING'
    if not exists:
        all_ok = False
    print('  %-25s %s  (%s)' % (sym, status, note))

if all_ok:
    print('\nAll symbols resolve: YES')
else:
    print('\nAll symbols resolve: NO - check failures above')

# Test GRAM candle fetch
print('\n=== GRAM candle fetch test ===')
try:
    candles = hl.fetch_ohlcv('GRAM/USDC:USDC', '1h', limit=3)
    if candles:
        print('  Got %d candles. Latest close: %s' % (len(candles), candles[-1][4]))
    else:
        print('  No candles returned')
except Exception as e:
    print('  FAILED: %s' % e)
