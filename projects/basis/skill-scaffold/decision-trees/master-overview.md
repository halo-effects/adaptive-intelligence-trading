# Basis Agent Strategy — Master Overview
_The map of maps. How all decision trees connect._
_Last updated: 2026-03-16_

---

## The Three Trees

| Tree | File | Purpose |
|---|---|---|
| 🔮 **Prediction Markets** | `prediction-markets.md` | Scout → Create → Analyze → Position → Amplify → Manage → Exit |
| 🪙 **Token Launch** | `token-launch.md` | Ideate → Configure → Launch → Grow → Monetize → Sustain |
| 💰 **Capital Management** | `capital-management.md` | Source → Allocate → Deploy → Recycle → Optimize |
| 📣 **Growth & Promotion** | `growth-and-promotion.md` | Content → Distribute → Community → Product Loop → Scale |

**Capital Management is the connective tissue.** It's not a separate activity — it's the layer that runs underneath everything. Every prediction market position and every token position feeds into and out of the capital management tree via the loan layer.

---

## How The Trees Connect

```
┌──────────────────────────────────────────────────────────────────┐
│                        AGENT STARTS HERE                          │
│                                                                   │
│  "I have $X USDC and I want to earn on Basis. What do I do?"     │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  What's my edge?     │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
   ┌─────────────┐    ┌──────────────┐    ┌──────────────┐
   │ I know WHAT  │    │ I know WHO   │    │ I know HOW   │
   │ will happen  │    │ wants what   │    │ money works  │
   │              │    │              │    │              │
   │ → Prediction │    │ → Token      │    │ → Capital    │
   │   Markets    │    │   Launch     │    │   Management │
   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
          │                   │                   │
          │    ┌──────────────┼───────────────┐   │
          │    │              │               │   │
          ▼    ▼              ▼               ▼   ▼
   ┌─────────────────────────────────────────────────┐
   │              💰 LOAN LAYER (Bridge)              │
   │                                                   │
   │  Position in ANY tree → 100% LTV loan → USDC     │
   │  USDC → Deploy into ANY tree                      │
   │  Cost: 2.0% + 0.005%/day                         │
   └──────────────────────┬──────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │     ♻️ COMPOUND        │
              │   Recycle → Redeploy  │
              │   Every $ works 2-5x  │
              └───────────────────────┘
```

---

## Entry Points by Agent Type

### The Newcomer ($100–$500)
```
START → Buy STASIS → Stake in vault → Earn yield → Learn platform
      → When comfortable: try first prediction bet or token buy
      → When confident: create first token or prediction market
```
**Primary tree**: Capital Management → gradually expand to others

### The Predictor (has domain knowledge)
```
START → Scout Polymarket → Create market on Basis → Buy token + Bet
      → Loan against tokens → Bet more or create another market
      → Promote on social → Drive volume → Earn creator fees
```
**Primary tree**: Prediction Markets → Capital Management for recycling

### The Builder (wants to create)
```
START → Identify niche → Launch Floor+ token → Seed bonding
      → Build community → Drive volume → Harvest 20% fees
      → Loan against tokens → Launch next token
```
**Primary tree**: Token Launch → Capital Management for expansion

### The Optimizer (wants max returns)
```
START → Spread across vault + tokens + predictions
      → Loan loop everything → Maximize capital velocity
      → Refinance vault regularly → Points farm everything
      → Compound all earnings back into highest-yield positions
```
**Primary tree**: Capital Management with tentacles into both others

### The Creator Army (fleet of agents)
```
CONTROLLER → Deploy 10+ agents, each with different focus:
  Agent 1-3: Create prediction markets across categories
  Agent 4-6: Launch tokens across niches
  Agent 7-8: Capital management (loan loops, vault optimization)
  Agent 9: Points farming + social promotion
  Agent 10: Referral network builder
All → Cross-refer each other (10% lifetime points each)
```
**All trees**, orchestrated by a meta-strategy

---

## Cross-Tree Synergies

These are the highest-value moves that span multiple trees:

### 1. Prediction-Token Synergy
```
Create prediction market about a topic
  → Also launch a related community token
  → Prediction traders discover your token
  → Token traders discover your prediction market
  → Both earn you 20% creator fees
  → Volume on each drives volume on the other
```

### 2. Loan Bridge
```
Hold tokens in Tree A (predictions)
  → Loan against them (capital management)
  → Deploy USDC in Tree B (new token launch)
  → Now earning in both trees from same capital
  → Repeat: loan from Tree B → deploy in Tree A
```

### 3. Vault Anchor
```
Core position: STASIS → wSTASIS vault (safe, compounding)
  → Refinance periodically → extract USDC
  → Deploy USDC into prediction markets or token launches
  → Earn from: vault yield + creator fees + bet payouts
  → Reinvest earnings back to vault → compound
```

### 4. Volume Flywheel
```
Create token → Create prediction about token
  → Bet drives prediction volume (fees to you)
  → Prediction attention drives token volume (fees to you)
  → Social promote both → amplify
  → Volume begets volume (momentum)
```

### 5. Points Multiplier Stack
```
Every action earns points:
  Create market (300) + Create token (500) + Trade ($1=1pt)
  + Bet + Loan (200+1/day) + Vault (2/$1/day) + Social (50-150)
  + Referrals (10% lifetime)
  → ACS score = weighted sum → airdrop multiplier
  → Higher multiplier = more BASIS tokens at TGE
  → More BASIS = more staking rewards = more USDC
```

---

## Decision Framework: Which Tree First?

| If you have... | Start with... | Then expand to... |
|---|---|---|
| Strong opinions about events | Prediction Markets | Tokens (related themes) |
| An audience / community | Token Launch | Predictions (about your token) |
| Pure capital, no edge | Capital Management (vault) | Gradually explore both |
| Technical skills (agent dev) | Token Launch (multi-token) | Cross-tree optimization |
| Social reach | Token Launch + Amplify | Predictions + Referrals |
| Small capital (<$100) | Single prediction bet or token buy | Compound before diversifying |
| Large capital (>$10K) | Split across all three trees | Loan loops for max velocity |

---

## The Composability Principle

Nothing on Basis is a dead end. Every action creates optionality:

```
Buy token      → Can loan, leverage, sell, hold, stake
Take loan      → Can buy, bet, create, vault, reserve
Place bet      → Can win (USDC) → redeploy anywhere
Create token   → Earns fees (USDC) → redeploy anywhere
Stake vault    → Appreciates → refinance → USDC → redeploy
Earn points    → ACS score → airdrop → more capital
```

**The best agents don't follow a single path. They weave between trees, using loans as bridges and fees as fuel, compounding across every dimension simultaneously.**

---

## Skill Layer Reference

Every branch in every tree maps to atomic skills:

| Skill | Trees It Serves |
|---|---|
| `create-prediction.py` | Prediction Markets |
| `bet.py` | Prediction Markets |
| `create-token.py` | Token Launch |
| `trade.py` | All (buying/selling tokens) |
| `lend.py` | Capital Management (core) |
| `leverage.py` | All (amplification) |
| `vault.py` | Capital Management |
| `portfolio.py` | All (monitoring) |
| `points.py` | All (optimization layer) |
| `promote.py` | All (amplification) |
| `polymarket-scout` | Prediction Markets (discovery) |

---

## Strategy Layer Reference

Pre-packaged pathways (single paths through the trees):

### Prediction Strategies
| Strategy | Path |
|---|---|
| `polymarket-mirror` | Scout → Create on Basis → Position → Promote |
| `probability-arb` | Analyze differential → Bet where mispriced |
| `creator-fee-farm` | Create many markets → Promote → Harvest fees |
| `loan-bet-combo` | Buy token → Loan → Bet with USDC |
| `full-stack` | All paths simultaneously |

### Token Strategies
| Strategy | Path |
|---|---|
| `launch-and-promote` | Create Floor+/Stable+ → Drive volume |
| `bonding-sniper` | Early bonding entry → Reward shares forever |
| `loan-compound` | Buy → Loan → Buy more → Loop |
| `vault-yield` | STASIS → wSTASIS → Refinance loop |
| `token-portfolio` | Diversified positions across multiple tokens |

### Cross-Platform Strategies
| Strategy | Path |
|---|---|
| `capital-recycler` | Maximize capital velocity across all trees |
| `points-optimizer` | Max ACS score across all actions |
| `referral-network` | Onboard agents → Earn 10% lifetime points |

---

_Read the trees. Pick your path. Or forge your own. The platform rewards action — any action, everywhere._
