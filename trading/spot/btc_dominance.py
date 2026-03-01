"""BTC Dominance helper for V14 trading system.

Fetches current BTC dominance from CoinGecko free API.
Called alongside CFGI poll in the V14 runner.
"""

import urllib.request
import json
import time


def fetch_btc_dominance() -> dict:
    """Fetch current BTC dominance from CoinGecko.
    
    Returns:
        {
            'dominance_pct': float,      # e.g. 58.5
            'btc_market_cap': float,     # in USD
            'total_market_cap': float,   # in USD
            'timestamp': int             # unix timestamp
        }
    
    Raises:
        Exception on API failure
    """
    url = 'https://api.coingecko.com/api/v3/global'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    
    global_data = data['data']
    btc_dominance = global_data['market_cap_percentage']['btc']
    total_market_cap = global_data['total_market_cap']['usd']
    btc_market_cap = total_market_cap * (btc_dominance / 100)
    
    return {
        'dominance_pct': round(btc_dominance, 2),
        'btc_market_cap': btc_market_cap,
        'total_market_cap': total_market_cap,
        'timestamp': int(time.time())
    }


if __name__ == '__main__':
    result = fetch_btc_dominance()
    print(f"BTC Dominance: {result['dominance_pct']}%")
    print(f"BTC Market Cap: ${result['btc_market_cap']/1e12:.2f}T")
    print(f"Total Market Cap: ${result['total_market_cap']/1e12:.2f}T")
