"""Read-only SDK tests against live BSC — no wallet needed."""
import sys
import os
import json
import traceback

# Add SDK parent to path so 'basis_sdk' package can be imported
sdk_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sdk-python")

# We need to make the sdk-python dir importable as a package
# Create a wrapper that imports correctly
import importlib.util

# Temporarily add parent and use direct module loading
sys.path.insert(0, os.path.dirname(sdk_path))

# Rename sdk-python dir reference for import
import types
basis_sdk = types.ModuleType("basis_sdk")
sys.modules["basis_sdk"] = basis_sdk

# Load modules manually to handle the relative imports
# Actually, let's just fix the import by making it a proper package import
# The SDK uses relative imports (.api, .modules), so we need to set it up as a package

import importlib
spec = importlib.util.spec_from_file_location(
    "basis_sdk", 
    os.path.join(sdk_path, "__init__.py"),
    submodule_search_locations=[sdk_path]
)
basis_sdk = importlib.util.module_from_spec(spec)
sys.modules["basis_sdk"] = basis_sdk
spec.loader.exec_module(basis_sdk)

BasisClient = basis_sdk.BasisClient

USDB = "0x78dD776204aA7e06BaF488959a90142f0B3027CE"
MAINTOKEN = "0x76ACb5F98A422995a801008c8b7b28dBC23946Ff"
MAX_TOKEN = "0x09A3b840ac0d151F2dfB427a7E006FE44970EDB9"  # Alex's test token
MAX_MARKET = "0xf510891992a5004Be3783aE1b4D7Cfa67907D8d8"  # Alex's test market

results = []

def test(name, fn):
    try:
        result = fn()
        results.append({"test": name, "status": "PASS", "result": str(result)[:200]})
        print(f"  ✅ {name}: {str(result)[:100]}")
        return result
    except Exception as e:
        results.append({"test": name, "status": "FAIL", "error": str(e)[:200]})
        print(f"  ❌ {name}: {e}")
        traceback.print_exc()
        return None

print("=" * 60)
print("Basis Python SDK — Read-Only Tests")
print("=" * 60)

# 1. Init stateless client
print("\n1. Initialize stateless client (no key)")
client = BasisClient()
print(f"  ✅ Connected to BSC via {client.web3.provider.endpoint_uri}")
print(f"  ✅ Chain ID: {client.web3.eth.chain_id}")
results.append({"test": "init_stateless", "status": "PASS"})

# 2. Trading reads
print("\n2. Trading module reads")
test("get_usd_price(MAINTOKEN)", lambda: client.trading.get_usd_price(MAINTOKEN))
test("get_token_price(MAX_TOKEN)", lambda: client.trading.get_token_price(MAX_TOKEN))
test("get_amounts_out(5 USDB → MAINTOKEN)", lambda: client.trading.get_amounts_out(5 * 10**18, [USDB, MAINTOKEN]))
test("get_amounts_out(5 USDB → MAX)", lambda: client.trading.get_amounts_out(5 * 10**18, [USDB, MAINTOKEN, MAX_TOKEN]))

# 3. Factory reads
print("\n3. Factory module reads")
test("get_token_state(MAX_TOKEN)", lambda: client.factory.get_token_state(MAX_TOKEN))
test("is_ecosystem_token(MAX_TOKEN)", lambda: client.factory.is_ecosystem_token(MAX_TOKEN))
test("get_fee_amount()", lambda: client.factory.get_fee_amount())

# 4. Staking reads
print("\n4. Staking module reads")
test("convert_to_shares(100 STASIS)", lambda: client.staking.convert_to_shares(100 * 10**18))
test("convert_to_assets(100 wSTASIS)", lambda: client.staking.convert_to_assets(100 * 10**18))

# 5. Taxes reads
print("\n5. Taxes module reads")
test("get_base_tax_rates()", lambda: client.taxes.get_base_tax_rates())
test("get_current_surge_tax(MAX_TOKEN)", lambda: client.taxes.get_current_surge_tax(MAX_TOKEN))

# 6. Prediction markets reads
print("\n6. Prediction markets reads")
test("get_market_data(MAX_MARKET)", lambda: client.prediction_markets.get_market_data(MAX_MARKET))
test("get_outcome(MAX_MARKET, 0)", lambda: client.prediction_markets.get_outcome(MAX_MARKET, 0))
test("get_initial_reserves(2)", lambda: client.prediction_markets.get_initial_reserves(2))

# 7. Agent identity reads
print("\n7. Agent identity reads")
test("is_registered(Alex wallet placeholder)", lambda: client.agent.is_registered("0x0000000000000000000000000000000000000001"))

# 8. Market reader reads
print("\n8. Market reader reads")
MARKET_TRADING = "0xCb64910a19B3641eb600b904741a074578Dda3F7"
test("get_all_outcomes(MAX_MARKET)", lambda: client.market_reader.get_all_outcomes(MARKET_TRADING, MAX_MARKET))

# 9. Leverage simulator reads
print("\n9. Leverage simulator reads")
test("simulate_leverage(10 USDB, 7 days)", lambda: client.leverage_simulator.simulate_leverage(10 * 10**18, [USDB, MAINTOKEN], 7))

# 10. Resolver reads
print("\n10. Resolver reads")
test("is_resolved(MAX_MARKET)", lambda: client.resolver.is_resolved(MAX_MARKET))
test("is_in_dispute(MAX_MARKET)", lambda: client.resolver.is_in_dispute(MAX_MARKET))

# Summary
print("\n" + "=" * 60)
passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
print(f"Results: {passed} passed, {failed} failed, {len(results)} total")
print("=" * 60)

# Save results
with open(os.path.join(os.path.dirname(__file__), "sdk-test-results.json"), "w") as f:
    json.dump(results, f, indent=2)
print("Results saved to sdk-test-results.json")
