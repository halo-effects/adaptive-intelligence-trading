# Skill: basis-defi

**Name:** basis-defi  
**Version:** 0.3.0 (scripts wired to SDK API — 2026-03-16)  
**Status:** ✅ All 7 core scripts wired to Basis SDK (`basis-sdk`). SDK docs received 2026-03-16, package not yet on PyPI — scripts will work as-is once `pip install basis-sdk` is available. `points.py` remains a stub (points backend not built).

## Description

Interact with the Basis DeFi platform — create prediction markets, launch tokens, trade on the DEX, lend idle capital, manage vault positions, and earn airdrop points toward the BASIS TGE. Basis is an agent-native DeFi ecosystem on BNB Chain with zero-liquidation lending, dynamic leverage (up to ~28x depending on pool liquidity and position size), and USDC-native earnings.

**Why agents should use this skill:**
- Create prediction markets and earn **20% of all trading fees forever**
- Launch Stable+ or Floor+ tokens for your community — earn 20% of DEX fees
- Borrow USDC at **100% LTV** against token collateral — no price liquidation, time-only risk
- Stake STASIS in the wSTASIS vault — earn yield + refinance loans without leaving the vault
- Earn airdrop points toward BASIS TGE (pre-TGE farming is live)
- All earnings paid in **USDC** — immediately spendable, no sell pressure

---

## Prerequisites

- **Python 3.10+**
- **basis-sdk** package: `pip install basis-sdk` *(not yet on PyPI — awaiting beta publish)*
- **python-dotenv**: `pip install python-dotenv`
- **BNB Chain wallet** with small BNB for gas (~$0.01–0.14 per transaction)
- **USDB** (test stablecoin) from faucet: https://basis.exchange/faucet *(zero financial risk, real airdrop points)*

### Environment Setup

Create a `.env` file in your skill directory:

```env
# Required for write operations (trading, creating, lending)
BASIS_PRIVATE_KEY=0x...         # Agent wallet private key (enables auto SIWE + all writes)

# Optional — read-only access
BASIS_API_KEY=bsk_...           # API key for off-chain data (auto-provisioned in full mode)

# Optional — custom RPC
BASIS_RPC_URL=https://bsc-dataseed.binance.org/  # BNB Chain RPC (default)

# Optional — wallet address for read-only queries (status, portfolio)
BASIS_WALLET_ADDRESS=0x...      # For portfolio.py and points.py

# Optional — operator safety limits
MAX_BET_PER_MARKET=100          # Max USDC per prediction bet
MAX_TRADE_SIZE=500              # Max USDC per DEX trade
AUTO_EXTEND_LOANS=true          # Auto-extend loans before expiry
VAULT_REFINANCE_THRESHOLD=0.05  # Refinance when wSTASIS up 5%
```

---

## Architecture Note

Scripts use the **Basis SDK** (`basis-sdk`) which wraps all 13 smart contracts + off-chain API into a single `BasisClient`. Three init modes:
1. **Read-only** (no credentials): on-chain reads — prices, balances, market data
2. **API key**: adds off-chain data — candles, trade history, tokens, orders
3. **Full mode** (private key): auto SIWE auth + all write operations

All write methods auto-approve token spending. No manual approve steps needed.

See `references/api-reference.md` for the contract function reference, or the full SDK docs at `../../sdk-docs-2026-03-16.md`.

---

## Commands Overview

### Core Operations

| Script | Command | What It Does |
|--------|---------|--------------|
| `create-prediction.py` | Create a prediction market | Deploy a Predict+ market, set outcomes, earn 20% fees |
| `bet.py` | Place a bet on an outcome | Buy shares in a prediction outcome, win from losing pool |
| `create-token.py` | Launch a Stable+ or Floor+ token | Deploy elastic-supply token with bonding curve |
| `trade.py` | Buy/sell tokens on DEX | Swap tokens via Basis internal DEX |
| `lend.py` | Take or manage a loan | Borrow USDC at 100% LTV against token collateral |
| `vault.py` | Manage STASIS vault (wSTASIS) | Stake STASIS, earn yield, refinance loans from vault |
| `portfolio.py` | Check balances, positions, P&L | Full position summary + net P&L |
| `points.py` | Check airdrop points + rank | ACS score, tier, breakdown, leaderboard rank |

### Strategy Scripts (composite operations)

| Script | Path | Strategy |
|--------|------|---------|
| `predict-leverage.py` | `scripts/strategies/` | Path A: Create market → dynamic leverage buy → ride curve |
| `predict-loan-bet.py` | `scripts/strategies/` | Path B: Buy tokens → 100% LTV loan → bet with borrowed USDC |
| `predict-exit-timing.py` | `scripts/strategies/` | Wait for post-resolution sell wave → exit last |
| `vault-compound.py` | `scripts/strategies/` | Auto-refinance wSTASIS vault → redeploy USDC |
| `polymarket-mirror.py` | `scripts/strategies/` | Mirror Polymarket events on Basis → earn creator fees |
| `capital-recycler.py` | `scripts/strategies/` | Route earnings through loan → redeploy → compound |

### Monitor Scripts

| Script | Path | Watches For |
|--------|------|-------------|
| `new-markets.py` | `scripts/monitors/` | New prediction markets → trigger strategies |
| `sell-wave-detector.py` | `scripts/monitors/` | Post-resolution sell peak → trigger exit |
| `loan-expiry-tracker.py` | `scripts/monitors/` | Loan near expiry → trigger auto-extend |
| `refinance-checker.py` | `scripts/monitors/` | wSTASIS appreciation → trigger vault refinance |

---

## Configuration Reference

### Risk Parameters (configurable per operator)

```python
# risk_config.py — loaded by all scripts
RISK_CONFIG = {
    # Leverage is DYNAMIC — depends on pool liquidity and position size
    # Smaller buys = higher leverage (up to ~28x on fresh pools)
    # Larger buys = lower leverage due to price impact
    # Use ASwap.mixedBuy() to split spot/leverage in one call (SDK only, not on frontend)
    # Use ALEVERAGE.simulateLeverage() to preview before executing
    "max_leverage_pct": 50,         # max % of position to leverage via mixedBuy
    
    # Prediction markets
    "max_bet_per_market": 100,      # USDC — cap per prediction bet
    "min_market_participants": 5,   # skip low-activity markets
    
    # Trading
    "max_trade_size": 500,          # USDC per DEX swap
    "max_concurrent_positions": 10, # total open positions
    
    # Loans
    "auto_extend_loans": True,      # extend before expiry
    "max_loan_duration_days": 30,   # loan term
    
    # Vault
    "vault_refinance_threshold": 0.05,  # refinance when wSTASIS up 5%
    "vault_min_position": 100,          # USDC min for vault deposit
    
    # Exit
    "exit_timing": "wait_for_wave",     # post-resolution sell timing
    
    # Safety
    "dry_run": False,               # simulate all actions if True
    "verbose": True,                # print detailed action logs
}
```

### Token Type Reference

See `references/token-frameworks.md` for full details.

| Type | Use Case | Leverage | Loans |
|------|---------|---------|-------|
| Stable+ | Base pairs, prediction tokens | Dynamic (up to ~36x, depends on pool depth + position size) | 100% LTV |
| Floor+ | Community tokens, agent identities | Dynamic (higher at launch, decreases as pool grows) | 100% LTV |
| Predict+ | Prediction market tokens (Stable+) | Dynamic (same as Stable+) | 100% LTV |
| STASIS | System base token (Stable+) | Dynamic (same as Stable+) | 100% LTV via wSTASIS |

---

## Dry-Run Mode

All scripts support `--dry-run`. In dry-run mode:
- All transaction params are computed and logged
- No transactions are submitted
- Gas estimates are printed
- Expected outcomes are simulated

```bash
python create-prediction.py \
  --title "Will ETH close above $4000 on March 20?" \
  --outcomes "Yes,No" \
  --duration-days 7 \
  --dry-run
```

---

## Quick Start (USDB Testing Phase)

```bash
# 1. Install dependencies
pip install basis-sdk python-dotenv  # basis-sdk not yet on PyPI — coming soon

# 2. Set up .env with your wallet
echo "BASIS_PRIVATE_KEY=0xYourPrivateKey" > .env

# 3. Get USDB from faucet (zero financial risk, real airdrop points)
# Visit: https://basis.exchange/faucet

# 4. Check your portfolio
python portfolio.py --wallet 0xYourWallet

# 5. Create your first prediction market (earn 300 airdrop points)
python create-prediction.py \
  --title "Will BTC hit ATH this week?" \
  --outcomes "Yes,No" \
  --duration-days 7

# 6. Buy tokens on the DEX
python trade.py --token 0xTokenAddress --direction buy --amount 50

# 7. Borrow USDC against your tokens (100% LTV)
python lend.py --action borrow --token 0xTokenAddress --token-amount 100 --duration-days 30

# 8. Check your airdrop points
python points.py --wallet 0xYourWallet
```

---

## Earning Paths Summary

| Path | Action | Earnings | Airdrop Points |
|------|--------|---------|----------------|
| 🎯 Predict Create | Deploy prediction market | 20% of trading fees | 300 pts/market |
| 💰 Predict Bet | Bet on outcome correctly | Share of entire losing pool | 1 pt/$1 net profit |
| 🪙 Token Launch | Deploy Stable+/Floor+ token | 20% of DEX trading fees | 500 pts/token |
| 📈 DEX Trading | Buy/sell tokens | Price alpha | 1 pt/$1 volume |
| 🏦 Lending | Lock tokens, borrow USDC | Redeploy capital | 200 base + 1/day |
| 🏛️ Vault | Stake STASIS → wSTASIS | Yield + refinance USDC | 2 pts/$1/day |
| 🐦 Social | Post about Basis on X | Community reputation | 50–150 pts/post |
| 📨 Referrals | Refer agents/users | 10% of referee's lifetime points | Ongoing |

---

## Shared Helpers

All scripts use `client_helper.py` for:
- `get_client(require_write, register_agent)` — BasisClient initialization from env vars
- `usdc_to_raw()` / `raw_to_usdc()` — USDC decimal conversion (6 decimals)
- `token_to_raw()` / `raw_to_token()` — Token decimal conversion (18 decimals)
- `output_result()` — JSON output formatting
- Contract address constants: `MAINTOKEN`, `USDC`, `MARKET_TRADING`

## References

- `references/api-reference.md` — Contract function reference (all 13 contracts)
- `references/token-frameworks.md` — Stable+, Floor+, Predict+ token mechanics
- `references/earning-guide.md` — All earning paths, point values, multipliers
- `../../sdk-docs-2026-03-16.md` — Full SDK documentation (13 modules, Python + TypeScript)

## Links

- SDK docs (full): `../../sdk-docs-2026-03-16.md`
- SDK package: `pip install basis-sdk` *(not yet on PyPI)*
- Contract Reference: `references/api-reference.md`
- Basis platform: https://basis.exchange
- BNB Chain faucet (for gas): https://www.bnbchain.org/en/testnet-faucet
