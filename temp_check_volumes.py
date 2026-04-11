"""Check 24h volumes on Aster for all scanner coins."""
import os, sys
sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")
from dotenv import load_dotenv
load_dotenv(r"C:\Users\Never\.openclaw\workspace\.env")

import ccxt

exchange = ccxt.aster({
    "apiKey": os.getenv("ASTER_API_KEY"),
    "secret": os.getenv("ASTER_API_SECRET"),
    "options": {"defaultType": "swap"},
})

tickers = exchange.fetch_tickers()

# All coins from the 50-coin universe
import json
scanner_path = r"C:\Users\Never\.openclaw\workspace\docs\data\v14\cycle_scanner.json"
with open(scanner_path) as f:
    scanner = json.load(f)

scanner_syms = [c["symbol"] for c in scanner.get("rankings", [])]

print(f"{'Symbol':20s} {'24h Vol ($)':>15s} {'Bid':>12s} {'Ask':>12s} {'Spread':>8s}")
print("-" * 70)

results = []
for sym in scanner_syms:
    t = tickers.get(sym)
    if not t:
        # Try alternative format
        base = sym.split("/")[0]
        for k, v in tickers.items():
            if base in k:
                t = v
                sym = k
                break
    if t:
        vol = t.get("quoteVolume") or 0
        bid = t.get("bid") or 0
        ask = t.get("ask") or 0
        spread_pct = ((ask - bid) / bid * 100) if bid > 0 else 0
        results.append((sym, vol, bid, ask, spread_pct))

results.sort(key=lambda x: x[1], reverse=True)
for sym, vol, bid, ask, spread in results:
    flag = " ⚠️" if vol < 100000 else ""
    print(f"{sym:20s} ${vol:>14,.0f} {bid:>12.6f} {ask:>12.6f} {spread:>7.3f}%{flag}")

print(f"\n--- Volume thresholds ---")
for cap in [340, 5000, 10000, 20000, 50000]:
    # 5 coins, 90/10 split, L1 = 30% of allocation
    alloc = cap * 0.9 / 5
    l1 = alloc * 0.3
    print(f"${cap:>6,} capital: L1=${l1:>8,.1f} | Need ${l1/0.01:>10,.0f} vol for <1% impact | ${l1/0.02:>10,.0f} for <2%")
