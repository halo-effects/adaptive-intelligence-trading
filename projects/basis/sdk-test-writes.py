"""SDK write tests against live BSC with funded wallet."""
import sys, os, json, time, traceback
sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient
from web3 import Web3

PRIVATE_KEY = "0x062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"
USDB = "0x78dD776204aA7e06BaF488959a90142f0B3027CE"
MAINTOKEN = "0x76ACb5F98A422995a801008c8b7b28dBC23946Ff"

results = []

def test(name, fn):
    try:
        result = fn()
        r_str = str(result)[:200]
        results.append({"test": name, "status": "PASS", "result": r_str})
        print(f"  PASS {name}")
        if "hash" in str(type(result)).lower() or (isinstance(result, dict) and "hash" in result):
            print(f"       TX: {result.get('hash', result)}")
        return result
    except Exception as e:
        results.append({"test": name, "status": "FAIL", "error": str(e)[:300]})
        print(f"  FAIL {name}: {e}")
        traceback.print_exc()
        return None

print("=" * 60)
print("Basis Python SDK v3 - Write Tests (Live BSC)")
print("=" * 60)

# 1. Init with private key
print("\n1. Initialize with private key (SIWE auth)")
try:
    client = BasisClient.create(private_key=PRIVATE_KEY)
    wallet = client.account.address
    print(f"  PASS Wallet: {wallet}")
    print(f"  PASS SIWE authenticated, API key provisioned")
    results.append({"test": "create_with_key", "status": "PASS"})
except Exception as e:
    print(f"  FAIL Init: {e}")
    traceback.print_exc()
    results.append({"test": "create_with_key", "status": "FAIL", "error": str(e)[:300]})
    # Fall back to basic client
    client = BasisClient(private_key=PRIVATE_KEY)
    wallet = client.account.address
    print(f"  WARN Fell back to basic init (no SIWE). Wallet: {wallet}")

# Check balances
bnb = client.web3.eth.get_balance(wallet)
print(f"\n  BNB: {Web3.from_wei(bnb, 'ether')}")

erc20_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
usdb_contract = client.web3.eth.contract(address=Web3.to_checksum_address(USDB), abi=erc20_abi)
usdb_bal = usdb_contract.functions.balanceOf(wallet).call()
print(f"  USDB: {usdb_bal / 10**18}")

# 2. Trading - Buy MAINTOKEN with USDB
print("\n2. Trading - Buy STASIS with 5 USDB")
buy_result = test("buy(MAINTOKEN, 5 USDB)", lambda: client.trading.buy(MAINTOKEN, 5 * 10**18))

if buy_result:
    time.sleep(3)
    # Check STASIS balance
    main_contract = client.web3.eth.contract(address=Web3.to_checksum_address(MAINTOKEN), abi=erc20_abi)
    main_bal = main_contract.functions.balanceOf(wallet).call()
    print(f"  STASIS balance after buy: {main_bal / 10**18}")

# 3. Trading - Sell STASIS back
print("\n3. Trading - Sell 50% of STASIS")
sell_result = test("sell_percentage(MAINTOKEN, 50)", lambda: client.trading.sell_percentage(MAINTOKEN, 50))

# 4. Get amounts preview
print("\n4. Trading - Preview swap")
test("get_amounts_out(2 USDB -> MAINTOKEN)", lambda: client.trading.get_amounts_out(2 * 10**18, [USDB, MAINTOKEN]))

# 5. Factory - Create token (if fee is 0 BNB)
print("\n5. Factory - Create token")
fee = client.factory.get_fee_amount()
print(f"  Creation fee: {fee} BNB")
if fee == 0:
    create_result = test("create_token(TEST, Test Token)", lambda: client.factory.create_token(
        "GTEST", "GeeGee Test Token", 50, False, 0, 1000, False, 0, False
    ))
    if create_result:
        # Try to find token address from receipt
        receipt = create_result.get("receipt", {})
        logs = receipt.get("logs", [])
        if logs:
            print(f"  Token address (from logs): {logs[0].get('address', 'unknown')}")
else:
    print(f"  SKIP - Creation fee is {fee} BNB, would cost real money")
    results.append({"test": "create_token", "status": "SKIP", "result": f"Fee: {fee} BNB"})

# 6. Staking - convert preview (read-only, already tested but confirming with auth)
print("\n6. Staking - Preview conversions (authed)")
test("convert_to_shares(10 STASIS)", lambda: client.staking.convert_to_shares(10 * 10**18))

# 7. Agent Identity
print("\n7. Agent Identity - Check registration")
test("is_registered(self)", lambda: client.agent.is_registered(wallet))

# 8. Leverage simulation
print("\n8. Leverage - Simulate")
test("simulate_leverage(5 USDB, 7 days)", lambda: client.leverage_simulator.simulate_leverage(5 * 10**18, [USDB, MAINTOKEN], 7))

# 9. Check final balances
print("\n9. Final balances")
bnb_final = client.web3.eth.get_balance(wallet)
usdb_final = usdb_contract.functions.balanceOf(wallet).call()
main_final = client.web3.eth.contract(address=Web3.to_checksum_address(MAINTOKEN), abi=erc20_abi).functions.balanceOf(wallet).call()
print(f"  BNB: {Web3.from_wei(bnb_final, 'ether')} (spent {Web3.from_wei(bnb - bnb_final, 'ether')} on gas)")
print(f"  USDB: {usdb_final / 10**18}")
print(f"  STASIS: {main_final / 10**18}")

# Summary
print("\n" + "=" * 60)
passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
skipped = sum(1 for r in results if r["status"] == "SKIP")
print(f"Results: {passed} passed, {failed} failed, {skipped} skipped, {len(results)} total")
print("=" * 60)

if failed > 0:
    print("\nFailed tests:")
    for r in results:
        if r["status"] == "FAIL":
            print(f"  - {r['test']}: {r.get('error', '')[:150]}")

with open("sdk-test-writes-results.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nResults saved to sdk-test-writes-results.json")
