import json
with open(r"C:\Users\Never\.openclaw\workspace\docs\data\v14\cycle_scanner.json") as f:
    d = json.load(f)

print("Liquidity filter:", json.dumps(d.get("liquidity_filter", {}), indent=2))
print()

print("Top 5 TRADEABLE:")
for r in d["windows"]["30d"]["rankings"]:
    if r.get("liquidity_status") == "TRADEABLE":
        print(f"  {r['coin']:8s} vol=${r.get('volume_24h',0):>12,.0f}  impact={r.get('volume_impact_pct','?'):>5}%  score={r['dca_score']:.1f}")

print()
print("First 5 LOW_LIQUIDITY:")
count = 0
for r in d["windows"]["30d"]["rankings"]:
    if r.get("liquidity_status") == "LOW_LIQUIDITY":
        vol = r.get("volume_24h")
        vol_str = f"${vol:>12,.0f}" if vol else "    NO DATA"
        print(f"  {r['coin']:8s} vol={vol_str}  impact={r.get('volume_impact_pct','?'):>5}%  score={r['dca_score']:.1f}")
        count += 1
        if count >= 5:
            break
