import json, os
os.chdir(r"C:\Users\Never\.openclaw\workspace")

for fname in ["trading/live/scanner_t1.json", "trading/live/scanner_recommendation.json"]:
    try:
        with open(fname) as f:
            data = json.load(f)
        if "ranked" in data:
            print(f"T1 results: {data.get('timestamp','?')}")
            for c in data["ranked"][:10]:
                print(f"  {c['symbol']}: {c['score']:.1f}")
        else:
            print(f"{fname}:")
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"{fname}: {e}")
