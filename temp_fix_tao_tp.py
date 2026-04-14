"""Fix TAO TP: cancel both orders, place one trailing stop for full position."""
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
CALLBACK_RATE = 0.5

# 1. Get position
positions = exchange.fetch_positions([SYM])
pos = None
for p in positions:
    if p.get("symbol") == SYM and abs(float(p.get("contracts", 0))) > 0:
        pos = p
        break

if not pos:
    print("No TAO position found!")
    sys.exit(1)

qty = abs(float(pos.get("contracts", 0)))
entry = float(pos.get("entryPrice", 0))
activation = round(entry * 1.015, 4)
print(f"TAO position: {qty} @ ${entry}")
print(f"New activation: ${activation}")

# 2. Cancel all open orders on TAO
orders = exchange.fetch_open_orders(SYM)
print(f"\nOpen orders: {len(orders)}")
for o in orders:
    otype = o.get("info", {}).get("type", "?")
    try:
        exchange.cancel_order(o["id"], SYM)
        print(f"  Cancelled {o['id']} (type={otype}, qty={o.get('amount')})")
    except Exception as e:
        print(f"  Failed to cancel {o['id']}: {e}")

time.sleep(1)

# 3. Place single trailing stop for full position
print(f"\nPlacing trailing stop: {qty} TAO, activate=${activation}, callback={CALLBACK_RATE}%")
try:
    order = exchange.create_order(
        symbol=SYM,
        type="TRAILING_STOP_MARKET",
        side="sell",
        amount=qty,
        params={
            "quantity": str(qty),
            "activationPrice": str(activation),
            "callbackRate": str(CALLBACK_RATE),
            "positionSide": "BOTH",
            "reduceOnly": "true",
        }
    )
    new_id = order.get("id")
    act = order.get("info", {}).get("activatePrice", "?")
    rate = order.get("info", {}).get("priceRate", "?")
    print(f"  Trailing stop placed: id={new_id}, activate={act}, callback={rate}%")
except Exception as e:
    print(f"  FAILED: {e}")
    sys.exit(1)

time.sleep(1)

# 4. Update state file
state_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json"
with open(state_path) as f:
    state = json.load(f)

if "TAO/USDT" in state.get("coins", {}):
    tao = state["coins"]["TAO/USDT"]
    tao["tp_order_id"] = new_id
    tao["tp_limit_price"] = activation
    tao["tp_type"] = "trailing"
    tao["tp_activation_price"] = activation
    tao["trailing_callback_pct"] = CALLBACK_RATE
    
    tmp = state_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, state_path)
    print("State file updated")

# 5. Verify
orders2 = exchange.fetch_open_orders(SYM)
print(f"\nVerification — open orders on TAO: {len(orders2)}")
for o in orders2:
    otype = o.get("info", {}).get("type", "?")
    act = o.get("info", {}).get("activatePrice", "")
    print(f"  id={o['id']} type={otype} qty={o.get('amount')} activate={act}")
