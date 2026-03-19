"""Full read-only SDK v2 tests against live BSC."""
import sys
import os
import json
import traceback

# Add SDK v2 to path as a proper package
sdk_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sdk-python-v2")
sys.path.insert(0, sdk_root)

from basis import BasisClient

USDB = "0x78dD776204aA7e06BaF488959a90142f0B3027CE"
MAINTOKEN = "0x76ACb5F98A422995a801008c8b7b28dBC23946Ff"
MAX_TOKEN = "0x09A3b840ac0d151F2dfB427a7E006FE44970EDB9"
MAX_MARKET = "0xf510891992a5004Be3783aE1b4D7Cfa67907D8d8"
MARKET_TRADING = "0xCb64910a19B3641eb600b904741a074578Dda3F7"

results = []

def test(name, fn):
    try:
        result = fn()
        results.append({"test": name, "status": "PASS", "result": str(result)[:200]})
        print(f"  PASS {name}: {str(result)[:100]}")
        return result
    except Exception as e:
        results.append({"test": name, "status": "FAIL", "error": str(e)[:200]})
        print(f"  FAIL {name}: {e}")
        return None

print("=" * 60)
print("Basis Python SDK v2 - Full Read-Only Tests")
print("=" * 60)

# 1. Init
print("\n1. Initialize client")
client = BasisClient()
chain = client.web3.eth.chain_id
print(f"  PASS Connected to BSC (chain {chain})")
results.append({"test": "init", "status": "PASS" if chain == 56 else "FAIL"})

# 2. Trading reads
print("\n2. Trading module")
test("get_usd_price(MAINTOKEN)", lambda: client.trading.get_usd_price(MAINTOKEN))
test("get_token_price(MAX_TOKEN)", lambda: client.trading.get_token_price(MAX_TOKEN))
test("get_amounts_out(5 USDB -> MAINTOKEN)", lambda: client.trading.get_amounts_out(5 * 10**18, [USDB, MAINTOKEN]))
test("get_amounts_out(5 USDB -> MAX 3-hop)", lambda: client.trading.get_amounts_out(5 * 10**18, [USDB, MAINTOKEN, MAX_TOKEN]))

# 3. Factory reads
print("\n3. Factory module")
state = test("get_token_state(MAX_TOKEN)", lambda: client.factory.get_token_state(MAX_TOKEN))
test("is_ecosystem_token(MAX_TOKEN)", lambda: client.factory.is_ecosystem_token(MAX_TOKEN))
test("get_fee_amount()", lambda: client.factory.get_fee_amount())
test("get_tokens_by_creator(zero addr)", lambda: client.factory.get_tokens_by_creator("0x0000000000000000000000000000000000000001"))

# 4. Staking reads
print("\n4. Staking module")
test("convert_to_shares(100 STASIS)", lambda: client.staking.convert_to_shares(100 * 10**18))
test("convert_to_assets(100 wSTASIS)", lambda: client.staking.convert_to_assets(100 * 10**18))

# 5. Taxes reads
print("\n5. Taxes module")
test("get_base_tax_rates()", lambda: client.taxes.get_base_tax_rates())
test("get_current_surge_tax(MAX_TOKEN)", lambda: client.taxes.get_current_surge_tax(MAX_TOKEN))
test("get_available_surge_quota(MAX_TOKEN)", lambda: client.taxes.get_available_surge_quota(MAX_TOKEN))

# 6. Prediction markets reads
print("\n6. Prediction markets module")
test("get_market_data(MAX_MARKET)", lambda: client.prediction_markets.get_market_data(MAX_MARKET))
test("get_outcome(MAX_MARKET, 0)", lambda: client.prediction_markets.get_outcome(MAX_MARKET, 0))
test("get_initial_reserves(2)", lambda: client.prediction_markets.get_initial_reserves(2))
test("get_user_shares(MAX_MARKET, zero, 0)", lambda: client.prediction_markets.get_user_shares(MAX_MARKET, "0x0000000000000000000000000000000000000001", 0))

# 7. Agent identity reads
print("\n7. Agent identity module")
test("is_registered(zero addr)", lambda: client.agent.is_registered("0x0000000000000000000000000000000000000001"))

# 8. Market reader reads
print("\n8. Market reader module")
test("get_all_outcomes(MAX_MARKET)", lambda: client.market_reader.get_all_outcomes(MARKET_TRADING, MAX_MARKET))

# 9. Leverage simulator reads
print("\n9. Leverage simulator module")
test("simulate_leverage(10 USDB, 7 days)", lambda: client.leverage_simulator.simulate_leverage(10 * 10**18, [USDB, MAINTOKEN], 7))

# 10. Resolver reads (PREVIOUSLY FAILED - should be fixed now)
print("\n10. Resolver module (previously failed)")
test("is_resolved(MAX_MARKET)", lambda: client.resolver.is_resolved(MAX_MARKET))
test("is_in_dispute(MAX_MARKET)", lambda: client.resolver.is_in_dispute(MAX_MARKET))
test("is_in_veto(MAX_MARKET)", lambda: client.resolver.is_in_veto(MAX_MARKET))
test("get_final_outcome(MAX_MARKET)", lambda: client.resolver.get_final_outcome(MAX_MARKET))
test("get_current_round(MAX_MARKET)", lambda: client.resolver.get_current_round(MAX_MARKET))

# 11. Loans reads
print("\n11. Loans module")
test("get_user_loan_count(zero addr)", lambda: client.loans.get_user_loan_count("0x0000000000000000000000000000000000000001"))

# 12. Vesting reads
print("\n12. Vesting module")
test("get_claimable_amount(0)", lambda: client.vesting.get_claimable_amount(0))

# 13. Module availability check
print("\n13. Module availability")
modules = ["trading", "factory", "loans", "staking", "vesting", "prediction_markets", 
           "order_book", "resolver", "private_markets", "market_reader", 
           "leverage_simulator", "taxes", "agent", "api"]
for mod in modules:
    has = hasattr(client, mod)
    results.append({"test": f"has_{mod}", "status": "PASS" if has else "FAIL"})
    print(f"  {'PASS' if has else 'FAIL'} client.{mod}")

# 14. Check pyproject.toml exists (was missing in v1)
print("\n14. Package structure")
has_pyproject = os.path.exists(os.path.join(sdk_root, "pyproject.toml"))
has_readme = os.path.exists(os.path.join(sdk_root, "README.md"))
has_pycache = os.path.exists(os.path.join(sdk_root, "basis", "__pycache__"))
results.append({"test": "has_pyproject_toml", "status": "PASS" if has_pyproject else "FAIL"})
results.append({"test": "has_readme", "status": "PASS" if has_readme else "FAIL"})
results.append({"test": "no_pycache_in_zip", "status": "WARN" if has_pycache else "PASS"})
print(f"  {'PASS' if has_pyproject else 'FAIL'} pyproject.toml exists")
print(f"  {'PASS' if has_readme else 'FAIL'} README.md exists")
print(f"  {'WARN' if has_pycache else 'PASS'} __pycache__ {'present (should exclude from release)' if has_pycache else 'not present'}")

# Summary
print("\n" + "=" * 60)
passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
warned = sum(1 for r in results if r["status"] == "WARN")
print(f"Results: {passed} passed, {failed} failed, {warned} warnings, {len(results)} total")
print("=" * 60)

if failed > 0:
    print("\nFailed tests:")
    for r in results:
        if r["status"] == "FAIL":
            print(f"  - {r['test']}: {r.get('error', 'no error msg')}")

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sdk-test-v2-results.json"), "w") as f:
    json.dump(results, f, indent=2)
print("\nResults saved to sdk-test-v2-results.json")
