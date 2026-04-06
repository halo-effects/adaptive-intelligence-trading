import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from dotenv import load_dotenv
import os, json
load_dotenv()
from basis import BasisClient
pk = os.getenv('BASIS_PRIVATE_KEY')
client = BasisClient.create(private_key=pk, api_key='skip')
client.authenticate()
wallet = client.account.address
geegee_token = '0xbb8c70bDC0Fe13B25753E81Af676c23DdcfD6e28'

def tx_hash(result):
    return result.get('hash', 'no hash') if isinstance(result, dict) else str(result)

print('=== TRADING: Buy STASIS ===')
try:
    result = client.staking.buy(30 * 10**18)
    print(f'buy STASIS: tx={tx_hash(result)}')
except Exception as e:
    print(f'buy STASIS ERROR: {e}')

print()
print('=== STAKING: Lock in vault ===')
try:
    avail = client.staking.get_available_stasis(wallet)
    print(f'Available STASIS after buy: {avail}')
    if avail > 0:
        result = client.staking.lock(avail)
        print(f'lock STASIS: tx={tx_hash(result)}')
    else:
        print('No STASIS to lock')
except Exception as e:
    print(f'lock STASIS ERROR: {e}')

print()
print('=== STAKING: Check details after lock ===')
try:
    details = client.staking.get_user_stake_details(wallet)
    print(f'stake details: {json.dumps(details, default=str)}')
except Exception as e:
    print(f'stake details ERROR: {e}')

print()
print('=== STAKING: Borrow against locked STASIS ===')
try:
    result = client.staking.borrow(5 * 10**18)
    print(f'borrow: tx={tx_hash(result)}')
except Exception as e:
    print(f'borrow ERROR: {e}')

print()
print('=== LOANS: Check loan details ===')
try:
    count = client.loans.get_user_loan_count(wallet)
    print(f'loan count: {count}')
    if count > 0:
        for i in range(count):
            details = client.loans.get_user_loan_details(wallet, i)
            print(f'loan {i}: {json.dumps(details, default=str)[:300]}')
except Exception as e:
    print(f'loan details ERROR: {e}')

print()
print('=== TRADING: Sell some GEEGEE ===')
try:
    result = client.trading.sell(geegee_token, 10 * 10**18)
    print(f'sell GEEGEE: tx={tx_hash(result)}')
except Exception as e:
    print(f'sell GEEGEE ERROR: {e}')

print()
print('=== TRADING: Leverage buy GEEGEE ===')
try:
    result = client.trading.leverage_buy(geegee_token, 10 * 10**18)
    print(f'leverage_buy GEEGEE: tx={tx_hash(result)}')
except Exception as e:
    print(f'leverage_buy GEEGEE ERROR: {e}')

print()
print('=== TRADING: Check leverage positions ===')
try:
    count = client.trading.get_leverage_count(wallet)
    print(f'leverage count: {count}')
    if count > 0:
        for i in range(count):
            pos = client.trading.get_leverage_position(wallet, i)
            print(f'position {i}: {json.dumps(pos, default=str)[:300]}')
except Exception as e:
    print(f'leverage positions ERROR: {e}')

print()
print('=== PREDICTION MARKETS: Create market ===')
try:
    result = client.prediction_markets.create_market_with_metadata(
        question="Will Basis have 10+ registered agents by end of Phase 1?",
        options=["Yes", "No"],
        end_time=1776200000,  # ~8 days from now
        hybrid_multiplier=100,
        start_lp=500,
        description="Testing prediction market creation via SDK",
    )
    print(f'create market: {tx_hash(result)}')
    if isinstance(result, dict) and 'token_address' in result:
        print(f'market token: {result["token_address"]}')
except Exception as e:
    print(f'create market ERROR: {e}')

print()
print('=== VESTING: Create gradual vesting ===')
try:
    import time
    result = client.vesting.create_gradual_vesting(
        token_address=geegee_token,
        beneficiary=wallet,
        amount=5 * 10**18,
        start_time=int(time.time()) + 3600,
        duration=86400 * 7,
    )
    print(f'create vesting: tx={tx_hash(result)}')
except Exception as e:
    print(f'create vesting ERROR: {e}')

print()
print('=== TAXES: Check surge quota ===')
try:
    quota = client.taxes.get_available_surge_quota(geegee_token)
    print(f'surge quota: {quota}')
except Exception as e:
    print(f'surge quota ERROR: {e}')

try:
    base_rates = client.taxes.get_base_tax_rates(geegee_token)
    print(f'base tax rates: {base_rates}')
except Exception as e:
    print(f'base tax rates ERROR: {e}')

print()
print('=== RESOLVER: Check constants ===')
try:
    constants = client.resolver.get_constants()
    print(f'resolver constants: {json.dumps(constants, default=str)[:300]}')
except Exception as e:
    print(f'resolver constants ERROR: {e}')

print()
print('=== API: Token endpoints with SIWE session ===')
try:
    session = client.api.session
    r = session.get(f'{client.api_domain}/api/v1/tokens?sort=newest&page=1&limit=20')
    print(f'get_tokens via session: {r.status_code} - {r.text[:300]}')
except Exception as e:
    print(f'get_tokens session ERROR: {e}')

print()
print('=== API: Wallet transactions ===')
try:
    txns = client.api.get_wallet_transactions(wallet)
    print(f'wallet transactions: {json.dumps(txns, default=str)[:500]}')
except Exception as e:
    print(f'wallet transactions ERROR: {e}')

print()
print('=== API: Bug report ===')
try:
    result = client.api.submit_bug_report(
        title="SDK test: buy() expects wei but docs show whole USDB",
        description="trading.buy(token, 50) sends 50 wei, not 50 USDB. The Python SDK passes the raw int to the contract. Docs should clarify that amounts must be in wei (amount * 10**18).",
        severity="low"
    )
    print(f'submit_bug_report: {json.dumps(result, default=str)[:300]}')
except Exception as e:
    print(f'submit_bug_report ERROR: {e}')

print()
print('=== DONE ===')
