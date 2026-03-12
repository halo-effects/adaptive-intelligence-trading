# Mechanics Corrections — From Diamond's Live Walkthrough (2026-03-12)

_Source of truth: live platform at launchonbasis.com, walked through by Diamond with screenshots._

---

## Token Creation — Corrected Understanding

### Step 1: Metadata
- Token Name (required)
- Token Symbol (required)
- Description (required)
- Icon image (required — PNG, JPG, SVG, max 2MB, drag-and-drop supported)
- Social Media (optional): Telegram, X/Twitter, Website
- Next button only active when all required fields are filled

### Step 2: Tokenomics
- **All tokens start at $1.00** — no custom initial price
- **Starting Liquidity:** $100–$10,000 slider. Sets virtual liquidity depth (price impact baseline). NOT a bonding curve like pump.fun.
- **Bonding Phase USDC:** $100–$150,000. Volume target — bonding phase ends when this is hit.
- **Freeze Token:** Toggle. When ON, creator can whitelist specific wallets with max buy limits before public trading.
- **Token Type:** Stable+ or Floor+
  - If Floor+: Stability slider appears (0%–100%, default 0% = most volatile)
  - If Stable+: Stability slider disappears entirely
- **Auto-Vesting:** Toggle. When ON, bonding phase buyers' tokens go to vesting contract.
  - Vesting Type: Cliff or Gradual
  - Vesting Period (Days): numeric input (default 30)

### Step 3: Review & Launch
- Summary page showing all parameters
- "Create Token" button → single contract call → ~$0.14 BNB gas cost (real-world measured)

### Post-Creation
- Confirmation page with contract address + links to Token Page and Dev Panel
- Token starts with 1,000 supply at $1.00 when starting liquidity = $1,000
- Starting liquidity = initial virtual supply × price

### Dev Panel (Creator Controls)
- **Unfreeze** button — opens public trading
- **Surge Tax:** "Activate Surge" button with 7-day total quota (not unlimited — creator picks moments strategically)
- **Dev Tax Sharing:** Add wallets to share creator's 20% fee (1%–100% per wallet, max 10 wallets, total ≤100%). Done POST-launch, not at creation. Displayed in basis points (100% = 10,000 bps).
- **Whitelist Management:** Add wallet addresses with max buy limits during freeze phase
- **Token Info:** Name, symbol, type, supply, price, market cap, created date, holders, frozen status

---

## Stable+ Token — Corrected Mechanics

**NOT a moonshot token.** It's a branded stablecoin with slow appreciation.

- Price appreciation is from **price impact (slippage retention)**, NOT fee injection
- When someone buys or sells, the "lost value" from slippage stays in the liquidity pool
- This increases the liquidity-to-supply ratio → price ticks up slightly
- Effect is **strongest at low supply**, diminishes as supply grows
- Needs constant buying AND selling (circulation) — not just buying pressure
- Price will flatten without active use cycles (buy → use → sell → buy)

**Use case:** Utility tokens, branded stablecoins, access passes, services — anything with recurring circulation.

**Fees do NOT inject back into Stable+ liquidity.** Fees are distributed to:
- Creator (20% of trading fee)
- Bonding phase buyers (their share)
- Platform revenue
- wSTASIS vault

**STASIS** itself is a Stable+ token — the base pair for all tokens on the platform. Appreciates slowly from the circulation volume of the entire ecosystem.

---

## Floor+ Token — Corrected Mechanics

- Price **goes up on buys, goes DOWN on sells** (unlike Stable+ which is up-only)
- Has rising floor for downside protection
- Stability dial: 0% (most volatile) to 100% (most stable)
- The more volatile (lower stability), the more price moves per trade
- Speculative/community token — this is where the trading action lives

**Price impact per $100 buy (approximate, pending exact numbers from Diamond):**
- 0% stability (most volatile): ~$1 price increase per $100 buy on $100 starting liquidity
- 90% stability: ~$0.09 per $100 buy (much slower appreciation)
- Exact numbers TBC

---

## Prediction Markets — Corrected Mechanics

### Critical Correction: ONE token per market, NOT one per outcome

- Each prediction market has **1 Predict+ token** (Stable+ type)
- The token represents the MARKET, not individual outcomes
- Buying the Predict+ token = trading on price (like any other token)
- Betting on outcomes = SEPARATE action

### How Betting Works
- **Betting is separate from buying the token**
- Players can bet using either:
  - The Predict+ token itself, OR
  - USDC/USDB directly
- **Separate betting pool in USDC/B** — this is where winner-takes-all payouts come from
- Distinct from the token's trading activity

### Fee Distribution on Predict+
- A % of the trading fee from buying the Predict+ token goes into a **separate pot**
- This pot is paid out to winners proportionally to their share of the winning pool
- This is the "trader-to-bettor pot" — feeds from trading into betting rewards

### Resolution
- Could be single resolver, multi-sig, or community vote (multiple options)
- There is a dispute resolution process (details TBD)
- Tokens exist until all holders sell (burned) — persist after resolution

---

## Trading Pairs — Corrected

- **All tokens pair against STASIS** (not USDC/USDB)
- STASIS itself pairs with USDC/USDB
- Pairing happens automatically at token creation
- **Buy panel dropdown:** USDC or STASIS (currently shows "BASIS" on dev — will be renamed STASIS on public)
- Agents can buy with either: USDC (auto-routes through STASIS) or STASIS directly
- **Leverage toggle** right on the buy panel (on/off, not slider)
- **Quick allocation buttons:** 25%, 50%, 75%, Max (of wallet balance)
- **Trade History + Open Positions** tracked per token per wallet

### Unfreeze is one-way
- Once unfrozen, cannot be re-frozen
- Unfreeze button disappears after use
- Token goes from "Trading: Paused" → "Trading: Live"

---

## Platform UI Structure

### Standard Mode (Pro toggle OFF)
- Home (portfolio overview)
- Tokens (browse/trade)
- Predictions (browse/bet)
- Loans
- Vault
- Activity

### Pro Mode (Pro toggle ON)
- All standard sections PLUS:
- **Devpanel:**
  - New Token (create Stable+/Floor+)
  - New Prediction (create prediction markets)
  - Vesting (manage vesting schedules)

### Portfolio Page
- Portfolio value in USDC
- Holdings with quick-action buttons: **Buy**, **Sell**, **Loan** per token
- My Projects section (tokens/predictions created)
- LIVE indicator (mainnet)

---

## Trading Mechanics — From Live UI

### Buy Flow (two contract calls)
1. **Approve** — ERC-20 approve for spend amount (one contract call)
   - Can approve a higher amount than immediate buy (e.g., approve $1,000, buy $10)
   - Subsequent buys up to approved amount don't need re-approval
   - SDK optimization: bulk approve upfront, save gas on repeated trades
2. **Buy** — execute the trade (second contract call)

### Trading Fee
- **0.5%** of trade amount (confirmed from live UI)
- Applied on both buy and sell
- Distributed to: Creator (20% of fee), bonding phase buyers, platform revenue, wSTASIS vault

### Price Impact
- Visible before execution in the UI
- $10 buy against $1,000 starting liquidity = 1.1% price impact
- This is the slippage retained in liquidity that drives Stable+ appreciation

### Example Trade
- Input: $10 USDC
- Trading fee (0.5%): $0.05
- Price impact: 1.1%
- Tokens received: 9.8824 GG (~$9.882)
- Price per token: $1.00

## Gas Costs (real-world measured)
- Token creation: ~$0.14 BNB
- Prediction creation: TBD
- Trading (buy): TBD (two calls: approve + buy)

---

## Whitelist Management

- Add one wallet at a time (CSV bulk upload planned)
- Fields:
  - Wallet Address (0x... — required)
  - Comment (optional — "Early supporter, VIP member, etc.")
  - Max Buy Amount toggle (OFF = unlimited buys. ON = set max USDC purchase limit per wallet)
- Cancel / Add buttons

---

## Still Pending (awaiting screenshots/confirmation)
- Prediction market creation flow (screenshots coming)
- Whitelist management UI
- Token trading page view
- Buying/selling flow
- Lending flow
- Vault flow
- Exact fee percentages and distribution ratios
- Exact stability dial → price impact numbers
- Dispute resolution details
- Surge tax details (boost amount, quota mechanics)

---

_Last updated: 2026-03-12 10:49 PDT during Diamond's live walkthrough_
