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

_That's it — 3 targeted fixes. Everything else on the live FAQ checks out against Diamond's corrections doc._
