import json
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json") as f:
    data = json.load(f)
for sym, c in data.get("coins", {}).items():
    if c.get("layers", 0) > 0:
        tp_type = c.get("tp_type", "MISSING")
        cb = c.get("trailing_callback_pct", "MISSING")
        act = c.get("tp_activation_price", "MISSING")
        print(f"  {sym}: tp_type={tp_type}, callback={cb}, activation={act}")
