"""Check which coins qualify for the paper bot (score >= 5.0)."""
import json

scanner_path = r"C:\Users\Never\.openclaw\workspace\docs\data\v14\cycle_scanner.json"
with open(scanner_path) as f:
    scanner = json.load(f)

# Paper bot uses 30d window
windows = scanner.get("windows", {})
rankings_30d = windows.get("30d", {}).get("rankings", [])

print(f"Scanner 30d rankings: {len(rankings_30d)} coins\n")

qualifying = []
non_qualifying = []
for r in rankings_30d:
    coin = r.get("coin", r.get("symbol", "?"))
    score = float(r.get("dca_score", 0))
    trend = float(r.get("trend_multiplier", 1.0))
    adj = score * trend
    if score >= 5.0:
        qualifying.append((coin, score, trend, adj))
    else:
        non_qualifying.append((coin, score, trend, adj))

print(f"Qualifying (score >= 5.0): {len(qualifying)}")
for coin, score, trend, adj in qualifying:
    print(f"  {coin}: score={score:.1f}, trend={trend:.2f}, adj={adj:.1f}")

print(f"\nNon-qualifying (score < 5.0): {len(non_qualifying)}")
for coin, score, trend, adj in sorted(non_qualifying, key=lambda x: -x[1])[:10]:
    print(f"  {coin}: score={score:.1f}, trend={trend:.2f}, adj={adj:.1f}")

# Check what the 4 active positions scored
active = ["ZRO", "TAO", "FET", "ARB"]
print(f"\nActive position scores:")
for r in rankings_30d:
    coin = r.get("coin", "?")
    if coin in active:
        print(f"  {coin}: score={r.get('dca_score')}, trend={r.get('trend_multiplier')}")
