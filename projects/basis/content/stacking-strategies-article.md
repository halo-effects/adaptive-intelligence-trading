# The BASIS Stacking Guide: How One Bag Does the Work of Five

**TL;DR:** On BASIS, buying a token doesn't lock your capital. You can borrow against any position to get USDB back, then redeploy it — stacking multiple yielding positions from a single bag. No price liquidation means stacking 3 layers deep is safe, not reckless. Start with Stable+ (STASIS) — it creates a yielding base layer that earns vault fees underneath every other play you make. Stack into Predict+ or Floor+ tokens (buy Floor+ near launch for best capital recovery), then finish with a prediction bet or leverage play. Three stacks is the sweet spot: 3 active positions, 4+ airdrop categories, and most of your USDB still working.

---

## The Problem With Traditional DeFi

In most DeFi ecosystems, your capital can only be in one place at a time. You stake it, it's locked. You lend it, it's gone until repaid. You trade into a token, your stablecoin disappears.

This forces a choice: do you want yield, exposure, or liquidity? Pick one. Maybe two if you're creative with liquid staking derivatives. But ultimately, $1,000 deployed in one protocol is $1,000 that isn't working anywhere else.

BASIS changes the math entirely.

---

## The BASIS Difference: Unified Collateral

Every product on BASIS — the AMM, lending, staking, prediction markets, token creation — shares the same collateral system. This is the foundational insight that makes everything else possible.

When you buy a token on BASIS, you can immediately borrow against it. That borrowed USDB can be deployed into another position. Which you can borrow against. And deploy again.

**One bag. Multiple simultaneous positions. Each one earning.**

And here's the kicker: there's no price liquidation on BASIS. Loans are time-based only. A 50% market crash on any other platform would cascade through your collateralized positions and wipe you out. On BASIS, you just extend your loans (at 1/400th the cost of a new loan) and wait for recovery.

This is what makes deep stacking viable instead of suicidal.

---

## The Building Blocks: Five Paths From USDB to USDB

Every stacking strategy is built from simple loops. Each one starts with USDB, creates an earning position, and returns USDB for the next move. Think of them as Lego bricks.

### 🟢 Path A: The Stable+ Path — Your Yielding Base Layer

```
USDB → Buy STASIS → Wrap to wSTASIS → Borrow USDB
```

This isn't just your first stack — it's the **foundation that makes every other play better.**

STASIS is a Stable+ token — its price can only go up. When you wrap it into wSTASIS, it earns vault yield generated from all platform trading fees. Then you borrow against it to get your USDB back, ready to deploy into anything else.

- **Cost:** ~2.5% (0.5% buy tax + 2% loan origination)
- **USDB recovered:** ~97.5% of input
- **What you hold:** wSTASIS — appreciating asset + passive yield
- **Points categories:** Trading, Staking, Lending

**Why this is the most important path:** Zero downside risk on the asset. The price literally cannot drop. Your only obligation is managing the loan expiry, which costs almost nothing to extend.

But here's what makes Path A truly powerful: **it turns idle capital into earning capital across every other strategy you run.**

Consider prediction markets. When you take a long-term outcome bet (Path D), your capital would normally just sit there, locked and idle while you wait weeks or months for the market to resolve. But if you start with Path A first, your wSTASIS position is earning vault yield the entire time — your money is working even while you wait. The prediction bet uses borrowed USDB, not your original capital. You get the upside of the bet AND the passive yield.

The same logic applies to every other path. Floor+ token you're holding for long-term upside? Your base layer is still earning. Predict+ token riding a slow-building market? wSTASIS is quietly compounding underneath.

**Path A doesn't just recover your USDB — it creates a yield engine that runs underneath everything else you do on the platform.** That's why it's always Stack 1.

### 🟡 Path B: The Floor+ Path

```
USDB → Buy Floor+ token → Borrow USDB
```

Floor+ tokens have a built-in rising price floor. The token can trade above the floor (upside), but can never fall below it (protected downside). Buy one, borrow against it, keep moving.

- **Cost:** ~3.5% (1.5% buy tax + 2% loan origination)
- **USDB recovered:** Varies — depends on when you buy relative to the floor
- **What you hold:** Floor+ token — capped downside, open upside
- **Points categories:** Trading, Lending

**Important nuance on LTV:** The amount of USDB you can borrow back depends on the token's loan-to-value ratio, which is tightest for Floor+ tokens. If you buy right after launch when the price is near the floor, you'll recover the most USDB. But if the token has already run up well above its floor, the LTV on your position will be lower — meaning less USDB comes back for the next stack. **Timing matters here.** For the best capital efficiency in a stacking strategy, target Floor+ tokens early, ideally close to launch when price and floor are still near each other.

**Best for:** Adding exposure with a safety net. Early-stage Floor+ tokens near their floor price offer the best risk/reward — both for the token's upside potential and for maximizing your borrowing power in the stack.

### 🔵 Path C: The Predict+ Token Path

```
USDB → Buy Predict+ token → Borrow USDB
```

Predict+ tokens are tied to prediction markets. Holding one gives you creator-like exposure to the trading volume on that market. More activity = more earnings for holders.

- **Cost:** ~3.5% (1.5% buy tax + 2% loan origination)
- **USDB recovered:** ~96.5% of input
- **What you hold:** Predict+ token — earns from market volume
- **Points categories:** Trading, Predictions, Lending

**Best for:** Markets you expect to stay active. High-volume prediction markets mean your token keeps earning.

### 🟣 Path D: The Outcome Bet Path

```
USDB → Buy outcome shares → Wait for resolution → USDB (if correct)
```

This is a straight prediction market bet. No borrowing loop — you're buying shares in an outcome. If you're right, the payout can be massive (and uncapped). If you're wrong, that portion is gone.

- **Cost:** Varies by outcome pricing
- **USDB recovered:** Only on correct outcome
- **What you hold:** Outcome shares in a live prediction market
- **Points categories:** Predictions

**Best for:** High-conviction calls where you want asymmetric upside. Size it appropriately — this is the one path where you can lose.

### 🔴 Path E: The Leverage Path

```
USDB → leverageBuy on a token → [auto-loops: buy → loan → buy → loan → ...]
```

The nuclear option. Your USDB automatically loops through multiple buy-and-borrow cycles, building a massive leveraged position. A small amount of USDB can become a huge bag.

- **Cost:** 2% origination per loop (6-8 loops typical)
- **USDB recovered:** 0 — this is a terminal path
- **What you hold:** Heavily leveraged token position
- **Points categories:** Trading, Lending (heavy)

**What to leverage:** The best leverage plays aren't on STASIS — Stable+ appreciation is slow and steady, which doesn't reward leverage well. Instead, **leverage buy a Floor+ token close to launch.** A Floor+ near its floor price gives you protected downside (no price liquidation AND a rising floor) with real upside potential. If the token runs, leverage amplifies it. If it doesn't, the floor limits your downside.

**Critical:** This path does NOT return USDB. It's always your last move. No price liquidation means the leverage is far safer than on any other platform — but you still need to manage loan expiries across all those loops.

---

## The Fee Math: Why Three Stacks Is the Sweet Spot

Every path costs fees. When you chain them, each layer works with a slightly smaller bag:

| Stacks Completed | USDB Remaining (from $1,000) | Positions Held |
|---|---|---|
| After Path A (Stable+) | ~$975 | 1 (wSTASIS — yielding) |
| After Path A → C (Predict+) | ~$941 | 2 (wSTASIS + Predict+) |
| After Path A → C → B (Floor+) | Varies* | 3 positions |
| After A → C → B → D (Bet) | Varies minus bet | 4 positions |

*Floor+ recovery depends heavily on timing — buying near launch when price is close to the floor returns significantly more USDB than buying after a run-up. Plan your stack order accordingly.

**The rule of thumb:** Path A (Stable+) is the most capital-efficient loop at ~2.5% cost. Predict+ and Floor+ cost ~3.5% in fees, but Floor+ LTV varies with market timing. After three stacks, you're typically running three separate yielding positions with most of your USDB still deployed.

After four or more stacks, the fee erosion starts to outweigh the benefits. Three is the sweet spot for almost everyone.

---

## Four Strategies: From Conservative to Aggressive

### Strategy 1: "The Conservative Stack"
**Risk: Low | Stacks: 3 | Goal: Maximum category diversity, minimal risk**

```
$1,000 USDB
  ↓
Stack 1 → Path A (Stable+): wSTASIS position (yielding base), ~$975 back
  ↓
Stack 2 → Path B (Floor+): Floor+ token near launch, borrow USDB
  ↓
Stack 3 → Path D (Outcome Bet): $100 on a long-term prediction market
  ↓
Result: 3 positions + liquid reserve
```

**Categories hit:** Trading ✅ Staking ✅ Lending ✅ Predictions ✅

Why it works: STASIS literally can't drop — and it's earning vault yield the entire time. Floor+ has a floor. Your prediction bet is sized small ($100 out of $1,000).

Here's the magic: that long-term prediction market might take weeks or months to resolve. On any other platform, that $100 is dead capital sitting in limbo. But because you started with Path A, your wSTASIS is earning yield underneath the whole time. You're not choosing between "earn yield" and "make a prediction" — you're doing both, with the same original bag. Maximum airdrop category diversity with minimal actual risk.

---

### Strategy 2: "The Yield Maximizer"
**Risk: Medium | Stacks: 3 | Goal: Every position generating ongoing returns**

```
$1,000 USDB
  ↓
Stack 1 → Path A (Stable+): wSTASIS earning vault yield from ALL platform fees
  ↓
Stack 2 → Path C (Predict+): Token earning from prediction market volume
  ↓
Stack 3 → Path B (Floor+): Near-launch Floor+ for best LTV, protected downside
  ↓
Result: 3 yielding positions + liquid reserve
```

**Categories hit:** Trading ✅ Staking ✅ Lending ✅ Predictions ✅

Why it works: Three distinct income streams from one bag. wSTASIS earns from platform-wide volume — it's your always-on yield engine underneath everything. Your Predict+ token earns from its market's activity. Floor+ captures token upside with downside protection. Everything is working, and your base layer never stops earning.

---

### Strategy 3: "The Deep Stack"
**Risk: Aggressive | Stacks: 3 + terminal | Goal: Maximum capital deployment**

```
$1,000 USDB
  ↓
Stack 1 → Path A (Stable+): wSTASIS position (yielding base), ~$975 back
  ↓
Stack 2 → Path C (Predict+): Token position, ~$941 back
  ↓
(Set aside ~$50 for loan extensions)
  ↓
Stack 3 → Path E (Leverage): ~$891 into a leveraged Floor+ token near launch
  ↓
Result: 3 positions (1 heavily leveraged), $50 reserve
```

**Categories hit:** Trading ✅ Staking ✅ Lending ✅ Predictions ✅

Why it works: You're fully deployed. Your wSTASIS base is earning yield underneath everything. The leveraged Floor+ position has a rising floor protecting your downside, and no price liquidation on top of that — so the leverage is as safe as leverage gets. If the Floor+ token runs after launch, the amplified returns are massive. But you're tight on reserves — loan expiry management is critical.

---

### Strategy 4: "The Creator's Edge"
**Risk: Medium | Stacks: 3 | Goal: Create income-generating assets, then stack on them**

```
Step 0: Create a Floor+ or Predict+ token (small gas cost)
→ You now earn 20% of ALL net trading fees on this token. Forever.

$1,000 USDB
  ↓
Stack 1 → Path A (Stable+): wSTASIS position, ~$975 back
  ↓
Stack 2 → Buy YOUR token: Seed liquidity in your own creation, ~$941 back
  ↓
Stack 3 → Path D (Outcome Bet) or hold liquid
  ↓
Result: 3 positions + creator fee income + reserve
```

**Categories hit:** Trading ✅ Staking ✅ Lending ✅ Token Creation ✅ (+ Predictions if you bet)

Why it's special: You're not just deploying capital — you've created a perpetual income stream. Every time anyone trades your token, you earn. The 20% creator fee compounds with all your stacking yield. You're building an asset, not just using one.

---

## Why This Only Works on BASIS

This isn't a strategy you can copy-paste to Aave or Uniswap. It requires a very specific set of platform mechanics working together:

**Unified collateral system** — AMM, lending, staking, and predictions all share the same collateral infrastructure. On other protocols, you'd need to bridge between 3-4 separate platforms, paying gas and fees at every hop.

**Borrow against any token** — Most lending protocols have curated collateral lists (ETH, BTC, major stablecoins). On BASIS, any factory-created token can be used as collateral. That's what makes the loops possible.

**No price liquidation** — This is the big one. On Aave or Compound, a 15% price drop triggers liquidation. Three layers of collateralized positions would cascade into total wipeout. On BASIS, loans expire based on time only. Price crashes don't touch your positions.

**Stacked airdrop incentives** — Most protocols incentivize one action (provide liquidity, stake, etc.). BASIS awards points across multiple categories, and hitting more categories multiplies your rewards. Stacking naturally diversifies your category exposure.

**Built-in token creation** — You don't need to go to another platform to create tokens or prediction markets. It's all in one place, and creators earn ongoing fees from their creations.

---

## The Golden Rules

1. **Always keep a USDB reserve.** Loan extensions cost 1/400th of a new loan. That's almost nothing — but "almost nothing" times zero USDB is still zero. Don't get caught dry.

2. **Three stacks is the sweet spot.** After that, fees erode your bag faster than the additional positions earn. Master three before considering more.

3. **Stagger your loan expiry dates.** If all three loans expire on the same day and you miss it, you're scrambling. Spread them out.

4. **Category diversity is a multiplier.** Don't stack three of the same path. Each stack should hit a different airdrop category when possible.

5. **Leverage (Path E) is always last.** It's terminal — no USDB comes back. Use it only with capital you're willing to fully deploy.

6. **Stable+ is always your first stack.** wSTASIS is the safest collateral on the platform. Build your foundation before reaching for riskier positions.

---

## Getting Started

If you're new to BASIS, here's the simplest way to start stacking:

1. **Get USDB** — Bridge or swap into USDB on BASIS
2. **Stack 1 — Buy STASIS, wrap to wSTASIS, borrow USDB** — This is your base layer. Safest possible position.
3. **Stack 2 — Pick a Floor+ or Predict+ token, buy it, borrow USDB** — Now you have two positions working.
4. **Stack 3 — Place a prediction bet OR buy another token** — Hit that third airdrop category.
5. **Keep your remaining USDB liquid** — You'll need it for loan extensions and future opportunities.

That's it. One bag, three positions, four airdrop categories, and most of your capital still accessible.

Stack smart. Stack deep. 🦞
