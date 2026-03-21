"""Smoke test for new SDK + new contract deployment"""
import sys
sys.path.insert(0, '../basis-sdk-python')

from basis.client import BasisClient
from web3 import Web3

client = BasisClient()
wallet = '0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2'

results = []

def test(name, fn):
    try:
        result = fn()
        print(f"PASS: {name} => {result}")
        results.append(("PASS", name))
        return result
    except Exception as e:
        print(f"FAIL: {name} => {type(e).__name__}: {e}")
        results.append(("FAIL", name))
        return None

# Read tests
test("STASIS USD price", lambda: client.trading.get_usd_price(client.main_token_address))
test("Base tax rates", lambda: client.taxes.get_base_tax_rates())
test("5 USDB -> STASIS preview", lambda: client.trading.get_amounts_out(5 * 10**18, [client.usdb_address, client.main_token_address]))
test("1 STASIS -> wSTASIS shares", lambda: client.staking.convert_to_shares(1 * 10**18))
test("STASIS token price", lambda: client.trading.get_token_price(client.main_token_address))
test("Is ecosystem token (STASIS)", lambda: client.factory.is_ecosystem_token(client.main_token_address))
test("Fee amount (token creation)", lambda: client.factory.get_fee_amount())

# Resolver tests (previously missing from ABI)
test("Resolver getConstants", lambda: client.resolver.get_constants(client.main_token_address))

# Wallet balance checks
bnb_bal = client.web3.eth.get_balance(wallet)
print(f"\nTest wallet BNB: {Web3.from_wei(bnb_bal, 'ether')}")

usdb_abi = [{"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}]
usdb = client.web3.eth.contract(address=Web3.to_checksum_address(client.usdb_address), abi=usdb_abi)
usdb_bal = usdb.functions.balanceOf(Web3.to_checksum_address(wallet)).call()
print(f"Test wallet USDB (new): {Web3.from_wei(usdb_bal, 'ether')}")

stasis_abi = usdb_abi  # same ERC20 balanceOf
stasis = client.web3.eth.contract(address=Web3.to_checksum_address(client.main_token_address), abi=stasis_abi)
stasis_bal = stasis.functions.balanceOf(Web3.to_checksum_address(wallet)).call()
print(f"Test wallet STASIS (new): {Web3.from_wei(stasis_bal, 'ether')}")

# Summary
passed = sum(1 for r in results if r[0] == "PASS")
failed = sum(1 for r in results if r[0] == "FAIL")
print(f"\n{'='*50}")
print(f"Results: {passed} PASS, {failed} FAIL out of {len(results)}")
if failed:
    print("Failures:")
    for r in results:
        if r[0] == "FAIL":
            print(f"  - {r[1]}")
