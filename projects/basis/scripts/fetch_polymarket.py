import json, urllib.request, sys

slug = sys.argv[1] if len(sys.argv) > 1 else "democratic-presidential-nominee-2028"
url = f"https://gamma-api.polymarket.com/events?slug={slug}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
data = json.loads(urllib.request.urlopen(req, timeout=15).read())

if not data:
    print("No data found")
    sys.exit(1)

event = data[0]
print(f"Event: {event['title']}")
print(f"Total markets/outcomes: {len(event.get('markets', []))}")
print()

markets = event.get("markets", [])
# Sort by volume descending
results = []
for m in markets:
    vol_str = m.get("volume", "0")
    vol = float(vol_str) if vol_str else 0
    title = m.get("groupItemTitle") or m.get("question", "")[:60]
    prices = m.get("outcomePrices", "")
    try:
        price_list = json.loads(prices) if prices else []
        yes_price = float(price_list[0]) if price_list else 0
    except:
        yes_price = 0
    results.append({"title": title, "volume": vol, "probability": yes_price})

results.sort(key=lambda x: x["volume"], reverse=True)

total_vol = sum(r["volume"] for r in results)
print(f"Total volume: ${total_vol:,.0f}")
print()
print(f"{'#':<4} {'Outcome':<40} {'Volume':>15} {'Vol%':>8} {'Prob':>8}")
print("-" * 80)
for i, r in enumerate(results, 1):
    vol_pct = (r["volume"] / total_vol * 100) if total_vol > 0 else 0
    print(f"{i:<4} {r['title']:<40} ${r['volume']:>13,.0f} {vol_pct:>7.1f}% {r['probability']:>7.1%}")

# Also dump JSON for simulation
with open(f"polymarket_{slug.replace('-','_')}_outcomes.json", "w") as f:
    json.dump({"event": event["title"], "total_volume": total_vol, "outcomes": results}, f, indent=2)
print(f"\nJSON saved to polymarket_{slug.replace('-','_')}_outcomes.json")
