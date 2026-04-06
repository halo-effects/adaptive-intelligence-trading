import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from dotenv import load_dotenv
import os, json, time, inspect
load_dotenv()
from basis import BasisClient
from web3 import Web3

pk = os.getenv('BASIS_PRIVATE_KEY')
api_key = os.getenv('BASIS_API_KEY')
client = BasisClient.create(private_key=pk, api_key=api_key)
client.authenticate()
wallet = client.account.address
geegee_token = '0xbb8c70bDC0Fe13B25753E81Af676c23DdcfD6e28'
stasis = client.main_token_address
usdb_addr = client.usdb_address

def tx_hash(result):
    return result.get('hash', 'no hash') if isinstance(result, dict) else str(result)

# Check balances
usdb_c = client.web3.eth.contract(address=Web3.to_checksum_address(usdb_addr), abi=client.trading.erc20_abi)
stasis_c = client.web3.eth.contract(address=Web3.to_checksum_address(stasis), abi=client.trading.erc20_abi)
print(f'USDB: {usdb_c.functions.balanceOf(wallet).call() / 1e18}')
print(f'STASIS: {stasis_c.functions.balanceOf(wallet).call() / 1e18}')

# Check staking.buy source to understand the overflow
print()
print('=== staking.buy source ===')
src = inspect.getsource(client.staking.buy)
print(src[:1500])

print()
print('=== STAKING: Check vault/staking addresses ===')
print(f'staking contract: {client.staking.contract.address if hasattr(client.staking, "contract") else "unknown"}')

# Check if STASIS needs approval for staking contract
print()
print('=== Check STASIS approval for staking ===')
staking_addr = client.staking.contract.address if hasattr(client.staking, 'contract') else None
if staking_addr:
    allowance = stasis_c.functions.allowance(wallet, staking_addr).call()
    print(f'STASIS allowance for staking: {allowance / 1e18}')

# Try lock with explicit amount (maybe the balance read is wrong)
print()
print('=== STAKING: Try lock with explicit smaller amount ===')
stasis_bal = stasis_c.functions.balanceOf(wallet).call()
print(f'STASIS balance (raw): {stasis_bal}')
try:
    # Try locking half
    half = stasis_bal // 2
    print(f'Trying to lock {half / 1e18} STASIS...')
    result = client.staking.lock(half)
    print(f'lock: tx={tx_hash(result)}')
except Exception as e:
    print(f'lock ERROR: {e}')

# Try staking.buy with explicit approval first
print()
print('=== STAKING: Buy with approval check ===')
try:
    # Check what staking.buy actually does
    result = client.staking.buy(10 * 10**18)
    print(f'staking.buy: tx={tx_hash(result)}')
except Exception as e:
    print(f'staking.buy ERROR: {e}')
    # Check if it's a USDB approval issue
    if staking_addr:
        usdb_allowance = usdb_c.functions.allowance(wallet, staking_addr).call()
        print(f'USDB allowance for staking: {usdb_allowance / 1e18}')

print()
print('=== PREDICTION MARKET: Private (seed=0) ===')
try:
    end = int(time.time()) + 86400 * 8
    # Check private_markets signature
    sig = inspect.signature(client.private_markets.create_market_with_metadata)
    print(f'private create sig: {sig}')
    
    result = client.private_markets.create_market_with_metadata(
        market_name="Will GeeGee reach Tidal Lobster tier in Phase 1?",
        symbol="GEETIDAL",
        end_time=end,
        option_names=["Yes", "No"],
        maintoken=stasis,
        description="Will the GeeGee AI agent reach Tidal Lobster tier before Phase 1 ends?",
    )
    print(f'private market: {tx_hash(result)}')
    if isinstance(result, dict):
        for k in ['market_token_address', 'token_address']:
            if k in result:
                print(f'{k}: {result[k]}')
except Exception as e:
    print(f'private market ERROR: {e}')

print()
print('=== PREDICTION MARKET: Public (seed=50) ===')
try:
    end = int(time.time()) + 86400 * 8
    result = client.prediction_markets.create_market_with_metadata(
        market_name="Will Basis have 10+ agents by Phase 1 end?",
        symbol="AGENTS10",
        end_time=end,
        option_names=["Yes", "No"],
        maintoken=stasis,
        description="Will 10 or more ERC-8004 agents register on Basis before Phase 1 concludes?",
        seed_amount=50 * 10**18,
    )
    print(f'public market: {tx_hash(result)}')
    if isinstance(result, dict):
        for k in ['market_token_address', 'token_address']:
            if k in result:
                print(f'{k}: {result[k]}')
except Exception as e:
    print(f'public market ERROR: {e}')

print()
print('=== FINAL BALANCES ===')
print(f'USDB: {usdb_c.functions.balanceOf(wallet).call() / 1e18}')
print(f'STASIS: {stasis_c.functions.balanceOf(wallet).call() / 1e18}')

print()
print('=== DONE ===')
