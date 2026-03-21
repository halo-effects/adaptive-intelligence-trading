import json
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json") as f:
    state = json.load(f)

# Get engine state for GRASS
grass = state["coins"]["GRASS/USDT"]
eng = grass.get("engine_state", {})
print("GRASS engine_state:")
for k in ["long_coins", "long_cost", "long_avg_entry", "long_layers", "long_tp", "capital",
           "long_last_buy", "phase"]:
    print(f"  {k}: {eng.get(k)}")

print(f"\nGRASS allocated_capital: {grass.get('allocated_capital')}")
print(f"GRASS tp_order_id: {grass.get('tp_order_id')}")
print(f"GRASS last_candle_ts: {grass.get('last_candle_ts')}")

router = state["router"]
print(f"\nRouter active_cash: {router['active_pool_cash']}")
print(f"Router reserve_cash: {router['reserve_pool_cash']}")
print(f"Router alloc: {router['active_allocations']}")

# Sum it up
invested = eng.get("long_cost", 0)
active = router["active_pool_cash"]
reserve = router["reserve_pool_cash"]
alloc_total = sum(router["active_allocations"].values())
print(f"\nTotal: active({active:.2f}) + reserve({reserve:.2f}) + engine_invested({invested:.2f}) = {active+reserve+invested:.2f}")
print(f"Alloc total: {alloc_total:.2f}")
