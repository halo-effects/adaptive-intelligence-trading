# Basis SDK Module Test Report
**Date:** April 6, 2026 | **Tester:** GeeGee (AI Agent) | **SDK:** basis-sdk 0.1.0b1 (Python)

## Summary

Tested 14 modules across reads and writes. Out of ~80 methods tested, most work correctly. Key issues found below.

---

## ✅ Working Correctly

### Trading Module
- `buy(token, amount_wei)` — works (amount in wei, not USDB units)
- `sell(token, amount_wei)` — works
- `sell_percentage(token, pct, to_usdb, min_out, swap_to_eth)` — signature confirmed
- `get_token_price(token)` — works, returns raw wei
- `get_usd_price(token)` — works
- `get_amounts_out(amount, path)` — works
- `get_leverage_count(wallet)` — works
- `leverage_buy(amount, min_out, path, days)` — works (tx confirmed)

### Factory Module
- `create_token_with_metadata(...)` — works perfectly
- `get_token_state(token)` — works
- `get_floor_price(token)` — works
- `get_tokens_by_creator(wallet)` — works
- `get_claimable_rewards(token, wallet)` — works
- `is_ecosystem_token(token)` — works
- `get_fee_amount()` — works (returns 0 in Phase 1)

### Staking Module
- `get_available_stasis(wallet)` — works
- `get_user_stake_details(wallet)` — works
- `total_assets()` — works

### Loans Module
- `get_user_loan_count(wallet)` — works
- `get_user_loan_details(wallet, id)` — works

### Agent Module
- `register(config)` — works (on-chain)
- `register_and_sync(config)` — works (after Alex's fix)
- `is_registered(wallet)` — works
- `list_agents()` — works
- `lookup_from_api(wallet)` — works
- `get_metadata(wallet)` — works
- `set_agent_uri()` — signature confirmed

### Resolver Module
- `get_constants()` — works (returns DISPUTE_PERIOD, PROPOSAL_PERIOD, etc.)

### Taxes Module
- `get_available_surge_quota(token)` — works (returned 604800)
- `get_base_tax_rates()` — works (stasis:50, stable:50, default:150, prediction:150)
- `get_current_surge_tax(token)` — works (returned 0)

### Leverage Simulator
- `simulate_leverage(amount, path, days)` — works (returns array of position data)

### API Module (reads)
- `get_pulse()` — works
- `get_me()` — works
- `get_my_stats()` — works
- `get_my_referrals()` — works
- `get_leaderboard()` — works
- `get_faucet_status()` — works
- `get_moltbook_status()` — works
- `get_my_profile()` — works
- `get_public_profile(wallet)` — works
- `update_my_profile({username})` — works
- `claim_faucet()` — works
- `upload_image(file_path)` — works
- `create_reef_post(section, title, body)` — works
- `link_moltbook(name)` — works (returned challenge code)

---

## ⚠️ Issues Found

### 1. SDK amounts are in wei — docs show whole units
**Module:** Trading, Staking, all write operations
**Issue:** `trading.buy(token, 50)` sends 50 wei (~nothing), not 50 USDB. The Python SDK passes raw integers directly to the contract. Our docs show examples like `start_lp=1000` which works because it's not a token amount, but any USDB/token amount must be `amount * 10**18`.
**Doc fix needed:** Add a clear note that all amounts are in wei (18 decimals). Consider adding a helper like `client.to_wei(50)` or `client.parse_usdb(50)`.
**Severity:** HIGH — first thing any agent will hit

### 2. `staking.buy()` panics with arithmetic overflow
**Module:** Staking
**Issue:** `client.staking.buy(20 * 10**18)` throws `Panic error 0x11: Arithmetic operation results in underflow or overflow`. But `client.trading.buy(stasis_address, 20 * 10**18)` works fine and buys STASIS. The staking.buy() method has a different code path that hits an overflow.
**Severity:** MEDIUM — workaround exists (use trading.buy for STASIS)

### 3. `staking.lock()` fails with "transfer amount exceeds balance"
**Module:** Staking
**Issue:** After buying 30 STASIS via `trading.buy()`, calling `staking.lock(stasis_balance)` fails with "ERC20: transfer amount exceeds balance" even though the wallet clearly holds 30 STASIS. Possible approval issue or the lock() method reads from a different contract/wrapper.
**Severity:** HIGH — blocks the entire staking→borrow→leverage flow

### 4. Prediction market creation: "Seed below minimum"
**Module:** Prediction Markets
**Issue:** `create_market_with_metadata()` fails with "Seed below minimum" even with `seed_amount=10*10**18`. The minimum seed isn't documented. Also tried with seed_amount=0 — same error. What's the minimum seed?
**Severity:** HIGH — can't create prediction markets

### 5. Vesting: `time_unit` is uint8, not seconds
**Module:** Vesting
**Issue:** `create_gradual_vesting()` has `time_unit` parameter typed as `uint8` on-chain but the SDK accepts `int`. Passing `86400` (seconds per day) fails because uint8 max is 255. The docs say "time_unit" but don't clarify it's an enum, not seconds.
**Doc fix needed:** Document what valid `time_unit` values are (probably 0=seconds, 1=minutes, 2=hours, 3=days?)
**Severity:** MEDIUM — confusing param, needs doc

### 6. `/api/v1/tokens` requires API key, not SIWE
**Module:** API
**Issue:** `get_tokens()`, `get_token()`, `get_token_trades()`, `get_token_candles()`, `get_wallet_transactions()` all return 401 even with SIWE session. Error says "An API key is required." But the SDK creates the client with `api_key='skip'` and the docs say these endpoints accept "SIWE Session or API Key."
**Doc fix needed:** Clarify which endpoints are API-key-only vs SIWE-compatible
**Severity:** MEDIUM — blocks token discovery for agents using SIWE auth

### 7. `leverage_buy()` returns empty position data
**Module:** Trading
**Issue:** `leverage_buy(10*10**18, 0, path, 7)` succeeds (tx confirmed, gas used), leverage_count shows 1, but `get_leverage_position(wallet, 0)` returns all zeros/empty addresses. The position may be stored differently or the read method has wrong index.
**Severity:** LOW — position might just need different query approach

### 8. `staking.borrow()` signature differs from docs
**Module:** Staking
**Issue:** SDK signature is `borrow(stasis_amount_to_borrow, days)` but our docs describe the borrow amount in USDB terms. The first param name says "stasis_amount" — is it STASIS or USDB? Clarify.
**Severity:** LOW — naming confusion

### 9. `register()` doesn't sync to backend DB
**Module:** Agent
**Issue:** `register()` mints on-chain but doesn't sync to the API database. Only `register_and_sync()` does. But if the on-chain tx succeeds and the sync fails, `register_and_sync()` returns 0 and doesn't retry the sync (since NFT exists). Alex has since added retry logic.
**Status:** FIXED by Alex (3-retry with backoff)

### 10. Avatar upload not supported via API (until today)
**Module:** API
**Issue:** `update_my_profile({avatarUrl})` returned "No valid action." Avatar was browser-only.
**Status:** FIXED by Alex (now accepts `{avatar: url}`)

---

## 📝 Doc Changes Needed

1. **All amounts are in wei (18 decimals)** — add this prominently to the SDK quickstart. The Python examples in 06-atomic-skills show `start_lp=1000` and `hybrid_multiplier=50` which are NOT wei, but any USDB/token amount IS wei. This distinction is critical.

2. **`create_market_with_metadata` params differ from docs** — Docs say `question`, `options`. SDK says `market_name`, `symbol`, `option_names`, `maintoken`, `seed_amount`. The mapping isn't obvious.

3. **`create_gradual_vesting` time_unit** — Document valid uint8 values

4. **Prediction market minimum seed** — Document the minimum required seed amount

5. **`leverage_buy` needs min_out param** — Docs show `leverage_buy(token, amount)` but SDK needs `(amount, min_out, path, days)`

6. **API key vs SIWE auth per endpoint** — Several v1 endpoints reject SIWE and require API key only. Document which is which.

7. **`staking.buy()` vs `trading.buy(stasis)`** — If staking.buy is broken, document the workaround or remove it

8. **Module count in MCP docs** — Verify tool count matches after SDK updates

---

## 🔧 SDK Improvements Suggested

1. **`client.parse_amount(50)` helper** — Convert human-readable to wei. Most common mistake.
2. **`trading.buy()` accept float** — `buy(token, 50.0)` should auto-convert to wei
3. **`staking.buy()` should work** — Currently panics; fix or remove
4. **Better error messages** — "Seed below minimum" should say what the minimum is
5. **`register_and_sync()` should always sync** — Even if on-chain already exists, force-sync metadata to DB

---

## Test Results Summary

| Module | Read Methods | Write Methods | Status |
|--------|-------------|---------------|--------|
| Trading | 4/4 ✅ | 3/4 (leverage position reads empty) | ⚠️ |
| Factory | 6/6 ✅ | 1/1 ✅ | ✅ |
| Staking | 3/3 ✅ | 0/2 (buy panics, lock fails) | ❌ |
| Loans | 2/2 ✅ | 0/1 (no collateral to test) | ⚠️ |
| Prediction Markets | N/A | 0/1 (seed minimum) | ❌ |
| Vesting | N/A | 0/1 (time_unit type) | ❌ |
| Agent | 5/5 ✅ | 2/2 ✅ (after fix) | ✅ |
| Resolver | 1/1 ✅ | N/A (no market to resolve) | ✅ |
| Taxes | 3/4 ⚠️ | N/A | ⚠️ |
| Leverage Sim | 1/1 ✅ | N/A | ✅ |
| Order Book | N/A | N/A (no market) | — |
| Market Reader | N/A | N/A (no market) | — |
| API | 12/17 ⚠️ | 4/4 ✅ | ⚠️ |
| Gasless | Broken (shows int methods) | — | ❌ |

**Overall: Read operations work well. Write operations have significant blockers in staking, prediction markets, and vesting.**
