# Token Types Deep Dive

**What this covers:** Complete reference for the three token types on Basis: Stable+, Floor+, and Predict+. Every mechanic, every parameter, every edge case -- extracted from the canonical SDK documentation.

---

## Universal Mechanics (All Token Types)

### Elastic Supply

Every token on Basis uses **elastic supply**: tokens are minted on buy and burned on sell. There is no pre-minted supply. Zero insider allocations. 100% of circulating tokens were purchased at market price. This makes rug pulls structurally impossible -- there is nothing to dump.

Burning IS selling on elastic supply tokens. When a loan expires and collateral is "burned to cover debt," that's mechanically identical to selling.

### The Factory

All tokens tradeable on the Basis DEX originate from the **Basis Factory contract** (`ATokenFactory`). No external token imports, no arbitrary ERC-20 listings. If it trades on Basis, Basis created it.

- No honeypots -- every token uses the same audited Factory contract
- No malicious contracts -- creators don't write the contract; the Factory enforces the rules
- No rug pulls via code -- elastic supply, protocol-managed liquidity
- Every token is structurally safe to trade

The Factory is the only door in, and it only creates safe tokens.

### Token Creation Parameters

| Parameter | Required | Range | Description |
|-----------|----------|-------|-------------|
| `symbol` | Yes | -- | Token ticker. **Must be CAPITALISED.** |
| `name` | Yes | -- | Token full name |
| `hybridMultiplier` | Yes | 1-100 | Controls token type. **1-90 = Floor+.** **100 = Stable+.** Do NOT use 91-99. |
| `startLP` | Yes | 100-10,000 | Starting virtual liquidity. Sets the dollar scale of price movement. Free -- costs nothing. |
| `frozen` | No | bool | Start frozen (only whitelisted wallets can trade until `disableFreeze()`) |
| `usdbForBonding` | No | 0-150,000 | USDB volume threshold defining the reward phase. Must be >= 1 if `frozen=true`. |
| `autoVest` | No | bool | Auto-vest tokens the creator buys (NOT pre-minting -- creator must buy like anyone else) |
| `autoVestDuration` | No | days | Required when `autoVest` is true |
| `gradualAutovest` | No | bool | Linear unlock (true) vs cliff unlock (false) |

### Understanding startLP

startLP is a **scaling factor** controlling how much capital moves the price. It does NOT affect percentage change -- only absolute dollar amounts. Think of it as the "zoom level" on the price chart.

A $100 buy into a 1,000 LP token has the **same percentage impact** as a $1,000 buy into a 10,000 LP token.

| startLP | $100 buy moves price | $1,000 buy moves price | Best for |
|---------|---------------------|----------------------|----------|
| 100 | Very large move | Extreme move | Micro-cap, tiny wallets |
| 1,000 | ~$0.10 | ~$1.00 | Most tokens (default) |
| 5,000 | ~$0.02 | ~$0.20 | Larger expected volume |
| 10,000 | ~$0.01 | ~$0.10 | High-volume, smooth price |

Lower startLP = more visible price action for the same trade volume. Higher startLP = more capital needed to move the price.

### AMM Pricing

Basis uses a **modified constant-product AMM** (similar to Uniswap V2's `x * y = k`), with a critical modification: the `hybridMultiplier` controls how much of each sell's value is retained in the pool versus returned to the seller.

- **Buys** work like a standard AMM -- send USDB, receive tokens, price increases along the curve
- **Sells** are where Basis diverges -- a portion of the sell value stays in the pool (slippage retention)

How `startLP` initializes reserves:
1. Converts the dollar value to STASIS at current STASIS price (e.g., $1,000 -> 837 STASIS at $1.19/STASIS)
2. Sets the token side so starting price = $1 per token (e.g., 837 STASIS : 1,000 tokens)
3. Creates a standard AMM pair, with `hybridMultiplier` modifying how sells affect reserves going forward

### Swap Routing

All trades route through STASIS. No direct token-to-token swaps.

- Buying STASIS: `USDB -> STASIS` (2-hop)
- Buying a factory token: `USDB -> STASIS -> Token` (3-hop)
- Selling reverses the path

### Fee Distribution (Standard Tokens)

For standard (non-Predict+) tokens, each trade's fee is distributed:

| Recipient | Share |
|-----------|-------|
| Creator (dev fee) | 20% |
| Staking yield (vault) | 16% |
| Reward phase buyers | 4% |
| Platform treasury | 60% |

The creator earns 20% of every single trade on their token -- forever.

### Reward Phase

The reward phase is the initial period where early buyers earn reward shares (claimable via `claimRewards()`). Controlled by the `usdbForBonding` parameter at creation.

- Tokens are tradeable on the DEX from the moment of creation -- the same AMM formula runs forever
- The reward phase lasts until cumulative trading volume hits the `usdbForBonding` threshold
- Once the threshold is hit, `hasBonded` flips to true and the reward phase ends
- After the reward phase, trading continues normally -- new buys simply no longer earn reward shares
- Reward phase buys also earn boosted airdrop points

**Calibration:** Set 0 for no reward phase. Set it low and buy it yourself to capture all shares. Set it higher if you have a community that will participate early.

### Anti-Rug Design

- 100% elastic supply -- every token in circulation was purchased at market price
- Zero pre-minting, zero insider allocations
- It is mathematically impossible for creators to dump insider tokens
- Creator revenue comes from fees, not tokens

---

## Stable+ (Up-Only)

### Core Mechanic

**Price can only go up.** This is NOT a "rising floor" -- the price itself never decreases. Tokens are minted on buy and burned on sell. Price appreciation comes from **slippage retention**: the value "lost" to price impact on each trade stays in the liquidity pool, permanently increasing the liquidity-to-supply ratio.

- `hybridMultiplier` = **100** (exactly)
- At multiplier=100: **100% retention** -- ALL sell value stays in the pool. Price never drops.
- On-chain: `hybridMultiplier()` returns `100n` for Stable+ and Predict+ tokens

### Trading Fee

| Action | Fee |
|--------|-----|
| Buy/sell Stable+ (incl. STASIS) | **0.5% per swap** |
| Raw round-trip | ~1.0% + slippage |

Creator gets 0.1% (20% of 0.5% gross fee) per trade.

### Surge Tax

Max surge tax on Stable+ (hybridMultiplier=100): **0.5% (50 basis points)**

Max total fee with surge active: 1.0%

### Leverage

- **20-36x leverage** available (varies by pool depth and position size)
- Loans at **100% LTV at spot price** (floor = spot for Stable+, so you borrow the full market value)
- **No price liquidation** -- floor = spot, floor never decreases, nothing to liquidate against
- Only risk is time-based loan expiry
- Smaller positions on deep pools = more loops = higher leverage
- Larger positions = fewer effective loops = lower leverage due to price impact

### The Velocity Thesis

**Stable+ tokens thrive on velocity, not holding.** The more the token cycles through buy -> use -> sell, the better it performs. Each cycle leaves slippage residue that permanently raises the price.

The tradeoff: price appreciation slows as supply grows. This makes Stable+ tokens best suited for **cyclical use cases** where tokens are regularly bought, used, and sold/burned -- keeping supply low and the appreciation engine running.

### Ideal Use Cases

- **Online casinos / gambling** -- players buy tokens to play, house burns on wins, winners sell. Constant cycle keeps supply low and price slowly appreciating.
- **Loyalty/reward tokens** -- earn, spend at merchants, earn again
- **Access tokens** -- buy to use a service, token burned on use
- **In-game currencies** -- buy, spend in-game, tokens burned on use
- **Tipping/creator tokens** -- fans buy, tip creator, creator sells

### STASIS: The Canonical Stable+ Token

**STASIS** is the ecosystem token and the canonical Stable+ token.

- Every trade routes through STASIS (all swap paths include STASIS)
- Platform fees flow to the STASIS vault, increasing its value
- Holding STASIS = holding a share of platform activity
- STASIS price can only go up from slippage retention
- Can be staked in the vault (wrap to wSTASIS) for yield from ALL platform trading fees
- Can be used as collateral for loans at 100% LTV

### Loan Expiry on Stable+

When a leverage position or loan expires without repayment:
- Tokens are burned to cover the debt (burning IS selling on elastic supply tokens)
- Since Stable+ tokens only go up, the debt is **always** covered
- Remaining tokens are claimable via `claimLiquidation(hubId)`

---

## Floor+ (Rising Floor)

### Core Mechanic

Prices go up on buys AND down on sells -- creating real trading opportunity. Like Stable+, tokens are minted on buy and burned on sell. But unlike Stable+, sells DO return value to the seller (partially).

- `hybridMultiplier` = **1-90**
- The multiplier controls the **stability dial**: how much of each sell's value is retained by the pool vs returned to the seller
- **1 = most volatile** (50% stabilized vs standard AMM) -- most value returns to seller, weakest floor growth
- **90 = most stable** (near Stable+ behavior) -- most value retained by pool, strongest floor growth
- The dapp UI shows this as a 0%-100% stability slider mapping to values 1-90

### The Stability Dial (hybridMultiplier)

**hybridMultiplier price impact** (tested on-chain, startLP=1000):

| hybridMultiplier | Price increase per LP-equivalent buy | Floor growth |
|-----------------|-------------------------------------|-------------|
| 1 (most volatile) | +$1.00 | Weakest |
| 15 | +$0.83 | Low |
| 30 | +$0.69 | Moderate |
| 45 | +$0.54 | Moderate-high |
| 60 | +$0.39 | High |
| 90 (most stable) | +$0.11 | Very high |
| 100 (Stable+) | price increases due to full retention | Maximum |

An LP-equivalent buy = a buy equal to the startLP value (e.g., $1,000 on a startLP=1000 token).

### How the Floor Works

If all holders sold every token in circulation, the price would drop -- but NOT all the way back to the launch price. This lowest possible price is the **floor price**. It comes from liquidity retained in the AMM due to price impact from trading -- each buy-and-sell cycle leaves a residue that permanently raises the floor.

- Higher hybridMultiplier = more of each trade's price impact is retained = floor rises faster
- The floor price **never decreases** -- it can only go up with trading volume
- Even this is secondary to the reduced sell impact -- but it means the worst-case price only improves with activity

### Trading Fee

| Action | Fee |
|--------|-----|
| Buy/sell Floor+ | **1.5% per swap** |
| Raw round-trip | ~3.0% + slippage |

Creator gets 0.3% (20% of 1.5% gross fee) per trade.

### Surge Tax Table

The surge tax is a temporary extra fee that **token creators manually activate**. Maximum allowed surge depends on hybridMultiplier:

| hybridMultiplier | Max Surge Tax | Max Total Fee (base + surge) |
|-----------------|---------------|------------------------------|
| 1 (most volatile) | 15% (1500 BP) | 16.5% |
| 45 (mid) | 8% (800 BP) | 9.5% |
| 90 (high stability) | 1% (100 BP) | 2.5% |

Surge constraints:
- Duration: minimum 1 hour (linear decay from startRate to endRate)
- Quota: maximum 7 days of surge per rolling 30-day window
- Extra fee goes primarily to the creator (all surge basis points added to dev portion)
- The more stable the token, the lower the maximum allowed surge

### The Sell Absorption Advantage

**Sells don't hit as hard.** A whale dumping the same dollar amount on a traditional AMM token would crater the price -- on Floor+, the hybrid AMM absorbs far more of the sell pressure. The price dips, not crashes.

**Why this matters:** Tokens don't die from lack of buying -- they die from panic selling. On traditional launch platforms, a single large sell triggers a cascade: price craters -> holders panic -> everyone sells -> token dead in hours. Floor+ breaks this cycle. The same sell creates a smaller dip, which looks like a buying opportunity instead of a death spiral.

### The Paradox: Slower Gains, Better Survival

Floor+ tokens go up slower per dollar of buy volume -- but because they survive sells that would kill traditional tokens, they have the potential to go higher overall.

**You sacrifice the spike to kill the crash, and killing the crash is what actually matters.**

There is nothing like this in the market.

### Leverage on Floor+

- Loans are valued at **floor price**, not spot price
- 100% LTV at floor price (floor < spot, so you borrow less than market value -- the gap is your safety margin)
- **No price liquidation** -- floor never decreases
- Effective leverage is **highest at launch** (when floor ~ spot price) and after large sell events (when spot drops closer to floor)
- The further spot is above floor, the less you can borrow per loop -- effective leverage drops sharply while the 2% origination fee per loop stays the same

**Best leverage play for Floor+:** Leverage at launch when floor ~ spot gives highest effective leverage. Get a big bag at launch price with minimal capital.

### Loan Expiry on Floor+

When a leverage position or loan expires:
- Tokens are sold on market to cover the debt
- Since the debt is based on floor price, the number of tokens sold is usually small -- especially if the token has appreciated
- Example: $10 leveraged into $200 bag (debt ~ $200). Token price goes 5x, bag now worth $1,000. On expiry, only ~$200 of tokens sold to cover debt. You claim the remaining ~$800.
- Worst case (no price increase): entire bag sold to repay debt, nothing left to claim. But you never owe anything beyond your collateral.

---

## Predict+ (Prediction Market Tokens)

### Core Identity

Each prediction market creates one **Predict+ token** -- a **market token** that is a Stable+ subtype with `hybridMultiplier = 100`. It has a short, defined lifecycle tied to the market's duration.

**Critical distinction:**
- **Predict+ tokens are MARKET tokens** -- they represent the market itself, NOT individual outcomes
- **Outcome shares are separate** -- buying outcome shares (betting) is a completely different action from buying the Predict+ token
- Buying the Predict+ token is trading for appreciation; buying outcome shares is betting on results

### Why Predict+ Is the Ideal Stable+ Use Case

The Predict+ token launches fresh with zero supply, gets the strongest price appreciation during the low-supply early period, and resolves before it ever hits the supply wall that long-lived Stable+ tokens eventually face.

This is the **ideal use case for Stable+ mechanics**: short lifecycle, high volume, natural resolution point.

### Trading Fee

| Action | Fee |
|--------|-----|
| Buy/sell Predict+ | **1.5% per swap** (gross) |
| Raw round-trip | ~3.0% + slippage |

**But the fee distribution is different from other token types.**

### Predict+ Fee Breakdown (per $100 trade)

| Component | Amount | Destination |
|-----------|--------|-------------|
| **Prediction ecosystem portion** | **$1.00** (1% of trade) | Fed back into the market |
| - Resolver bounty pool | $0.05 (5% of ecosystem portion) | Rewards for resolvers |
| - General pot | $0.95 (95% of ecosystem portion) | Distributed to winning outcome holders at resolution |
| **Net platform fee** | **$0.50** (0.5% of trade) | Standard platform distribution |
| - Staking yield (16%) | $0.08 | Vault holders |
| - Creator dev fee (20%) | $0.10 | Market creator |
| - Reward phase buyers (4%) | $0.02 | Early supporters |
| - Platform treasury (60%) | $0.30 | Platform operations |

**Key insight:** Every trade on a prediction market makes the winning pot bigger. The creator earns **0.1% of trade value** on Predict+ (compared to 0.3% on Floor+ tokens) because the 20% dev fee is calculated on the net 0.5%, not the gross 1.5%.

### No Surge Tax on Predict+

The surge mechanism is **disabled entirely** for prediction markets. Max fee is always the base 1.5%.

### Leverage on Predict+

- Same as Stable+: **100% LTV at spot price** (floor = spot)
- 20-36x leverage available
- No price liquidation
- **Best leverage play:** Leverage buy at market launch, hold through activity, exit after post-resolution sell wave for maximum returns

### The General Pot

95% of the prediction ecosystem portion of trading fees (0.95% per trade) accumulates in a **general pot** over the market's entire lifetime, from every trade across every outcome. On resolution, this merges with all outcome pools into one big pot.

This benefits all participants -- especially latecomers who enter at high probability -- by growing the total pot above what outcome pools alone would deliver.

### Resolution Mechanics

```
Market ends -> Propose outcome (5 USDB bond) -> Challenge period (30 min*)
  |-- No dispute -> finalizeUncontested() -> Proposer gets bond + full bounty -> Winners redeem
  |-- Disputed (5 USDB bond) -> Voting period (30 min*) -> Voters decide -> Finalize -> Winners redeem
      |-- EARLY outcome wins -> Round resets, fresh proposal cycle
```

*Testing values -- production targets: 2-hour challenge period, 24-hour voting period.*

**Special outcomes:**

| Outcome | ID | Who Can Propose | Effect |
|---------|----|----------------|--------|
| Normal | 0-252 | Anyone | Standard resolution |
| EARLY | 253 | Only the disputer | Market resets, fresh proposal cycle |
| INVALID | 254 | Anyone | Proportional refund to all participants |
| UNRESOLVED | 255 | Internal | Default state before any proposal |

**Bond outcomes:**
- Correct proposer/disputer gets BOTH bonds (theirs + opponent's)
- Neither correct -> insurance pool gets both
- Uncontested -> proposer gets bond back + 100% of bounty pool

**Voting:**
- Must stake >= 5 tokens of any active ecosystem token
- One-staker-one-vote (staking above minimum gives no extra power)
- 70% supermajority required
- Quorum: `bountyPool / (50 * $1)`, clamped between 2 and 100

### Post-Resolution Selling

On Basis, mass selling after resolution pushes the price **UP** (selling burns tokens -> slippage stays in pool -> price rises). Patient sellers who wait through the sell wave exit at the **highest** price.

**Avoid selling during the active trading phase.** You're exiting before maximum volume has accumulated. The optimal exit is **after market resolution**, when the post-resolution sell wave pushes the price to its peak. Patience is rewarded structurally.

### Predict+ Token vs Outcome Shares

| Aspect | Predict+ Token | Outcome Shares |
|--------|---------------|----------------|
| What it represents | The market itself | A bet on a specific outcome |
| Price mechanic | Stable+ (up-only) | AMM-priced per outcome |
| Risk | Zero outcome risk -- profits from volume | Binary -- win the bet or lose |
| Payout | Sell on market (appreciation) | Proportional share of one big pot |
| Can be leveraged | Yes (100% LTV, no liquidation) | No |
| Can be used as collateral | Yes | No |
| Can be sold on order book | No (AMM only) | Yes |

---

## Comparison Tables

### Fee Comparison

| Token Type | Trading Fee (per swap) | Round-Trip | Creator Earns | Surge Tax |
|-----------|----------------------|------------|---------------|-----------|
| Stable+ (incl. STASIS) | 0.5% | ~1.0% | 0.1% (20% of 0.5%) | Max 0.5% (50 BP) |
| Floor+ | 1.5% | ~3.0% | 0.3% (20% of 1.5%) | Max 1-15% (varies by multiplier) |
| Predict+ | 1.5% (gross) | ~3.0% | 0.1% (20% of net 0.5%) | Disabled |

### hybridMultiplier Mapping

| Value | Token Type | Price Behavior | Fee |
|-------|-----------|---------------|-----|
| 1 | Floor+ (most volatile) | Up and down, weakest floor | 1.5% |
| 2-89 | Floor+ | Up and down, rising floor | 1.5% |
| 90 | Floor+ (most stable) | Up and down, near up-only behavior | 1.5% |
| 91-99 | **DO NOT USE** | Technically work, disallowed by convention | -- |
| 100 | Stable+ / Predict+ | Up-only | 0.5% (Stable+) / 1.5% gross (Predict+) |

### Leverage & LTV Comparison

| Token Type | LTV Basis | Effective LTV | Typical Leverage | Liquidation Risk |
|-----------|-----------|---------------|-----------------|-----------------|
| Stable+ | Spot price | 100% of market value | 20-36x | None (time-based expiry only) |
| Predict+ | Spot price | 100% of market value | 20-36x | None (time-based expiry only) |
| Floor+ | Floor price | 100% of floor (< spot) | Lower (gap reduces per-loop yield) | None (time-based expiry only) |

**No price liquidation on ANY token type.** Leverage is valued against the floor price, which never decreases. The only risk is time-based loan expiry.

### Surge Tax by Token Type

| hybridMultiplier | Max Surge Tax | Max Total Fee |
|-----------------|---------------|---------------|
| 1 (most volatile Floor+) | 15% (1500 BP) | 16.5% |
| 45 (mid Floor+) | 8% (800 BP) | 9.5% |
| 90 (high stability Floor+) | 1% (100 BP) | 2.5% |
| 100 (Stable+) | 0.5% (50 BP) | 1.0% |
| Predict+ | N/A -- disabled | 1.5% (base only) |

### Use Case Matrix

| Use Case | Best Token Type | Why |
|----------|----------------|-----|
| Ecosystem token | Stable+ (STASIS) | Every trade routes through it, fees compound |
| Casino / gambling | Stable+ | Velocity thesis -- constant buy/use/sell cycle |
| Community token | Floor+ | Real trading, sell absorption prevents death spirals |
| Meme token | Floor+ (low multiplier) | Volatile enough for speculation, floor prevents zero |
| Prediction market | Predict+ | Short lifecycle maximizes Stable+ appreciation |
| Loyalty / reward | Stable+ | Earn/spend cycle keeps supply low |
| Access / utility | Stable+ | Buy to use, burn on use, price rises |

---

## Edge Cases and Nuances

### Values 91-99

Technically work on-chain but are **disallowed by convention**. There's no practical difference between a 91 Floor+ and a Stable+. Pick 1-90 for Floor+ or exactly 100 for Stable+.

### Reading Token Type On-Chain

Every factory token has a public `hybridMultiplier()` view function (no params, returns uint256):
- Returns 100 = Stable+ or Predict+
- Returns 1-90 = Floor+
- To distinguish Stable+ from Predict+, check if the token is associated with a prediction market

### Predict+ Is NOT an Outcome Token

This is a common misconception. The Predict+ token is the **market token** -- a Stable+ token that represents the market as a whole. Outcome shares are a completely separate mechanism purchased through a different contract. You can hold both simultaneously, or either independently.

### Post-Resolution Predict+ Price Dynamics

After a market resolves, the sell wave begins. On Stable+ mechanics:
1. Sellers burn tokens to exit
2. Slippage from those burns stays in the pool
3. Price goes UP as supply decreases and liquidity is retained
4. The LAST seller gets the BEST price

This is counterintuitive but mathematically guaranteed by the Stable+ mechanic.

### Floor+ Floor Price vs Spot Price

- **Spot price** = current market price (moves up and down)
- **Floor price** = minimum possible price if all tokens were sold (only goes up)
- Loans on Floor+ tokens are valued at floor price, not spot
- The gap between spot and floor is your "safety margin" on loans
- After large sell events, spot drops closer to floor -- this is when leverage is most effective

### HFT Does Not Work

Round-trip fees are ~1% for Stable+ and ~3% for Floor+/Predict+ -- before slippage. HFT strategies designed for 0.1% fee environments will bleed out on Basis.

### Elastic Supply and Burning = Selling

On elastic supply tokens, burning tokens is mechanically identical to selling. When a loan expires and collateral is "burned to cover debt," the AMM processes it as a sell. On Stable+ tokens, this burning-as-selling actually pushes the price up (slippage retention).

### The Flywheel

Every action generates fees. Those fees flow to:
1. The STASIS vault (yield for stakers)
2. Token developers (20% creator share)
3. Reward phase buyers (early supporter share)
4. Platform revenue

More activity -> more fees -> higher vault yield -> STASIS more attractive -> more staking -> more activity. Self-reinforcing.

### Standard AMM Arbitrage Assumptions Don't Apply

On Stable+ tokens, selling doesn't lower the price -- it literally can't. On Floor+ tokens, the floor rises with every sell. Model strategies accordingly. Traditional AMM arbitrage math will produce wrong results on Basis.
