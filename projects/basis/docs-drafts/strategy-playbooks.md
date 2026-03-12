# Strategy Playbooks — Pre-Built Agent Strategies

_Multi-step automated playbooks for maximizing earnings on Basis. Each strategy can be run as a set-and-forget script or executed step by step._

---

## Strategy A: Predict Leverage Play

**Goal:** Maximum price exposure on a prediction market you create.

**Best for:** High conviction on market volume, not specific outcome.

```
Step 1: Create prediction market on trending topic
        → Earn 20% creator fees on all trading volume

Step 2: Buy Predict+ tokens with 36x leverage
        → Tokens held in leverage contract
        → Floor = spot for Stable+/Predict+ → max leverage always available
        → No price liquidation

Step 3: Hold during market activity
        → Token price rises with each trade (Stable+ mechanics)
        → Creator fees accumulate

Step 4: (Optional) Bet on outcome with SEPARATE USDC
        → Leverage and loans are separate paths
        → Can still bet using non-leveraged USDC

Step 5: After resolution — wait through sell wave
        → Selling burns tokens → fees inject → price goes UP
        → Exit LAST for highest price
```

**Income streams:** Creator fees + token price appreciation + optional bet winnings
**Risk:** Token fees only (no liquidation). Bet loss if outcome is wrong.

---

## Strategy B: Predict Loan-Bet Play

**Goal:** Multiple income streams from a single prediction market.

**Best for:** Strong conviction on a specific outcome.

```
Step 1: Create prediction market
        → Earn 20% creator fees

Step 2: Buy Predict+ tokens outright (NO leverage)
        → Tokens free to use as collateral

Step 3: Take a 100% LTV loan against Predict+ tokens
        → Receive USDC equal to token floor value
        → Tokens locked in loan contract
        → No price liquidation, time-only risk

Step 4: Bet on your conviction outcome using borrowed USDC
        → If correct: share of ENTIRE losing pool

Step 5: After resolution:
        → Collect bet winnings (if correct)
        → Repay loan with winnings
        → Unlock tokens
        → Wait through sell wave → exit tokens at peak

Step 6: Compound — reinvest winnings into next market
```

**Income streams:** Creator fees + token appreciation + bet winnings + capital recycling
**Risk:** Bet loss (borrowed USDC) + loan interest + time management on loan expiry

---

## Strategy C: Exit Timing (Post-Resolution)

**Goal:** Maximize exit price after a prediction market resolves.

**The counterintuitive mechanic:** On Basis, mass selling after resolution pushes the price UP (selling burns tokens → fees inject into liquidity). Last sellers get the best price.

```
Step 1: Monitor resolution event via WebSocket
        → WS /api/v1/stream/events → filter for resolution

Step 2: Track sell volume surge
        → Many holders rush to sell immediately
        → Each sell: tokens burned, fees injected, price rises

Step 3: Detect peak (sell wave subsiding)
        → Volume drops, price stabilization
        → This is the maximum price point

Step 4: Sell tokens AFTER the wave
        → Exit at highest price, not lowest
        → Opposite of every other platform
```

**Use with:** Strategy A or B — this is the exit phase for both.
**Script:** `scripts/monitors/sell-wave-detector.py`

---

## Strategy D: Vault Compound

**Goal:** Set-and-forget treasury that auto-compounds.

```
Step 1: Acquire STASIS tokens (buy on DEX or earn from activity)

Step 2: Stake STASIS → receive wSTASIS
        → Platform fees injected into vault
        → STASIS:wSTASIS ratio increases over time
        → Earning 2 pts/$1/day for airdrop

Step 3: Take a loan against wSTASIS (stays in vault)
        → Borrow USDC at 100% LTV of floor value
        → wSTASIS keeps earning yield while collateralized

Step 4: Deploy borrowed USDC into active strategies
        → Create prediction markets
        → Trade on DEX
        → Bet on outcomes

Step 5: Monitor wSTASIS appreciation
        → When ratio increases past threshold (e.g., 5%)
        → Refinance loan → pull additional USDC
        → Redeploy into more strategies

Step 6: Manage loan expiry
        → Extend before maturity (100 pts per extension)
        → Or repay and re-enter at new ratio
```

**Income streams:** Vault yield + USDC from refinancing + returns from deployed capital
**Agent manages:** Two variables only — refinance threshold and loan timer.
**Script:** `scripts/strategies/vault-compound.py`

---

## Strategy E: Polymarket Mirror

**Goal:** Arbitrage the prediction market structure — same events, better economics.

```
Step 1: Monitor Polymarket for popular multi-outcome markets
        → Use Polymarket API or scrape trending markets

Step 2: Create the SAME market on Basis (permissionless)
        → Same question, same outcomes
        → You're the creator → earn 20% of all trading fees

Step 3: Promote the market on X/social
        → "Same predictions, bigger payouts, and I earn creator fees"
        → Social engagement points + referral links

Step 4: Trade/bet on the Basis version
        → Predict+ winner-takes-all pool = higher payouts
        → Multi-outcome markets dramatically outperform Polymarket
        → You earn from both sides: creator fees + personal position

Step 5: Repeat with trending topics
        → Breaking news → instant market creation
        → Agents can beat humans to market by minutes
```

**Agent alpha:** Arbitraging the prediction market STRUCTURE itself — same events, better payout mechanics, plus creator fees on top.

---

## Strategy F: Capital Recycler

**Goal:** Never let capital sit idle. Continuous earn → lend → deploy → earn loop.

```
Step 1: Agent earns tokens from any activity
        → Prediction fees, trading profits, token launch fees

Step 2: Lock tokens as collateral → borrow USDC at 100% LTV
        → Capital recycled without selling position

Step 3: Deploy USDC into next opportunity
        → New prediction market, another token, vault deposit

Step 4: When collateral appreciates → cash-out refinance
        → Pull additional USDC from same position

Step 5: Repeat — compound indefinitely
        → Successful agents compound without ever selling
```

**The loop:** Earn → Lock → Borrow → Deploy → Earn → Refinance → Deploy → ...

---

## Risk Parameters (configurable per strategy)

Set these in your `.env` or `risk_config.py`:

```
max_leverage: 1-36 (effective via position splitting)
max_bet_per_market: USDC cap per prediction
max_trade_size: USDC cap per DEX trade
max_concurrent_positions: total open positions
auto_extend_loans: true/false
exit_timing: immediate | wait_for_wave | manual
vault_refinance_threshold: % appreciation before refinancing
min_market_participants: skip low-activity markets
```

All strategies support `--dry-run` mode — simulate everything without executing.
