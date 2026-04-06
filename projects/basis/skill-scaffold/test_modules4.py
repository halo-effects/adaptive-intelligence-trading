import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from dotenv import load_dotenv
import os, json, time, inspect
load_dotenv()
from basis import BasisClient
pk = os.getenv('BASIS_PRIVATE_KEY')
client = BasisClient.create(private_key=pk, api_key='skip')
client.authenticate()
wallet = client.account.address
geegee_token = '0xbb8c70bDC0Fe13B25753E81Af676c23DdcfD6e28'
stasis = client.main_token_address

def tx_hash(result):
    return result.get('hash', 'no hash') if isinstance(result, dict) else str(result)

from web3 import Web3

print('=== STAKING: Lock STASIS (fresh balance check) ===')
stasis_c = client.web3.eth.contract(address=Web3.to_checksum_address(stasis), abi=client.trading.erc20_abi)
stasis_bal = stasis_c.functions.balanceOf(wallet).call()
print(f'STASIS in wallet: {stasis_bal / 1e18}')

try:
    if stasis_bal > 0:
        result = client.staking.lock(stasis_bal)
        print(f'lock: tx={tx_hash(result)}')
        details = client.staking.get_user_stake_details(wallet)
        print(f'stake details after lock: {json.dumps(details, default=str)}')
except Exception as e:
    print(f'lock ERROR: {e}')

print()
print('=== STAKING: Borrow ===')
try:
    details = client.staking.get_user_stake_details(wallet)
    print(f'stake details: {json.dumps(details, default=str)}')
    # borrow 5 USDB for 7 days
    result = client.staking.borrow(5 * 10**18, 7)
    print(f'borrow: tx={tx_hash(result)}')
    count = client.loans.get_user_loan_count(wallet)
    print(f'loan count: {count}')
    if count > 0:
        loan = client.loans.get_user_loan_details(wallet, count - 1)
        print(f'latest loan: {json.dumps(loan, default=str)[:400]}')
except Exception as e:
    print(f'borrow ERROR: {e}')

print()
print('=== PREDICTION MARKETS: Create with seed ===')
try:
    # "Seed below minimum" - need to check what minimum is
    # Let's check the create_market source more carefully
    sig = inspect.signature(client.prediction_markets.create_market_with_metadata)
    print(f'Sig: {sig}')
    # Try with seed_amount
    end = int(time.time()) + 86400 * 8
    result = client.prediction_markets.create_market_with_metadata(
        market_name="Will Basis have 10+ agents by Phase 1 end?",
        symbol="AGENTS10",
        end_time=end,
        option_names=["Yes", "No"],
        maintoken=stasis,
        description="First prediction market on Basis",
        seed_amount=10 * 10**18,  # seed with 10 USDB
    )
    print(f'create market: {tx_hash(result)}')
    if isinstance(result, dict):
        print(f'market token: {result.get("market_token_address", "unknown")}')
except Exception as e:
    print(f'create market ERROR: {e}')

print()
print('=== LEVERAGE: Buy with correct args ===')
try:
    path = [client.usdb_address, stasis, geegee_token]
    # leverage_buy(amount, min_out, path, number_of_days)
    result = client.trading.leverage_buy(10 * 10**18, 0, path, 7)
    print(f'leverage buy: tx={tx_hash(result)}')
    lev_count = client.trading.get_leverage_count(wallet)
    print(f'leverage count: {lev_count}')
    if lev_count > 0:
        pos = client.trading.get_leverage_position(wallet, lev_count - 1)
        print(f'position: {json.dumps(pos, default=str)[:400]}')
except Exception as e:
    print(f'leverage ERROR: {e}')

print()
print('=== VESTING: Create with correct params ===')
try:
    # create_gradual_vesting(beneficiary, token, total_amount, start_time, duration_in_days, time_unit, memo, ecosystem)
    result = client.vesting.create_gradual_vesting(
        beneficiary=wallet,
        token=geegee_token,
        total_amount=5 * 10**18,
        start_time=int(time.time()) + 3600,
        duration_in_days=7,
        time_unit=86400,  # daily
        memo="Test vesting from GeeGee",
        ecosystem=geegee_token,  # not sure what this should be
    )
    print(f'create vesting: tx={tx_hash(result)}')
except Exception as e:
    print(f'vesting ERROR: {e}')

print()
print('=== SELL PERCENTAGE test ===')
try:
    sig = inspect.signature(client.trading.sell_percentage)
    print(f'sell_percentage sig: {sig}')
except Exception as e:
    print(f'sig ERROR: {e}')

print()
print('=== API: get_tokens requires API key ===')
try:
    # Try with API key from env
    api_key = os.getenv('BASIS_API_KEY', '')
    if api_key:
        headers = {'X-API-Key': api_key}
        import requests
        r = requests.get(f'{client.api_domain}/api/v1/tokens?sort=newest&page=1&limit=5', headers=headers)
        print(f'get_tokens with API key: {r.status_code} - {r.text[:300]}')
    else:
        print('No API key in env')
except Exception as e:
    print(f'get_tokens API key ERROR: {e}')

print()
print('=== FINAL BALANCES ===')
usdb_c = client.web3.eth.contract(address=Web3.to_checksum_address(client.usdb_address), abi=client.trading.erc20_abi)
usdb_bal = usdb_c.functions.balanceOf(wallet).call()
stasis_bal = stasis_c.functions.balanceOf(wallet).call()
geegee_c = client.web3.eth.contract(address=Web3.to_checksum_address(geegee_token), abi=client.trading.erc20_abi)
geegee_bal = geegee_c.functions.balanceOf(wallet).call()
print(f'USDB: {usdb_bal / 1e18}')
print(f'STASIS: {stasis_bal / 1e18}')
print(f'GEEGEE: {geegee_bal / 1e18}')

print()
print('=== DONE ===')
