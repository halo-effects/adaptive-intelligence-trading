"""GAP-09: Does Aster's usdt_total already include unrealized PnL?"""
import ccxt, os

ex = ccxt.aster({
    'apiKey': os.environ.get('ASTER_API_KEY', ''),
    'secret': os.environ.get('ASTER_API_SECRET', ''),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
    'timeout': 15000,
})
ex.load_markets()

bal = ex.fetch_balance({'type': 'future'})
usdt = bal.get('USDT', {})
free = float(usdt.get('free', 0))
used = float(usdt.get('used', 0))
total = float(usdt.get('total', 0))

print(f"USDT free:  {free:.4f}")
print(f"USDT used:  {used:.4f}")
print(f"USDT total: {total:.4f}")
print(f"free + used = {free + used:.4f}")
print(f"diff (total - free - used) = {total - free - used:.4f}")

pos = ex.fetch_positions()
for p in pos:
    c = float(p.get('contracts', 0) or 0)
    if c > 0:
        unrealized = float(p.get('unrealizedPnl', 0) or 0)
        margin = float(p.get('initialMargin', 0) or 0)
        entry = float(p.get('entryPrice', 0) or 0)
        notional = entry * c
        print(f"\nPosition: {p['symbol']}")
        print(f"  unrealizedPnl: {unrealized:.4f}")
        print(f"  initialMargin: {margin:.4f}")
        print(f"  notional (entry*qty): {notional:.2f}")
        print(f"\n  total + unrealized = {total + unrealized:.4f}")
        print(f"  total - unrealized = {total - unrealized:.4f}")
        print(f"  free + notional = {free + notional:.4f}")
        print(f"\n  If total INCLUDES unrealized: equity = total = {total:.4f}")
        print(f"  If total EXCLUDES unrealized: equity = total + unrealized = {total + unrealized:.4f}")
