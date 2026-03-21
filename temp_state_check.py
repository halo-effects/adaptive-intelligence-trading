import json
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json") as f:
    state = json.load(f)
engines = state.get("engine_states", {})
for sym, es in engines.items():
    print(f"{sym}:")
    for k in ["long_coins", "long_cost", "long_avg_entry", "long_layers", "long_tp", "capital"]:
        print(f"  {k}: {es.get(k)}")
router = state.get("router", {})
print(f"router active_cash: {router.get('active_pool_cash')}")
print(f"router reserve_cash: {router.get('reserve_pool_cash')}")
print(f"router allocations: {router.get('active_allocations')}")

# Check what exchange actually has
import ccxt, os
client = ccxt.aster({
    'apiKey': os.environ.get('ASTER_API_KEY', ''),
    'secret': os.environ.get('ASTER_API_SECRET', ''),
    'options': {'defaultType': 'swap'},
    'timeout': 15000
})
bal = client.fetch_balance({"type": "future"})
usdt = bal.get("USDT", {})
print(f"\nExchange USDT free: {usdt.get('free')}")
print(f"Exchange USDT total: {usdt.get('total')}")
positions = client.fetch_positions()
for p in positions:
    c = float(p.get('contracts', 0) or 0)
    if c > 0:
        print(f"Position: {p['symbol']} qty={c} entry={p.get('entryPrice')} upnl={p.get('unrealizedPnl')}")
