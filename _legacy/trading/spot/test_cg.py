import requests
print('Testing CoinGecko...', flush=True)
r = requests.get('https://api.coingecko.com/api/v3/coins/bitcoin?localization=false&tickers=false&community_data=false&developer_data=false', timeout=15)
print(f'Status: {r.status_code}', flush=True)
data = r.json()
price = data.get('market_data', {}).get('current_price', {}).get('usd')
print(f'Price: {price}', flush=True)
