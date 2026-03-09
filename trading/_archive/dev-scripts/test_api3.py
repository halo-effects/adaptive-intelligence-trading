import os, sys, time, hmac, hashlib, requests, winreg

with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Environment') as k:
    api_key = winreg.QueryValueEx(k, 'ASTER_API_KEY')[0]
    api_secret = winreg.QueryValueEx(k, 'ASTER_API_SECRET')[0]

base = "https://fapi.asterdex.com"
session = requests.Session()
session.headers.update({"X-MBX-APIKEY": api_key})

def signed(method, path, params=None):
    if params is None: params = {}
    params['timestamp'] = int(time.time() * 1000)
    params['recvWindow'] = 10000
    qs = '&'.join(f'{k}={v}' for k, v in params.items())
    sig = hmac.new(api_secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
    url = f'{base}{path}?{qs}&signature={sig}'
    return getattr(session, method.lower())(url, timeout=10)

# Place limit buy: 1 HYPE @ $10 = $10 notional > $5 min
r = signed('POST', '/fapi/v1/order', {
    'symbol': 'HYPEUSDT', 'side': 'BUY', 'type': 'LIMIT',
    'timeInForce': 'GTC', 'quantity': '1', 'price': '10.00'
})
if r.status_code == 200:
    oid = r.json()['orderId']
    print(f"ORDER PLACE OK: {oid}")
    r2 = signed('DELETE', '/fapi/v1/order', {'symbol': 'HYPEUSDT', 'orderId': oid})
    print(f"ORDER CANCEL: {r2.status_code} {r2.json().get('status','?')}")
else:
    print(f"ORDER FAIL: {r.status_code} {r.text[:300]}")
