import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from dotenv import load_dotenv
import os, json, time
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

# Check balances
from web3 import Web3
usdb_c = client.web3.eth.contract(address=Web3.to_checksum_address(client.usdb_address), abi=client.trading.erc20_abi)
usdb_bal = usdb_c.functions.balanceOf(wallet).call()
print(f'USDB balance: {usdb_bal / 1e18}')

stasis_c = client.web3.eth.contract(address=Web3.to_checksum_address(stasis), abi=client.trading.erc20_abi)
stasis_bal = stasis_c.functions.balanceOf(wallet).call()
print(f'STASIS balance: {stasis_bal / 1e18}')

geegee_c = client.web3.eth.contract(address=Web3.to_checksum_address(geegee_token), abi=client.trading.erc20_abi)
geegee_bal = geegee_c.functions.balanceOf(wallet).call()
print(f'GEEGEE balance: {geegee_bal / 1e18}')

print()
print('=== TRADING: Buy STASIS directly via trading.buy ===')
try:
    result = client.trading.buy(stasis, 20 * 10**18)
    print(f'buy STASIS via trading: tx={tx_hash(result)}')
    stasis_bal = stasis_c.functions.balanceOf(wallet).call()
    print(f'STASIS balance now: {stasis_bal / 1e18}')
except Exception as e:
    print(f'buy STASIS ERROR: {e}')

print()
print('=== STAKING: Lock and borrow ===')
try:
    stasis_bal = stasis_c.functions.balanceOf(wallet).call()
    if stasis_bal > 0:
        result = client.staking.lock(stasis_bal)
        print(f'lock: tx={tx_hash(result)}')
        details = client.staking.get_user_stake_details(wallet)
        print(f'stake details: {json.dumps(details, default=str)}')
        
        # Borrow 5 USDB for 7 days
        result = client.staking.borrow(5 * 10**18, 7)
        print(f'borrow: tx={tx_hash(result)}')
        
        # Check loan
        count = client.loans.get_user_loan_count(wallet)
        print(f'loan count: {count}')
        if count > 0:
            loan = client.loans.get_user_loan_details(wallet, 0)
            print(f'loan 0: {json.dumps(loan, default=str)[:300]}')
    else:
        print('No STASIS to lock')
except Exception as e:
    print(f'staking/borrow ERROR: {e}')

print()
print('=== PREDICTION MARKETS: Create ===')
try:
    end = int(time.time()) + 86400 * 8  # 8 days
    result = client.prediction_markets.create_market_with_metadata(
        market_name="Will Basis have 10+ registered agents by end of Phase 1?",
        symbol="AGENTS10",
        end_time=end,
        option_names=["Yes", "No"],
        maintoken=stasis,
        description="First prediction market on Basis. Will the platform attract 10 or more registered ERC-8004 agents before Phase 1 ends?",
    )
    print(f'create market: {tx_hash(result)}')
    if isinstance(result, dict):
        print(f'market token: {result.get("market_token_address", "unknown")}')
except Exception as e:
    print(f'create market ERROR: {e}')

print()
print('=== LEVERAGE SIMULATOR: simulate ===')
try:
    path = [client.usdb_address, stasis, geegee_token]
    result = client.leverage_simulator.simulate_leverage(10 * 10**18, path, 7)
    print(f'simulate leverage: {json.dumps(result, default=str)[:500]}')
except Exception as e:
    print(f'simulate ERROR: {e}')

print()
print('=== FACTORY: Claim rewards ===')
try:
    rewards = client.factory.get_claimable_rewards(geegee_token, wallet)
    print(f'claimable rewards: {rewards}')
    if rewards > 0:
        result = client.factory.claim_rewards(geegee_token)
        print(f'claim: tx={tx_hash(result)}')
except Exception as e:
    print(f'claim rewards ERROR: {e}')

print()
print('=== TAXES: Read-only checks ===')
try:
    rates = client.taxes.get_base_tax_rates()
    print(f'base tax rates: {json.dumps(rates, default=str)}')
except Exception as e:
    print(f'base tax rates ERROR: {e}')

try:
    current = client.taxes.get_current_surge_tax(geegee_token)
    print(f'current surge tax: {current}')
except Exception as e:
    print(f'current surge ERROR: {e}')

try:
    tax_rate = client.taxes.get_tax_rate(geegee_token)
    print(f'tax rate: {tax_rate}')
except Exception as e:
    print(f'tax rate ERROR: {e}')

print()
print('=== API: get_tokens (correct call) ===')
try:
    tokens = client.api.get_tokens()
    print(f'get_tokens: {json.dumps(tokens, default=str)[:500]}')
except Exception as e:
    print(f'get_tokens ERROR: {e}')

print()
print('=== API: Leaderboard details ===')
try:
    lb = client.api.get_leaderboard()
    print(f'leaderboard: {json.dumps(lb, default=str)[:500]}')
except Exception as e:
    print(f'leaderboard ERROR: {e}')

print()
print('=== API: Moltbook verify challenge ===')
# We got the challenge earlier, let's note it for later
print('Moltbook challenge received: basis-verify-9e565205eb1bdb0cdb093faf31ec5a9b')
print('Need to post this on m/basis via Moltbook API, then call verify_moltbook()')

print()
print('=== MARKET READER ===')
try:
    # Need a prediction market address to test - check if we created one above
    print('market_reader requires a prediction market token address')
except Exception as e:
    print(f'market_reader ERROR: {e}')

print()
print('=== FINAL BALANCES ===')
usdb_bal = usdb_c.functions.balanceOf(wallet).call()
stasis_bal = stasis_c.functions.balanceOf(wallet).call()
geegee_bal = geegee_c.functions.balanceOf(wallet).call()
print(f'USDB: {usdb_bal / 1e18}')
print(f'STASIS: {stasis_bal / 1e18}')
print(f'GEEGEE: {geegee_bal / 1e18}')

print()
print('=== DONE ===')
