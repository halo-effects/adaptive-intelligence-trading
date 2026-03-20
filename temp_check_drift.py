import json
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json") as f:
    st = json.load(f)
eng = st["coins"]["GRASS/USDT"]["engine_state"]
print(f"Engine long_coins: {eng['long_coins']:.4f}")
print(f"Engine long_avg_entry: {eng['long_avg_entry']:.6f}")
print(f"Engine long_cost: {eng['long_cost']:.4f}")
print(f"Exchange has: 635.4 @ 0.389043")
print(f"Qty drift: {635.4 - eng['long_coins']:.4f} coins")
