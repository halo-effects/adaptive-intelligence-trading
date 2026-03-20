import ccxt, os
client = ccxt.aster({
    'apiKey': os.environ.get('ASTER_API_KEY', ''),
    'secret': os.environ.get('ASTER_API_SECRET', ''),
    'options': {'defaultType': 'swap'},
    'timeout': 15000
})
orders = client.fetch_open_orders()
print(f"Total open orders: {len(orders)}")
for o in orders:
    print(f"  {o['id']}: {o['side']} {o['amount']} {o['symbol']} @ {o['price']}")
