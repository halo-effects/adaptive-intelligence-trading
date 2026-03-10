# Finances — Trading Overview
_Last updated: 2026-03-10_

## Active Trading

### V14PM Paper (MVP — Target for Live Production)
- **Capital**: $50,000 paper
- **Equity**: $50,504 (+1.01%)
- **Trades**: 22 completed, 100% win rate
- **Strategy**: Dynamic capital rotation, 10 coin slots, trend-adjusted scoring
- **Profile**: High, 12 layers, 1.0x leverage (no liquidation risk)
- **Exchange**: Hyperliquid perps
- **State**: Stable — full audit complete 2026-03-10

### V14 Live (Aster — REAL MONEY)
- **Capital**: $300 USDT
- **Coin**: ASTER/USDT (spot)
- **Exchange**: Aster DEX
- **Purpose**: Proof-of-concept with real capital

### V14 Paper (Customer Demo)
- **Capital**: $10,000 paper
- **Equity**: ~$69K+ (+595%)
- **Profile**: Medium, Hyperliquid

### V14-ETF Paper (Customer Demo)
- **Capital**: $10,000 paper
- **Coins**: SOL/XRP/LTC/HBAR/ADA
- **Profile**: High, Hyperliquid

## Infrastructure Costs
- **Exchange fees**: Hyperliquid maker 0.02%, taker 0.05%
- **API costs**: CFGI.io (optional), OpenClaw (primary LLM spend)
- **Cloud (planned)**: ~$5-12/month (Hetzner/DO/Vultr)

## Next: Cloud Migration
- V14PM → Hyperliquid mainnet, production Linux server
- Paper bots stay on Windows as demos
- Decisions pending: cloud provider, initial live capital, Hyperliquid API wallet
