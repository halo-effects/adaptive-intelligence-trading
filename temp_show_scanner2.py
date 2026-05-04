"""Show corrected scanner results."""
import json

with open(r"C:\Users\Never\.openclaw\workspace\docs\data\v14\cycle_scanner.json", encoding="utf-8") as f:
    data = json.load(f)

print(f"Generated: {data.get('generated_at')}")
print(f"Scanned: {data.get('coins_scanned')}, Mature: {data.get('coins_mature')}")

# Show top picks per window
for window, picks in data.get("top_picks", {}).items():
    print(f"\n=== {window} window ===")
    for coin in picks[:10]:
        sym = coin.get("symbol", "?")
        score = coin.get("dca_score", 0)
        dpw = coin.get("deals_per_week", 0)
        mark = " <<" if score >= 5.0 else ""
        print(f"  {sym:<10} score={score:>6.1f}  deals/wk={dpw:>4.1f}{mark}")

# Show liquidity filter
liq = data.get("liquidity_filter", {})
tradeable = liq.get("tradeable", liq.get("TRADEABLE", []))
low_liq = liq.get("low_liquidity", liq.get("LOW_LIQUIDITY", []))
print(f"\nLiquidity: {len(tradeable)} tradeable, {len(low_liq)} low-liquidity")

# Show trend scores  
trends = data.get("trend_scores", {})
if trends:
    print(f"\nTrend scores ({len(trends)} coins):")
    for sym, ts in sorted(trends.items(), key=lambda kv: kv[1].get("adjusted_score", 0), reverse=True)[:10]:
        adj = ts.get("adjusted_score", 0)
        base = ts.get("base_score", ts.get("dca_score", 0))
        mult = ts.get("trend_mult", ts.get("multiplier", 1.0))
        mark = " <<" if adj >= 5.0 else ""
        print(f"  {sym:<10} base={base:>6.1f} x mult={mult:.2f} = adj={adj:>6.1f}{mark}")
