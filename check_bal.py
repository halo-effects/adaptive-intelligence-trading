import sys, os
sys.path.insert(0, 'C:/Users/Never/.openclaw/workspace')

def load_env(path):
    with open(path) as f:
        for line in f:
            if '=' in line:
                k, v = line.strip().split('=', 1)
                os.environ[k] = v.strip('\"\n')

load_env('C:/Users/Never/.openclaw/workspace/trading/spot/live/v14/.env')

from trading.spot.exchange_client import SpotExchangeClient

try:
    client = SpotExchangeClient()
    client.connect('aster')
    
    bal = client.exchange.fetch_balance()
    aster_free = bal.get('ASTER', {}).get('free', 0)
    aster_total = bal.get('ASTER', {}).get('total', 0)
    usdt_free = bal.get('USDT', {}).get('free', 0)
    usdt_total = bal.get('USDT', {}).get('total', 0)
    
    print('REAL EXCHANGE BALANCE:')
    print(f'ASTER: {aster_free} free / {aster_total} total')
    print(f'USDT:  {usdt_free} free / {usdt_total} total')
except Exception as e:
    import traceback
    traceback.print_exc()
