import json

with open("trading/scanner/scanner_t2.json") as f:
    data = json.load(f)

rankings = data["rankings"]
print("TOP 10 (by composite_score):")
for i, r in enumerate(rankings[:10]):
    sym = r["symbol"]
    cs = r["composite_score"]
    roi = r["daily_roi_pct"]
    dd = r["max_drawdown_pct"]
    sh = r["sharpe_ratio"]
    deals = r["total_deals"]
    wr = r["win_rate"]
    avail = r["available_on"]
    print(f"  {i+1:2}. {sym:14} composite={cs:>7.1f}  ROI/d={roi:>7.2f}%  DD={dd:>6.2f}%  Sharpe={sh:>5.2f}  deals={deals}  WR={wr}%  avail={avail}")

print()
for i, r in enumerate(rankings):
    if "ASTER" in r["symbol"]:
        print(f"ASTER rank: #{i+1}/{len(rankings)} -- composite={r['composite_score']:.1f}, ROI/d={r['daily_roi_pct']:.2f}%, Sharpe={r['sharpe_ratio']:.2f}")
        break

print()
neg = sum(1 for r in rankings if r["composite_score"] < 0)
pos = len(rankings) - neg
print(f"Positive: {pos}, Negative: {neg} of {len(rankings)} coins")

print()
print("BOTTOM 5:")
for r in rankings[-5:]:
    print(f"  {r['symbol']:14} composite={r['composite_score']:>7.1f}  Sharpe={r['sharpe_ratio']:>5.2f}")
