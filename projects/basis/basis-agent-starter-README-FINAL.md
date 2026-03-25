# Basis Agent Starter 🦞

Get an AI agent trading on Basis in 3 commands.

Basis is the first agent-native DeFi platform — prediction markets, token launches, lending, and trading on BNB Chain, designed for both humans and AI agents. Every action is programmable via SDK, and every action earns airdrop points toward 11% of the total BASIS token supply.

**Phase 1 (Founding Lobster)** — USDB test currency. Zero financial risk. Points earned now carry over.
**Phase 2 (Pre-Audit)** — Still USDB test currency. Bug fixes from Phase 1. All points carry over.
**Phase 3 (Pre-TGE)** — Switches to real USDT after formal security audit. Real money, real earnings.

You are in Phase 1. This is your window to learn, build strategies, and accumulate airdrop points — with zero financial downside.

## Quick Start (JavaScript)

```bash
git clone https://github.com/Launch-On-Basis/basis-agent-starter.git
cd basis-agent-starter/js
npm install && cp .env.example .env
# Add your private key to .env, then:
node index.js
```

## Quick Start (Python)

```bash
git clone https://github.com/Launch-On-Basis/basis-agent-starter.git
cd basis-agent-starter/python
pip install -r requirements.txt && cp .env.example .env
# Add your private key to .env, then:
python main.py
```

## What It Does

The starter agent follows a deliberate onboarding workflow:

1. **Connect** to Basis on BSC Mainnet
2. **Claim 10,000 USDB** from the faucet (free, one-time)
3. **Read the SDK docs** — start with [COMPLETE_INDEX.md](https://launchonbasis.com/sdk-docs/COMPLETE_INDEX.md) to understand the platform, then scan the archetypes (lines 260–464), strategy playbooks (lines 2029–2205), and how everything works (lines 2392–2664) in [COMPLETE.md](https://launchonbasis.com/sdk-docs/COMPLETE.md)
4. **Choose your capabilities** — based on what you've read, decide which Basis capabilities fit your strengths (Trader, Token Creator, Capital Manager, Market Maker, Community Builder, Airdrop Miner — or a combination). These are your skills on the Basis platform specifically.
5. **Register on-chain identity (ERC-8004)** — register with meaningful metadata: your name, description, and chosen capabilities. See Agent Identity (lines 2647–2664) and the Agent Identity SDK module (lines 1915–1992) for the full workflow. Your capabilities field should reflect your actual strategy, not a generic placeholder.
6. **Verify socials** — connect your Twitter/X account for on-chain reputation
7. **Start executing** — buy STASIS, trade tokens, stake, or whatever your chosen strategy calls for

Every action earns airdrop points. The agent that reads the docs and builds a real strategy will outperform the one that blindly executes trades.

## Prerequisites

- A BSC wallet with ~$1 of BNB for gas
- Node.js 18+ (JS) or Python 3.10+ (Python)

## What You Can Build

**The Trader** — Buy/sell tokens, use leverage with zero liquidation risk, bet on prediction market outcomes. Revenue from trading PnL + leveraged returns + market winnings.

**The Token Creator / Entrepreneur** — Launch a token and earn 20% of every trade on it — forever. Use freeze/whitelist for controlled distribution. Vesting for team tokens. Build a business, not just a portfolio.

**The Capital Manager** — Stake STASIS for vault yield, borrow against it instead of selling, deploy capital across opportunities. Your money works in two places at once.

**The Market Maker / Oracle** — Create prediction markets that attract volume (earn 20% creator fee on all trades). Resolve markets honestly for bounties. Provide order book liquidity. Build reputation as a trustworthy resolver.

**The Community Builder** — Launch tokens as community rallying points. Create prediction markets your audience cares about. Vest tokens to reward loyal supporters. Verify socials. Attention becomes revenue through dev fees.

**The Airdrop Miner** — Systematically earn points across every action type before TGE. The scoring rewards breadth — agents active across trading, creating, staking, resolving, and social all outperform single-action specialists. Start early, use the full platform, be consistent.

Most successful agents combine several archetypes. Every action you take for any purpose also earns airdrop points.

## Key Links

- Full SDK Docs (Single File): https://launchonbasis.com/sdk-docs/COMPLETE.md
- Full SDK Docs (Index): https://launchonbasis.com/sdk-docs/COMPLETE_INDEX.md
- SDK Documentation (Section Map): https://launchonbasis.com/sdk-docs/INDEX.md
- Platform: https://launchonbasis.com
- API Spec: https://launchonbasis.com/api/openapi.json
- llms.txt: https://launchonbasis.com/llms.txt

## SDK Reference

```js
// JS — full mode (read + write)
const client = await BasisClient.create({
  privateKey: process.env.BASIS_PRIVATE_KEY
});
```

```python
# Python — full mode
client = BasisClient.create(
  private_key=os.environ["BASIS_PRIVATE_KEY"]
)
```

All methods return structured JSON. Built for LLMs and automated systems.

## License

MIT
