import ccxt, os
api_key = os.environ.get("ASTER_API_KEY", "")
api_secret = os.environ.get("ASTER_API_SECRET", "")
if not api_key:
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Environment') as k:
        api_key = winreg.QueryValueEx(k, 'ASTER_API_KEY')[0]
        api_secret = winreg.QueryValueEx(k, 'ASTER_API_SECRET')[0]

# Check futures balance
print("=== Futures wallet ===")
ex_fut = ccxt.aster({'apiKey': api_key, 'secret': api_secret, 'options': {'defaultType': 'future'}})
bal = ex_fut.fetch_balance()
print(f"  USDT: free={bal['USDT']['free']}, total={bal['USDT']['total']}")

# Check spot balance
print("\n=== Spot wallet ===")
ex_spot = ccxt.aster({'apiKey': api_key, 'secret': api_secret, 'options': {'defaultType': 'spot'}})
bal = ex_spot.fetch_balance()
usdt = bal.get('USDT', {})
print(f"  USDT: free={usdt.get('free',0)}, total={usdt.get('total',0)}")
for asset, v in bal.items():
    if isinstance(v, dict) and v.get('total',0) and v['total'] > 0 and asset not in ('info','free','used','total','timestamp','datetime'):
        print(f"  {asset}: free={v['free']}, total={v['total']}")
