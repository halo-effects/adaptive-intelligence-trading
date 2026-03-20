import json
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json") as f:
    s = json.load(f)
print(f"equity: {s.get('equity')}")
print(f"pnl_pct: {s.get('pnl_pct')}")
print(f"exchange_balance: {s.get('exchange_balance')}")
grass = s.get("coins", {}).get("GRASS/USDT", {})
print(f"avg_entry: {grass.get('avg_entry')}")
print(f"invested: {grass.get('invested')}")
print(f"next_tp_price: {grass.get('next_tp_price')}")
print(f"layers: {grass.get('layers')}")
print(f"tp_order_id: {grass.get('tp_order_id')}")
print(f"unrealized_pnl: {grass.get('unrealized_pnl')}")
