import sys, os
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv('C:/Users/Never/.openclaw/workspace/projects/basis/skill-scaffold/.env')
from basis import BasisClient

client = BasisClient.create(private_key=os.environ['BASIS_PRIVATE_KEY'], api_key=os.environ.get('BASIS_API_KEY'))
wallet = client.account.address

print('=== Moltbook ===')
try:
    ms = client.api.get_moltbook_status()
    print(ms)
except Exception as e:
    print(f'Error: {e}')

print('\n=== Faucet ===')
try:
    fs = client.api.get_faucet_status()
    print(fs)
except Exception as e:
    print(f'Error: {e}')

print('\n=== Profile ===')
try:
    p = client.api.get_my_profile()
    print(p)
except Exception as e:
    print(f'Error: {e}')

print('\n=== Stats ===')
try:
    s = client.api.get_my_stats()
    print(s)
except Exception as e:
    print(f'Error: {e}')

print('\n=== STASIS Price ===')
try:
    price = client.trading.get_usd_price(client.main_token_address)
    print(f'STASIS USD price: {int(price) / 10**18:.6f}')
except Exception as e:
    print(f'Error: {e}')

print('\n=== Available STASIS for staking ===')
try:
    avail = client.staking.get_available_stasis(wallet)
    print(f'Available: {int(str(avail)) / 10**18:.6f}')
except Exception as e:
    print(f'Error: {e}')

print(f'\nStaking address: {client.staking.staking_address}')

print('\n=== Staking Details ===')
details = client.staking.get_user_stake_details(wallet)
print(f'Liquid shares: {details[0] / 10**18:.6f}')
print(f'Locked shares: {details[1] / 10**18:.6f}')
print(f'Total shares: {details[2] / 10**18:.6f}')
print(f'Total asset value (STASIS): {details[3] / 10**18:.6f}')

print('\n=== Active Prediction Markets ===')
try:
    tokens = client.api.get_tokens(is_prediction=True, limit=10)
    if isinstance(tokens, dict) and 'data' in tokens:
        for t in tokens['data']:
            print(f"  {t.get('symbol','?')} | {t.get('name','?')[:40]} | status: {t.get('predictionStatus','?')} | addr: {t.get('address','?')[:20]}...")
    else:
        print(tokens)
except Exception as e:
    print(f'Error: {e}')

print('\n=== Recent Floor+ Tokens ===')
try:
    all_tokens = client.api.get_tokens(limit=20, sort='newest')
    if isinstance(all_tokens, dict) and 'data' in all_tokens:
        for t in all_tokens['data']:
            mult = t.get('multiplier', '?')
            if mult != '?' and int(mult) < 100:
                print(f"  {t.get('symbol','?')} | mult={mult} | addr: {t.get('address','?')[:20]}... | liq: ${t.get('liquidityUSD', '?')}")
    else:
        print(all_tokens)
except Exception as e:
    print(f'Error: {e}')

print('\n=== BNB Balance ===')
try:
    bnb = client.web3.eth.get_balance(wallet)
    print(f'BNB: {bnb / 10**18:.6f}')
except Exception as e:
    print(f'Error: {e}')
