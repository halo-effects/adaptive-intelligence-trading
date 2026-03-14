# GitBook Live FAQ — Corrections for Alex
_2026-03-14 | 3 fixes needed on docs.launchonbasis.com/faq_

---

## Fix 1: Floor+ Stability Dial (Q3)

**Current text:**
> **Stability Dial:** 0% (most volatile) to 100% (most stable), set at creation and immutable.

**Replace with:**
> **Stability Dial:** 0% (most volatile, default) to ~90% (most stable), set at creation and immutable. At 100% stability, a token would behave identically to Stable+ — so the Floor+ range caps below that.

---

## Fix 2: Leverage Stable+ vs Floor+ Distinction (Q11)

**Current text:**
> Leverage is a **toggle** (on/off). Effective leverage is **dynamic** -- depends on liquidity and position size. "Up to 36x" theoretical maximum. Leverage fee: 43-70% of collateral. No forced liquidation from market volatility.

**Replace with:**
> Leverage is a **toggle** (on/off). Effective leverage is **dynamic** — it fluctuates based on current pool liquidity and position size. Up to 36x is possible in optimal conditions; larger buys produce lower effective leverage. For **Stable+** tokens (where floor = spot), maximum leverage is always available. For **Floor+** tokens, maximum leverage is available at launch (floor ≈ spot) but decreases as spot price rises above the floor. Leverage fee: 43–70% of collateral for small buys. No forced liquidation from market volatility.

---

## Fix 3: Predict+ Post-Resolution (Q7)

**Current text:**
> **Post-resolution:** Selling burns tokens > fees inject > price goes UP. Patient holders exit at higher prices.

**Replace with:**
> **Post-resolution:** Selling burns tokens, and the slippage retention from those sells continues to push the price up. Patient holders can exit at higher prices. (Note: this is slippage retention — the same mechanism as all Stable+ tokens — not fee injection.)

---

## Fix 4: Remove "NFT holders" Reference (Q17)

**Current text:**
> It aligns incentives by ensuring creators profit from long-term success rather than dumps, while early supporters and NFT holders benefit from all ecosystem activity.

**Replace with:**
> It aligns incentives by ensuring creators profit from long-term success rather than dumps, while early supporters and BASIS stakers benefit from all ecosystem activity.

**Reason:** NFT holder rewards was an old model that's been removed. Current model: creators get 20% trading fees, bonding phase buyers get reward shares (3.33%), and BASIS stakers get 90% of net platform revenue as USDC.

---

## Fix 5: Predict+ Trading Fee — GLOBAL (Q14 + Executive Summary + all pages)

**Current text (appears on multiple pages):**
> Predict+ | 0.5%

And Q14:
> Fees are transparently set at 1.5% for DEX trades and 2.5% for loan origination

**Correction:** Predict+ trading fee is **1.5%**, not 0.5%. The fee table should be:

| Token Type | Trading Fee | Creator Share |
|---|---|---|
| Stable+ | 0.5% | 0.1% per trade |
| Floor+ | 1.5% | 0.3% per trade |
| Predict+ | 1.5% | 0.3% per trade |

Q14's "1.5% for DEX trades" is misleading — it's only 1.5% for Floor+ and Predict+. Stable+ is 0.5%. Also "2.5% for loan origination" needs verification — Diamond's walkthrough showed dynamic fees: ~2% for 10-day loans to ~7% for 1,000-day loans.

**Pages to check on live GitBook:**
- FAQ (Q14 fee table)
- Executive Summary (fee table)
- Any other page with a fee table or fee reference

---

_That's it — 5 fixes for the live site. All replacement text is copy-paste ready._
