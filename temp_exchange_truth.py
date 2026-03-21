"""Fetch exchange position truth for comparison with engine state."""
import ccxt, os

ex = ccxt.aster({
    'apiKey': os.environ.get('ASTER_API_KEY', ''),
    'secret': os.environ.get('ASTER_API_SECRET', ''),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
    'timeout': 15000,
})
ex.load_markets()

positions = ex.fetch_positions()
for p in positions:
    contracts = float(p.get('contracts', 0) or 0)
    if contracts > 0:
        sym = p.get('symbol', '')
        entry = p.get('entryPrice', 0)
        unrealized = p.get('unrealizedPnl', 0)
        side = p.get('side', '')
        cost = float(entry) * contracts
        print(f"Position: {sym}")
        print(f"  qty: {contracts}")
        print(f"  entry: {entry}")
        print(f"  cost (qty*entry): {cost:.2f}")
        print(f"  unrealized: {unrealized}")
        print(f"  side: {side}")

bal = ex.fetch_balance({'type': 'future'})
usdt = bal.get('USDT', {})
print(f"\nUSDT free: {usdt.get('free')}")
print(f"USDT total: {usdt.get('total')}")
print(f"USDT used: {usdt.get('used')}")
