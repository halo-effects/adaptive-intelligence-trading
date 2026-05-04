import json

with open(r"C:\Users\Never\.openclaw\workspace\docs\data\v14\cycle_scanner.json", encoding="utf-8") as f:
    data = json.load(f)

print(f"Generated: {data.get('generated_at')}")

# Get 30d rankings (what the PM bot uses)
rankings = data.get("windows", {}).get("30d", {}).get("rankings", [])
trend_scores = data.get("trend_scores", {})

print(f"\n30d Scanner Results (corrected BO=30%, fee=0.035%):")
print(f"{'Coin':<10} {'Base':>7} {'Trend':>6} {'Adj':>7} {'Deals/Wk':>9} {'DD%':>6}")
print("-" * 50)

above = 0
for r in rankings[:20]:
    coin = r.get("coin", r.get("symbol", "?").split("/")[0])
    base = r.get("dca_score", 0)
    ts = trend_scores.get(coin, {})
    mult = ts.get("trend_multiplier", 1.0)
    adj = base * mult
    dpw = r.get("deals_per_week", 0)
    dd = r.get("max_drawdown_pct", 0)
    mark = " <<" if adj >= 5.0 else ""
    if adj >= 5.0: above += 1
    print(f"{coin:<10} {base:>7.1f} {mult:>5.2f}x {adj:>7.1f} {dpw:>9.1f} {dd:>5.1f}%{mark}")

print(f"\nCoins above 5.0 hurdle: {above}")
