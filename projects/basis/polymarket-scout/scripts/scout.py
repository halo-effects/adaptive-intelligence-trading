#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Windows: set PYTHONIOENCODING=utf-8 if emoji output fails
"""Polymarket Scout — fetch and score prediction markets for Basis cross-listing.

Usage:
    python scout.py [--min-volume 10000] [--min-outcomes 3] [--limit 50] [--tag TAG_ID] [--json]

Outputs a ranked table of Polymarket markets suitable for Basis, prioritizing:
  1. Multi-outcome markets (>2 outcomes) — these are the sweet spot for Basis
  2. High volume / liquidity
  3. Active & not yet closed
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError


GAMMA_API = "https://gamma-api.polymarket.com"
POLYMARKET_BASE = "https://polymarket.com/event"


def fetch_json(url: str, retries: int = 2) -> dict | list:
    """Fetch JSON from URL with basic retry."""
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers={"User-Agent": "BasisPolymarketScout/1.0"})
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except (HTTPError, URLError) as e:
            if attempt < retries:
                time.sleep(1)
                continue
            raise SystemExit(f"API error fetching {url}: {e}")


def fetch_events(limit: int = 100, tag_id: str | None = None) -> list[dict]:
    """Fetch active, open events from Polymarket Gamma API (paginated)."""
    all_events = []
    offset = 0
    page_size = min(limit, 100)

    while len(all_events) < limit:
        url = (
            f"{GAMMA_API}/events?active=true&closed=false"
            f"&limit={page_size}&offset={offset}"
        )
        if tag_id:
            url += f"&tag_id={tag_id}"

        events = fetch_json(url)
        if not events:
            break
        all_events.extend(events)
        offset += page_size

    return all_events[:limit]


def fetch_tags() -> list[dict]:
    """Fetch available tags for filtering."""
    return fetch_json(f"{GAMMA_API}/tags")


def score_event(event: dict) -> dict | None:
    """Score an event for Basis suitability. Returns enriched dict or None if filtered out."""
    markets = event.get("markets", [])
    if not markets:
        return None

    # Count active markets (each market = one outcome in Polymarket's model)
    active_markets = [m for m in markets if m.get("active") and not m.get("closed")]
    num_outcomes = len(active_markets)

    # Aggregate volume and liquidity
    total_volume = sum(float(m.get("volume", 0) or 0) for m in active_markets)
    total_liquidity = sum(float(m.get("liquidity", 0) or 0) for m in active_markets)

    # Collect outcome details
    outcomes = []
    for m in active_markets:
        outcomes.append({
            "question": m.get("question", ""),
            "outcome_prices": m.get("outcomePrices", ""),
            "volume": float(m.get("volume", 0) or 0),
            "slug": m.get("slug", ""),
        })

    # Score: heavily weight multi-outcome markets
    # Multi-outcome bonus: 2x for 3 outcomes, 3x for 4+, etc.
    outcome_multiplier = max(1, num_outcomes - 1)
    score = total_volume * outcome_multiplier

    # Liquidity bonus (sqrt to dampen)
    score += (total_liquidity ** 0.5) * 100

    return {
        "title": event.get("title", "Unknown"),
        "slug": event.get("slug", ""),
        "url": f"{POLYMARKET_BASE}/{event.get('slug', '')}",
        "num_outcomes": num_outcomes,
        "total_volume": round(total_volume, 2),
        "total_liquidity": round(total_liquidity, 2),
        "score": round(score, 2),
        "tags": [t.get("label", "") for t in event.get("tags", [])],
        "end_date": event.get("endDate", ""),
        "outcomes": outcomes,
    }


def main():
    parser = argparse.ArgumentParser(description="Scout Polymarket for Basis-worthy markets")
    parser.add_argument("--min-volume", type=float, default=5000, help="Min total volume USD (default: 5000)")
    parser.add_argument("--min-outcomes", type=int, default=2, help="Min number of outcomes (default: 2, use 3+ for multi-outcome focus)")
    parser.add_argument("--limit", type=int, default=200, help="Max events to fetch (default: 200)")
    parser.add_argument("--tag", type=str, default=None, help="Filter by tag ID")
    parser.add_argument("--list-tags", action="store_true", help="List available tags and exit")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--top", type=int, default=20, help="Show top N results (default: 20)")
    args = parser.parse_args()

    if args.list_tags:
        tags = fetch_tags()
        for t in sorted(tags, key=lambda x: x.get("label", "")):
            print(f"  {t.get('id', '?'):>8}  {t.get('label', 'unknown')}")
        return

    # Fetch and score
    events = fetch_events(limit=args.limit, tag_id=args.tag)
    scored = []
    for ev in events:
        result = score_event(ev)
        if result is None:
            continue
        if result["total_volume"] < args.min_volume:
            continue
        if result["num_outcomes"] < args.min_outcomes:
            continue
        scored.append(result)

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:args.top]

    if args.json:
        print(json.dumps(top, indent=2))
        return

    # Pretty print
    print(f"\n🔍 Polymarket Scout — Top {len(top)} markets for Basis")
    print(f"   Filters: volume ≥ ${args.min_volume:,.0f} | outcomes ≥ {args.min_outcomes}")
    print(f"   Scanned: {len(events)} events → {len(scored)} matched\n")
    print(f"{'#':>3}  {'Score':>10}  {'Out':>3}  {'Volume':>12}  {'Liquidity':>10}  Title")
    print("─" * 90)

    for i, m in enumerate(top, 1):
        print(
            f"{i:>3}  {m['score']:>10,.0f}  {m['num_outcomes']:>3}  "
            f"${m['total_volume']:>11,.0f}  ${m['total_liquidity']:>9,.0f}  "
            f"{m['title'][:45]}"
        )
        if m["num_outcomes"] > 2:
            print(f"     ⭐ MULTI-OUTCOME ({m['num_outcomes']} ways) — ideal for Basis")
        if m["tags"]:
            print(f"     Tags: {', '.join(m['tags'][:5])}")
        print(f"     {m['url']}")
        print()


if __name__ == "__main__":
    main()
