# How Everything Works

**What this covers:** Mechanical deep-dives into how each system actually works — trading paths, loan system, vault layers, leverage loops, prediction market lifecycle, agent identity.
**Related sections:** → See: [06-why.md](06-why.md) for the rationale · → See: [03-atomic-skills.md](03-atomic-skills.md) for method signatures · → See: [09-fees.md](09-fees.md) for fee details · → See: [13-mistakes.md](13-mistakes.md) for common errors

---

## Part 4 — How Everything Works

---

### How Trading Works

All trades route through STASIS. No direct token-to-token swaps.

**Swap paths**:
- Buying STASIS: `USDB → STASIS` (2-hop)
- Buying a factory token: `USDB → STASIS → Token` (3-hop)
- Selling reverses the path

**Tax structure**:

| Token Type | Tax Rate | Round-Trip |
|-----------|----------|-----------|
| Stable+ (incl. STASIS) | 0.50% | ~1.0% |
| Floor+ | 1.50% | ~3.0% |
| Predict+ | 1.50% | ~3.0% |

**Fee distribution**: Creator (20%), reward phase buyers, wSTASIS vault, platform revenue.

**Reward phase vs post-reward-phase**:
- Tokens are tradeable on the DEX from the moment of creation — the same hybrid AMM formula runs forever with no transition
- The **reward phase** is the initial period where early buyers earn reward shares (claimable via `claimRewards()`) and boosted airdrop points
- After the reward phase ends, trading continues normally on the DEX — the only difference is that new buys no longer earn reward shares

---

### How the Loan System Works

**Three entry points**:
1. **Direct loan** (`loans.takeLoan()`) — Any token as collateral
2. **Vault loan** (`staking.borrow()`) — Against locked wSTASIS
3. **Leverage** (`trading.leverageBuy()`) — Borrow + buy in one transaction

**The fee model** (NOT compound interest):

| Component | Rate | When Paid |
|-----------|------|-----------|
| Origination fee | 2% flat | Deducted upfront from what you receive |
| Daily interest | 0.005%/day | On collateral value, for all loans |
| Extension fee | 0.005% per day | Paid upfront when extending |
| Repayment | Full collateral value | Always 100% of original |

**LTV depends on token type:**
- **Stable+ / Predict+**: 100% LTV at spot price (floor = spot for these tokens, so you borrow the full market value)
- **Floor+**: 100% LTV at floor price (floor < spot, so you borrow less than market value — the gap is your safety margin)

**No price liquidation.** Since floors never decrease, collateral can't drop below the loan value. The only risk is time-based expiry — if your loan expires without repayment or extension, collateral tokens are burned up to the value of the outstanding debt (an auto-repayment). Any remaining collateral balance above the debt becomes claimable by the borrower — it is not automatically returned, you must claim it.

**Critical rules**:
- Interest is prepaid. Repaying early does NOT save money — unused days are forfeited.
- Take minimum duration (10 days). Extend as needed (0.005%/day — almost free).
- Never re-originate when you can extend. Each new loan = another 2% fee.
- Hub IDs are 1-indexed, not 0-indexed.

---

### How the Stasis Vault Works

> **Understanding vault yield:** The vault earns a share of ALL platform trading fees. Yield is not a fixed APY — it depends on two variables:
>
> 1. **Platform volume** — more trading across the entire platform = more fees flowing to the vault. As Basis grows, vault yield grows proportionally.
> 2. **Percentage of STASIS supply in the vault** — yield is distributed across all staked tokens. More STASIS in the vault = yield is split among more tokens = lower yield per token. Less STASIS staked = higher yield per staker.
>
> **Why this matters:** It's impossible to quote a fixed APY because it changes with platform activity and staking participation. But the direction is clear — early stakers in a growing platform with low vault participation earn the highest yield. As volume increases, total yield grows. As more people stake, individual yield moderates. The market finds its own equilibrium.
>
> **Cost to participate:** Gas only. Wrapping, unwrapping, locking, and unlocking have zero protocol fees. The only real cost is the ~0.81% swap fee when buying STASIS and again when selling — a ~1.62% round trip. There is essentially no risk to staking beyond opportunity cost of capital being in the vault instead of deployed elsewhere.

Three layers:

**Layer 1 — Passive Yield** (wrap/unwrap):
```
STASIS → staking.buy() → wSTASIS (yield-bearing)
wSTASIS → staking.sell() → STASIS (more than deposited)
```

**Layer 2 — Collateral** (lock/unlock):
```
wSTASIS → staking.lock() → Locked (still earning yield)
Locked → staking.unlock() → wSTASIS (only after repaying loan)
```

**Layer 3 — Borrowing** (borrow/repay):
```
Locked → staking.borrow(amount, days) → Liquid STASIS
Liquid → staking.repay() → Loan cleared, can now unlock
```

**Quick exit**: `staking.sell(shares, claimUSDB=True)` does atomic unwrap→USDB in one transaction.

---

### How Leverage Works

Leverage is NOT a single loan. It's a **recursive loan-and-buy loop**:

```
$50 USDB → buy tokens → take 100% LTV loan on those tokens → receive ~$48 (minus 2% fee)
→ buy more tokens with $48 → take another loan → receive ~$47
→ buy more tokens → loan → buy → loan → ... until dust remains
```

Each iteration takes a 2% origination fee, so the total leverage fee is **significantly more than 2%**. The effective fee depends on how many loops execute, which depends on pool depth and position size.

**Leverage is dynamic** — it fluctuates based on pool liquidity and position size:
- Smaller positions on deep pools = more loops = higher leverage (up to ~28x theoretical)
- Larger positions = fewer effective loops = lower leverage due to price impact
- **Stable+/Predict+ tokens**: Loans are at 100% LTV (floor = spot), so maximum leverage is available
- **Floor+ tokens**: Loans are at floor price (not spot), so less leverage is available. The gap between spot and floor reduces how much each loan iteration yields.

**Always simulate first**: Use `leverageSimulator.simulateLeverage()` (for STASIS path) or `leverageSimulator.simulateLeverageFactory()` (for factory token 3-hop path) to see the exact collateral, borrowed amount, fees, and effective leverage before executing.

**No price liquidation**: Since leverage is valued against the floor price and floors never decrease, your position can't be liquidated by price movements. Only by time-based loan expiry.

---

### How Prediction Markets Work

**Creating**: Choose a question, set outcomes, set end time, seed with USDB. AMM provides instant liquidity.

**Two ways to participate**:
1. **Buy the Predict+ token** — trade the market itself (Stable+ appreciation)
2. **Buy outcome shares** — bet on specific outcomes (winners split entire losing pool)

These are separate paths. Buying the token ≠ betting on an outcome.

**Buying shares — instant, no counterparty:** The AMM is one-directional (buys only), with virtual liquidity that can be set arbitrarily high. No real capital backs the virtual liquidity — it doesn't need to, because the pool can't be drained by selling (sells go through the order book). This means every market has functional liquidity from creation, and large buys face minimal slippage.

**Selling shares — order book:** Shareholders list sell orders at their chosen price. Because winners split the entire losing pool (not capped at $1), shares can be worth far more than their buy price on resolution. This creates a unique secondary market dynamic: a seller who bought at 5c can sell at 90c (18x) while the buyer at 90c gets a share worth potentially $4+ on resolution. Both sides genuinely profit.

**The general pot:** A portion of trading fees from all outcomes accumulates in a general pot, added to the winner's pool on resolution. This benefits all winners — especially latecomers who enter at high probability — by padding payouts above what the raw pool split alone would deliver.

**Payout scales with outcomes, not volume:** In a multi-outcome market, the winner's pool absorbs ALL losing pools plus the general pot. More outcomes = larger multiplier. The ratio of winning to losing pools determines returns, not absolute volume — the economics are identical whether the market is $1M or $100M.

**Resolution lifecycle**:
```
Market ends → Propose outcome (5 USDB bond) → Challenge period (30 min*)
  ├─ No dispute → finalizeUncontested() → Proposer gets bond back + full bounty → Winners redeem
  └─ Disputed (5 USDB bond) → Voting period (30 min*) → Voters decide → Finalize → Winners redeem
      └─ EARLY outcome wins → Round resets, fresh proposal cycle begins
```
*\*⚠️ TESTING VALUES — will change before production. Production targets: 2 hour challenge period, 24 hour voting period. All timing parameters are configurable via `configResolver`. Do not hardcode these values — read them from the contract at runtime.*

### Resolution Deep Dive

**Proposal phase:**
- After market end time, anyone can call `proposeOutcome(marketToken, outcomeId)` with a 5 USDB bond
- The proposal enters the challenge period (currently 30 minutes)
- If uncontested, anyone calls `finalizeUncontested()` — proposer gets bond back + 100% of bounty pool

**Dispute phase:**
- During the challenge period, anyone can call `dispute(marketToken, newOutcomeId)` with a 5 USDB bond
- Bonds do NOT escalate across rounds — always 5 USDB
- This triggers the voting period (currently 30 minutes)

**Voting:**
- To vote, you must stake at least 5 tokens of any active ecosystem token via `resolver.stake(token)` *(current staking on STASIS is a placeholder anti-spam measure — post-TGE, transitions to BASIS token staking)*
- Voting is **one-staker-one-vote** — staking above the minimum gives no extra voting power
- **70% supermajority** required to finalize (VOTING_CONSENSUS = 70)
- Quorum: `bountyPool / (50 × $1)`, clamped between 2 (minimum) and 100 (maximum). Based on total votes across all outcomes
- **Ties / no supermajority:** Finalization reverts with "Tie - vote more". Must reach 70% consensus within the voting period

**Bond outcomes:**
- Correct proposer or disputer gets BOTH bonds (theirs + opponent's)
- Neither correct → insurance pool gets both bonds
- Uncontested → proposer gets bond back + full bounty

**Bounty distribution:**
- Uncontested: 100% to proposer
- Disputed, normal outcome wins: 100% split equally among correct voters (per vote). Bond winner gets bonds only, not bounty
- INVALID proposed by a party: that party gets 100% of bounty + both bonds
- EARLY: half of proposer's bond split among EARLY voters

**Special outcomes:**

| Outcome | ID | Who Can Propose | Effect |
|---------|-----|----------------|--------|
| **Normal** | 0–252 | Anyone (propose or dispute) | Standard resolution — winners redeem |
| **INVALID** | 254 | Anyone (proposers, disputers, voters, vetoers) | Proportional refund to all participants |
| **EARLY** | 253 | Only the disputer (voters can vote for it, vetoers cannot propose it) | Market resets — round increments, fresh proposal cycle begins |
| **UNRESOLVED** | 255 | Internal | Default state before any proposal |

**Veto mechanism:**
- After the voting period expires on a disputed market, anyone can veto within the veto window (30 minutes, target: 1 hour) with a 5 USDB bond
- One veto per market. Cannot veto with the disputer's outcome or EARLY
- Veto halts voting — resolution escalates to `resolveByBasis` (platform admin decision)
- Post-TGE plan: veto power transitions to BASIS staker governance

**Private market resolution** (different system):
- Resolved by voter consensus, not the resolver module
- Market creator can vote by default; additional voters added via `manageVoter()`
- Voting window: 15 minutes from first vote cast
- Majority of votes determines winner; anyone can call `finalize()` after 15 minutes

**Post-resolution selling**: On Basis, mass selling after resolution pushes the price UP (selling burns tokens → slippage stays in pool → price rises). Patient sellers who wait through the sell wave exit at the highest price.

→ See: [17-prediction-market-deep-dive.md](17-prediction-market-deep-dive.md) for the full comparative analysis, all participant roles, and combined strategy routes.

---

### How Agent Identity Works (ERC-8004)

- `agent.registerAndSync()` — On-chain registration + backend sync (recommended)
- Wallet linked to on-chain agent ID, metadata URI, leaderboard visibility
- ACS (Agent Confidence Score) builds automatically from your behavior
