"""
Basis SDK — Tiers 2-6 (excluding resolution/dispute)
Frozen tokens, private markets, vesting management, agent identity,
reads, leverage sim, taxes, API endpoints
"""
import sys, os, time, json, traceback

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'basis-sdk-python'))
from basis import BasisClient

PK = '0x062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4'
WALLET = '0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2'
MARKET_TRADING = '0xCb64910a19B3641eb600b904741a074578Dda3F7'

results = []

def log(test_id, name, status, detail=""):
    icon = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "SKIP"
    entry = {"id": test_id, "name": name, "status": status, "detail": str(detail)[:300]}
    results.append(entry)
    print(f"[{icon}] [{test_id}] {name}: {str(detail)[:200]}")

def run(test_id, name, fn):
    try:
        result = fn()
        log(test_id, name, "PASS", result)
        return result
    except Exception as e:
        log(test_id, name, "FAIL", f"{type(e).__name__}: {e}")
        return None

print("=" * 60)
print("BASIS SDK TIERS 2-6 (excl. resolution)")
print("=" * 60)

c = BasisClient.create(private_key=PK)
USDB = c.usdb_address
MAIN = c.main_token_address
print(f"Client ready. USDB={USDB[:10]}... MAIN={MAIN[:10]}...")

# Get existing tokens
tokens = c.factory.get_tokens_by_creator(WALLET)
TOKEN = tokens[-1] if tokens else None
print(f"Using token: {TOKEN}")

# Load market token from batch 2
mkt_file = os.path.join(os.path.dirname(__file__), 'market_token.txt')
MARKET_TOKEN = None
if os.path.exists(mkt_file):
    MARKET_TOKEN = open(mkt_file).read().strip()
    print(f"Market token: {MARKET_TOKEN}")

# =============================================
# TIER 2 — Frozen Token & Whitelist
# =============================================
print("\n--- TIER 2: Frozen Token & Whitelist ---")

frozen_token = None
def test_create_frozen():
    global frozen_token
    result = c.factory.create_token_with_metadata(
        name="SDK Frozen Test",
        symbol="SDKFRZ",
        description="Frozen token for SDK testing",
        image_url="https://picsum.photos/512/512",
        frozen=True,
        initial_buy_amount=50 * 10**18,
    )
    frozen_token = result.get("token_address") or result.get("tokenAddress")
    return f"token={frozen_token}"
run("T2-01", "factory.create_token(frozen=True, $50 initial buy)", test_create_frozen)
time.sleep(5)

if frozen_token:
    # Set whitelist for our wallet
    run("T2-02", "factory.set_whitelisted_wallet(our wallet, 100 tokens, tag=0)",
        lambda: c.factory.set_whitelisted_wallet(frozen_token, [WALLET], 100 * 10**18, 0))

    # Buy within whitelist limit
    run("T2-03", "trading.buy(frozen token, $50 — within whitelist)",
        lambda: c.trading.buy(frozen_token, 50 * 10**18))
    time.sleep(3)

    # Remove whitelist
    run("T2-04", "factory.remove_whitelist(our wallet)",
        lambda: c.factory.remove_whitelist(frozen_token, WALLET))

    # Disable freeze entirely
    run("T2-05", "factory.disable_freeze()",
        lambda: c.factory.disable_freeze(frozen_token))

    # Buy after freeze disabled — should work
    run("T2-06", "trading.buy(frozen token, $50 — post-freeze-disable)",
        lambda: c.trading.buy(frozen_token, 50 * 10**18))

# =============================================
# TIER 1 GAPS — Order Book, Vesting, Staking mgmt
# =============================================
print("\n--- TIER 1 GAPS: Order Book ---")

if MARKET_TOKEN:
    # Cancel the order we listed in batch 2
    run("T1-40", "order_book.cancel_order(market, order 0)",
        lambda: c.order_book.cancel_order(MARKET_TOKEN, 0))

    # List a new order, then buy it
    shares = c.prediction_markets.get_user_shares(MARKET_TOKEN, WALLET, 0)
    if shares and int(shares) > 0:
        list_amt = int(shares) // 5
        run("T1-41a", "order_book.list_order(20% shares at 0.55)",
            lambda: c.order_book.list_order(MARKET_TOKEN, 0, list_amt, 55 * 10**16))
        time.sleep(3)

        # Buy our own order (self-fill allowed?)
        run("T1-41b", "order_book.buy_order(order 1, fill 50%)",
            lambda: c.order_book.buy_order(MARKET_TOKEN, 1, list_amt // 2))

        # Get order cost
        run("T1-41c", "order_book.get_buy_order_cost(order 1, fill remaining)",
            lambda: c.order_book.get_buy_order_cost(MARKET_TOKEN, 1, list_amt // 2))

    # buyOrdersAndContract (hybrid AMM + book)
    run("T1-38", "prediction_markets.buy_orders_and_contract(Yes, $50, no orders)",
        lambda: c.prediction_markets.buy_orders_and_contract(MARKET_TOKEN, 0, [], USDB, 50 * 10**18, 0))

print("\n--- TIER 1 GAPS: Vesting Management ---")

# Create a vesting we can manage
vesting_token = TOKEN
run("T1-VE-buy", "Buy $50 tokens for vesting",
    lambda: c.trading.buy(TOKEN, 50 * 10**18))
time.sleep(3)

vesting_id = None
def test_create_vest():
    global vesting_id
    result = c.vesting.create_cliff_vesting(
        WALLET, TOKEN, 5 * 10**18,
        int(time.time()) + 120,  # 2 min from now (future)
        "SDK cliff test", MAIN
    )
    return f"tx={result.get('hash', '')[:16]}..."
run("T1-25", "vesting.create_cliff_vesting($5, unlock in 2 min)", test_create_vest)
time.sleep(3)

vestings = c.vesting.get_vestings_by_beneficiary(WALLET)
if vestings and len(vestings) > 0:
    vesting_id = vestings[-1] if isinstance(vestings[-1], int) else int(vestings[-1])
    
    # Gradual vesting for management tests
    gradual_id = None
    def test_gradual():
        global gradual_id
        result = c.vesting.create_gradual_vesting(
            WALLET, TOKEN, 5 * 10**18,
            int(time.time()) + 60,  # start in 60s
            1,  # 1 day
            0,  # per-second
            "SDK gradual for mgmt", MAIN
        )
        return f"tx={result.get('hash', '')[:16]}..."
    run("T1-24b", "vesting.create_gradual_vesting(start +60s)", test_gradual)
    time.sleep(3)

    vestings2 = c.vesting.get_vestings_by_beneficiary(WALLET)
    if len(vestings2) > len(vestings):
        gradual_id = vestings2[-1] if isinstance(vestings2[-1], int) else int(vestings2[-1])

        run("T1-30", "vesting.extend_vesting_period(+1 day)",
            lambda: c.vesting.extend_vesting_period(gradual_id, 1))

        run("T1-31", "vesting.add_tokens_to_vesting(+2 tokens)",
            lambda: c.vesting.add_tokens_to_vesting(gradual_id, 2 * 10**18))

        run("T1-29", "vesting.change_beneficiary(to self — noop)",
            lambda: c.vesting.change_beneficiary(gradual_id, WALLET))

        run("T1-32", "vesting.transfer_creator_role(to self — noop)",
            lambda: c.vesting.transfer_creator_role(gradual_id, WALLET))

    # Take loan on vesting
    run("T1-27", f"vesting.take_loan_on_vesting(id={vesting_id})",
        lambda: c.vesting.take_loan_on_vesting(vesting_id))

    # Repay loan on vesting
    run("T1-28", f"vesting.repay_loan_on_vesting(id={vesting_id})",
        lambda: c.vesting.repay_loan_on_vesting(vesting_id))

    # Batch vestings
    run("T1-33", "vesting.batch_create_gradual_vesting(2 beneficiaries)",
        lambda: c.vesting.batch_create_gradual_vesting(
            [WALLET, "0x0000000000000000000000000000000000000001"],
            TOKEN, [1 * 10**18, 1 * 10**18],
            ["batch test 1", "batch test 2"],
            int(time.time()) + 120, 1, 0, MAIN
        ))

    run("T1-34", "vesting.batch_create_cliff_vesting(2 beneficiaries)",
        lambda: c.vesting.batch_create_cliff_vesting(
            [WALLET, "0x0000000000000000000000000000000000000001"],
            TOKEN, [1 * 10**18, 1 * 10**18],
            int(time.time()) + 86400,
            ["batch cliff 1", "batch cliff 2"], MAIN
        ))

# Vestings by creator
run("T5-88", "vesting.get_vestings_by_creator(wallet)",
    lambda: c.vesting.get_vestings_by_creator(WALLET))

print("\n--- TIER 1 GAPS: Staking Extended ---")

# Buy STASIS for staking tests
run("STK-buy", "Buy $50 STASIS for staking",
    lambda: c.trading.buy(MAIN, 50 * 10**18))
time.sleep(3)

# Full staking lifecycle with bigger amounts
shares = c.staking.convert_to_shares(10 * 10**18)
run("STK-01", "staking.buy(10 STASIS) wrap", lambda: c.staking.buy(10 * 10**18))
time.sleep(3)

run("STK-02", f"staking.lock({shares} shares)", lambda: c.staking.lock(shares))

# Borrow bigger amount
run("STK-03", "staking.borrow(5 STASIS, 10 days)",
    lambda: c.staking.borrow(5 * 10**18, 10))

# Add to loan
run("STK-04", "staking.add_to_loan(2 STASIS)",
    lambda: c.staking.add_to_loan(2 * 10**18))

# Extend staking loan
run("STK-05", "staking.extend_loan(+5 days, pay USDB, no refinance)",
    lambda: c.staking.extend_loan(5, True, False))

# Get user stake details
run("STK-06", "staking.get_user_stake_details(wallet)",
    lambda: c.staking.get_user_stake_details(WALLET))

# Repay
run("STK-07", "staking.repay()", lambda: c.staking.repay())

# Unlock and sell
run("STK-08", f"staking.unlock({shares} shares)", lambda: c.staking.unlock(shares))
run("STK-09", f"staking.sell({shares} shares)", lambda: c.staking.sell(shares))

# =============================================
# TIER 4 — Private Markets
# =============================================
print("\n--- TIER 4: Private Markets ---")

private_market = None
def test_create_private():
    global private_market
    result = c.private_markets.create_market(
        market_name="SDK Private Test",
        symbol="SDKPRV",
        end_time=int(time.time()) + 7200,  # 2 hours
        option_names=["Yes", "No"],
        maintoken=MAIN,
        frozen=False,
        bonding=0,
        seed_amount=50 * 10**18,
    )
    private_market = result.get("market_token_address") or result.get("marketTokenAddress") or result.get("market_token")
    return f"market={private_market}"
run("T4-60", "private_markets.create_market($50 seed)", test_create_private)
time.sleep(5)

if private_market:
    run("T4-61", "private_markets.buy(Yes, $50)",
        lambda: c.private_markets.buy(private_market, 0, USDB, 50 * 10**18, 0, 0))

    run("T4-61r", "private_markets.get_market_data()",
        lambda: c.private_markets.get_market_data(private_market))

    run("T4-62r", "private_markets.get_outcome(0)",
        lambda: c.private_markets.get_outcome(private_market, 0))

    run("T4-63r", "private_markets.get_user_shares(outcome 0)",
        lambda: c.private_markets.get_user_shares(private_market, WALLET, 0))

    run("T4-64r", "private_markets.get_initial_reserves(2)",
        lambda: c.private_markets.get_initial_reserves(2))

    # List order on private market
    priv_shares = c.private_markets.get_user_shares(private_market, WALLET, 0)
    if priv_shares and int(priv_shares) > 0:
        run("T4-70a", "private_markets.list_order(20% at 0.60)",
            lambda: c.private_markets.list_order(private_market, 0, int(priv_shares) // 5, 6 * 10**17))

    # Save for later
    with open(os.path.join(os.path.dirname(__file__), 'private_market.txt'), 'w') as f:
        f.write(private_market or "")

# =============================================
# TIER 4 — Agent Identity
# =============================================
print("\n--- TIER 4: Agent Identity ---")

run("T4-A01", "agent.is_registered(wallet)", lambda: c.agent.is_registered(WALLET))

agent_id = None
def test_register():
    global agent_id
    result = c.agent.register({"name": "SDK Test Agent v2", "description": "Automated test"})
    agent_id = result
    return result
run("T4-A02", "agent.register()", test_register)

def test_register_sync():
    result = c.agent.register_and_sync({"name": "SDK Test Agent v3", "description": "Automated test with sync"})
    return result
run("T4-A03", "agent.register_and_sync()", test_register_sync)

run("T4-A04", "agent.lookup_from_api(wallet)", lambda: c.agent.lookup_from_api(WALLET))
run("T4-A05", "agent.list_agents(page=1)", lambda: c.agent.list_agents(page=1, limit=5))

# Try to get agent URI/wallet if we have an agent ID
run("T4-A06", "agent.get_agent_uri(1)", lambda: c.agent.get_agent_uri(1))
run("T4-A07", "agent.get_agent_wallet(1)", lambda: c.agent.get_agent_wallet(1))

# =============================================
# TIER 5 — All Read Methods
# =============================================
print("\n--- TIER 5: Read Methods ---")

# Trading reads
run("T5-71", "trading.get_amounts_out(50 USDB, [USDB, MAIN])",
    lambda: c.trading.get_amounts_out(50 * 10**18, [USDB, MAIN]))
run("T5-72", "trading.get_token_price(MAIN)",
    lambda: c.trading.get_token_price(MAIN))
run("T5-73", "trading.get_usd_price(MAIN)",
    lambda: c.trading.get_usd_price(MAIN))
if TOKEN:
    run("T5-72b", "trading.get_token_price(factory token)",
        lambda: c.trading.get_token_price(TOKEN))
    run("T5-73b", "trading.get_usd_price(factory token)",
        lambda: c.trading.get_usd_price(TOKEN))

run("T5-74", "trading.get_leverage_count(wallet)",
    lambda: c.trading.get_leverage_count(WALLET))

lev_count = c.trading.get_leverage_count(WALLET)
if lev_count and lev_count > 0:
    run("T5-75", f"trading.get_leverage_position(wallet, {lev_count-1})",
        lambda: c.trading.get_leverage_position(WALLET, lev_count - 1))

# Factory reads
run("T5-76", "factory.get_token_state(token)",
    lambda: c.factory.get_token_state(TOKEN) if TOKEN else "no token")
run("T5-77", "factory.is_ecosystem_token(MAIN)",
    lambda: c.factory.is_ecosystem_token(MAIN))
run("T5-78", "factory.get_tokens_by_creator(wallet)",
    lambda: c.factory.get_tokens_by_creator(WALLET))
run("T5-79", "factory.get_fee_amount()",
    lambda: c.factory.get_fee_amount())
run("T5-79b", "factory.get_claimable_rewards(token, wallet)",
    lambda: c.factory.get_claimable_rewards(TOKEN, WALLET) if TOKEN else "no token")

# Loan reads
run("T5-80", "loans.get_user_loan_details(wallet, 1)",
    lambda: c.loans.get_user_loan_details(WALLET, 1))
run("T5-81", "loans.get_user_loan_count(wallet)",
    lambda: c.loans.get_user_loan_count(WALLET))

# Staking reads
run("T5-82", "staking.get_available_stasis(wallet)",
    lambda: c.staking.get_available_stasis(WALLET))
run("T5-83", "staking.convert_to_shares(1 STASIS)",
    lambda: c.staking.convert_to_shares(1 * 10**18))
run("T5-84", "staking.convert_to_assets(1e18 shares)",
    lambda: c.staking.convert_to_assets(1 * 10**18))

# Vesting reads
if vestings and len(vestings) > 0:
    vid = vestings[-1] if isinstance(vestings[-1], int) else int(vestings[-1])
    run("T5-85", f"vesting.get_vesting_details({vid})",
        lambda: c.vesting.get_vesting_details(vid))
    run("T5-86", f"vesting.get_claimable_amount({vid})",
        lambda: c.vesting.get_claimable_amount(vid))
run("T5-87", "vesting.get_vestings_by_beneficiary(wallet)",
    lambda: c.vesting.get_vestings_by_beneficiary(WALLET))

# Prediction reads (using market from batch 2)
if MARKET_TOKEN:
    run("T5-89", "prediction_markets.get_market_data()",
        lambda: c.prediction_markets.get_market_data(MARKET_TOKEN))
    run("T5-90", "prediction_markets.get_outcome(0)",
        lambda: c.prediction_markets.get_outcome(MARKET_TOKEN, 0))
    run("T5-91", "prediction_markets.get_user_shares(0)",
        lambda: c.prediction_markets.get_user_shares(MARKET_TOKEN, WALLET, 0))
    run("T5-92", "prediction_markets.get_num_outcomes()",
        lambda: c.prediction_markets.get_num_outcomes(MARKET_TOKEN))
    run("T5-93", "prediction_markets.get_option_names()",
        lambda: c.prediction_markets.get_option_names(MARKET_TOKEN))
    run("T5-94", "prediction_markets.get_bounty_pool()",
        lambda: c.prediction_markets.get_bounty_pool(MARKET_TOKEN))
    run("T5-95", "prediction_markets.get_general_pot()",
        lambda: c.prediction_markets.get_general_pot(MARKET_TOKEN))
    run("T5-96", "prediction_markets.has_betted_on_market()",
        lambda: c.prediction_markets.has_betted_on_market(MARKET_TOKEN, WALLET))

    # Market reader
    run("T5-102", "market_reader.get_all_outcomes()",
        lambda: c.market_reader.get_all_outcomes(MARKET_TRADING, MARKET_TOKEN))
    run("T5-103", "market_reader.estimate_shares_out(50 USDB)",
        lambda: c.market_reader.estimate_shares_out(MARKET_TRADING, MARKET_TOKEN, 0, 50 * 10**18, [], WALLET))
    run("T5-104", "market_reader.get_potential_payout(1000 shares)",
        lambda: c.market_reader.get_potential_payout(MARKET_TRADING, MARKET_TOKEN, 0, 1000 * 10**18, 50 * 10**18))

# Resolver reads (no resolution yet, but reads should still work)
if MARKET_TOKEN:
    run("T5-94r", "resolver.is_resolved(market)",
        lambda: c.resolver.is_resolved(MARKET_TOKEN))
    run("T5-96r", "resolver.is_in_dispute(market)",
        lambda: c.resolver.is_in_dispute(MARKET_TOKEN))
    run("T5-97r", "resolver.is_in_veto(market)",
        lambda: c.resolver.is_in_veto(MARKET_TOKEN))
    run("T5-98r", "resolver.get_current_round(market)",
        lambda: c.resolver.get_current_round(MARKET_TOKEN))
    run("T5-99r", "resolver.get_dispute_data(market)",
        lambda: c.resolver.get_dispute_data(MARKET_TOKEN))
    run("T5-100r", "resolver.get_user_stake(wallet)",
        lambda: c.resolver.get_user_stake(WALLET))
    run("T5-101r", "resolver.is_voter(wallet)",
        lambda: c.resolver.is_voter(WALLET))
    run("T5-101b", "resolver.get_constants()",
        lambda: c.resolver.get_constants())

# Leverage simulator
run("T5-105", "leverage_sim.simulate_leverage(50 USDB, [USDB, MAIN], 10d)",
    lambda: c.leverage_simulator.simulate_leverage(50 * 10**18, [USDB, MAIN], 10))
run("T5-106", "leverage_sim.simulate_leverage_factory(50, [USDB, MAIN, TOKEN], 10d)",
    lambda: c.leverage_simulator.simulate_leverage_factory(50 * 10**18, [USDB, MAIN, TOKEN], 10) if TOKEN else "no token")

# Taxes
run("T5-107", "taxes.get_tax_rate(MAIN, wallet)",
    lambda: c.taxes.get_tax_rate(MAIN, WALLET))
run("T5-108", "taxes.get_current_surge_tax(MAIN)",
    lambda: c.taxes.get_current_surge_tax(MAIN))
run("T5-109", "taxes.get_available_surge_quota(MAIN)",
    lambda: c.taxes.get_available_surge_quota(MAIN))
run("T5-110", "taxes.get_base_tax_rates()",
    lambda: c.taxes.get_base_tax_rates())

# =============================================
# TIER 6 — Off-Chain API
# =============================================
print("\n--- TIER 6: Off-Chain API ---")

# Auth & API keys
run("T6-116", "api.create_api_key('sdk-test')",
    lambda: c.api.create_api_key("sdk-test"))
run("T6-117", "api.list_api_keys()",
    lambda: c.api.list_api_keys())

api_keys = c.api.list_api_keys()
if api_keys and api_keys.get("data"):
    # Delete the test key we just made
    test_key = api_keys["data"][-1]
    key_id = test_key.get("id") or test_key.get("_id")
    if key_id:
        run("T6-118", f"api.delete_api_key({key_id})",
            lambda: c.api.delete_api_key(str(key_id)))

# Image upload
run("T6-119", "api.upload_image_from_url(picsum)",
    lambda: c.api.upload_image_from_url("https://picsum.photos/512/512"))

# Token data endpoints
if TOKEN:
    run("T6-128", "api.get_tokens(limit=5)",
        lambda: c.api.get_tokens(limit=5))
    run("T6-129", f"api.get_token({TOKEN[:10]}...)",
        lambda: c.api.get_token(TOKEN))
    run("T6-130", "api.get_token_candles(token, 1h)",
        lambda: c.api.get_token_candles(TOKEN, interval="1h", limit=10))
    run("T6-131", "api.get_token_trades(token)",
        lambda: c.api.get_token_trades(TOKEN, limit=5))
    run("T6-132", "api.get_token_orders(token)",
        lambda: c.api.get_token_orders(TOKEN, limit=5))
    run("T6-133", "api.get_token_comments(token)",
        lambda: c.api.get_token_comments(TOKEN, limit=5))
    run("T6-134", "api.get_token_whitelist(token)",
        lambda: c.api.get_token_whitelist(TOKEN))

run("T6-135", "api.get_wallet_transactions(wallet)",
    lambda: c.api.get_wallet_transactions(WALLET, limit=5))

if MARKET_TOKEN:
    run("T6-136", "api.get_market_liquidity(market)",
        lambda: c.api.get_market_liquidity(MARKET_TOKEN, limit=5))

# Metadata update
if TOKEN:
    run("T6-121", "api.update_metadata(token, description update)",
        lambda: c.api.update_metadata(TOKEN, description="Updated by SDK test suite"))

    run("T6-122", "api.update_project(token, website)",
        lambda: c.api.update_project(TOKEN, website="https://test.basis.market"))

# Comments
if TOKEN:
    comment_result = run("T6-123", "api.create_comment(token)",
        lambda: c.api.create_comment(TOKEN, "SDK test comment - automated"))

    if comment_result and isinstance(comment_result, dict):
        cid = comment_result.get("id") or comment_result.get("data", {}).get("id")
        if cid:
            run("T6-124", f"api.delete_comment({cid})",
                lambda: c.api.delete_comment(cid, WALLET))

# Twitter challenge (just test the request, won't verify)
run("T6-126", "api.request_twitter_challenge()",
    lambda: c.api.request_twitter_challenge())

# Trading convertToNative
if MARKET_TOKEN:
    run("T1-07", "trading.convert_to_native(market, USDB, $50)",
        lambda: c.trading.convert_to_native(MARKET_TOKEN, USDB, 50 * 10**18))

# Claim rewards on factory token
if TOKEN:
    run("T1-CR", "factory.claim_rewards(token)",
        lambda: c.factory.claim_rewards(TOKEN))

# =============================================
# SUMMARY
# =============================================
print("\n" + "=" * 60)
print("TEST SUMMARY — TIERS 2-6")
print("=" * 60)
passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
skipped = sum(1 for r in results if r["status"] == "SKIP")
print(f"Total: {len(results)} | PASS: {passed} | FAIL: {failed} | SKIP: {skipped}")
print()

if failed > 0:
    print("FAILURES:")
    for r in results:
        if r["status"] == "FAIL":
            print(f"  [{r['id']}] {r['name']}: {r['detail'][:200]}")

results_path = os.path.join(os.path.dirname(__file__), 'tier2_6_results.json')
with open(results_path, 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved to {results_path}")
