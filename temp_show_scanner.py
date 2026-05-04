"""Show corrected scanner results."""
import json

with open(r"C:\Users\Never\.openclaw\workspace\docs\data\v14\cycle_scanner.json", encoding="utf-8") as f:
    data = json.load(f)

ts = data.get("timestamp", "?")
coins = data.get("coins", {})
print(f"Timestamp: {ts}")
print(f"Total coins: {len(coins)}")

ranked = sorted(coins.items(), key=lambda kv: kv[1].get("score", kv[1].get("trade_score", 0)), reverse=True)

header = f"{'Coin':<10} {'Score':>8} {'Deals/Wk':>10} {'Liquidity':>12}"
print(f"\n{header}")
print("-" * 45)

above = 0
for sym, d in ranked[:25]:
    score = d.get("score", d.get("trade_score", 0))
    dpw = d.get("deals_per_week", 0)
    liq = d.get("liquidity", d.get("liquidity_tag", "?"))
    mark = " <<" if score >= 5.0 else ""
    if score >= 5.0:
        above += 1
    print(f"{sym:<10} {score:>8.1f} {dpw:>10.1f} {str(liq):>12}{mark}")

print(f"\nCoins above 5.0 hurdle: {above}")
