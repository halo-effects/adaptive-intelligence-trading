# Website FAQ Corrections (launchonbasis.com)
_2026-03-14 | Separate from GitBook corrections — this is the main website FAQ_
_The website FAQ has more/different errors than the GitBook version_

---

## Fix 1: Stable+ Mechanism — CRITICAL ❌

**Current text:**
> Stable+ tokens use proprietary smart contract architecture that makes price decreases algorithmically impossible. This is achieved through a dynamic supply where tokens are minted when purchased and burned when sold, a price ratchet mechanism where each transaction reinforces the price floor, and mathematical certainty within the smart contract code that prevents any trade below the current price level. Furthermore, 16.67% of the 1.5% transaction fee directly reinforces this up-only mechanism. Think of it like a staircase where you can only go up or stay on the same step—never down.

**Problems:**
- "16.67% of the 1.5% transaction fee directly reinforces this up-only mechanism" — **wrong.** Fees do NOT inject back into Stable+ liquidity. Appreciation comes from slippage retention only.
- "1.5% transaction fee" — **wrong for Stable+.** Stable+ fee is 0.5%, not 1.5%.
- "price ratchet mechanism" — misleading. The mechanism is slippage retention (price impact from trades stays in the pool), not a ratchet.

**Replace with:**
> Stable+ tokens appreciate through **slippage retention** — when someone buys or sells, the price impact stays in the liquidity pool, permanently increasing the liquidity-to-supply ratio. Tokens are minted when purchased and burned when sold (elastic supply — no pre-minting). Trading fees (0.5% for Stable+) do NOT inject back into the token's liquidity — fees are distributed separately to creators (20%), bonding phase buyers, the wSTASIS vault, and platform revenue. The slippage retention effect is strongest at low supply and needs active trading volume (buy → use → sell → buy cycles) to drive meaningful appreciation. This makes Stable+ ideal for e-commerce, loyalty programs, and any use case requiring downside protection.

---

## Fix 2: Revenue Share Percentage

**Current text:**
> ...creating an ecosystem where everyone wins from everything. ...revenue share to BASIS Stakers (30%)

**Problem:** BASIS Stakers receive **90%** of net platform revenue, not 30%.

**Replace:** "30%" → "90%"

---

## Fix 3: Floor+ Missing Stability Dial & Fee Info

**Current text mentions Floor+ features but omits:**
- The stability dial (0%–~90%, set at creation, immutable)
- That Floor+ trading fee is 1.5% (vs 0.5% for Stable+)

**Suggested addition to the Floor+ answer:**
> Creators set a stability dial from 0% (most volatile, default) to ~90% (most stable) at launch — this is immutable. Lower stability means more price movement per trade. Trading fee: 1.5%.

---

## Fix 4: Token Creation Fee Claim

**Current text:**
> There are zero platform fees for token creation because Basis only earns from the 1.5% transaction fees on trades.

**Problems:**
- "1.5% transaction fees" — not all tokens are 1.5%. Stable+ is 0.5%.

**Replace with:**
> There are zero platform fees for token creation — Basis earns from trading fees on trades (0.5% for Stable+ tokens, 1.5% for Floor+ and Predict+ tokens).

---

## Fix 5: Bonding Phase Target

**Current text:**
> The bonding phase is the initial period after token creation that lasts until $10,000 in real liquidity accumulates.

**Problem:** Bonding target is creator-configurable ($100–$150,000), not fixed at $10,000.

**Replace with:**
> The bonding phase is the initial period after token creation that lasts until the creator's configured USDC target is reached (configurable from $100 to $150,000).

---

## Fix 6: "NFT holders" Reference

**Current text (last FAQ answer):**
> ...while early supporters and NFT holders benefit from all ecosystem activity.

**Replace:** "NFT holders" → "BASIS stakers"

---

## Fix 7: Event Resolution — "Basis Army of NFT holders"

**Current text:**
> ...while the Basis Army of NFT holders provides final arbitration for disputes.

**Problem:** It's the Basis Voting Army (staked token holders who vote), not "NFT holders."

**Replace with:**
> ...while the Basis Voting Army (staked participants) provides final arbitration for disputes.

---

## Fix 8: Loan Terms

**Current text:**
> Standard terms include a 2.5% origination fee and 0.005% daily interest with terms between 10 and 400 days

**Problems:**
- Max term is **1,000 days**, not 400
- ✅ Confirmed 2026-03-16: origination is **2.0%** (not 2.5%), daily interest is **0.005%**
- Source: `staticFeePercentage = 200`, `dynamicFeePercentage = 5` on MAIN_TOKEN contract

**Replace with:**
> Loan fees consist of a 2.0% flat origination fee plus 0.005% daily interest, all prepaid upfront. Total fees range from ~2.05% for a 10-day loan to ~7% for a 1,000-day loan. Terms: 10 to 1,000 days. _(Confirmed by Alex from contract source, 2026-03-16)_

---

## Fix 9: Predict+ Fee

**Current text (Q14):**
> Fees are transparently set at 1.5% for DEX trades and 2.5% for loan origination

**Problem:** Only Floor+ and Predict+ are 1.5%. Stable+ is 0.5%. Loan origination is 2.0%, not 2.5%.

**Replace with:**
> Trading fees are transparently set by token type: 0.5% for Stable+ tokens, 1.5% for Floor+ and Predict+ tokens. Loans have a 2.0% origination fee plus 0.005% daily interest. No hidden fees.

---

## Fix 10: ACS Description (Minor)

**Current text:**
> The ACS is an on-chain reputation score from 0.0 to 1.0...A higher score means greater trust, better airdrop weight, and increased visibility

**Issue:** Per today's discussion, ACS pre-TGE provides a small boost (up to ~1.2x), and post-TGE it's purely identity/reputation (no multipliers). "Better airdrop weight" oversells it. Also ACS is computed off-chain, not on-chain (though it may be reflected via a dynamic soulbound NFT).

**Replace with:**
> The ACS is a reputation score from 0.0 to 1.0 that reflects an agent's verified identity and track record on Basis. It combines identity signals (ERC-8004 registration, framework attestation, 24/7 activity patterns) with economic contribution. Pre-TGE, a higher ACS provides a modest airdrop boost. Post-TGE, ACS becomes the foundation for agent reputation and discovery on Moltbook.

---

## Fix 11: Predict+ "kept as unique collectibles or memorabilia"

**Current text:**
> ...tokens can be kept as unique collectibles or memorabilia.

**Issue:** Predict+ tokens are Stable+ type — they continue to have utility (tradeable, usable as collateral). Calling them "memorabilia" undersells their post-resolution value.

**Replace with:**
> ...tokens continue to function as Stable+ assets — tradeable and usable as loan collateral. Post-resolution selling actually drives further price appreciation through slippage retention.

---

## Summary

| # | Fix | Severity |
|---|---|---|
| 1 | Stable+ mechanism (fee injection → slippage retention, 1.5% → 0.5%) | 🔴 Critical |
| 2 | BASIS Staker revenue share (30% → 90%) | 🔴 Critical |
| 3 | Floor+ missing stability dial & fee info | 🟡 Medium |
| 4 | Token creation fee description (1.5% → varies by type) | 🟡 Medium |
| 5 | Bonding target ($10K fixed → $100-$150K configurable) | 🟡 Medium |
| 6 | "NFT holders" → "BASIS stakers" | 🟡 Medium |
| 7 | "Basis Army of NFT holders" → "Basis Voting Army (staked participants)" | 🟡 Medium |
| 8 | Loan terms (400 days → 1,000 days, fee structure) | 🟡 Medium |
| 9 | Generic "1.5% for DEX trades" → correct per-type fees | 🟡 Medium |
| 10 | ACS description (on-chain → off-chain, oversold airdrop weight) | 🟢 Minor |
| 11 | Predict+ "memorabilia" → ongoing Stable+ utility | 🟢 Minor |
