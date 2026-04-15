"""Swap TAO limit sell to trailing stop, update state. Bot must be DEAD."""
import os, sys, json, time
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

SYM = "TAO/USDT:USDT"
CALLBACK = 0.5

# Get position
positions = exchange.fetch_positions([SYM])
pos = [p for p in positions if abs(float(p.get("contracts", 0))) > 0]
if not pos:
    print("No TAO position"); sys.exit(1)
qty = abs(float(pos[0]["contracts"]))
entry = float(pos[0]["entryPrice"])
activation = round(entry * 1.015, 4)
print(f"Position: {qty} TAO @ ${entry}, activation=${activation}")

# Cancel all open orders
orders = exchange.fetch_open_orders(SYM)
for o in orders:
    exchange.cancel_order(o["id"], SYM)
    print(f"Cancelled {o['id']} ({o.get('info',{}).get('type','?')})")

time.sleep(1)

# Place trailing stop
order = exchange.create_order(
    symbol=SYM, type="TRAILING_STOP_MARKET", side="sell", amount=qty,
    params={"quantity": str(qty), "activationPrice": str(activation),
            "callbackRate": str(CALLBACK), "positionSide": "BOTH", "reduceOnly": "true"}
)
new_id = order["id"]
print(f"Trailing stop placed: {new_id}, activate={order.get('info',{}).get('activatePrice')}")

# Update state
state_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json"
with open(state_path) as f:
    state = json.load(f)
tao = state["coins"]["TAO/USDT"]
tao["tp_order_id"] = new_id
tao["tp_limit_price"] = activation
tao["tp_type"] = "trailing"
tao["tp_activation_price"] = activation
tao["trailing_callback_pct"] = CALLBACK
tmp = state_path + ".tmp"
with open(tmp, "w") as f:
    json.dump(state, f, indent=2)
os.replace(tmp, state_path)
print("State updated")

# Verify
time.sleep(1)
orders2 = exchange.fetch_open_orders(SYM)
for o in orders2:
    print(f"Verified: {o['id']} {o.get('info',{}).get('type')} activate={o.get('info',{}).get('activatePrice')}")
