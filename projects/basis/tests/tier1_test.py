"""
Basis SDK — Tier 1 Core Test Run (Python)
Tests all core write + read functions against live BSC mainnet.
"""
import sys, os, time, json, traceback

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
os.environ['PYTHONIOENCODING'] = 'utf-8'

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'basis-sdk-python'))
from basis import BasisClient

PRIVATE_KEY = "0x062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"
WALLET = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"

results = []

def log(test_id, name, status, detail=""):
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    entry = {"id": test_id, "name": name, "status": status, "detail": str(detail)[:200]}
    results.append(entry)
    print(f"{icon} [{test_id}] {name}: {status} — {str(detail)[:200]}")

def run_test(test_id, name, fn):
    try:
        result = fn()
        log(test_id, name, "PASS", result)
        return result
    except Exception as e:
        log(test_id, name, "FAIL", f"{type(e).__name__}: {e}")
        traceback.print_exc()
        return None

print("=" * 60)
print("BASIS SDK TIER 1 TEST RUN — Python")
print("=" * 60)

# ─── INIT ───
print("\n--- Initializing BasisClient (full mode) ---")
try:
    client = BasisClient.create(private_key=PRIVATE_KEY)
    print(f"✅ Client initialized. Wallet: {WALLET}")
except Exception as e:
    print(f"❌ Client init failed: {e}")
    traceback.print_exc()
    sys.exit(1)

USDB = client.usdb_address
MAINTOKEN = client.main_token_address

# ─── TIER 5: READ METHODS (quick, no gas) ───
print("\n--- Tier 5: Read Methods (no gas) ---")

run_test("R01", "trading.get_usd_price(MAINTOKEN)", 
    lambda: client.trading.get_usd_price(MAINTOKEN))

run_test("R02", "trading.get_token_price(MAINTOKEN)",
    lambda: client.trading.get_token_price(MAINTOKEN))

run_test("R03", "trading.get_amounts_out(1 USDB → MAINTOKEN)",
    lambda: client.trading.get_amounts_out(1 * 10**18, [USDB, MAINTOKEN]))

run_test("R04", "factory.get_fee_amount()",
    lambda: client.factory.get_fee_amount())

run_test("R05", "factory.is_ecosystem_token(MAINTOKEN)",
    lambda: client.factory.is_ecosystem_token(MAINTOKEN))

run_test("R06", "factory.get_tokens_by_creator(wallet)",
    lambda: client.factory.get_tokens_by_creator(WALLET))

run_test("R07", "taxes.get_tax_rate(MAINTOKEN, wallet)",
    lambda: client.taxes.get_tax_rate(MAINTOKEN, WALLET))

run_test("R08", "taxes.get_base_tax_rates()",
    lambda: client.taxes.get_base_tax_rates())

run_test("R09", "taxes.get_current_surge_tax(MAINTOKEN)",
    lambda: client.taxes.get_current_surge_tax(MAINTOKEN))

run_test("R10", "taxes.get_available_surge_quota(MAINTOKEN)",
    lambda: client.taxes.get_available_surge_quota(MAINTOKEN))

run_test("R11", "staking.get_available_stasis(wallet)",
    lambda: client.staking.get_available_stasis(WALLET))

run_test("R12", "staking.convert_to_shares(1 STASIS)",
    lambda: client.staking.convert_to_shares(1 * 10**18))

run_test("R13", "staking.convert_to_assets(1 share)",
    lambda: client.staking.convert_to_assets(1 * 10**18))

run_test("R14", "loans.get_user_loan_count(wallet)",
    lambda: client.loans.get_user_loan_count(WALLET))

run_test("R15", "trading.get_leverage_count(wallet)",
    lambda: client.trading.get_leverage_count(WALLET))

run_test("R16", "leverage_simulator.simulate_leverage(5 USDB, 7 days)",
    lambda: client.leverage_simulator.simulate_leverage(5 * 10**18, [USDB, MAINTOKEN], 7))

run_test("R17", "agent.is_registered(wallet)",
    lambda: client.agent.is_registered(WALLET))

# ─── TIER 6: API READ METHODS ───
print("\n--- Tier 6: API Read Methods ---")

run_test("A01", "api.get_tokens(limit=5)",
    lambda: client.api.get_tokens(limit=5))

run_test("A02", "api.get_token(MAINTOKEN)",
    lambda: client.api.get_token(MAINTOKEN))

# ─── TIER 1: CORE WRITES ───
print("\n--- Tier 1: Core Write Operations (costs gas + USDB) ---")

# T01: Create token with metadata
token_address = None
def test_create_token():
    global token_address
    result = client.factory.create_token_with_metadata(
        symbol="GEET3", name="GeeTest Three",
        hybrid_multiplier=50, start_lp=1000,
        description="SDK test token for full test run",
        image_url="https://picsum.photos/512/512",
    )
    token_address = result.get("token_address") or result.get("tokenAddress")
    return f"token={token_address}, tx={result.get('hash', '')[:16]}..."
run_test("T01", "factory.create_token_with_metadata()", test_create_token)

if not token_address:
    print("❌ Token creation failed — cannot continue write tests")
else:
    # T02: Get token state
    run_test("T02", "factory.get_token_state(new token)",
        lambda: client.factory.get_token_state(token_address))

    # T03: Buy 5 USDB worth
    buy_result = run_test("T03", "trading.buy(5 USDB)",
        lambda: client.trading.buy(token_address, 5 * 10**18))

    # T04: Get USD price of new token
    run_test("T04", "trading.get_usd_price(new token)",
        lambda: client.trading.get_usd_price(token_address))

    # T05: Sell 50% 
    time.sleep(5)  # block delay
    run_test("T05", "trading.sell_percentage(50%)",
        lambda: client.trading.sell_percentage(token_address, 50))

    # T06: Sell with explicit amount (1 token)
    time.sleep(5)
    run_test("T06", "trading.sell(1 token, to_usdb=True)",
        lambda: client.trading.sell(token_address, 1 * 10**18, to_usdb=True))

    # T07: Get claimable rewards (new function)
    run_test("T07", "factory.get_claimable_rewards(token, wallet)",
        lambda: client.factory.get_claimable_rewards(token_address, WALLET))

    # T08: Take loan against remaining tokens
    loan_result = None
    def test_take_loan():
        global loan_result
        loan_result = client.loans.take_loan(MAINTOKEN, token_address, 1 * 10**18, 7)
        return f"tx={loan_result.get('hash', '')[:16]}..."
    run_test("T08", "loans.take_loan(1 token, 7 days)", test_take_loan)

    # T09: Get loan count + details
    run_test("T09", "loans.get_user_loan_count(wallet)",
        lambda: client.loans.get_user_loan_count(WALLET))

    loan_count = None
    try:
        loan_count = client.loans.get_user_loan_count(WALLET)
    except:
        pass

    if loan_count and loan_count > 0:
        run_test("T10", "loans.get_user_loan_details(wallet, last_loan)",
            lambda: client.loans.get_user_loan_details(WALLET, loan_count - 1))

        # T11: Extend loan
        run_test("T11", "loans.extend_loan(+5 days)",
            lambda: client.loans.extend_loan(loan_count - 1, 5, True, False))

        # T12: Repay loan
        run_test("T12", "loans.repay_loan()",
            lambda: client.loans.repay_loan(loan_count - 1))

    # T13: Leverage buy
    time.sleep(3)
    lev_result = run_test("T13", "trading.leverage_buy(5 USDB, 7 days)",
        lambda: client.trading.leverage_buy(5 * 10**18, 0, [USDB, MAINTOKEN], 7))

    # T14: Partial leverage sell
    if lev_result:
        time.sleep(6)  # block delay
        lev_count = None
        try:
            lev_count = client.trading.get_leverage_count(WALLET)
        except:
            pass
        if lev_count and lev_count > 0:
            run_test("T14", "trading.partial_loan_sell(50%)",
                lambda: client.trading.partial_loan_sell(lev_count - 1, 50, True, 0))

    # T15: Leverage simulator for factory token
    run_test("T15", "leverage_simulator.simulate_leverage_factory()",
        lambda: client.leverage_simulator.simulate_leverage_factory(
            5 * 10**18, [USDB, MAINTOKEN, token_address], 7))

# ─── SUMMARY ───
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
skipped = sum(1 for r in results if r["status"] == "SKIP")
print(f"Total: {len(results)} | ✅ Passed: {passed} | ❌ Failed: {failed} | ⚠️ Skipped: {skipped}")
print()

if failed > 0:
    print("FAILURES:")
    for r in results:
        if r["status"] == "FAIL":
            print(f"  [{r['id']}] {r['name']}: {r['detail']}")

# Save results
results_path = os.path.join(os.path.dirname(__file__), 'tier1_results.json')
with open(results_path, 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved to {results_path}")
