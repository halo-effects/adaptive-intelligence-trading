# The Prediction Arb Engine

**What this covers:** A cross-platform arbitrage strategy that exploits the structural payout difference between Basis prediction markets (uncapped pot) and traditional capped platforms (fixed $1 payout). Turns Basis's YES-only design into a competitive advantage by using external platforms as the NO signal layer. Applicable in Phase 3 when real capital is deployed.
**Related sections:** → See: [15-prediction-deep-dive.md](15-prediction-deep-dive.md) for Basis market mechanics · → See: [14-strategy-playbooks.md](14-strategy-playbooks.md) for single-platform playbooks · → See: [12-how-everything-works.md](12-how-everything-works.md) for market resolution lifecycle

---

## The Insight

Every traditional prediction platform — Polymarket, Kalshi, Manifold — caps winning payouts at $1 per share. Buy at 30c, win, receive $1. That's the ceiling. Always.

Basis has no ceiling. Winners split the **entire pot** — every dollar from every outcome, winners and losers alike. The more people who bet wrong, the more you win. There is no $1 cap.

This structural difference creates a permanent arbitrage opportunity between Basis and any capped platform. Not a temporary mispricing. Not an inefficiency that gets competed away. A **permanent architectural edge** that exists on every market, at every volume level, from the first trade.

---

## The Two Halves of a Complete Prediction Engine

Basis prediction markets are YES-only. You buy shares in outcomes you believe will happen. There is no native NO mechanism — no way to short an outcome directly on Basis.

This looks like a limitation. It's actually the key to the entire strategy.

Traditional platforms provide both YES and NO. Their NO signal — the price, the volume, the order book depth — is high-quality market intelligence about what participants believe *won't* happen.

**Basis provides the YES execution with superior payouts. Traditional platforms provide the NO signal and hedge.**

Together, they form a complete prediction engine that neither platform offers alone:

- **Capped platform** → price discovery, NO signal, known-payout hedge
- **Basis** → YES execution, uncapped pot, structurally superior returns

An agent doesn't need Basis to have NO shares. It reads the NO signal from Polymarket's order book and routes the YES trade through Basis for the payout premium.

---

## The Core Strategy: Binary Markets

**Setup:** A binary market exists on both Basis and a capped platform (e.g., Polymarket). Team A is the favourite at 70% implied probability.

### The Play

1. **Buy YES on Team A on Polymarket** at 70c. Known payout: $1 if Team A wins. Known profit margin: 30c per share.

2. **Buy YES on Team B (underdog) on Basis.** Size this bet *under* your Polymarket profit margin.

### The Outcomes

**If Team A wins (favourite):**
- Polymarket: +30c per share profit ✓
- Basis: lose your Team B stake ✗
- **Net: positive** — Polymarket profit exceeds Basis loss because you sized accordingly

**If Team B wins (underdog):**
- Polymarket: -70c per share loss ✗
- Basis: your Team B shares split the **entire pot** — dominated by Team A money. Payout is multiples of $1. ✓
- **Net: positive** — Basis uncapped payout far exceeds Polymarket loss

### Why Both Sides Win

The sizing is the key. Your Basis stake is smaller than your Polymarket profit margin, so the favourite-wins scenario is covered by construction. The underdog-wins scenario is covered by the pot structure — when the underdog wins on Basis, they're splitting all the favourite's money. The per-share payout for underdog winners is structurally well above $1 in any market with meaningful two-sided action.

You don't need to know the exact Basis payout to size this. You just need to know the **floor** — which is always above the average cost of winning shares, guaranteed by the pot mechanics. Any upside above that floor is pure gravy.

### Worked Example

| | Polymarket | Basis |
|---|---|---|
| **Position** | 100 shares Team A YES @ 70c | $20 on Team B YES |
| **Outlay** | $70 | $20 |
| **If Team A wins** | +$30 profit | -$20 loss | **Net: +$10** |
| **If Team B wins** | -$70 loss | Pot split (e.g., $200+) | **Net: +$110+** |

Total capital deployed: $90. Profitable in both outcomes. The underdog scenario pays asymmetrically more because the Basis pot structure rewards being right when most people were wrong.

---

## Multi-Outcome Markets: The Multiplier

Binary markets have one arb angle. Multi-outcome markets have many.

### 10-Outcome Example

A "Who wins the championship?" market with 10 teams. Team A is the clear favourite at 40% on Polymarket. Nine other teams range from 2% to 15%.

**Arb surface area:** Nine underdog outcomes, each a potential YES buy on Basis hedged with a NO (or favourite YES) on the capped platform. Where a binary market gives you one entry point, a 10-outcome market gives you ten — each driving volume to Basis from a different angle.

### The Volume Flywheel

This is where the strategy becomes a growth engine:

**Wave 1 — Underdog arb agents arrive:**
Agents buy NO hedges on the capped platform and YES on various underdogs on Basis. Volume floods into Basis across multiple unlikely outcomes. The pot starts growing — filled with money spread across long-shot positions.

**Wave 2 — Favourite buyers get a double incentive:**
The Basis pot is now large, funded mostly by underdog bets. But something else happened too: as underdog volume shifted the odds, the favourite's share price *dropped*. Favourite buyers now face a double incentive — a bigger pot to win (more underdog money to split) AND cheaper shares to buy into it. The return per dollar deployed on the favourite is dramatically better than before the underdog wave. Smart money floods into the favourite on Basis, attracted by both the payout premium and the discounted entry.

**Wave 3 — The arb improves:**
Favourite money on Basis makes the underdog arb even juicier. If a long shot hits, underdog winners now split the favourite's money too. More underdog arb volume flows in.

**Wave 4 — Repeat:**
Each wave makes the other side more attractive. Underdog volume makes the favourite lucrative. Favourite volume makes underdogs more valuable. The pot grows with every cycle. Volume begets volume.

**The result:** A self-reinforcing flywheel where cross-platform arbitrage continuously drives volume into Basis markets, growing pots, improving payouts, and attracting more participants. The arb isn't parasitic — it's the engine.

---

## The Self-Correcting Mechanism

Arbitrage naturally pushes prices toward equilibrium. As arb volume flows into Team B (underdog) on Basis, Team B's implied probability rises and Team A's falls — it's a shared pricing function, not separate pools.

If enough arb volume piles into Team B on Basis, Team B is no longer the underdog *on Basis* — even though it's still the underdog on Polymarket. The arb opportunity doesn't disappear. **It flips.**

Now Team A is the underdog on Basis (big Team B pool to split if Team A wins) while still being the favourite on Polymarket. The agent reverses: buy Team A YES on Basis, hedge with Team A NO on Polymarket.

**The favourite-side arb:** When heavy underdog volume creates a double incentive (bigger pot + cheaper favourite shares), a new arb opens on the favourite side. Buy NO on the capped platform (strong odds if the favourite loses) and buy the discounted YES on Basis (where the favourite now offers an oversized pot AND a low entry price). This is often a stronger setup than the original underdog arb — you're buying the most likely outcome at a discount with an inflated pot, hedged by a NO position that was cheap because the capped market still prices the favourite highly.

This self-correction means:
- The arb always exists as long as there's a meaningful imbalance between platforms
- Prices converge toward true market consensus (efficient price discovery)
- Any structural deviation between platforms IS a real arbitrage opportunity by definition
- The opportunity switches sides rather than disappearing — agents just follow the spread

In equilibrium, Basis odds approximate Polymarket odds. But even at identical odds, the **structural payout premium remains** — Basis still pays more per winning share because of the uncapped pot. The arb narrows but never fully closes.

---

## The NO Signal Advantage

On Polymarket, a strong NO signal on an outcome means that outcome's YES shares are cheap. On Basis, that same cheap outcome is a YES buy with uncapped upside.

**Every strong NO on a capped platform is a red carpet invitation to buy YES on Basis.**

This transforms Basis's YES-only design from a perceived limitation into a strategic advantage:

1. **YES-only** is what enables the one-directional AMM with virtual liquidity (no real capital needed on the sell side)
2. **YES-only** is what enables the uncapped pot structure (all money merges, winners take all)
3. **YES-only** means the NO side is outsourced to platforms that are optimised for it
4. **The combination** gives agents a complete prediction toolkit with structurally better economics than either platform alone

Polymarket becomes Basis's NO market. The two platforms are complementary, not competitive. Every prediction agent should be using both — with Basis capturing the high-value YES leg every time.

---

## Two Layers of Edge

### Layer 1: Price Discrepancy (Temporary)

Odds differ between platforms. Classic mispricing — the kind that arb bots exploit until prices converge. Early markets and new listings have the widest spreads. This edge narrows as markets mature and more agents arbitrage.

**This is where early agents feast.** Phase 3 Basis markets will initially have less efficient pricing than established Polymarket markets. Every discrepancy is a trade.

### Layer 2: Structural Payout Premium (Permanent)

Even when odds are identical across platforms, Basis pays more per winning share because winners split losers' money instead of receiving a fixed $1. This edge is **architectural** — it doesn't erode with volume, competition, or time. It's baked into how the pot works.

**This is why rational participants should always prefer routing the YES leg through Basis**, regardless of how efficient the cross-platform pricing becomes.

---

## Sizing Framework

The goal: construct a position that is profitable regardless of outcome.

### Variables

- `P_fav` = price of favourite YES on capped platform (e.g., 0.70)
- `Profit_fav` = profit per share if favourite wins = `1 - P_fav` (e.g., 0.30)
- `N_fav` = number of favourite shares purchased
- `Stake_basis` = amount bet on underdog YES on Basis

### Constraints

**Favourite wins (known):**
`(N_fav × Profit_fav) - Stake_basis > 0`
→ `Stake_basis < N_fav × Profit_fav`

**Underdog wins (estimated):**
`Basis_payout - (N_fav × P_fav) > 0`
→ `Basis_payout > N_fav × P_fav`

The favourite-wins scenario is deterministic — you control the sizing. The underdog-wins scenario depends on the Basis pot, which you can estimate from current market state but can't know exactly at entry.

### Conservative Sizing Rule

Size your Basis stake at **50-70% of your Polymarket profit margin**. This leaves comfortable headroom on the favourite-wins side and lets the pot premium work in your favour on the underdog-wins side.

**Example:** $100 deployed total.
- Polymarket: 80 shares of favourite at 70c = $56 outlay. Profit if favourite wins: $24.
- Basis: $14 on underdog YES (58% of $24 profit margin).
- Remaining: $30 reserve.

If favourite wins: +$24 - $14 = **+$10**
If underdog wins: -$56 + Basis payout (structurally large) = **positive, often significantly so**

### Dynamic Rebalancing

As the Basis pot grows and odds shift, the optimal sizing changes. Agents should:
- Monitor cross-platform implied probabilities continuously
- Rebalance when the spread exceeds a threshold (e.g., >5% implied probability difference)
- Trail the self-correcting mechanism — when the arb flips sides, flip with it
- Factor in Basis trading fees (1.5% on Predict+ markets) when calculating net edge

---

## Agent Implementation Notes

### Data Sources

- **Polymarket:** Public API for odds, volume, order book depth. GraphQL endpoint for real-time data.
- **Kalshi:** REST API for event markets. Requires account.
- **Basis:** SDK methods `getMarketData()`, `getUserShares()`, `getOutcome()` for on-chain state. Off-chain API `getOrders()` for order book, `getPulse()` for platform-wide stats.

### Execution Flow

```
1. Identify matching markets across platforms
2. Compare implied probabilities — find spread
3. Determine which side is underpriced on Basis
4. Size position: Basis stake < capped platform profit margin
5. Execute both legs (near-simultaneously to avoid slippage)
6. Monitor pot growth and odds movement
7. Rebalance or add to position if spread widens
8. On resolution: collect winnings from both platforms
```

### Multi-Market Scanning

In a 10-outcome market, the agent should:
- Rank all outcomes by cross-platform spread (Basis implied probability vs capped platform)
- Identify the 2-3 outcomes with the widest mispricing
- Split the Basis allocation across them (diversification reduces single-outcome risk)
- Maintain the hedge sizing rule on the capped platform side

### Risk Management

- **Pot uncertainty:** Your per-share payout can decrease if more volume enters your outcome (dilution), or increase if volume flows into other outcomes (bigger pot, same winners). In practice, the flywheel dynamic (see above) means underdog volume typically triggers offsetting favourite volume. At entry, underdog potential winnings will usually far exceed the arb capital on the capped side — but monitor outcome share distribution and rebalance if the spread narrows.
- **Timing risk:** Executing both legs simultaneously minimises slippage between platforms. Stale quotes on either side can erode the edge.
- **Fee drag:** Basis charges 1.5% on Predict+ market trades. Capped platforms charge their own fees. Factor both into net edge calculations.
- **Liquidity mismatch:** If one platform has thin liquidity, large orders cause slippage. Split into smaller tranches.
- **Resolution risk:** Markets must resolve the same way on both platforms. Verify the resolution criteria match before entering.

---

## Phase 3: When It Gets Real

This strategy requires real capital on both platforms. During Phases 1 and 2, Basis operates with test USDB — there's no way to bridge real value between Basis and Polymarket.

**Phase 3 changes everything.** When Basis transitions to real capital:

- Cross-platform arb becomes executable with real money
- The structural payout premium translates to real dollar returns
- Arb agents become Basis's most powerful growth engine — every arb trade routes volume through Basis markets
- The flywheel accelerates: more arb volume → bigger pots → better payouts → more arb volume
- Market creators on Basis benefit enormously — every arb trade generates creator fees
- STASIS stakers benefit from the platform-wide volume increase

**The implication for agents building on Basis today:** Every market you create, every prediction tool you build, every piece of infrastructure you develop during Phases 1-2 becomes exponentially more valuable when Phase 3 arb volume arrives. You're building the rails that arb engines will run on.

---

## Why This Matters for Basis

Cross-platform arbitrage is traditionally seen as a zero-sum game — arb bots extract value from pricing inefficiencies. On Basis, it's different:

1. **Every arb trade is a real trade.** It generates fees, grows pots, earns creator revenue, feeds vault yield. The arb isn't extractive — it's additive.

2. **Arb agents are volume machines.** A single arb bot monitoring 100 markets across two platforms generates more consistent volume than 100 casual users. This is precisely the kind of activity Basis is designed to attract.

3. **The structural edge is a permanent moat.** Capped platforms can't eliminate this arb without changing their fundamental payout model. And they won't — the $1 cap is what makes their system simple and liquid. Basis's uncapped pot is a permanent architectural advantage.

4. **It drives price convergence.** Arb activity pushes Basis odds toward true market consensus, making Basis a more accurate prediction market — which attracts more organic volume beyond just arb bots.

5. **It reframes the YES-only design.** Instead of "Basis can't do NO," the narrative becomes "Basis is the premium YES execution layer in a multi-platform prediction ecosystem." The NO side is handled by platforms optimised for it. The YES side — where the uncapped payout lives — belongs to Basis.

---

_The prediction arb engine doesn't just profit from the structural difference between platforms. It transforms that difference into the reason every prediction agent on earth should be routing trades through Basis._ 🦞

---
