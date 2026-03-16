---
name: polymarket-scout
description: Scout Polymarket prediction markets to find high-potential markets for cross-listing on Basis Protocol. Use when asked to find prediction markets, scout Polymarket, identify trending markets, find multi-outcome markets, or research prediction market opportunities for Basis. Triggers on "polymarket", "prediction markets", "scout markets", "find markets for Basis", "multi-outcome markets", "market opportunities".
---

# Polymarket Scout

Scout Polymarket's public API for prediction markets worth cross-listing on Basis Protocol (BNB Chain).

## Strategy

Basis benefits most from markets that:
1. **Have 3+ outcomes** — Basis's multi-outcome structure outperforms binary-only platforms
2. **High volume** — proven demand means agents will find liquidity
3. **Active & time-bounded** — markets with clear end dates drive urgency
4. **Trending categories** — crypto, politics, sports, entertainment

## Quick Start

Run the scout script (no API key needed — Polymarket data endpoints are public):

```bash
# On Windows, set encoding first: $env:PYTHONIOENCODING="utf-8"
python scripts/scout.py --min-outcomes 3 --min-volume 10000 --top 20
```

### Common Commands

```bash
# Multi-outcome focus (the sweet spot for Basis)
python scripts/scout.py --min-outcomes 3 --min-volume 5000

# All markets above volume threshold
python scripts/scout.py --min-outcomes 2 --min-volume 25000

# Filter by category tag
python scripts/scout.py --list-tags                    # discover tag IDs
python scripts/scout.py --tag 100381 --min-outcomes 3  # filter by tag

# JSON output for programmatic use
python scripts/scout.py --min-outcomes 3 --json > markets.json
```

### Scoring

Markets are ranked by a composite score:
- **Volume × outcome multiplier** — multi-outcome markets get (N-1)x boost
- **Liquidity bonus** — sqrt-dampened liquidity depth
- Markets with 3+ outcomes are flagged as ⭐ ideal for Basis

## Chain Note

Polymarket is on Polygon; Basis is on BNB Chain. This skill only reads Polymarket data — no cross-chain interaction needed. The goal is market intelligence, not bridging.

## API Reference

For endpoint details, parameters, and data model: read `references/api.md`.

## Future: Basis SDK Integration

Once the Basis SDK is published, this skill can be extended to:
1. Auto-create corresponding markets on Basis from scouted Polymarket data
2. Seed initial liquidity parameters based on Polymarket volume/odds
3. Feed agent strategies with real-time odds comparison between platforms
