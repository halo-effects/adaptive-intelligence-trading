# Fable Review — GeeGee Session Summary 2026-07-04
_Date: 2026-07-04 | Author: Claude (Fable) | For: GeeGee (via Brett)_
_Reviewing: fable-review-2026-07-04-session-summary.md. Standing caveat: this reviews the report, not the code — the claims get byte-level verification at the next package sync, same as always. The review below takes the reported data at face value and tests it for internal consistency._

First, credit where due: the G-6 three-round leak analysis is exactly how the fork should have been resolved, the G-7 options test is the right instinct (test calibrations, don't argue about them), and the higher-low discovery — that one structural anchor eliminates the need for a flush primitive entirely — is a better outcome than any of my three §1 options. Good session. Now the findings.

---

## Review findings (blocking items marked ⛔)

### R-1 ⛔ — The recommended deployment configuration was never tested
Option 2's numbers are gate-only. Production would run **veto + L4-gate combined** — and the G-7 four-arm table contains a loud warning about combinations: TON veto+gate collapsed to 9 deals / $1,428 / 76.4h versus 31/$5,913 (veto alone) and 29/$4,449 (gate alone). The interaction was not additive; it was destructive — veto blocking re-entries while the gate stretches deals compounds into idle time. Before any deploy decision, run the **veto + opt2_l4_only** arm across the same 8 coins and confirm the TON-class interaction doesn't reappear. This is one more mode in an existing harness — cheap, and it's the actual thing being shipped.

### R-2 ⛔ — G-1 fixture and G-5 backtest tell different NEAR stories, and G-5's version weakens the original anchor
Same coin, same stated parameters, two different event streams:
- **G-1 fixture:** trigger May 21 → holds at $2.43 (no clear) → re-trigger Jun 1 → **clear Jun 27** at $1.87.
- **G-5 backtest:** trigger May 8 → clear May 17 → re-trigger May 20 → **clear May 30 → re-trigger May 31** → clear Jun 7.

Two problems. (a) If the same model on the same coin produces different events depending on lookback start (Apr 1 vs May fixture start changes SMA50/ATR warm-up), the veto is **history-length-sensitive**, which is itself a finding that needs characterizing — production behavior would depend on how much candle history the scanner holds. (b) The May 30→31 clear/re-trigger gap is a one-day window at elevated prices in which a rotation entry would have bought within days of the crash — this is *precisely* the failure case the original spec anchor ("does not clear at ~2.40 on the first cooldown; clears at the ~1.80 basing") was written to prevent. G-5's assertion list was redrafted around observed behavior rather than held to the spec anchor. Required: reconcile the two event streams (same inputs → same events), and either the May 30 clear is a bug, or the spec anchor is being relaxed — in which case that's a Brett decision to record, not a silent assertion rewrite.

### R-3 ⛔ — Option 3's results are identical to strict gate on every coin, which is suspicious, and the swing-low definition is unstated
A relaxation that changes *nothing* across 8 coins × 90 days × thousands of gated candles is more likely a no-op code path (or a logically equivalent condition given the swing-low definition) than a genuine null result. Please publish the exact **prior swing low** definition (fractal? N-bar lookback? reset rules?) — every G-6/G-7 number hinges on it — and verify opt3's branch actually executes differently. If it's a true null result after verification, fine; say so with evidence.

### R-4 ⛔ — Define MaxDD precisely; Option 2's drawdown collapse is disproportionate
Gating L4 defers 16% of allocation, yet average MaxDD falls 23.9% → 6.2%. That's arithmetically surprising: if DD is unrealized loss over allocation, removing a 16-point tranche can't cut DD by three quarters. The collapse suggests DD may be measured per-deal against invested capital, or marked at fill events rather than candle lows — either of which changes what the number means for Brett's actual account. Publish the DD formula (numerator, denominator, sampling), and spot-check one NEAR deal by hand. The Option 2 recommendation currently rests mostly on this metric.

### R-5 — The two mechanical baselines don't match between G-7 and the options test
TAO: 5 deals/$726 vs 4/$607. INJ: $8,530 vs $8,578. HYPE: $1,927 vs $1,915. JUP strict gate: 17/$2,808 vs 18/$2,927. Small deltas, but comparison tables are only meaningful against a frozen baseline. Pin the window edges and code revision, rerun the options test from the same commit as G-7, and confirm baselines are byte-identical before the summary table is treated as decision evidence.

### R-6 — 100% win rate means this window can only measure gating's cost, never its benefit
With no stop-loss, completed deals are +3% TPs by construction; failures appear as *open* deals at window end, not losses — and the report never shows end-of-window state. Two consequences: (a) the PnL comparison across arms is incomplete without `open_deals_at_end` + unrealized PnL per arm (an arm that ends with a trapped deep deal hides its cost); (b) Apr–Jul 2026 never realized the catastrophe the gate exists to prevent, so the gate's benefit is structurally invisible here — only its 7.5% PnL cost is measurable. This is why the §8 window set demanded bear-leg and continuation-fakeout windows, which remain missing. One 2025 bear-leg window (NEAR or INJ) plus one continuation-fakeout window closes this. Not optional per the spec's own acceptance frame.

### R-7 — Self-correction on my P1: end-state layer sampling makes the score hard-zero
The `/MAX_LAYERS` fix is faithful to my spec, and the spec had a blind spot the fix revealed: `capital_freedom` samples **end-of-window open layers**, and with a 4-layer grid that's near-binary — TAO, your best live coin (17 deals, 100%), scored 14.1 → **0.0** because the sim happened to end mid-grid. A multiplicative zero from a snapshot condition will churn rankings every time a coin's grid fills and TPs. Combined with P2, depth is now penalized twice (end-state layers × median depth-hours). Recommended amendment (P1b): replace end-state sampling with **average open-layer fraction over the window** (`1 − mean(open_layers)/MAX_LAYERS`), keeping [0,1] range without snapshot cliffs — or, minimally, floor the term at 0.2. My spec, my miss; one line either way.

### R-8 — Live Part A config ≠ backtested Part A config (A3)
The scanner sets divergence to False, so production veto = A1+A2 only; G-7's parameter block claims A3 side-resolved was active in backtest. Whichever is true, the artifact of record must match the deployed configuration — either re-run G-5 with A3 off (matching production) or wire A3 in before claiming its coverage. See Q3 below for my recommendation.

---

## Answers to the six questions

**Q1 — Concur with Option 2 (gate L4 only)?**
Directionally yes — it's the right shape, and I'd add a reframe that makes it more defensible, not less: across 8 coins and 90 days, Option 2 admitted **zero L4 fills**. In practice it converts L4 from a grid layer into a **crash-insurance tranche** — 16% of allocation that deploys only on confirmed exhaustion, which is precisely the original spec's motivation (§1: stop L3/L4 deploying *into* waterfalls). That's a legitimate and even elegant design, but it should be adopted *as that decision*, with Brett signing off on "16% of every allocation is usually idle insurance" — not discovered later. Concurrence is conditional on: R-1 (test the actual veto+opt2 combination), R-4 (DD metric verified), R-6 (one bear window + one fakeout window + end-of-window state reported), R-5 (frozen baselines). No concern about L3 ungated — L3 is the workhorse averaging layer (55 fills in opt2, your live data shows L3+ deals winning at 91%+), and gating it was where the 25% PnL cost lived.

**Q2 — Higher-low as universal anchor: edge cases?**
Three, two real and one to test. *Too strict:* V-bottoms — a vertical reversal never prints a higher-low before price is back in TP territory; that's exactly why opt2 shows L4=0 everywhere, and it's acceptable **if** the insurance-tranche framing from Q1 is adopted deliberately. Also Wyckoff springs: a marginal undercut of the prior low during basing resets the anchor and delays re-arm — acceptable delay, worth knowing. *Too loose (the one that matters):* **bear-flag staircases** — multi-day descents print genuine 1h higher-lows inside consolidation flags mid-crash; stall + higher-low can admit at a flag top before the next leg down. This is precisely the §8 continuation-fakeout case, which remains untested (R-6). Don't debate it — run that window. And per R-3, the answer to "too strict or too loose" is unknowable until the swing-low definition is published.

**Q3 — A3 = False in scanner: acceptable?**
Acceptable for Part A short-term, with two requirements. First, evidence-config parity (R-8): the G-5 artifact of record must reflect A3-off if that's what's deployed. Second, don't let it silently become permanent: the NEAR top was caught by A1 in your own fixture, so A3's marginal value on tops may be small — but that's an empirical claim you can test cheaply by re-running G-5 with A3 on (HybridDetector2D is importable at scanner level) and diffing trigger counts. If the diff is negligible, document A3 as engine-tier-only and close it; if not, wire it. Either way it stops being an ambiguous "deferred."

**Q4 — EXT_ATR_MULT=3.0: validate more broadly?**
Yes, and you already have the dataset: the G-5 run's 46-coin / 3-month event log. Two cheap analyses: (a) distribution of `(close − SMA50)/ATR14` at every A2 trigger and at every *non-trigger* daily candle — if 3.0 sits in a stable valley between the populations, it's well-placed; if triggers cluster right at 3.0, it's knife-edge; (b) per-coin trigger-rate table — any coin vetoed >30% of days in a quarter is being over-muted and will tell you whether 3.0 penalizes structurally-high-momentum coins. One threshold, one round of evidence, per house tuning rules. The 74%-of-coins-had-an-event / 15%-currently-vetoed numbers look sane for a hot quarter, but the distribution check turns "looks sane" into "is calibrated."

**Q5 — M-1 (reserve zeroing): spec now?**
Yes — spec now, implement later, exactly as the audit recommended. It's a 15-minute spec while the reconcile method's context is fresh: gate the zeroing on the active split tier (`reserve = equity × reserve_pct` above $10K), define which consumers may draw from reserve, and add a self-test asserting pool conservation at $9,999 / $10,001. Implementation waits until equity approaches the threshold; the spec shouldn't.

**Q6 — DYDX anomaly (strict gate DD 22.6% > mechanical 20.1%): investigate?**
Yes, but reframed: it's not an anomaly, it's the honest data point. Gating defers fills; deferred fills sometimes land at *worse* prices; DD is not monotonically improved by gating — DYDX under opt2 (20.4%) shows the same. One-deal forensics is worth an hour precisely because it's your best evidence that the gate has costs beyond PnL, and it belongs in the report to Brett rather than smoothed over. It also feeds R-4: if DD can *rise* under gating on one coin while averaging 74% lower, the averaging is hiding a wide distribution — report per-coin DD deltas, not just the mean.

---

## Consolidated punch list before Part B deploy

1. R-1: veto+opt2 combined arm, 8 coins (⛔ blocking)
2. R-2: reconcile G-1/G-5 NEAR event streams; May 30 clear is a bug or a recorded spec relaxation (⛔ blocking)
3. R-3: publish swing-low definition; verify opt3 branch executes (⛔ blocking)
4. R-4: publish MaxDD formula; hand-verify one NEAR deal (⛔ blocking)
5. R-6: one bear-leg window + one continuation-fakeout window; add `open_deals_at_end` + unrealized PnL per arm (⛔ blocking per spec §8)
6. R-5: frozen-baseline rerun of the options table
7. R-7: P1b amendment (average-layer sampling or floor) — scanner-side, rides anytime
8. R-8 / Q3: A3 parity run
9. Q4: EXT_ATR_MULT distribution check from existing G-5 data
10. Q5: M-1 spec (no implementation)

Items 1–5 are the Gate B evidence package. Nothing here diminishes the session — Part A live with observability, P1–P5 shipped, and the fork resolved with data instead of debate is a genuinely strong day. The gate discipline exists so that when Part B ships, the numbers underneath it are load-bearing.
