import hmac, hashlib, time, urllib.parse, requests, winreg

with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Environment') as k:
    api_key = winreg.QueryValueEx(k, 'ASTER_API_KEY')[0]
    api_secret = winreg.QueryValueEx(k, 'ASTER_API_SECRET')[0]

base = 'https://fapi.asterdex.com'
s = requests.Session()
s.headers.update({'X-MBX-APIKEY': api_key})

def sign(p):
    p['timestamp'] = str(int(time.time()*1000))
    p['recvWindow'] = '5000'
    qs = urllib.parse.urlencode(p)
    p['signature'] = hmac.new(api_secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
    return p

# Cancel ALL open orders
r = s.delete(base+'/fapi/v1/allOpenOrders', params=sign({'symbol': 'HYPEUSDT'}), timeout=15)
print(f"Cancel all: {r.status_code} - {r.text[:200]}")

# Close any open position
time.sleep(1)
r2 = s.get(base+'/fapi/v2/positionRisk', params=sign({'symbol': 'HYPEUSDT'}), timeout=15)
for p in r2.json():
    amt = float(p.get('positionAmt', 0))
    if amt != 0:
        side = 'SELL' if amt > 0 else 'BUY'
        qty = abs(amt)
        print(f"Closing position: {side} {qty}")
        r3 = s.post(base+'/fapi/v1/order', params=sign({
            'symbol': 'HYPEUSDT', 'side': side, 'type': 'MARKET', 'quantity': str(qty)
        }), timeout=15)
        print(f"Close: {r3.status_code}")
    else:
        print("No open position")

# Final balance
time.sleep(1)
r4 = s.get(base+'/fapi/v2/balance', params=sign({}), timeout=15)
for b in r4.json():
    if b['asset'] == 'USDT':
        print(f"Final balance: {b['availableBalance']} USDT")
