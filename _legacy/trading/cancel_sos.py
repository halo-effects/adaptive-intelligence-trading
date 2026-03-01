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

# Cancel deep Short SOs
to_cancel = [1405092994, 1405093027, 1405093069]
for oid in to_cancel:
    r = s.delete(base+'/fapi/v1/order', params=sign({'symbol': 'HYPEUSDT', 'orderId': str(oid)}), timeout=15)
    data = r.json()
    status = data.get('status', data.get('msg', 'unknown'))
    print(f"Cancel {oid}: {r.status_code} - {status}")

# Check balance
time.sleep(1)
r2 = s.get(base+'/fapi/v2/balance', params=sign({}), timeout=15)
for b in r2.json():
    if b['asset'] == 'USDT':
        print(f"Available balance: {b['availableBalance']} USDT")
