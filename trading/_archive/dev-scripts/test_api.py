import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Load env
env = {}
with open(os.path.join(os.path.dirname(__file__), 'live', '.env')) as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            env[k] = v

import ccxt
ex = ccxt.binance({
    'apiKey': env.get('ASTER_API_KEY', ''),
    'secret': env.get('ASTER_SECRET', ''),
    'options': {'defaultType': 'future'}
})
# Patch URLs for Aster
for k in ex.urls['api']:
    if isinstance(ex.urls['api'][k], str):
        ex.urls['api'][k] = ex.urls['api'][k].replace('binance.com', 'aster.finance')

# Test 1: public ticker
try:
    t = ex.fetch_ticker('HYPE/USDT')
    print(f"TICKER OK: ${t['last']}")
except Exception as e:
    print(f"TICKER FAIL: {e}")

# Test 2: private balance
try:
    b = ex.fetch_balance()
    usdt = b.get('USDT', {}).get('free', '?')
    print(f"BALANCE OK: {usdt} USDT free")
except Exception as e:
    print(f"BALANCE FAIL: {e}")

# Test 3: open orders
try:
    o = ex.fetch_open_orders('HYPE/USDT')
    print(f"OPEN ORDERS OK: {len(o)} orders")
except Exception as e:
    print(f"OPEN ORDERS FAIL: {e}")

# Test 4: place + cancel a tiny limit buy far from market
try:
    order = ex.create_limit_buy_order('HYPE/USDT', 0.1, 10.0)
    print(f"ORDER PLACE OK: id={order['id']}")
    ex.cancel_order(order['id'], 'HYPE/USDT')
    print("ORDER CANCEL OK")
except Exception as e:
    print(f"ORDER PLACE/CANCEL FAIL: {e}")
