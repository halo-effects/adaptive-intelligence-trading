import os, sys, json
sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")
from dotenv import load_dotenv
load_dotenv(r"C:\Users\Never\.openclaw\workspace\.env")
import ccxt

exchange = ccxt.aster({
    "apiKey": os.getenv("ASTER_API_KEY"),
    "secret": os.getenv("ASTER_API_SECRET"),
    "options": {"defaultType": "swap"},
})
exchange.load_markets()

SYM = "JTO/USDT:USDT"

# Position
positions = exchange.fetch_positions([SYM])
for p in positions:
    if abs(float(p.get("contracts", 0))) > 0:
        qty = float(p["contracts"])
        entry = float(p["entryPrice"])
        tp_expected = round(entry * 1.015, 6)
        print(f"JTO position: {qty} @ ${entry}")
        print(f"Expected TP activation: ${tp_expected}")

# Open orders
orders = exchange.fetch_open_orders(SYM)
print(f"\nOpen orders: {len(orders)}")
for o in orders:
    otype = o.get("info", {}).get("type", "?")
    act = o.get("info", {}).get("activatePrice", "")
    cb = o.get("info", {}).get("priceRate", "")
    print(f"  id={o['id']} type={otype} side={o['side']} qty={o.get('amount')} activate={act} callback={cb}%")

# State file
state_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json"
with open(state_path) as f:
    state = json.load(f)
jto = state.get("coins", {}).get("JTO/USDT", {})
eng = jto.get("engine_state", {})
print(f"\nState file:")
print(f"  coins={eng.get('long_coins')}, layers={eng.get('long_layers')}, cost=${eng.get('long_cost', 0):.2f}")
print(f"  tp_order_id={jto.get('tp_order_id')}")
print(f"  tp_type={jto.get('tp_type')}")
print(f"  tp_limit_price={jto.get('tp_limit_price')}")
print(f"  tp_activation_price={jto.get('tp_activation_price')}")
