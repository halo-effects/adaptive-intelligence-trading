# Basis Python SDK — Review Report

_GeeGee | 2026-03-19 | SDK version: 0.1.0b1_
_Files reviewed: client.py, api.py, 13 modules, 42 ABIs_

---

## Overall Assessment: 🟢 Solid

Clean, well-structured SDK. All 13 modules from the docs are present with full feature parity. The code is readable, consistent, and follows good patterns. A few items to address before PyPI publish — nothing blocking for internal testing.

---

## ✅ What's Good

### Architecture
- **Clean module separation** — 13 modules mirror the docs exactly (trading, factory, predictions, order book, loans, vesting, staking, resolver, private markets, market reader, leverage sim, taxes, agent identity)
- **Consistent patterns** — Every write module follows `_approve_if_needed` → `_build_and_send_tx` → return `{hash, receipt}`
- **BSC PoA middleware** — Correctly injected with fallback for older web3.py versions
- **SIWE auth flow** — Full `authenticate()` → `ensure_api_key()` chain in `BasisClient.create()`
- **Auto-approval** — All write methods auto-approve tokens before transacting, which is exactly what agents need (no manual approve step)
- **Order sync** — OrderBook and PrivateMarkets auto-sync to backend after writes, with non-fatal warning on failure
- **Image pipeline** — `upload_image_from_url()` does download → center-crop → 512x512 → WebP → IPFS in one call

### Feature Coverage (vs SDK docs v2)
- `createTokenWithMetadata` ✅
- `createMarketWithMetadata` ✅
- `sellPercentage` ✅
- `convertToNative` ✅
- `getMarketLiquidity` (API) ✅
- `getInitialReserves` ✅
- Agent identity with ERC-8004 ✅
- Full off-chain API (auth, metadata, comments, candles, trades, orders, whitelist, wallet tx) ✅

---

## 🟡 Minor Issues (non-blocking, fix before PyPI publish)

### 1. No `pyproject.toml` or `setup.py`
The zip contains only the source — no package metadata. Need at minimum:
```toml
[project]
name = "basis-sdk"
version = "0.1.0b1"
dependencies = [
    "web3>=6.0",
    "requests>=2.28",
    "eth-account>=0.8",
]

[project.optional-dependencies]
images = ["Pillow>=9.0"]
```
Without this, `pip install .` won't work. For my local testing I can add the directory to `sys.path`, but agents won't be able to `pip install basis-sdk` until this exists.

### 2. `__pycache__` included in zip
Compiled `.pyc` files from your local machine are in `modules/__pycache__/`. Not harmful but should be excluded from the release zip and future npm/PyPI packages. Add to `.gitignore` if not already.

### 3. Inline `import requests` in `agent_identity.py`
Lines in `_sync_to_api()` and `lookup_from_api()` do `import requests` inside the function body. The `requests` library is already imported at module level in `api.py`, so this works, but it's inconsistent. Suggest moving to the top of the file or using `self.client.api._session_request()` which already wraps requests (and `_sync_to_api` already does this for the POST).

### 4. `loans.repay_loan()` struct index assumption
```python
full_amount = int(loan_details[7])  # assumes index 7 = fullAmount
```
This relies on the exact tuple ordering of `FullLoanDetails`. If the struct ever changes order, this silently breaks. Consider adding a comment with the full struct layout or using named fields if web3.py supports it for this ABI.

### 5. Generous USDB approval in `staking.repay()` and `loans.extend_loan()`
Both approve the **entire USDB balance** rather than just the amount needed:
```python
balance = usdb_contract.functions.balanceOf(self.client.account.address).call()
if balance > 0:
    self._approve_if_needed(self.client.usdb_address, self.staking_address, balance)
```
This works but is more permissive than necessary. For a production SDK, consider reading the actual owed amount first. Not a security issue (the contracts only take what's owed), but some security-conscious users may flag it.

### 6. No return type annotations on most methods
Methods return `dict` but aren't annotated. Adding `-> Dict[str, Any]` to write methods and specific types to read methods would improve DX and IDE support.

### 7. `get_base_tax_rates()` uses `default_` key
```python
return {
    'stasis': result[0],
    'stable': result[1],
    'default_': result[2],  # trailing underscore to avoid Python keyword
    'prediction': result[3],
}
```
The trailing underscore is a valid workaround for the Python `default` keyword, but the docs say the key should be `"default"`. Consider using `'default'` as the key (it's only a reserved word in some contexts, dict keys are fine).

---

## 🔴 Potential Issues (verify before live deployment)

### 1. Nonce race condition on rapid sequential calls
Each `_build_and_send_tx` calls `get_transaction_count()` fresh. Since `_approve_if_needed` **does** call `wait_for_transaction_receipt`, sequential approve→action flows should be safe. But if an agent makes two independent SDK calls concurrently (e.g., two buys from different threads), they could get the same nonce. This is a known web3.py pattern — not a bug per se, but worth documenting that the SDK is **not thread-safe**.

### 2. Gas estimation
No explicit `gas` or `gasPrice` is set in any `build_transaction` call. Web3.py auto-estimates these, which works on BSC 99% of the time. But complex transactions (batch vesting, multi-order fills) might occasionally underestimate. Consider adding a gas multiplier option (e.g., `gas_multiplier=1.2`) to the client config for safety.

### 3. No timeout on `wait_for_transaction_receipt`
All write methods call `wait_for_transaction_receipt(tx_hash)` with no timeout. If BSC is congested and a tx sits in mempool, this blocks indefinitely. Consider adding a configurable timeout (e.g., `timeout=120` seconds) with a meaningful error message.

---

## 📝 Doc vs Code Mismatches (minor)

| Doc Says | Code Does | Impact |
|---|---|---|
| `get_amounts_out` returns `string` | Returns `int` (raw contract return) | None — int is actually better |
| `get_token_price` returns `string` | Returns `str(price)` — converts to string | Matches docs ✅ |
| Leverage `get_leverage_count` and `get_leverage_position` live on `client.trading` | Correct — reads from MAINTOKEN contract via inline ABI | Matches docs ✅ |
| `resolver.get_vote_count(marketToken, outcomeId)` | Code has `get_vote_count(market_token, round, outcome_id)` — extra `round` param | Code is more correct (needs round) |
| `resolver.has_voted(marketToken, user)` | Code has `has_voted(market_token, round, voter)` — extra `round` param | Code is more correct |
| `resolver.get_voter_choice(marketToken, user)` | Code has `get_voter_choice(market_token, round, voter)` — extra `round` param | Code is more correct |

The resolver methods having an extra `round` parameter vs the docs is actually **correct behavior** — the docs should be updated to match the code, not the other way around. Dispute rounds are per-round, so you need to specify which round.

---

## 🧪 Testing Plan

### Read-only tests (no private key needed)
These I can run immediately:
1. `BasisClient()` — stateless init, connect to BSC
2. `client.trading.get_usd_price(MAINTOKEN)` — read MAINTOKEN price
3. `client.trading.get_amounts_out(5 * 10**18, [USDB, MAINTOKEN])` — preview swap
4. `client.factory.get_token_state("0x09A3b840ac0d151F2dfB427a7E006FE44970EDB9")` — read Alex's MAX token
5. `client.factory.is_ecosystem_token(...)` — verify token registry
6. `client.taxes.get_base_tax_rates()` — read tax config
7. `client.agent.is_registered("0x...")` — check agent registration

### Write tests (need testnet private key + USDB faucet)
Need: BSC private key with BNB for gas + USDB from faucet at launchonbasis.com/profile

8. `BasisClient.create(private_key=...)` — SIWE auth + API key
9. `client.trading.buy(token, 5 * 10**18)` — buy with 5 USDB
10. `client.trading.sell(token, amount, to_usdb=True)` — sell back
11. `client.factory.create_token_with_metadata(...)` — full token creation flow
12. `client.prediction_markets.create_market_with_metadata(...)` — full market creation
13. `client.loans.take_loan(...)` → `client.loans.repay_loan(...)` — loan cycle
14. `client.staking.buy(...)` → `client.staking.lock(...)` → `client.staking.borrow(...)` — staking cycle
15. `client.vesting.create_gradual_vesting(...)` — vesting creation
16. `client.order_book.list_order(...)` — order + sync
17. `client.agent.register(...)` — ERC-8004 registration

### API tests (need API key)
18. `client.api.get_tokens(limit=5)` — token list
19. `client.api.get_candles("0x...", interval="1h")` — candle data
20. `client.api.get_token_trades("0x...")` — trade history

---

## Summary

| Category | Count |
|---|---|
| Modules implemented | 13/13 ✅ |
| Feature parity with docs | ~98% ✅ |
| Blocking issues | 0 |
| Pre-publish fixes needed | 2 (pyproject.toml, __pycache__) |
| Nice-to-haves | 5 |
| Doc corrections needed | 3 (resolver round params) |

**Bottom line:** Ready for internal testing. I need a pyproject.toml (or I'll just add the path to sys.path) and a funded wallet to start running the write tests. Ship the pyproject.toml when convenient, no rush — I can work around it.

Alex, great work. This is clean, well-organized code. 🦞
