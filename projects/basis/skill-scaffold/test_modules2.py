import sys, io, inspect
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

def tx_hash(result):
    return result.get('hash', 'no hash') if isinstance(result, dict) else str(result)

# Check signatures for things that failed
print('=== SIGNATURE CHECK ===')
for name, method in [
    ('staking.borrow', client.staking.borrow),
    ('trading.leverage_buy', client.trading.leverage_buy),
    ('prediction_markets.create_market_with_metadata', client.prediction_markets.create_market_with_metadata),
    ('vesting.create_gradual_vesting', client.vesting.create_gradual_vesting),
    ('taxes.get_base_tax_rates', client.taxes.get_base_tax_rates),
    ('api.submit_bug_report', client.api.submit_bug_report),
    ('api.get_tokens', client.api.get_tokens),
]:
    sig = inspect.signature(method)
    print(f'{name}{sig}')

print()
print('=== STAKING: Buy STASIS (lower amount) ===')
try:
    # Try 20 USDB - the overflow might be from insufficient balance
    result = client.staking.buy(20 * 10**18)
    print(f'buy STASIS (20 USDB): tx={tx_hash(result)}')
except Exception as e:
    print(f'buy STASIS (20) ERROR: {e}')

# Check USDB balance first
from web3 import Web3
usdb = client.web3.eth.contract(address=Web3.to_checksum_address(client.usdb_address), abi=client.trading.erc20_abi)
bal = usdb.functions.balanceOf(wallet).call()
print(f'USDB balance: {bal / 1e18}')

print()
print('=== STAKING: Borrow (with days) ===')
try:
    avail = client.staking.get_available_stasis(wallet)
    print(f'Available STASIS: {avail}')
    if avail > 0:
        client.staking.lock(avail)
        result = client.staking.borrow(5 * 10**18, 7)  # 5 USDB for 7 days
        print(f'borrow: tx={tx_hash(result)}')
except Exception as e:
    print(f'borrow ERROR: {e}')

print()
print('=== TRADING: Leverage buy (with path and days) ===')
try:
    sig = inspect.signature(client.trading.leverage_buy)
    print(f'leverage_buy sig: {sig}')
    # Build path manually
    path = [client.usdb_address, client.main_token_address, geegee_token]
    result = client.trading.leverage_buy(10 * 10**18, path, 7)
    print(f'leverage_buy: tx={tx_hash(result)}')
except Exception as e:
    print(f'leverage_buy ERROR: {e}')

print()
print('=== PREDICTION MARKETS: Check signature and create ===')
try:
    sig = inspect.signature(client.prediction_markets.create_market_with_metadata)
    print(f'create_market sig: {sig}')
    src = inspect.getsource(client.prediction_markets.create_market_with_metadata)
    print(src[:1500])
except Exception as e:
    print(f'create_market source ERROR: {e}')

print()
print('=== VESTING: Check signature ===')
try:
    sig = inspect.signature(client.vesting.create_gradual_vesting)
    print(f'create_gradual_vesting sig: {sig}')
    src = inspect.getsource(client.vesting.create_gradual_vesting)
    print(src[:1000])
except Exception as e:
    print(f'vesting source ERROR: {e}')

print()
print('=== API: get_tokens signature ===')
try:
    sig = inspect.signature(client.api.get_tokens)
    print(f'get_tokens sig: {sig}')
except Exception as e:
    print(f'sig ERROR: {e}')

print()
print('=== API: submit_bug_report signature ===')
try:
    sig = inspect.signature(client.api.submit_bug_report)
    print(f'submit_bug_report sig: {sig}')
except Exception as e:
    print(f'sig ERROR: {e}')

print()
print('=== MOLTBOOK: Link ===')
try:
    result = client.api.link_moltbook('geegee')
    print(f'link_moltbook: {json.dumps(result, default=str)}')
except Exception as e:
    print(f'link_moltbook ERROR: {e}')

print()
print('=== ORDER BOOK: Check ===')
try:
    sig = inspect.signature(client.order_book.list_order)
    print(f'list_order sig: {sig}')
except Exception as e:
    print(f'list_order sig ERROR: {e}')

print()
print('=== LEVERAGE SIMULATOR ===')
try:
    result = client.leverage_simulator.simulate_leverage(geegee_token, 10 * 10**18)
    print(f'simulate_leverage: {json.dumps(result, default=str)[:300]}')
except Exception as e:
    print(f'simulate_leverage ERROR: {e}')

try:
    sig = inspect.signature(client.leverage_simulator.simulate_leverage)
    print(f'simulate_leverage sig: {sig}')
except Exception as e:
    pass

print()
print('=== DONE ===')
