"""Check 24h volumes on Aster for scanner coins."""
import os, sys, json
sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")
from dotenv import load_dotenv
load_dotenv(r"C:\Users\Never\.openclaw\workspace\.env")
import ccxt

exchange = ccxt.aster({
    "apiKey": os.getenv("ASTER_API_KEY"),
    "secret": os.getenv("ASTER_API_SECRET"),
    "options": {"defaultType": "swap"},
})
exchange.load_markets()
tickers = exchange.fetch_tickers()

# Get all unique coins from scanner
with open(r"C:\Users\Never\.openclaw\workspace\docs\data\v14\cycle_scanner.json") as f:
    scanner = json.load(f)

# Get top picks
top_picks = scanner.get("top_picks", [])
trend_scores = scanner.get("trend_scores", {})

# Get all coins from 30d window
coins_30d = {}
for w in scanner.get("windows", {}).values():
    for r in w.get("rankings", []):
        sym = r["symbol"]
        if sym not in coins_30d:
            coins_30d[sym] = r

# Match to tickers
results = []
for sym, info in coins_30d.items():
    ticker_key = f"{sym}:USDT"
    t = tickers.get(ticker_key)
    if t:
        vol = t.get("quoteVolume") or 0
        bid = t.get("bid") or 0
        ask = t.get("ask") or 0
        spread = ((ask - bid) / bid * 100) if bid > 0 else 0
        is_top = sym.split("/")[0] in [tp.get("coin", tp) if isinstance(tp, dict) else tp for tp in top_picks]
        trend = trend_scores.get(sym.split("/")[0], {}).get("trend_multiplier", 1.0) if isinstance(trend_scores.get(sym.split("/")[0]), dict) else 1.0
        results.append((sym, vol, bid, ask, spread, is_top, trend))

results.sort(key=lambda x: x[1], reverse=True)

print(f"{'Symbol':15s} {'24h Vol':>12s} {'Spread':>8s} {'Top?':>5s} {'Trend':>6s} {'Notes'}")
print("-" * 75)
for sym, vol, bid, ask, spread, is_top, trend in results:
    notes = ""
    if vol < 50000: notes = "⚠️ LOW VOL"
    elif vol < 100000: notes = "⚡ MARGINAL"
    top = "✓" if is_top else ""
    print(f"{sym:15s} ${vol:>11,.0f} {spread:>7.3f}% {top:>5s} {trend:>5.2f}x {notes}")

low_vol = sum(1 for _, v, *_ in results if v < 50000)
marginal = sum(1 for _, v, *_ in results if 50000 <= v < 100000)
ok = sum(1 for _, v, *_ in results if v >= 100000)
print(f"\nSummary: {ok} OK (>$100K) | {marginal} marginal ($50-100K) | {low_vol} low (<$50K) | {len(results)} total")
