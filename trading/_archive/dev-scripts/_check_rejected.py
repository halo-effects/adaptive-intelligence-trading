import json
d = json.load(open("trading/live/scanner_t1.json"))
print("Sample too_new:")
for r in d["rejected_by_maturity"]:
    if "too_new" in r["filter_reason"]:
        print(f"  {r['symbol']}: {r['filter_reason']}")
        
print("\nSample price_swing:")
for r in d["rejected_by_maturity"]:
    if "price_swing" in r["filter_reason"]:
        print(f"  {r['symbol']}: {r['filter_reason']}")
