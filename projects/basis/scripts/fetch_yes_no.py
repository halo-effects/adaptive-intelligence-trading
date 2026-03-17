"""Check if Polymarket API provides YES/NO volume or price breakdown."""
import json, urllib.request

slug = "democratic-presidential-nominee-2028"
url = f"https://gamma-api.polymarket.com/events?slug={slug}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
data = json.loads(urllib.request.urlopen(req, timeout=15).read())

event = data[0]
markets = event.get("markets", [])

# Look at a few high-profile outcomes
targets = ["Gavin Newsom", "Chelsea Clinton", "Alexandria Ocasio-Cortez", "Kamala Harris", "Josh Shapiro"]

print("Checking Polymarket API fields for YES/NO data...\n")

for m in markets:
    title = m.get("groupItemTitle") or m.get("question", "")
    if not any(t in title for t in targets):
        continue
    
    vol = float(m.get("volume", 0))
    if vol == 0:
        continue
    
    print(f"=== {title} ===")
    print(f"  volume: ${vol:,.0f}")
    print(f"  outcomePrices: {m.get('outcomePrices', 'N/A')}")
    print(f"  bestBid: {m.get('bestBid', 'N/A')}")
    print(f"  bestAsk: {m.get('bestAsk', 'N/A')}")
    
    # Dump ALL keys to see what's available
    interesting_keys = [k for k in m.keys() if k not in ('question', 'description', 'image', 'icon')]
    for k in sorted(interesting_keys):
        v = m[k]
        if isinstance(v, str) and len(v) > 200:
            continue
        if k in ('volume', 'outcomePrices', 'bestBid', 'bestAsk', 'groupItemTitle'):
            continue
        print(f"  {k}: {v}")
    print()
