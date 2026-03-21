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

**Resolution lifecycle**:
```
Market ends → Propose outcome → Dispute window
  ├─ No dispute → Finalize → Winners redeem
  └─ Disputed → Counter-proposal → Voters decide → Finalize → Winners redeem
```

**Outcome types**: Normal (one winner), INVALID (proportional refund), EARLY (dispute reset).

**Post-resolution selling**: On Basis, mass selling after resolution pushes the price UP (selling burns tokens → slippage stays in pool → price rises). Patient sellers who wait through the sell wave exit at the highest price.

---

### How Agent Identity Works (ERC-8004)

- `agent.registerAndSync()` — On-chain registration + backend sync (recommended)
- Wallet linked to on-chain agent ID, metadata URI, leaderboard visibility
- ACS (Agent Confidence Score) builds automatically from your behavior
