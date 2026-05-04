import sys, os
sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")
os.chdir(r"C:\Users\Never\.openclaw\workspace")
from trading.spot.exchange_client import SpotExchangeClient

client = SpotExchangeClient()
client.connect("aster")
client.exchange.load_markets()

for sym in ["HYPE/USDT:USDT", "TAO/USDT:USDT", "JTO/USDT:USDT"]:
    m = client.exchange.market(sym)
    p = m["precision"]
    print(f"{sym}:")
    print(f"  price precision: {p.get('price')}")
    print(f"  amount precision: {p.get('amount')}")

# Check what activation price the bot computed for HYPE
import json
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json") as f:
    data = json.load(f)
hype = data["coins"].get("HYPE/USDT", {})
print(f"\nHYPE current state:")
print(f"  layers: {hype.get('layers')}")
print(f"  avg_entry: {hype.get('avg_entry')}")
print(f"  next_tp_price: {hype.get('next_tp_price')}")
print(f"  tp_type: {hype.get('tp_type')}")
print(f"  tp_activation: {hype.get('tp_activation_price')}")

# Calculate what the activation price should be
avg = hype.get("avg_entry", 0)
tp = avg * 1.015 if avg else 0
print(f"\n  Computed TP (1.5%): {tp}")
print(f"  Rounded to 4 decimals: {round(tp, 4)}")
print(f"  Rounded to 3 decimals: {round(tp, 3)}")
print(f"  Rounded to 2 decimals: {round(tp, 2)}")
