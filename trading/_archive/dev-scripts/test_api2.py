import os, sys, time, hmac, hashlib, requests

# Get keys from registry
try:
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Environment') as k:
        api_key = winreg.QueryValueEx(k, 'ASTER_API_KEY')[0]
        api_secret = winreg.QueryValueEx(k, 'ASTER_API_SECRET')[0]
except:
    print("FAIL: Could not read API keys from registry")
    sys.exit(1)

base = "https://fapi.asterdex.com"
session = requests.Session()
session.headers.update({"X-MBX-APIKEY": api_key})

def signed_request(method, path, params=None):
    if params is None:
        params = {}
    params['timestamp'] = int(time.time() * 1000)
    params['recvWindow'] = 10000
    qs = '&'.join(f'{k}={v}' for k, v in params.items())
    sig = hmac.new(api_secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
    qs += f'&signature={sig}'
    url = f'{base}{path}?{qs}'
    if method == 'GET':
        return session.get(url, timeout=10)
    else:
        return session.post(url, timeout=10)

# Test 1: Account info
try:
    r = signed_request('GET', '/fapi/v2/account')
    if r.status_code == 200:
        data = r.json()
        print(f"ACCOUNT OK: balance={data.get('totalWalletBalance','?')}")
    else:
        print(f"ACCOUNT FAIL: {r.status_code} {r.text[:300]}")
except Exception as e:
    print(f"ACCOUNT FAIL: {e}")

# Test 2: Open orders
try:
    r = signed_request('GET', '/fapi/v1/openOrders', {'symbol': 'HYPEUSDT'})
    if r.status_code == 200:
        print(f"OPEN ORDERS OK: {len(r.json())} orders")
    else:
        print(f"OPEN ORDERS FAIL: {r.status_code} {r.text[:300]}")
except Exception as e:
    print(f"OPEN ORDERS FAIL: {e}")

# Test 3: Place a tiny limit order far from market, then cancel
try:
    r = signed_request('POST', '/fapi/v1/order', {
        'symbol': 'HYPEUSDT',
        'side': 'BUY',
        'type': 'LIMIT',
        'timeInForce': 'GTC',
        'quantity': '0.1',
        'price': '10.00'
    })
    if r.status_code == 200:
        oid = r.json().get('orderId')
        print(f"ORDER PLACE OK: {oid}")
        # Cancel it
        r2 = signed_request('DELETE', '/fapi/v1/order', {'symbol': 'HYPEUSDT', 'orderId': oid})
        # DELETE not in our helper, use session directly
    else:
        print(f"ORDER PLACE FAIL: {r.status_code} {r.text[:300]}")
except Exception as e:
    print(f"ORDER PLACE FAIL: {e}")

# Cancel cleanup
try:
    params = {'symbol': 'HYPEUSDT', 'orderId': oid}
    params['timestamp'] = int(time.time() * 1000)
    params['recvWindow'] = 10000
    qs = '&'.join(f'{k}={v}' for k, v in params.items())
    sig = hmac.new(api_secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
    qs += f'&signature={sig}'
    r = session.delete(f'{base}/fapi/v1/order?{qs}', timeout=10)
    if r.status_code == 200:
        print("ORDER CANCEL OK")
    else:
        print(f"ORDER CANCEL: {r.status_code} {r.text[:200]}")
except:
    pass
