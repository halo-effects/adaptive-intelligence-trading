import json

with open("trading/scanner/scanner_t2.json") as f:
    data = json.load(f)

rankings = data["rankings"]
print(f"Scanned: {data['candidates_tested']}, Passed: {data['passed']}")
print()
print("TOP 10:")
for i, r in enumerate(rankings[:10]):
    sym = r["symbol"]
    score = r.get("score", 0)
    roi = r["total_profit_pct"]
    dd = r["max_drawdown_pct"]
    sharpe = r.get("sharpe_ratio", 0)
    deals = r["total_deals"]
    wr = r["win_rate"]
    print(f"  {i+1:2}. {sym:14} score={score:>7}  ROI/d={roi:>7.2f}%  DD={dd:>6.2f}%  Sharpe={sharpe:>5.2f}  deals={deals}  WR={wr}%")

print()
# ASTER position
for i, r in enumerate(rankings):
    if "ASTER" in r["symbol"]:
        print(f"ASTER rank: #{i+1}/{len(rankings)} -- score={r.get('score',0)}, ROI/d={r['total_profit_pct']:.2f}%, Sharpe={r.get('sharpe_ratio',0):.2f}")
        break

print()
# Count negative scores
neg = sum(1 for r in rankings if r.get("score", 0) < 0)
print(f"Negative score coins: {neg}/{len(rankings)}")

# Failed coins
with open("trading/scanner/scanner_recommendation.json") as f:
    rec = json.load(f)
print(f"Action: {rec['action']}")
print(f"Best coin: {rec['best_coin']} (score={rec['best_score']})")
print(f"Current coin: {rec['current_coin']} (score={rec['current_score']})")
