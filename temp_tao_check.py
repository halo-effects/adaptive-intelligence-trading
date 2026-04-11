import json, csv
from pathlib import Path

# Check paper bot status
status = json.loads(Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json").read_text(encoding="utf-8"))
print("=== PM Paper Status ===")
print("Last update:", status.get("last_update", "?"))

for sym, c in status.get("coins", {}).items():
    if "TAO" in sym:
        print(f"TAO in status: {json.dumps(c, indent=2)[:500]}")
        break
else:
    print("TAO not in active coins (already closed)")

# Check trades CSV
csv_path = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\trades.csv")
if csv_path.exists():
    with open(csv_path) as f:
        reader = list(csv.DictReader(f))
    tao_trades = [t for t in reader if "TAO" in t.get("symbol", "")]
    print(f"\nTAO trades in CSV: {len(tao_trades)}")
    for t in tao_trades[-8:]:
        print(f"  {t.get('timestamp','?')[:19]} | {t.get('action','?'):6s} | layers={t.get('layers','?')} | avg_entry={t.get('avg_entry','?')} | tp_price={t.get('tp_price','?')} | exit={t.get('exit_price','?')} | pnl=${t.get('pnl','?')} | inv=${t.get('invested','?')}")

# Check state for TAO engine details
state_path = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\state.json")
if state_path.exists():
    state = json.loads(state_path.read_text(encoding="utf-8"))
    for sym, cs in state.get("coins", {}).items():
        if "TAO" in sym:
            eng = cs.get("engine_state", {})
            print(f"\nTAO engine state:")
            print(f"  long_avg_entry: {eng.get('long_avg_entry')}")
            print(f"  long_layers: {eng.get('long_layers')}")
            print(f"  long_cost: {eng.get('long_cost')}")
            print(f"  long_coins: {eng.get('long_coins')}")
            print(f"  current_price: {eng.get('current_price')}")
            print(f"  tp_limit_price: {cs.get('tp_limit_price')}")
            break
