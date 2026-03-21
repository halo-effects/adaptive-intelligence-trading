"""
Directly correct state.json with exchange-sourced position data.
Run while bot is STOPPED.
"""
import json, ccxt, os, time
from pathlib import Path

STATE_PATH = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json")

# Fetch exchange truth
client = ccxt.aster({
    'apiKey': os.environ.get('ASTER_API_KEY', ''),
    'secret': os.environ.get('ASTER_API_SECRET', ''),
    'options': {'defaultType': 'swap'},
    'timeout': 15000
})

bal = client.fetch_balance({"type": "future"})
usdt_free = float(bal.get("USDT", {}).get("free", 0))
usdt_total = float(bal.get("USDT", {}).get("total", 0))

positions = client.fetch_positions()
grass_pos = None
for p in positions:
    if "GRASS" in p.get("symbol", ""):
        contracts = float(p.get("contracts", 0) or 0)
        if contracts > 0:
            grass_pos = p

print(f"Exchange USDT free: {usdt_free:.4f}")
print(f"Exchange USDT total: {usdt_total:.4f}")
if grass_pos:
    qty = float(grass_pos.get("contracts", 0))
    entry = float(grass_pos.get("entryPrice", 0))
    upnl = float(grass_pos.get("unrealizedPnl", 0))
    print(f"GRASS position: qty={qty}, entry={entry:.6f}, upnl={upnl:.4f}")
else:
    print("No GRASS position found!")
    exit(1)

# Load and patch state.json
with open(STATE_PATH) as f:
    state = json.load(f)

print(f"\nBefore patch:")
print(f"  engine long_coins: {state['coins']['GRASS/USDT']['engine_state'].get('long_coins')}")
print(f"  engine long_cost:  {state['coins']['GRASS/USDT']['engine_state'].get('long_cost')}")
print(f"  router active_cash: {state['router']['active_pool_cash']}")

# Patch engine state
eng = state["coins"]["GRASS/USDT"]["engine_state"]
long_cost = qty * entry
tp_pct = 0.015
long_tp = entry * (1 + tp_pct)

eng["long_coins"] = qty
eng["long_cost"] = long_cost
eng["long_avg_entry"] = entry
eng["long_tp"] = long_tp
eng["long_layers"] = 2  # keep as-is (or set based on known history)
eng["capital"] = usdt_free  # engine capital = free USDT

# Patch router: active_cash = usdt_free - (anything already allocated excluding this position)
# With 1 coin and 90/10 split: active_cash = usdt_free minus reserve
reserve = 350 * 0.10  # $35 reserve
state["router"]["active_pool_cash"] = max(0, usdt_free - 0)  # all free USDT is active cash
state["router"]["reserve_pool_cash"] = reserve
state["router"]["active_allocations"] = {"GRASS/USDT": long_cost}

# Patch tp_order_id (set to the known correct one)
state["coins"]["GRASS/USDT"]["tp_order_id"] = "222562153"
state["coins"]["GRASS/USDT"]["tp_limit_price"] = 0.3962

print(f"\nAfter patch:")
print(f"  engine long_coins: {eng['long_coins']}")
print(f"  engine long_cost:  {eng['long_cost']:.4f}")
print(f"  engine long_avg_entry: {eng['long_avg_entry']:.6f}")
print(f"  engine long_tp: {eng['long_tp']:.6f}")
print(f"  router active_cash: {state['router']['active_pool_cash']:.4f}")

# Atomic write
tmp = STATE_PATH.with_suffix(".tmp")
with open(tmp, "w") as f:
    json.dump(state, f, indent=2)
tmp.replace(STATE_PATH)
print(f"\nstate.json patched successfully.")
