"""Check Aster trade history for GRASS to determine actual layer count."""
import ccxt, os, json
from datetime import datetime, timezone

ex = ccxt.aster({
    'apiKey': os.environ.get('ASTER_API_KEY', ''),
    'secret': os.environ.get('ASTER_API_SECRET', ''),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
    'timeout': 15000,
})
ex.load_markets()

# Fetch recent trades/orders for GRASS
symbol = 'GRASS/USDT:USDT'

# Try fetching closed orders
try:
    orders = ex.fetch_closed_orders(symbol, limit=50)
    print(f"=== Closed Orders ({len(orders)}) ===")
    for o in orders:
        ts = datetime.fromtimestamp(o['timestamp']/1000, tz=timezone.utc)
        print(f"  {ts.strftime('%m-%d %H:%M')} | {o['side']:4s} | {o['type']:6s} | "
              f"qty={o.get('filled', o.get('amount', 0)):.2f} | "
              f"price=${o.get('average', o.get('price', 0)):.6f} | "
              f"cost=${o.get('cost', 0):.2f} | status={o.get('status')}")
except Exception as e:
    print(f"fetch_closed_orders failed: {e}")

# Also try my_trades
try:
    trades = ex.fetch_my_trades(symbol, limit=50)
    print(f"\n=== My Trades ({len(trades)}) ===")
    for t in trades:
        ts = datetime.fromtimestamp(t['timestamp']/1000, tz=timezone.utc)
        print(f"  {ts.strftime('%m-%d %H:%M')} | {t['side']:4s} | "
              f"qty={t.get('amount', 0):.2f} | "
              f"price=${t.get('price', 0):.6f} | "
              f"cost=${t.get('cost', 0):.2f} | "
              f"fee={t.get('fee', {}).get('cost', 0):.4f}")
except Exception as e:
    print(f"fetch_my_trades failed: {e}")
