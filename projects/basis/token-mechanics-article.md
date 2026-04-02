# Token Mechanics: How Basis Tokens Actually Work

## The Two Foundations

Every Basis token — Stable+, Floor+, and Predict+ — is built on two properties that don't exist in traditional crypto tokens:

**Elastic supply.** Tokens are minted when you buy and burned when you sell. There is no fixed supply. This is what makes rising floors possible — fixed-supply tokens can't do it because there's no mechanism to create the surplus.

**No separate LP pool.** The real liquidity (USDB, BNB, or whatever the value token is) lives inside the token contract itself. There is no external liquidity pool to drain, no LP tokens to rug. The token reserve is purely a pricing calculation mechanism, not actual stored tokens.

---

## The Constant Product Formula

Basis uses a constant product (CP) formula for pricing:

**x × y = k**

Where x = tokens in reserve (pricing mechanism), y = USDB in reserve (real value).

When you **buy** with USDB amount `d`:
- Circulating tokens minted = x × d / (y + d)
- This is always slightly less than d ÷ price, because the denominator grows

When you **sell** `n` tokens:
- USDB returned = y × n / (x + n)
- This is always slightly less than n × price, because the denominator grows

The "slightly less" in both directions is key. Every trade leaves a small surplus in the reserve. Over thousands of trades, this surplus compounds into a permanently rising floor.

---

## How Stable+ Works

Start with the basics. Imagine a token with a 100% liquidity reserve — no CP formula:

- Liquidity: $1,000 · Tokens: 1,000 · Price: $1.00
- Someone buys $1 → Liquidity: $1,001 · Tokens: 1,001 · Price: $1.00

Every token is backed 1:1. The price never moves. Simple.

Now here's what Stable+ does differently: it uses the constant product formula, so your $1 buy mints *slightly less* than 1 token. The extra stays in the pool.

- Liquidity: $1,001 · Tokens: 1,000.99 · Price: $1.00001

Sells work the same way. Burning 1 token at a $1 price gives you $0.99 back — the difference stays in the liquidity reserve.

Every trade — buy or sell — leaves slightly more liquidity backing each remaining token. Multiply across thousands of trades and the floor ratchets up permanently.

Not a peg. Not an algorithm. Just more money in the pool than tokens in circulation, and that gap only widens.

### The Hybrid Multiplier (Stable+)

Stable+ uses a hybrid multiplier of 200 (100% stability). Here's the two-step process on each buy:

1. **Run CP formula:** tokens_out = x × d / (y + d). This temporarily reduces the token reserve.
2. **Add back 2× tokens_out** to the token reserve.

Net effect: token reserve increases by +tokens_out per buy. Both the token reserve and USDB reserve grow in near-lockstep, so the price barely moves per trade.

### Stable+ Demo Table

Starting pool: 1,000 tokens / $1,000 USDB / Price $1.00

| Action | Tokens Reserve | USDB Reserve | Price | Circ | MCap |
|---|---|---|---|---|---|
| Launch | 1,000 | $1,000 | $1.000 | 0 | $0 |
| Buy $100 | 1,091 | $1,100 | $1.008 | 91 | $92 |
| Buy $100 | 1,182 | $1,200 | $1.015 | 182 | $185 |
| Buy $100 | 1,273 | $1,300 | $1.021 | 273 | $279 |
| Sell 91 | 1,182 | $1,213 | $1.026 | 182 | $187 |
| Sell 91 | 1,091 | $1,127 | $1.033 | 91 | $94 |
| Sell all | 1,000 | $1,040 | $1.040 | 0 | $0 |

**Floor: $1.000 → $1.040. It can never go back down.**

Key observations:
- Token reserve moves with circulating supply (both increase on buys, decrease on sells)
- Price barely moves: $1.00 → $1.02 after $300 in buys
- Price goes up even on sells — every single trade ratchets the floor higher
- After all tokens sold and burned: 1,000 tokens in reserve, but $1,040 USDB instead of $1,000

---

## How Floor+ Works

Same constant product formula as Stable+, with one key difference: the hybrid multiplier.

### The Stability Dial

When a Floor+ token is created, the creator sets a stability dial (50%–90%). This controls the hybrid multiplier and is **locked forever at launch** — it can never be changed.

The two-step process is the same as Stable+, but with a different add-back amount:

1. **Run CP formula:** tokens_out = x × d / (y + d)
2. **Add back (stability% × 2) × tokens_out** to the token reserve

| Stability | Multiplier | Add-back | Net reserve change per buy |
|---|---|---|---|
| 100% (Stable+) | 200 | 2× tokens_out | +tokens_out (lockstep with supply) |
| 75% (Floor+) | 150 | 1.5× tokens_out | +0.5× tokens_out (moderate growth) |
| 50% (Floor+) | 100 | 1× tokens_out | 0 (constant reserve) |

Lower stability = fewer tokens absorbing the USDB = faster price movement in both directions. But the CP formula surplus still accumulates on every trade — the floor only goes up.

### Floor+ 75% Demo Table

Starting pool: 1,000 tokens / $1,000 USDB / Price $1.00

| Action | Tokens Reserve | USDB Reserve | Price | Circ | MCap |
|---|---|---|---|---|---|
| Launch | 1,000 | $1,000 | $1.000 | 0 | $0 |
| Buy $100 | 1,045 | $1,100 | $1.053 | 91 | $96 |
| Buy $100 | 1,089 | $1,200 | $1.102 | 178 | $196 |
| Buy $100 | 1,131 | $1,300 | $1.149 | 262 | $301 |
| Sell 84 | 1,089 | $1,210 | $1.111 | 178 | $198 |
| Sell 87 | 1,045 | $1,121 | $1.073 | 91 | $98 |
| Sell all | 1,000 | $1,031 | $1.031 | 0 | $0 |

**Floor: $1.000 → $1.031.**

### Floor+ 50% Demo Table

Starting pool: 1,000 tokens / $1,000 USDB / Price $1.00

| Action | Tokens Reserve | USDB Reserve | Price | Circ | MCap |
|---|---|---|---|---|---|
| Launch | 1,000 | $1,000 | $1.000 | 0 | $0 |
| Buy $100 | 1,000 | $1,100 | $1.100 | 91 | $100 |
| Buy $100 | 1,000 | $1,200 | $1.200 | 174 | $209 |
| Buy $100 | 1,000 | $1,300 | $1.300 | 251 | $326 |
| Sell 77 | 1,000 | $1,207 | $1.207 | 174 | $210 |
| Sell 83 | 1,000 | $1,115 | $1.115 | 91 | $101 |
| Sell all | 1,000 | $1,022 | $1.022 | 0 | $0 |

**Floor: $1.000 → $1.022.**

---

## Comparison: All Three Side by Side

|  | Reserve range | Price range | Floor after cycle |
|---|---|---|---|
| Stable+ (100%) | 1,000 → 1,273 → 1,000 | $1.00 – $1.04 | $1.040 |
| Floor+ (75%) | 1,000 → 1,131 → 1,000 | $1.00 – $1.15 | $1.031 |
| Floor+ (50%) | 1,000 → 1,000 → 1,000 | $1.00 – $1.30 | $1.022 |

The pattern:
- Lower stability = bigger price swings, constant or slower reserve growth
- Higher stability = minimal price movement, reserve grows with supply
- All settings produce a rising floor — the CP surplus accumulates regardless
- Lower stability tokens generate more trading volume in practice, which compounds the floor faster over time

---

## Why This Can't Be Rugged

1. **No LP tokens.** Liquidity lives inside the contract. There are no LP tokens to withdraw.
2. **No admin keys for liquidity.** The creator cannot drain the reserve.
3. **Factory-enforced.** Every token deployed through the Basis factory passes the same standard. No custom code, no backdoors.
4. **Elastic supply.** Tokens are minted and burned by the contract math. No pre-mints, no insider allocations.
5. **Immutable stability dial.** Once set at launch, the stability percentage can never be changed. The creator commits to a design philosophy permanently.
