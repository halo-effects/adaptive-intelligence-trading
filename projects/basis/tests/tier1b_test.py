"""
Basis SDK — Tier 1 Batch 2: Loans, Leverage Partial Sell, Staking, Vesting, Predictions
"""
import sys, os, time, json, traceback

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'basis-sdk-python'))
from basis import BasisClient

PRIVATE_KEY = "0x062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"
WALLET = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"

results = []

def log(test_id, name, status, detail=""):
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    entry = {"id": test_id, "name": name, "status": status, "detail": str(detail)[:300]}
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
print("BASIS SDK TIER 1 BATCH 2 — Python")
print("=" * 60)

# Init client
print("\n--- Init ---")
client = BasisClient.create(private_key=PRIVATE_KEY)
USDB = client.usdb_address
MAINTOKEN = client.main_token_address
print(f"✅ Client ready. USDB={USDB[:10]}... MAIN={MAINTOKEN[:10]}...")

# Use existing token from batch 1
tokens = client.factory.get_tokens_by_creator(WALLET)
if tokens:
    TOKEN = tokens[-1]  # latest created token
    print(f"Using existing token: {TOKEN}")
else:
    print("❌ No tokens found — run tier1_test.py first")
    sys.exit(1)

# ─── LOANS (fixed: 10 day minimum) ───
print("\n--- Loans ---")

# First buy some tokens to use as collateral
run_test("L00", "Buy 5 USDB of token for collateral",
    lambda: client.trading.buy(TOKEN, 5 * 10**18))

time.sleep(3)

loan_id = None
def test_take_loan():
    global loan_id
    result = client.loans.take_loan(MAINTOKEN, TOKEN, 1 * 10**18, 10)  # 10 days minimum!
    return f"tx={result.get('hash', '')[:16]}..."
run_test("L01", "loans.take_loan(1 token, 10 days)", test_take_loan)

loan_count = run_test("L02", "loans.get_user_loan_count()",
    lambda: client.loans.get_user_loan_count(WALLET))

if loan_count and loan_count > 0:
    loan_id = loan_count - 1
    run_test("L03", f"loans.get_user_loan_details(id={loan_id})",
        lambda: client.loans.get_user_loan_details(WALLET, loan_id))

    run_test("L04", "loans.extend_loan(+5 days, pay in USDB)",
        lambda: client.loans.extend_loan(loan_id, 5, True, False))

    # L05: increase loan (add more collateral)
    run_test("L05", "loans.increase_loan(+0.5 tokens)",
        lambda: client.loans.increase_loan(loan_id, 5 * 10**17))

    run_test("L06", "loans.repay_loan()",
        lambda: client.loans.repay_loan(loan_id))
else:
    print("⚠️ No loans found, skipping loan management tests")

# ─── LEVERAGE PARTIAL SELL ───
print("\n--- Leverage ---")

# Open a fresh leverage position
run_test("V01", "trading.leverage_buy(5 USDB, 10 days)",
    lambda: client.trading.leverage_buy(5 * 10**18, 0, [USDB, MAINTOKEN], 10))

time.sleep(6)  # block delay required

lev_count = run_test("V02", "trading.get_leverage_count()",
    lambda: client.trading.get_leverage_count(WALLET))

if lev_count and lev_count > 0:
    lev_id = lev_count - 1
    run_test("V03", f"trading.get_leverage_position(id={lev_id})",
        lambda: client.trading.get_leverage_position(WALLET, lev_id))

    run_test("V04", "trading.partial_loan_sell(50%, isLeverage=True)",
        lambda: client.trading.partial_loan_sell(lev_id, 50, True, 0))

# ─── STAKING ───
print("\n--- Staking ---")

# Need to buy MAINTOKEN (STASIS) first
run_test("S00", "Buy 10 USDB of STASIS for staking",
    lambda: client.trading.buy(MAINTOKEN, 10 * 10**18))

time.sleep(3)

# Wrap STASIS → wSTASIS
run_test("S01", "staking.buy(2 STASIS) — wrap",
    lambda: client.staking.buy(2 * 10**18))

# Check shares
shares = run_test("S02", "staking.convert_to_shares(1 STASIS)",
    lambda: client.staking.convert_to_shares(1 * 10**18))

# Lock
if shares:
    run_test("S03", f"staking.lock({shares} shares)",
        lambda: client.staking.lock(int(shares)))

    # Borrow against locked
    run_test("S04", "staking.borrow(0.5 STASIS, 10 days)",
        lambda: client.staking.borrow(5 * 10**17, 10))

    # Repay staking loan
    run_test("S05", "staking.repay()",
        lambda: client.staking.repay())

    # Unlock
    run_test("S06", f"staking.unlock({shares} shares)",
        lambda: client.staking.unlock(int(shares)))

    # Unwrap (sell wSTASIS → STASIS)
    run_test("S07", f"staking.sell({shares} shares)",
        lambda: client.staking.sell(int(shares)))

# ─── VESTING ───
print("\n--- Vesting ---")

# Buy tokens for vesting
run_test("VE00", "Buy 5 USDB of token for vesting",
    lambda: client.trading.buy(TOKEN, 5 * 10**18))

time.sleep(3)

# Create gradual vesting (per-second, 1 day duration for fast test)
import math
start_time = int(time.time())
vesting_id = None

def test_create_vesting():
    global vesting_id
    result = client.vesting.create_gradual_vesting(
        WALLET,          # beneficiary = self
        TOKEN,           # token
        1 * 10**18,      # 1 token
        start_time,      # start now
        1,               # 1 day duration (minimum)
        0,               # TimeUnit.Second (fastest unlock)
        "SDK test vesting",
        MAINTOKEN        # ecosystem
    )
    return f"tx={result.get('hash', '')[:16]}..."
run_test("VE01", "vesting.create_gradual_vesting(1 token, 1 day, per-second)", test_create_vesting)

# Get vesting IDs
vestings = run_test("VE02", "vesting.get_vestings_by_beneficiary(wallet)",
    lambda: client.vesting.get_vestings_by_beneficiary(WALLET))

if vestings and len(vestings) > 0:
    vesting_id = vestings[-1] if isinstance(vestings[-1], int) else int(vestings[-1])
    
    run_test("VE03", f"vesting.get_vesting_details(id={vesting_id})",
        lambda: client.vesting.get_vesting_details(vesting_id))

    run_test("VE04", f"vesting.get_claimable_amount(id={vesting_id})",
        lambda: client.vesting.get_claimable_amount(vesting_id))

    # Create cliff vesting
    def test_cliff():
        result = client.vesting.create_cliff_vesting(
            WALLET, TOKEN, 1 * 10**18,
            int(time.time()) + 86400,  # unlock in 24h
            "SDK cliff test", MAINTOKEN
        )
        return f"tx={result.get('hash', '')[:16]}..."
    run_test("VE05", "vesting.create_cliff_vesting(1 token, 24h)", test_cliff)

# ─── PREDICTION MARKETS ───
print("\n--- Prediction Markets ---")

market_token = None
def test_create_market():
    global market_token
    end_time = int(time.time()) + 3600  # 1 hour from now (short for testing)
    result = client.prediction_markets.create_market_with_metadata(
        market_name="SDK Test: Will this test pass?",
        symbol="SDKT1",
        end_time=end_time,
        option_names=["Yes", "No"],
        maintoken=MAINTOKEN,
        seed_amount=50 * 10**18,
        description="Automated SDK test market",
        image_url="https://picsum.photos/512/512",
    )
    market_token = result.get("market_token_address") or result.get("marketTokenAddress")
    return f"market={market_token}, tx={result.get('hash', '')[:16]}..."
run_test("P01", "prediction_markets.create_market_with_metadata()", test_create_market)

if market_token:
    # Read market data
    run_test("P02", "prediction_markets.get_market_data()",
        lambda: client.prediction_markets.get_market_data(market_token))

    run_test("P03", "prediction_markets.get_num_outcomes()",
        lambda: client.prediction_markets.get_num_outcomes(market_token))

    run_test("P04", "prediction_markets.get_option_names()",
        lambda: client.prediction_markets.get_option_names(market_token))

    run_test("P05", "prediction_markets.get_initial_reserves(2)",
        lambda: client.prediction_markets.get_initial_reserves(2))

    # Buy "Yes" shares (outcome 0) with 5 USDB
    run_test("P06", "prediction_markets.buy(Yes, 5 USDB)",
        lambda: client.prediction_markets.buy(market_token, 0, USDB, 5 * 10**18, 0, 0))

    # Check shares
    run_test("P07", "prediction_markets.get_user_shares(outcome 0)",
        lambda: client.prediction_markets.get_user_shares(market_token, WALLET, 0))

    run_test("P08", "prediction_markets.has_betted_on_market()",
        lambda: client.prediction_markets.has_betted_on_market(market_token, WALLET))

    run_test("P09", "prediction_markets.get_bounty_pool()",
        lambda: client.prediction_markets.get_bounty_pool(market_token))

    run_test("P10", "prediction_markets.get_general_pot()",
        lambda: client.prediction_markets.get_general_pot(market_token))

    # Market reader
    MARKET_TRADING = "0xCb64910a19B3641eb600b904741a074578Dda3F7"
    run_test("P11", "market_reader.get_all_outcomes()",
        lambda: client.market_reader.get_all_outcomes(MARKET_TRADING, market_token))

    run_test("P12", "market_reader.estimate_shares_out(5 USDB, outcome 0)",
        lambda: client.market_reader.estimate_shares_out(MARKET_TRADING, market_token, 0, 5 * 10**18, [], WALLET))

    run_test("P13", "market_reader.get_potential_payout(1000 shares, outcome 0)",
        lambda: client.market_reader.get_potential_payout(MARKET_TRADING, market_token, 0, 1000 * 10**18, 5 * 10**18))

    # Order book
    shares_held = None
    try:
        shares_held = int(client.prediction_markets.get_user_shares(market_token, WALLET, 0))
    except:
        pass

    if shares_held and shares_held > 0:
        list_amount = shares_held // 4  # list 25% of shares
        run_test("P14", "order_book.list_order(25% shares at 0.60 USDB)",
            lambda: client.order_book.list_order(market_token, 0, list_amount, 6 * 10**17))

        # Get order book
        run_test("P15", "prediction_markets.get_buy_order_amounts_out(order 0, 1 USDB)",
            lambda: client.prediction_markets.get_buy_order_amounts_out(market_token, 0, 1 * 10**18))

    # Save market token for resolver tests later
    with open(os.path.join(os.path.dirname(__file__), 'market_token.txt'), 'w') as f:
        f.write(market_token)
    print(f"  Market token saved for resolver tests: {market_token}")

# ─── AGENT IDENTITY ───
print("\n--- Agent Identity ---")

run_test("AG01", "agent.is_registered(wallet)",
    lambda: client.agent.is_registered(WALLET))

run_test("AG02", "agent.list_agents()",
    lambda: client.agent.list_agents(page=1, limit=5))

# ─── API ENDPOINTS ───
print("\n--- API Data Endpoints ---")

if tokens:
    run_test("API01", "api.get_candles(token, 1h)",
        lambda: client.api.get_candles(tokens[0], interval="1h", limit=10))

    run_test("API02", "api.get_trades(token)",
        lambda: client.api.get_trades(tokens[0], limit=5))

    run_test("API03", "api.get_wallet_transactions(wallet)",
        lambda: client.api.get_wallet_transactions(WALLET, limit=5))

if market_token:
    run_test("API04", "api.get_orders(market)",
        lambda: client.api.get_orders(market_token, limit=5))

    run_test("API05", "api.get_market_liquidity(market)",
        lambda: client.api.get_market_liquidity(market_token, limit=5))

# ─── SUMMARY ───
print("\n" + "=" * 60)
print("TEST SUMMARY — TIER 1 BATCH 2")
print("=" * 60)
passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
print(f"Total: {len(results)} | ✅ Passed: {passed} | ❌ Failed: {failed}")
print()

if failed > 0:
    print("FAILURES:")
    for r in results:
        if r["status"] == "FAIL":
            print(f"  [{r['id']}] {r['name']}: {r['detail'][:200]}")

results_path = os.path.join(os.path.dirname(__file__), 'tier1b_results.json')
with open(results_path, 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved to {results_path}")
