import ccxt, os, json

client = ccxt.aster({
    'apiKey': os.environ.get('ASTER_API_KEY', ''),
    'secret': os.environ.get('ASTER_API_SECRET', ''),
    'options': {'defaultType': 'swap'},
    'timeout': 15000
})

# Exchange truth
orders = client.fetch_open_orders('GRASS/USDT:USDT')
for o in orders:
    print(f"Exchange order: {o['side']} {o['amount']} @ {o['price']} (id={o['id']})")

positions = client.fetch_positions(['GRASS/USDT:USDT'])
for p in positions:
    qty = float(p.get('contracts', 0) or 0)
    if qty > 0:
        print(f"Exchange position: {qty} GRASS @ {p['entryPrice']}")

# Status.json
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json") as f:
    s = json.load(f)
grass = s.get('coins', {}).get('GRASS/USDT', {})
print(f"\nDashboard shows:")
print(f"  next_tp_price: {grass.get('next_tp_price')}")
print(f"  avg_entry: {grass.get('avg_entry')}")
print(f"  layers: {grass.get('layers')}")
print(f"  invested: {grass.get('invested')}")

# State.json
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json") as f:
    st = json.load(f)
gs = st.get('coins', {}).get('GRASS/USDT', {})
print(f"\nState file:")
print(f"  tp_order_id: {gs.get('tp_order_id')}")
print(f"  tp_limit_price: {gs.get('tp_limit_price')}")
eng = gs.get('engine_state', {})
print(f"  engine long_tp: {eng.get('long_tp')}")
print(f"  engine long_avg_entry: {eng.get('long_avg_entry')}")
print(f"  engine long_layers: {eng.get('long_layers')}")
print(f"  engine long_coins: {eng.get('long_coins')}")
print(f"  engine long_cost: {eng.get('long_cost')}")
