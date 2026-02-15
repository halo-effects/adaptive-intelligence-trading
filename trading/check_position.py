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

# Position
r = s.get(base+'/fapi/v2/positionRisk', params=sign({'symbol': 'HYPEUSDT'}), timeout=15)
for p in r.json():
    if float(p.get('positionAmt', 0)) != 0:
        print(f"Position: {p['positionAmt']} @ {p['entryPrice']} | Margin: {p['isolatedMargin']} | Leverage: {p['leverage']}")

# Account info
r2 = s.get(base+'/fapi/v2/account', params=sign({}), timeout=15)
acct = r2.json()
print(f"Total Balance: {acct['totalWalletBalance']}")
print(f"Available: {acct['availableBalance']}")
print(f"Total Margin: {acct['totalInitialMargin']}")
print(f"Total Unrealized PnL: {acct['totalUnrealizedProfit']}")

# Open orders
r3 = s.get(base+'/fapi/v1/openOrders', params=sign({'symbol': 'HYPEUSDT'}), timeout=15)
orders = r3.json()
print(f"\nOpen orders: {len(orders)}")
for o in orders:
    print(f"  {o['orderId']} {o['side']} {o['origQty']} @ {o['price']} type={o['type']}")
