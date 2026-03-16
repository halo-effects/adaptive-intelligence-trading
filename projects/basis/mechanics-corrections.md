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

### Trading Fees (by token type — platform-set, NOT creator-configurable)

| Token Type | Trading Fee | Creator Gets (20% of fee) |
|---|---|---|
| Stable+ | 0.5% | 0.1% per trade |
| Floor+ | 1.5% | 0.3% per trade |
| Predict+ | 1.5% | 0.3% per trade |

- Applied on both buy and sell
- Fees set by platform for transparency — creator cannot change the rate
- Creator controls the SPLIT of their 20% share (Dev Tax Sharing, up to 10 wallets)
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

## Leverage — Corrected Mechanics

**NOT a fixed 36x toggle.** Leverage is dynamic — depends on current liquidity and buy amount.

### How It Works
- Leverage calculated against floor price relative to pool state
- Larger buys = lower leverage (price impact moves spot away from floor)
- "Up to 36x" is theoretical max on perfectly liquid pools, not guaranteed
- **Leverage fee is substantial** — separate from trading fee

### Real Data (GeeGee token, $1,000 starting liquidity, Stable+)

| Buy Amount | Leverage | Leverage Fee | Price Impact | Position Size |
|---|---|---|---|---|
| $5 | 27.84x | $3.53 (70.6%) | 0.60% | ~$139 |
| $20 | 26.79x | $13.66 (68.3%) | 2.38% | ~$536 |
| $100 | 16.66x | $43.79 (43.8%) | 11.90% | ~$1,666 |

### Key Insights for Agents
- Small buys = high leverage but small position size
- Large buys = rapidly declining leverage + heavy price impact
- Leverage fee % decreases with size but absolute cost increases
- On low-liquidity pools, even moderate buys are "whale" trades
- **Strategy: split large leveraged positions into smaller buys, or wait for liquidity to build**
- Leveraged trades show "Open Position" button (not "Buy") — tracked as positions in leverage contract
- Leveraged tokens cannot be used as loan collateral

---

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

## Prediction Market Creation — From Live UI

### Step 1: Event Basics
- Event Name (required) — the prediction question
- Event Symbol (required) — ticker for the Predict+ token
- Icon (required — PNG, JPG, SVG, max 2MB)
- Description (required)
- End Date (optional — can leave empty for open-ended predictions)
- Answers: minimum 2, can add more with "Add+" button, delete with trash icon
- Social Media (optional): Telegram, X/Twitter, Website
- **Answers must be mutually exclusive** — only one can win

### Step 2: Tokenomics & Resolution
- **Bonding Phase USDC:** $0–$150,000 slider (can be $0 — predictions can skip bonding phase entirely)
- **Freeze Token:** toggle (same as tokens)
- **Resolve Style:**
  - **Basis Managed** — community votes via Basis Voting Army, disputes allowed
  - **Creator Managed** — creator resolves (or up to 10 whitelisted voter wallets, majority vote). No disputes — resolution is final.
- **Event Type** (Creator Managed only):
  - **Public** — anyone can participate
  - **Private** — only whitelisted wallets can purchase/participate
- **Starting Liquidity:** Currently fixed at $1,000 for all predictions (no slider yet). Planned: 4 tiers (low/medium/high/extreme volume) — lower liquidity = more price movement but limits single-outcome buying before reaching 90%+ odds. Buying spread across outcomes = no issue. Buying from sellers (not pool) bypasses this limit.

### Resolution/Access Matrix

| Resolve Style | Event Type | Who Participates | Who Resolves | Disputes? |
|---|---|---|---|---|
| Basis Managed | Public (only) | Everyone | Basis Voting Army | Yes |
| Creator Managed | Public | Everyone | Creator or voter panel (up to 10) | No |
| Creator Managed | Private | Betting: whitelisted only. Token buying: anyone (adds to pot) | Creator or voter panel (up to 10) | No |

### ONE Token Per Market (Critical)
- Each prediction has 1 Predict+ token (Stable+ type)
- Token represents the MARKET, not individual outcomes
- Buying the token = trading on price (separate from betting)
- Betting = separate action using Predict+ tokens OR USDC/B directly
- Separate betting pool in USDC/B for winner-takes-all payouts

---

## Prediction Event Page — Betting Interface (From Live UI)

### Layout
- **Header:** Public Event | Open badges, event name, description
- **Total Pot:** cumulative USDC from all bets
- **Total Bounty:** trader-to-bettor pot (% of Predict+ trading fees)
- **"Visit Trading Page"** link (separate from betting)

### Two Tabs
1. **Market Chart** — Implied Probability History (colored lines per outcome, 0-100%)
2. **Resolution Status** — Three-phase progress: Trading (T) → Resolution (🔨) → Resolved (R)

### Betting Panel (right side)
- **Select Outcome** dropdown — shows outcome name + current share price
- **Amount to spend (USDC)** — input field
- Quick buttons: 25%, 50%, 75%, 100%
- **"Buy [Outcome] Shares"** button

### Implied Probabilities
- Each outcome has a price and probability
- 3 outcomes start at 33.3% / $0.33 each (equal split, sums to ~$1.00)
- 2 outcomes would start at 50% / $0.50 each
- As shares are bought, probability shifts and price changes

### How Betting Works (NOW UNDERSTOOD)
1. Each outcome has a share price (starting at equal split: 2 outcomes = $0.50, 3 = $0.33, etc.)
2. Betting = buying shares in an outcome at current price using USDC
3. As shares are bought in one outcome, its price/probability rises, others fall
4. When resolved: winning outcome shareholders split the total pot proportionally
5. Total Bounty (from Predict+ trading fees) adds to the winning pot
6. This is COMPLETELY SEPARATE from buying/selling the Predict+ token on the Trading Page
7. **First bet on a market = $0 profit** (no losing pools to draw from). Profit comes from OTHER bettors on wrong outcomes.
8. **Second bettor on opposite side** gets best odds — nearly 2x if pools are equal

### Selling Shares (Order Book)
- **Market (Best):** Lists at current market price. NOT instant — fills when next buyer purchases that amount or more. Queued sell order.
- **Limit (Custom):** Set custom price per share ($0.001–$0.999). Fills when price reached. If set BELOW market, fills before other market orders (standard order book priority).
- Share price range: $0.001 to $0.999 (can never reach $1.00 — certainty has no risk premium)
- This is a REAL order book — buyers match with sellers, not just pool-based
- **Order matching is "underwater"** — buyer sees simple "Buy" UI, system routes to best source (sell orders first if cheaper, then pool). Buyer doesn't know if shares came from pool or sellers.
- No visible order book in current UI (simplicity). Future consideration: API/advanced mode to browse open sell orders.
- Agents can exit positions before resolution by selling shares at profit when probability shifts

### Agent Strategies (Predictions)
- **Market making:** Buy shares cheap, list limit sells higher
- **Early exit:** Sell when probability shifts favorably (don't wait for resolution)
- **Arbitrage:** Snipe mispriced limit orders vs implied probability
- **Contrarian:** Bet on unpopular outcomes early = highest payoff if correct
- **Pool analysis:** Monitor pool sizes per outcome to calculate expected value before betting

### Prediction Dev Panel (Basis Managed)
- Simple — just fees collected, whitelists (2 default: creator + betting contract), trading status, token info
- No surge tax, no dev tax sharing, no resolution controls
- Resolution handled by Basis Voting Army
- **Creator Managed dev panel** adds: "Manage Voter Whitelist" — 1/10 wallets, creator auto-included. Add up to 9 more for majority-vote resolution. Also has "Edit Info" button.
- **Edit Info** (post-launch): Can change Website, Telegram, Twitter/X, Description. CANNOT change: name, symbol, icon, answers, end date, resolve style.
- **Resolution controls** live on the Event Page (prediction market page), NOT the dev panel. Creator goes there to submit winning answer after end date.
- Basis Managed dev panel has no voter whitelist (resolution handled by Voting Army)

### Post-Creation Confirmation (Predictions)
- Three CTAs (vs two for tokens): **Trading Page**, **Event Page**, **Dev Panel**
- Event Page = betting interface (unique to predictions)

### Event Page Tabs (all prediction types)
1. **Market Chart** — implied probability history (colored lines per outcome)
2. **Resolution Status** — phase tracker + voting controls (Creator Managed) or status (Basis Managed)
3. **Discussion** — wallet-signed comments (added live by Alex 2026-03-12)

### Discussion Tab
- Wallet-signed comments — cryptographically tied to wallet address
- **Requires at least 1 trade ≥ $5** on that market to comment (anti-spam gate)
- **"CREATOR" badge** shown on creator's comments
- Creator can delete comments (trash icon)
- Posting as truncated wallet address (e.g. `0x25Af...7613`)
- Timestamped

### Creator Managed Resolution — How It Works
- **Voting available IMMEDIATELY** — runs simultaneously with trading (not sequential like Basis Managed)
- Market stays open for betting until resolution vote is submitted
- **"Cast Your Vote" button** on Resolution Status tab (only visible to whitelisted voters)
- **Vote options:** Each outcome + "Invalid / Ambiguous"
- **Invalid / Ambiguous** = all bettors refunded (⚠️ Diamond flagged there's an additional detail about this — TBD)
- Solo creator → resolves immediately on their vote
- Multi-wallet panel → majority needed from up to 10 voters
- **Bug noted:** Status shows "Voting Active" immediately, should show "Trading Live" until first vote cast

---

## Completed Walkthrough Items ✅
- ✅ Token creation flow (3-step wizard)
- ✅ Token dev panel (surge tax, whitelist, dev tax sharing, unfreeze)
- ✅ Token trading page (buy/sell, leverage toggle, trade history)
- ✅ Buy flow (approve + buy, two contract calls)
- ✅ Leverage mechanics (dynamic, real data at 3 price points)
- ✅ Whitelist management
- ✅ Prediction creation flow (3-step wizard)
- ✅ Prediction event page (betting interface, implied probabilities)
- ✅ Prediction dev panel (Basis Managed)
- ✅ Resolution types (Basis Managed vs Creator Managed, Public vs Private)
- ✅ Trading fees by token type

## Vesting System — Full Mechanics (from Diamond, 2026-03-13)

### Auto Vesting (set at token creation, Step 2: Tokenomics)
- Toggle ON/OFF during token creation
- When ON, all bonding phase buyers' tokens go to vesting contract automatically
- Vesting Type: **Cliff** (all at once after period) or **Gradual** (linear release over period)
- Vesting Period: configurable in days (default 30)
- Creator can **extend the vesting period** before cliff hits (trust signal to community)

### Normal Vesting (post-launch, via Dev Panel)
- Same structure: Cliff or Gradual, configurable period
- Creator sets up for specific wallets/allocations
- Period can also be extended

### Loans on Vested Tokens
- **Stable+ tokens**: 100% LTV loans (but no vesting needed since no dump risk)
- **Floor+ tokens**: 100% LTFP (Loan to Floor Price) — loans against guaranteed floor price
- LTFP is effectively close to full value at launch since spot starts near floor
- Creators access liquidity immediately without waiting for vest to expire

### Loan + Vesting Interaction
- **Active loan = tokens held** regardless of vesting schedule
- Even gradual-release tokens stay locked while a loan is active
- **To claim tokens: loan must be repaid first**
- **Partial sell option**: can sell a portion of vested tokens to cover loan repayment (no external USDC needed)
- Clean exit: partial sell to cover loan → remaining tokens released

### The Full Loop (why creators never need to dump)
1. Vest tokens → borrow against floor price for immediate liquidity
2. Extend vesting period to build community trust
3. Token appreciates → refinance for more USDC if needed
4. When ready to exit: partial sell covers loan, remaining tokens released
5. No scenario forces a creator to dump on their community

---

## Still Pending
- **⚠️ UNRESOLVED: Invalid/Ambiguous resolution** — everyone gets refunded, but Diamond flagged there's an additional detail about this he can't recall. ASK DIAMOND LATER.
## Loans — From Live UI

### Creating a Loan
- Select collateral token (pre-populated if navigating from token trading page)
- Set collateral amount (max = full balance)
- Choose loan term: **10 days minimum, 1,000 days maximum**
- **100% LTV** — loan amount = full collateral value (no over-collateralization)
- **Fee structure** (confirmed 2026-03-16 by Alex + Diamond):
  - **Origination fee: 2.0% flat** (`staticFeePercentage = 200` on MAIN_TOKEN)
  - **Interest: 0.005% per day** (`dynamicFeePercentage = 5` on MAIN_TOKEN)
  - **Minimum loan duration: 10 days**
  - Examples: 10-day = ~2.05%, 30-day = ~2.15%, 365-day = ~3.83%, 1,000-day = ~7.0%
  - Very cheap vs DeFi lending rates (5-15%/year). Total fee, not annualized.
  - ⚠️ UI previously showed blended "2.5%" — should be updated to show origination + interest separately.
- Loans pay out in **USDC**
- Same approve → create pattern (two contract calls)
- Collateral valued at **floor price** (conservative — protects lender)
- **All interest prepaid upfront** — fee deducted from loan proceeds. Zero payments during loan period.
- **Repayment = exact loan amount** (collateral value). No added interest, no installments, no margin calls.
- Flow: Lock tokens → receive USDC (minus fee) → repay exact loan amount to reclaim tokens
- **Leveraged tokens CANNOT be used as loan collateral** (captured earlier)

### Loan Expiry (not repaid)
- Collateral is **BURNED** (not liquidated/sold on market)
- If collateral value increased above loan amount, the **balance (excess) can be claimed** by borrower
- No liquidation cascades — clean design

### Extend / Refinance
- **Collateral increased in value:** Can extend term AND refinance (borrow more against new higher value)
- **Collateral decreased or flat:** Can still extend by paying additional USDC
- Both extension and refinancing available before loan expiry

### Loan Management (3 actions)
- **Repay:** Pay exact loan amount (collateral value) in USDC → get tokens back
- **Extend:** Two modes:
  - **Pay in USDC (toggle ON):** Pay extension fee externally in USDC. Always available.
  - **Pay from collateral (toggle OFF):** Fee paid from collateral's increased value. Only eligible if token appreciated. Also unlocks **Refinance (Borrow Extra)** toggle — borrow additional USDC against new higher collateral value.
  - Extension fee is duration-based (e.g., 1,000 days = $0.25 on ~$5 loan)
- **Sell (voluntary liquidation):** Burns collateral, you receive any value ABOVE the loan amount in USDC. Partial sell available (10-100% slider). If token hasn't increased, receive = $0. Same process as expiry liquidation, just voluntary.

### Loan Dashboard
- Active / Inactive tabs
- Auto-numbered (Loan 001, 002...)
- Shows: Collateral amount, Current Value (excess above loan), Repay Amount, You Spent, Cashed Out, P&L
- **Current Value** = value of collateral ABOVE loan amount (not tracking what you do with borrowed USDC)
- Time Left with visual progress bar

### Agent Strategies (Loans)
- Short-term loans (10 days): Borrow against tokens → deploy USDC → repay with profits
- Long-term holds (up to 1,000 days): Lock tokens, use USDC for other strategies
- Refinancing: If token moons, refinance to extract more USDC without selling
- Cost: Dynamic fee based on duration — shorter = cheaper. Very competitive vs DeFi lending rates

---

## Stasis Vault — From Live UI

### Overview
- **Wrap STASIS → wSTASIS** for guaranteed value appreciation
- wSTASIS share price ONLY goes up — "guaranteed value appreciation"
- Revenue source: Portion of trading fees previously injected into STASIS liquidity → now feeds vault → raises wSTASIS share price perpetually
- **This is NOT the same as the Basis Vault** (see below)
- Current share price: **1 wSTASIS = 5.8654 STASIS** (significant appreciation already)
- Note: UI shows "Stasis" but currently reads as "Basis" on live platform (rename in progress)

### Vault Mechanics (from Diamond's walkthrough)

**Three wSTASIS states:**
1. **Liquid wSTASIS** — wrapped but free. Can unwrap to STASIS anytime.
2. **Locked wSTASIS** — deposited into collateral pool. Can add more anytime. Can unlock anytime UNLESS loan exists.
3. **Loan-locked wSTASIS** — locked + borrowed against. Can't unlock until loan repaid.

**Process flow:**
1. **Wrap:** Convert STASIS → wSTASIS at current share price (only goes up)
2. **Lock:** Deposit wSTASIS into collateral pool (reversible if no loan)
3. **Borrow:** Draw USDC against locked wSTASIS (100% LTV, no liquidation)
4. **Appreciate:** Ecosystem revenue → vault → wSTASIS share price rises → collateral value increases
5. **Borrow more:** As collateral appreciates, can draw more USDC without depositing more wSTASIS. Or lock more to increase collateral further.

**Why no liquidation risk:** wSTASIS share price ONLY goes up (guaranteed). Collateral value can never drop below loan amount. No margin calls ever.

### Vault Stats
- Share Price, Net Worth, Total Assets, Liquid wSTASIS, Locked wSTASIS

### Two Tabs
- **Wrap & Appreciate:** Wrap STASIS / Unwrap subtabs, Amount input, Stake button
- **Collateral & Loans:** Borrow USDC against wSTASIS. Same loan mechanics as token loans (100% LTV, no liquidation, prepaid interest)

### Agent Strategy (Vault Loop)
1. Buy STASIS from trading
2. Wrap into wSTASIS (guaranteed appreciation)
3. Borrow USDC at 100% LTV against wSTASIS
4. Deploy USDC into tokens/predictions/other strategies
5. wSTASIS appreciates while locked as collateral
6. Repay loan → unwrap → profit from appreciation + deployed USDC returns

## Two Vaults — Critical Distinction

### STASIS Vault (live now)
- Revenue: Trading fee portion (previously injected into STASIS liquidity)
- wSTASIS price **only goes up** (guaranteed)
- **Loans available** (100% LTV, no liquidation)
- Safe, predictable yield

### BASIS Vault (post-TGE)
- Revenue: **90% of platform revenue** (AFTER creator fees, STASIS vault fees, bonding phase fees)
- Earns **USDC yield** (real revenue distribution to stakers)
- BASIS token price **fluctuates** (volatile governance/utility token)
- **No loans** — can't safely lend against volatile collateral at 100% LTV

### Fee Waterfall
Trading Fee → Creator (20%) → Bonding phase buyers → STASIS Vault (portion) → Platform Revenue (remainder) → 90% to BASIS Vault (USDC yield) + 10% platform operations

---

- Sell flow (token selling UI)
- Creator Managed prediction dev panel (resolution tools)
- Lending flow (take loan, extend, repay)
- Vault flow (stake, borrow against, refinance)
- Exact stability dial → price impact numbers for Floor+
- Dispute resolution details (Basis Voting Army)
- Surge tax details (boost amount during quota)
- How Predict+ trading fees flow into the betting bounty pot (exact %)
- Prediction resolution + payout flow
- Floor+ token trading page (differences from Stable+)

---

_Last updated: 2026-03-12 11:58 PDT during Diamond's live walkthrough_
