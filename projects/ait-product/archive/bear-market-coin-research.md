# Bear Market Coin Research — V14 DCA Optimization
**Date:** 2026-03-03
**Context:** BTC ~$66K, confirmed bear market, likely bottoming through 2026 into next halving (~Apr 2028)

## What V14 Needs From a Bear Market Coin

V14's DCA grid profits from **volatility within a range**, not directional moves. The ideal bear market coin:

1. **High daily range %** — wider intraday swings = more SO fills + TP cycles
2. **Frequent reversals** — up/down chop creates DCA cycle opportunities
3. **Sufficient liquidity** — need to enter/exit without slippage on a small account
4. **Won't die** — needs real utility/revenue to survive a 12-18 month bear
5. **Available on Hyperliquid perps** — for paper bots and potential live futures trading

## Current Bear (Jan-Mar 2026) — Volatility Rankings

From our candles.db analysis of the current drawdown:

| Rank | Coin | Avg Daily Range | Cycles/Week | DD from Jan 1 | Category |
|------|------|-----------------|-------------|----------------|----------|
| 1 | **INJ** | 8.5% | 1.6 | -39.4% | DeFi infrastructure |
| 2 | **UNI** | 8.1% | 1.8 | -47.5% | DeFi (DEX fees) |
| 3 | **SUI** | 7.8% | 1.5 | -46.5% | L1 infrastructure |
| 4 | **FIL** | 7.7% | 1.3 | -41.6% | Storage utility |
| 5 | **CRV** | 7.6% | 1.8 | -45.2% | DeFi (AMM fees) |
| 6 | **DOT** | 7.4% | 1.5 | -42.8% | L0 infrastructure |
| 7 | **GRT** | 7.4% | 2.0 | -33.6% | Data indexing utility |
| 8 | **NEAR** | 7.3% | 1.5 | -43.1% | L1 infrastructure |
| 9 | **AAVE** | 7.2% | 1.9 | -38.9% | DeFi (lending fees) |
| 10 | **ADA** | 6.9% | 1.4 | -37.8% | L1 infrastructure |
| 11 | **DOGE** | 6.9% | 1.1 | -37.6% | Meme (excluded) |
| 12 | **XRP** | 6.6% | 1.1 | -39.5% | Payments utility |
| 13 | **SOL** | 6.6% | 1.2 | -41.1% | L1 infrastructure |
| 14 | **ATOM** | 6.6% | 1.9 | -17.2% | L0 infrastructure |
| 15 | **HBAR** | 6.5% | 1.2 | -35.8% | Enterprise utility |
| 16 | **AVAX** | 6.3% | 1.1 | -40.0% | L1 infrastructure |
| 17 | **LINK** | 6.1% | 1.2 | -40.3% | Oracle utility |
| 18 | **ETH** | 5.9% | 0.9 | -41.5% | L1 base layer |
| 19 | **RUNE** | 5.7% | 0.6 | -34.5% | DeFi (cross-chain) |
| 20 | **LTC** | 5.7% | 1.2 | -38.0% | Payments utility |
| 21 | **BTC** | 4.2% | 0.9 | -30.1% | Store of value |

**Key metric: "Cycles/Week"** = number of 1.5%+ reversals per week. This directly maps to V14 DCA TP opportunities. Higher = more profit cycles.

## 2022 Bear Market Reference (Jun-Dec 2022)

| Coin | Avg Daily Range | Max DD | Price Range |
|------|-----------------|--------|-------------|
| SOL | 8.9% | -79.3% | 383% |
| LINK | 7.8% | -41.3% | 70% |
| HBAR | 6.5% | -62.3% | 165% |
| XRP | 6.3% | -37.4% | 73% |
| ETH | 6.6% | -46.5% | 99% |
| BTC | 4.5% | -49.7% | 99% |

**Lesson:** SOL had the highest volatility but also the deepest DD (FTX collapse). LINK and XRP had strong volatility with manageable drawdowns.

## Bear Market Coin Categories

### Tier 1: Revenue-Generating DeFi (Best for V14)
These protocols generate real fees regardless of market direction — trading volume creates volatility, and volatility is exactly what V14 needs.

**AAVE** — Lending protocol. Earns fees on borrows/liquidations. Bear markets drive liquidations → more activity → more volatility. TVL held relatively well in current bear (-12% vs market -40%). **7.2% daily range, 1.9 cycles/wk.**

**UNI** — DEX fees from Uniswap. Every swap generates fees. Bear market panic selling = high DEX volume = high fee revenue. **8.1% daily range, 1.8 cycles/wk.** Highest cycle frequency among DeFi.

**CRV** — Curve AMM. Core DeFi infrastructure for stablecoin swaps. Even in bears, stablecoin volume stays high. **7.6% daily range, 1.8 cycles/wk.**

**MKR** — MakerDAO. Generates revenue from DAI stability fees. One of the only DeFi tokens with consistent protocol revenue. Available on Hyperliquid perps. Lower volatility but extremely resilient.

**COMP** — Compound lending. Similar thesis to AAVE (lending + liquidations). Available on Hyperliquid.

### Tier 2: Infrastructure Utility (Survive + Volatile)
These have real utility that persists through bears, with enough volatility for DCA cycling.

**INJ** — Injective. Built for DeFi trading infrastructure. **8.5% daily range** — highest volatility of any quality coin right now. High risk but ideal for aggressive DCA.

**LINK** — Chainlink oracles. Used by every DeFi protocol. Revenue from data feeds is somewhat market-independent. Proven 2022 bear survivor. **6.1% range** but extremely reliable.

**ATOM** — Cosmos IBC. Only **-17.2% DD from Jan 1** — most resilient coin in the current bear. Still has **1.9 cycles/wk**. Interesting outlier.

**GRT** — The Graph. Data indexing for blockchain queries. Usage correlates with developer activity, not just price. **7.4% range, 2.0 cycles/wk** — highest cycle frequency of any coin. Not on Hyperliquid perps though.

**FIL** — Filecoin. Storage utility independent of market sentiment. **7.7% range, 1.3 cycles/wk.**

### Tier 3: L1s with Developer Ecosystems
Strong ecosystems mean continued activity even in bears.

**SUI** — Fast L1, gaining developer traction. **7.8% daily range, 1.5 cycles/wk.** High volatility.

**NEAR** — Already in our paper bot. Solid utility, good volatility profile.

**SOL** — Dominant L1 but correlated with broad market. Historically very volatile in bears (8.9% in 2022).

**AVAX** — Institutional focus (subnets). Moderate volatility.

### Tier 4: Avoid in Bear
- **BTC** — Too low volatility (4.2%) for DCA grid to cycle profitably
- **ETH** — Same issue (5.9%), though better than BTC
- **LTC** — Low vol, low cycles, mostly just follows BTC
- **RUNE** — Low cycle frequency (0.6/wk), long holds between reversals
- **Memecoins** — High vol but zero fundamentals, death spiral risk

## Recommended Bear Market Portfolio for V14

### Aggressive (maximize cycles):
| Coin | Why | Daily Range | Cycles/wk | On HL? |
|------|-----|-------------|-----------|--------|
| INJ | Highest vol, DeFi trading infra | 8.5% | 1.6 | ✅ |
| UNI | DEX fee revenue, high cycles | 8.1% | 1.8 | ✅ |
| CRV | AMM fees, stablecoin volume | 7.6% | 1.8 | ✅ |
| AAVE | Lending fees + liquidations | 7.2% | 1.9 | ✅ |

### Balanced (vol + resilience):
| Coin | Why | Daily Range | Cycles/wk | On HL? |
|------|-----|-------------|-----------|--------|
| AAVE | Revenue + bear resilience | 7.2% | 1.9 | ✅ |
| ATOM | Lowest DD (-17%), high cycles | 6.6% | 1.9 | ✅ |
| LINK | Proven bear survivor, oracle utility | 6.1% | 1.2 | ✅ |
| UNI | Fee revenue + high cycles | 8.1% | 1.8 | ✅ |

### Conservative (survive anything):
| Coin | Why | Daily Range | Cycles/wk | On HL? |
|------|-----|-------------|-----------|--------|
| LINK | Oracle monopoly, survived every bear | 6.1% | 1.2 | ✅ |
| ATOM | Remarkably stable this bear | 6.6% | 1.9 | ✅ |
| XRP | Regulatory clarity, payments utility | 6.6% | 1.1 | ✅ |
| HBAR | Enterprise adoption, steady | 6.5% | 1.2 | ✅ |

## Key Insight: DeFi Revenue Tokens Are the Bear Market Play

The thesis: **protocols that generate fees from trading activity create a positive feedback loop with V14**:
- Bear market → panic selling → high DEX/lending volume → protocol revenue stays up → token has floor
- High trading volume → price volatility → V14 DCA grid cycles more frequently
- Revenue generation → token doesn't go to zero → V14 positions are safer

This is why AAVE, UNI, CRV, and COMP stand out. They're not just surviving the bear — they're *fueled* by bear market activity (liquidations, panic swaps, flight-to-stablecoins routing through Curve).

## ATOM Anomaly Worth Noting

ATOM is only down 17.2% from Jan 1 while everything else is down 35-47%. This could mean:
- It already bottomed earlier and is in accumulation (bullish for V14 longs)
- OR it hasn't capitulated yet and has further to fall

Its 1.9 cycles/wk is excellent regardless. Worth including in any portfolio.

## Availability on Hyperliquid

All recommended coins confirmed available as USDC perps on Hyperliquid:
✅ INJ, UNI, CRV, AAVE, ATOM, LINK, COMP, MKR, SUI, FIL, NEAR, SOL, DOT, PENDLE, LDO, SNX, DYDX, ENS

**Not on Hyperliquid:** GRT (shame — 2.0 cycles/wk is highest)

## Additional Coins to Consider

From Hyperliquid's perp list that we haven't analyzed but fit the utility/DeFi thesis:
- **PENDLE** — DeFi yield trading, novel utility
- **LDO** — Lido staking, ETH staking demand persists in bears
- **SNX** — Synthetix, derivatives protocol
- **DYDX** — Decentralized perps exchange
- **ENS** — Ethereum naming, steady utility demand
- **EIGEN** — EigenLayer restaking

These would need candle data backfilled for volatility analysis.
