"""Check scanner integrity and recent score data."""
import json, os
from datetime import datetime

# Check scanner code version markers
scanner_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\v14_cycle_scanner.py"
with open(scanner_path, encoding="utf-8") as f:
    content = f.read()

# Key features that should be present
checks = {
    "liquidity_filter": "TRADEABLE" in content or "LOW_LIQUIDITY" in content,
    "bo_pct_030": "BO_PCT = 0.30" in content or "BO_PCT=0.30" in content or "0.30" in content,
    "taker_fee_035": "0.00035" in content,
    "hurdle_rate": "hurdle" in content.lower() or "HURDLE" in content,
    "score_calc": "deals_per_week" in content or "cycle_velocity" in content or "base_score" in content,
}

print("Scanner code integrity:")
for check, result in checks.items():
    print(f"  {'✅' if result else '❌'} {check}")

# Check recent scanner output
scanner_json = r"C:\Users\Never\.openclaw\workspace\docs\data\v14\cycle_scanner.json"
if os.path.exists(scanner_json):
    with open(scanner_json, encoding="utf-8") as f:
        data = json.load(f)
    
    ts = data.get("timestamp", "?")
    coins = data.get("coins", data.get("results", []))
    print(f"\nScanner output: {ts}")
    print(f"Total coins: {len(coins)}")
    
    # Show top 10 by score
    if isinstance(coins, list):
        scored = sorted(coins, key=lambda c: c.get("score", c.get("trade_score", 0)), reverse=True)
    elif isinstance(coins, dict):
        scored = sorted(coins.items(), key=lambda kv: kv[1].get("score", 0), reverse=True)
        scored = [{"symbol": k, **v} for k, v in scored]
    
    print(f"\nTop 10 by score:")
    for c in scored[:10]:
        sym = c.get("symbol", c.get("coin", "?"))
        score = c.get("score", c.get("trade_score", 0))
        print(f"  {sym:<15} score={score:.1f}")

# Check score history
score_hist = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\score_history.json"
if os.path.exists(score_hist):
    with open(score_hist, encoding="utf-8") as f:
        hist = json.load(f)
    print(f"\nScore history entries: {len(hist)}")
    # Show last few entries if it's a time series
    if isinstance(hist, list) and len(hist) > 0:
        for entry in hist[-3:]:
            print(f"  {entry.get('timestamp', '?')}: top={entry.get('top_coin', '?')} score={entry.get('top_score', '?')}")
    elif isinstance(hist, dict):
        keys = sorted(hist.keys())[-3:]
        for k in keys:
            print(f"  {k}: {hist[k]}")
