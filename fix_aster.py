import sys, os, time
sys.path.insert(0, 'C:/Users/Never/.openclaw/workspace')

def load_env(path):
    with open(path) as f:
        for line in f:
            if '=' in line:
                k, v = line.strip().split('=', 1)
                os.environ[k] = v.strip('\"')

load_env('C:/Users/Never/.openclaw/workspace/trading/spot/live/v14/.env')

from trading.spot.exchange_client import SpotExchangeClient

try:
    client = SpotExchangeClient()
    client.connect('aster')
    
    bal = client.exchange.fetch_balance()
    aster_free = bal.get('ASTER', {}).get('free', 0)
    print('Current ASTER:', aster_free)
    
    excess = aster_free - 126.33
    if excess > 0:
        sell_qty = int(excess * 100) / 100.0
        print('Selling excess ASTER at market:', sell_qty)
        order = client.create_market_sell('ASTER/USDT', sell_qty)
        print('Sold successfully:', order.get('id', 'N/A'))
    else:
        print('No excess ASTER found.')
except Exception as e:
    import traceback
    traceback.print_exc()
