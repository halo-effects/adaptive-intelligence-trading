# Token Frameworks Reference

_Basis uses three distinct token types, all built on elastic supply (100% mint-on-buy, burn-on-sell). Zero pre-minting, zero insider allocations — mathematically impossible to rug._

---

## Stable+ Tokens

### What They Are
Stable+ tokens have a price that **only ever goes up**. Built on a bonding curve where every buy mints new tokens and every sell burns them, injecting fees into liquidity. The result: the price curve is one-directional — selling pushes the price UP, not down.

### How They Work
- **Elastic supply:** Tokens are minted on buy, burned on sell
- **Fee injection on sell:** Sell transactions inject fees into the liquidity pool → increases price
- **No counterparty:** No LP to drain, no external liquidity needed
- **Vault-compatible:** STASIS (the system Stable+) can be staked in the wSTASIS vault for yield

### Key Parameters
| Parameter | Description |
|-----------|-------------|
| `initial_price` | Starting price on bonding curve |
| `fee_rate` | % of each trade injected back as liquidity |
| `surge_tax` | Optional: temporarily increase fees during hype (creator-controlled, on-chain) |
| `liquid_vesting_enabled` | Whether bonding phase buys go into vesting |

### Use Cases for Agents
- **STASIS:** System base token. All other tokens pair against STASIS. Stake in vault → earn yield → borrow USDC via wSTASIS.
- **Predict+ tokens:** Each prediction market is a fresh Stable+ token — starts at max price impact (low liquidity), agents profit from early volume.
- **Agent earnings tokens:** Agent creators earn 20% of all trading fees forever.

### Leverage on Stable+
- Floor price = spot price always (floor can never be below current price)
- **36x leverage permanently available** — calculated against floor, which equals spot
- Leveraged tokens held in leverage contract, cannot be used as loan collateral
- No price liquidation — floor can never decrease

---

## Floor+ Tokens

### What They Are
Floor+ tokens combine the Stable+ anti-dump mechanism with **customizable price stability**. The creator sets a "stability dial" (50%–90%) that controls how much of the bonding curve is stabilized vs. volatile. Once set, it's **immutable** — no bait-and-switch.

### How They Work
- **Modified constant product formula** with stability dial applied
- Floor price rises over time with trading volume
- Effect strongest at low market cap, diminishes at scale (natural progression)
- Stability dial is set at launch and cannot be changed afterward (trust signal)

### Key Parameters
| Parameter | Description | Range |
|-----------|-------------|-------|
| `stability_dial` | % of price movement that is stabilized | 50%–90% |
| `initial_price` | Starting bonding curve price | Any |
| `fee_rate` | Trading fee % | Configurable |
| `surge_tax` | Optional fee surge during hype cycles | On/off |
| `liquid_vesting` | Auto-vest early buyer tokens | Configurable |
| `vesting_duration` | How long bonding phase tokens vest | Days |

### Stability Dial in Practice

| Setting | Behavior | Best For |
|---------|----------|---------|
| 50% stability | More volatile, larger price swings | Speculative trading tokens |
| 70% stability | Balanced — tradeable + protected | Agent community tokens |
| 90% stability | Very stable floor, slower appreciation | Long-term treasury tokens |

### Leverage on Floor+
- Leverage is highest **at/just after launch** when floor ≈ spot price
- As trading volume pushes spot above floor, available leverage naturally decreases
- Self-regulating: early buyers get maximum leverage; mature tokens have lower leverage
- **Agent strategy:** Buy Floor+ early when leverage is highest, before volume builds

### Liquid Vesting (Floor+ and all types)
- Creator can require bonding phase buys to auto-vest
- Whitelisted wallets that buy early **cannot dump** — tokens go straight into vesting
- Vested holders can take **floor-price loans** against locked tokens
- Capital locked but not dead — holders get USDC without selling, no sell pressure
- **Agent use case:** Get whitelisted → buy during bonding → tokens vest → immediately borrow against floor → redeploy USDC → never idle

---

## Predict+ Tokens

### What They Are
Predict+ tokens are **Stable+ tokens used as prediction market shares**. Each prediction market deploys a fresh Stable+ token for each outcome. Tokens serve multiple functions simultaneously: tradeable asset, bet share, loan collateral.

### How They Work
1. **Market creation:** Creator deploys prediction event with N outcomes, each gets a Predict+ token
2. **Price action:** Token price rises with trading volume (same as Stable+)
3. **Betting:** Participants buy outcome tokens to bet; winning outcome gets entire losing pool
4. **Resolution:** Verified resolver submits winning outcome on-chain
5. **Post-resolution:** Token holders sell → burning fees inject back → price goes UP during sell wave
6. **Exit:** Patient sellers who wait through the frenzy exit at higher prices

### Key Mechanics

**Winner-Takes-All Pool:**
- Example: Outcome A: $50K | Outcome B: $30K | Outcome C: $10K
- Outcome C wins → C holders split the $80K losing pool
- Potential payout: 8x+ vs. maximum ~1.67x on Polymarket (binary)
- Multi-outcome markets = dramatically higher underdog payouts

**Fresh Bonding Curve Advantage:**
- Every new prediction market = fresh Stable+ at minimum liquidity
- Maximum price impact from early volume → maximum early appreciation
- Infinite supply of new markets = no diminishing returns (unlike STASIS at scale)

**Trader-to-Bettor Pot:**
- % of Predict+ trading fees → general pot paid to winning outcome
- Doesn't affect token prices — pure bonus on top of betting pool
- More traders → bigger pot → attracts bettors → more hype → more traders (flywheel)

**Post-Resolution Sell Dynamics (counterintuitive):**
- After resolution, token holders sell → tokens burned → selling fees inject into liquidity → **price goes UP**
- Opposite of every other platform (mass sell = crash elsewhere)
- **Strategy:** Wait through the sell wave, exit last at the highest price

### Key Parameters
| Parameter | Description |
|-----------|-------------|
| `outcomes` | List of outcome names (e.g., ["Yes", "No"] or ["Team A", "Team B", "Draw"]) |
| `resolution_date` | Unix timestamp when market resolves |
| `resolution_source` | Oracle/data source for resolution |
| `creator_fee` | % of trading fees to creator (standard: 20%) |
| `min_participants` | Minimum unique participants to qualify (default: 5, for airdrop points) |

### Two Strategy Paths

**Path A — Leverage Play (max price exposure):**
1. Create market → earn 20% creator fees
2. Buy Predict+ tokens with 36x leverage (floor = spot, max leverage always available)
3. Tokens held in leverage contract (cannot be used as loan collateral)
4. Ride pure price appreciation from trading volume
5. Optionally bet on outcome with separate USDC

**Path B — Loan Play (multi-income):**
1. Create market → earn 20% creator fees
2. Buy Predict+ tokens outright (no leverage)
3. Borrow USDC at 100% LTV against Predict+ tokens
4. Bet on outcome with borrowed USDC → winner takes entire losing pool
5. Token appreciates + creator fees + bet winnings = 3 income streams

_Note: Leverage and loans are separate paths — not stackable. Leveraged tokens cannot be used as loan collateral._

---

## STASIS — The System Token

### What It Is
STASIS is the system-level Stable+ token that serves as the **base pair for all other tokens** on Basis. All DEX pairs route through STASIS. It's the liquidity spine of the platform.

### Why It Matters for Agents
| Feature | Detail |
|---------|--------|
| Base pair | All tokens trade against STASIS |
| wSTASIS vault | Stake STASIS → earn platform fee yield |
| 100% LTV loans | Borrow USDC against wSTASIS (stays in vault) |
| Refinancing | Auto-refinance as wSTASIS appreciates → more USDC |
| Four functions | Yield-earning + collateral + appreciation + USDC liquidity simultaneously |

### wSTASIS Vault Mechanics
- Stake STASIS → receive wSTASIS (wrapped ratio token)
- Platform fees injected as STASIS into vault → STASIS:wSTASIS ratio increases
- Only vault participants earn fees (passive STASIS holders do not)
- wSTASIS can be used as 100% LTV loan collateral **without leaving the vault**
- As wSTASIS appreciates, refinance loans for additional USDC — still earning, still in vault
- Interest rate: very low single-digit APR (exact TBC)
- **Agent use case:** Set and forget treasury — park STASIS in vault, auto-refinance when threshold hit, deploy USDC into active strategies

---

## Lending — Universal to All Types

| Feature | Detail |
|---------|--------|
| LTV | 100% against floor price |
| Liquidation | Time only (loan expiry) — **never price depreciation** |
| Collateral | Tokens held by loan contract, cannot be sold during loan term |
| Liquidity source | Token's own internal liquidity — no external LPs, no counterparty |
| Interest | Low single-digit APR |
| Management | One variable: loan expiry timer. No collateral ratios, no oracle feeds. |

_Agents only need to track time. Compare to traditional DeFi: collateral ratios, liquidation prices, oracle feeds, gas spikes..._

---

## BASIS vs STASIS — Don't Confuse These

| Token | Type | Purpose |
|-------|------|---------|
| **BASIS** | Platform utility/presale token | Sold to investors. Stake for 90% platform revenue share. |
| **STASIS** | System Stable+ | Platform liquidity spine. Stake in vault → wSTASIS → earn + lend. |

BASIS is volatile, traded on external DEXs/CEXs. STASIS is Stable+ with internal liquidity — that's where 100% LTV loans and the Vault live. Do not mix them up.
