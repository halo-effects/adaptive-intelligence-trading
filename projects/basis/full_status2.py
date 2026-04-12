import sys, os, json, time
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv('C:/Users/Never/.openclaw/workspace/projects/basis/skill-scaffold/.env')
from basis import BasisClient
import urllib.request

API_KEY = os.environ.get('BASIS_API_KEY')
BASE = 'https://launchonbasis.com'

def api_get(path):
    """Direct REST call with API key auth"""
    req = urllib.request.Request(
        f'{BASE}{path}',
        headers={'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

client = BasisClient.create(private_key=os.environ['BASIS_PRIVATE_KEY'], api_key=API_KEY)
wallet = client.account.address

print(f'Wallet: {wallet}')
print(f'USDB: {client.usdb_address}')
print(f'STASIS: {client.main_token_address}')

# Balances via balanceOf
def get_balance(token_addr):
    bal = client.web3.eth.call({
        'to': token_addr,
        'data': '0x70a08231' + wallet[2:].lower().zfill(64)
    })
    return int(bal.hex(), 16) / 10**18

print(f'\n=== Balances ===')
print(f'USDB: {get_balance(client.usdb_address):.4f}')
print(f'STASIS: {get_balance(client.main_token_address):.4f}')
print(f'BNB: {client.web3.eth.get_balance(wallet) / 10**18:.6f}')

# STASIS price
price = client.trading.get_usd_price(client.main_token_address)
print(f'STASIS price: ${int(price) / 10**18:.4f}')

# Staking
details = client.staking.get_user_stake_details(wallet)
print(f'\n=== Staking ===')
print(f'Locked wSTASIS shares: {details[1] / 10**18:.10f}')
print(f'Total STASIS value: {details[3] / 10**18:.10f}')

# Loans
print(f'\n=== Loans ===')
count = client.loans.get_user_loan_count(wallet)
now = int(time.time())
for i in range(1, count + 1):
    loan = client.loans.get_user_loan_details(wallet, i)
    # Tuple: (hubId, ecosystem, coreLoanId, collateralToken, token, collateralAmount, 
    #  liquidatedAmount, fullAmount, borrowedAmount, liquidationTime, liquidationClaim,
    #  isLiquidated, active, creationTime)
    active = loan[12]
    liq_time = loan[9]
    collateral = loan[5] / 10**18
    borrowed = loan[8] / 10**18
    full_amt = loan[7] / 10**18
    days_left = (liq_time - now) / 86400
    print(f'  Loan {i}: active={active}, collateral={collateral:.4f}, borrowed={borrowed:.4f}, '
          f'repay={full_amt:.4f}, expires in {days_left:.1f} days')

# Try REST API for tokens
print(f'\n=== Prediction Markets (REST) ===')
try:
    data = api_get('/api/v1/tokens?isPrediction=true&limit=5&sort=newest')
    if 'data' in data:
        for t in data['data']:
            print(f"  {t.get('symbol','?')} | {t.get('name','?')[:50]} | "
                  f"status: {t.get('predictionStatus','?')} | addr: {t.get('address','?')}")
    else:
        print(data)
except Exception as e:
    print(f'Error: {e}')

print(f'\n=== Floor+ Tokens (REST) ===')
try:
    data = api_get('/api/v1/tokens?limit=30&sort=newest')
    if 'data' in data:
        for t in data['data']:
            mult = t.get('multiplier', 100)
            if mult is not None and int(mult) < 100:
                liq = t.get('liquidityUSD', 0)
                print(f"  {t.get('symbol','?')} | mult={mult} | liq=${liq} | "
                      f"addr: {t.get('address','?')}")
except Exception as e:
    print(f'Error: {e}')

# Faucet
print(f'\n=== Faucet (REST) ===')
try:
    data = api_get('/api/v1/faucet/status')
    print(json.dumps(data, indent=2))
except Exception as e:
    print(f'Error: {e}')

# Profile
print(f'\n=== Profile (REST) ===')
try:
    data = api_get('/api/v1/me/profile')
    print(json.dumps(data, indent=2))
except Exception as e:
    print(f'Error: {e}')

# Moltbook
print(f'\n=== Moltbook (REST) ===')
try:
    data = api_get('/api/moltbook/status')
    print(json.dumps(data, indent=2))
except Exception as e:
    print(f'Error: {e}')
