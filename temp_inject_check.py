"""
Read the CURRENT state.json and the CURRENT status.json side by side
to understand the discrepancy.
"""
import json

# State.json (what gets persisted)
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json") as f:
    state = json.load(f)
grass_eng = state["coins"]["GRASS/USDT"]["engine_state"]

# Status.json (what the running bot writes every 65s)  
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json") as f:
    status = json.load(f)
grass_status = status.get("coins", {}).get("GRASS/USDT", {})

print("=== STATE.JSON (persisted engine) ===")
print(f"  long_coins:     {grass_eng.get('long_coins')}")
print(f"  long_cost:      {grass_eng.get('long_cost')}")
print(f"  long_avg_entry: {grass_eng.get('long_avg_entry')}")
print(f"  long_layers:    {grass_eng.get('long_layers')}")
print(f"  long_tp:        {grass_eng.get('long_tp')}")
print(f"  capital:        {grass_eng.get('capital')}")

print("\n=== STATUS.JSON (dashboard output) ===")
print(f"  invested:       {grass_status.get('invested')}")
print(f"  avg_entry:      {grass_status.get('avg_entry')}")
print(f"  layers:         {grass_status.get('layers')}")
print(f"  next_tp:        {grass_status.get('next_tp_price')}")
print(f"  unrealized:     {grass_status.get('unrealized_pnl')}")
print(f"  current_price:  {grass_status.get('current_price')}")

print("\n=== KEY QUESTION ===")
print(f"State engine long_coins = {grass_eng.get('long_coins'):.4f}")
print(f"Exchange has 635.4 GRASS")
print(f"If state==68.17, the startup recon correction isn't persisting")
print(f"Possible cause: _save_state snapshot reads from a DIFFERENT engine")
print(f"  object than what the recon modified")

# Check: does status show exchange overlay?
print(f"\n=== EXCHANGE OVERLAY CHECK ===")
eb = status.get("exchange_balance", {})
print(f"  exchange_balance present: {eb is not None and len(eb) > 0}")
if eb:
    print(f"  usdt_free:  {eb.get('usdt_free')}")
    print(f"  usdt_total: {eb.get('usdt_total')}")

# Timing
print(f"\nState saved_at: {state.get('saved_at')}")
print(f"Status last_update: {status.get('last_update')}")
