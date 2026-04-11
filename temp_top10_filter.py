import json

with open(r"C:\Users\Never\.openclaw\workspace\docs\data\v14\cycle_scanner.json") as f:
    d = json.load(f)

rankings_30d = d["windows"]["30d"]["rankings"]
trend_scores = d.get("trend_scores", {})

volumes = {
    "BTC": 470962746, "ETH": 192647351, "SOL": 39685080, "XRP": 10984406,
    "DOGE": 9189277, "HYPE": 8166751, "TAO": 5614237, "ZEC": 2675368,
    "ARB": 569861, "SUI": 365707, "AVAX": 357182, "AAVE": 251974,
    "ADA": 154155, "DOT": 132243, "LINK": 119045, "FET": 110761,
    "SNX": 87023, "TRUMP": 85123, "RENDER": 74129, "APT": 73020,
    "LTC": 54623, "ZRO": 51102, "HBAR": 48774, "NEAR": 42365,
    "ENA": 30543, "ONDO": 29217, "SEI": 16259, "TIA": 14178,
    "JTO": 12385, "ATOM": 10954, "UNI": 10673, "JUP": 8874,
    "IP": 8430, "INJ": 7246, "CRV": 6993, "FIL": 6654,
    "S": 4951, "ORCA": 4561, "GRASS": 3785, "STX": 3346,
    "BERA": 2857, "PENDLE": 2561, "VIRTUAL": 2430, "INIT": 2312,
    "PYTH": 697, "MOVE": 691, "EIGEN": 394,
}

# $20K, 5 coins, 90/10, L1 = 30% of alloc
L1_SIZE = 20000 * 0.9 / 5 * 0.3  # $1,080
MIN_VOL = L1_SIZE / 0.02  # 2% threshold = $54,000

print("TOP 10 by scanner score (30d window) — $20K capital filter:")
print(f"  L1 order = ${L1_SIZE:,.0f} | Min volume (2%) = ${MIN_VOL:,.0f}")
print()
header = f"{'Rank':>4}  {'Symbol':15} {'AdjScore':>9} {'24h Vol':>13} {'L1/Vol':>8}  Status"
print(header)
print("-" * len(header))

for i, r in enumerate(rankings_30d[:10], 1):
    coin = r["coin"]
    vol = volumes.get(coin, 0)
    ts = trend_scores.get(coin, {})
    adj = ts.get("adjusted_score", r.get("realized_pnl", 0)) if isinstance(ts, dict) else r.get("realized_pnl", 0)
    
    l1_pct = (L1_SIZE / vol * 100) if vol > 0 else 999
    status = "✅ TRADEABLE" if vol >= MIN_VOL else "🚫 LOW LIQUIDITY"
    
    print(f"{i:>4}  {r['symbol']:15} {adj:>9.1f} ${vol:>12,} {l1_pct:>7.2f}%  {status}")

print()
affected = sum(1 for r in rankings_30d[:10] if volumes.get(r["coin"], 0) < MIN_VOL)
print(f"Result: {affected} of top 10 would be filtered to low-liquidity phase")
