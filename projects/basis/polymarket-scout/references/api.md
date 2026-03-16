# Polymarket API Reference

## Base URLs

- **Gamma API** (market data, public, no auth): `https://gamma-api.polymarket.com`
- **CLOB API** (order book, trading — requires auth): `https://clob.polymarket.com`
- **Frontend**: `https://polymarket.com`

## Key Endpoints (Gamma API — all public, no API key needed)

### Events
```
GET /events?active=true&closed=false&limit=100&offset=0
GET /events?slug={slug}
GET /events/slug/{slug}
GET /events?tag_id={tag_id}&related_tags=true
```
Each event contains a `markets[]` array (one market per outcome).

### Markets
```
GET /markets?active=true&closed=false&limit=100
GET /markets?slug={slug}
GET /markets/slug/{slug}
GET /markets?tag_id={tag_id}
```

### Tags
```
GET /tags          — all category tags
GET /sports        — sports-specific tags with metadata
```

### Pagination
All list endpoints support `limit` (max 100) and `offset` for pagination.

## Data Model

### Event
- `title`: Event title (e.g. "Who will win the 2026 World Cup?")
- `slug`: URL-friendly identifier
- `markets[]`: Array of market objects (each = one outcome)
- `tags[]`: Category tags (id, label)
- `endDate`: Resolution date
- `active`, `closed`: Status booleans

### Market (Outcome)
- `question`: Outcome question (e.g. "Will France win?")
- `outcomePrices`: Current implied probabilities (JSON string of [yes_price, no_price])
- `volume`: Total traded volume in USD
- `liquidity`: Current liquidity depth in USD
- `clobTokenIds`: Token IDs for Yes/No positions
- `active`, `closed`: Status booleans

## Multi-Outcome Markets
Polymarket models multi-outcome events as multiple binary markets under one event.
An event with 5 markets = 5 possible outcomes. This maps well to Basis's multi-outcome
prediction market structure.

Filter for multi-outcome: fetch events and check `len(event.markets) > 2`.

## Chain Info
- Polymarket runs on **Polygon** (MATIC), settles in USDC
- Basis runs on **BNB Chain**, settles in USDB
- For scouting purposes (read-only data), chain difference is irrelevant
- Cross-chain trading would require bridging (not in scope for this skill)

## Rate Limits
- Gamma API: No published rate limit, but be respectful (~1 req/sec)
- CLOB API: Requires API key credentials derived from wallet signature

## Related Repos
- `github.com/Polymarket/agents` — AI agent framework for Polymarket trading
- `github.com/Polymarket/py-clob-client` — Python CLOB client
- `github.com/Polymarket/polymarket-sdk` — TypeScript wallet SDK
