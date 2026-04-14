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

SYM = "GRASS/USDT:USDT"

# Check open orders
orders = exchange.fetch_open_orders(SYM)
print(f"Open orders on GRASS: {len(orders)}")
for o in orders:
    otype = o.get("info", {}).get("type", "?")
    print(f"  id={o['id']} type={otype} status={o['status']}")

# Check position
positions = exchange.fetch_positions([SYM])
pos_qty = 0
for p in positions:
    contracts = float(p.get("contracts", 0))
    if abs(contracts) > 0:
        print(f"Position: {contracts} @ {p['entryPrice']}, pnl={p.get('unrealizedPnl')}")
        pos_qty = contracts
        break
else:
    print("No open position — already closed?")

if pos_qty > 0:
    print(f"\nClosing {pos_qty} GRASS...")
    result = exchange.create_order(
        symbol=SYM,
        type="market",
        side="sell",
        amount=pos_qty,
        params={"positionSide": "BOTH", "reduceOnly": "true"}
    )
    print(f"Order ID: {result['id']}")
    print(f"Status: {result['status']}")
    print(f"Filled: {result.get('filled')}")
    avg = result.get("average") or result.get("info", {}).get("avgPrice")
    print(f"Average price: {avg}")

    import time; time.sleep(2)
    # Verify
    positions2 = exchange.fetch_positions([SYM])
    for p in positions2:
        c = float(p.get("contracts", 0))
        if abs(c) > 0:
            print(f"WARNING: Still open: {c}")
            break
    else:
        print("Confirmed closed on exchange")

    # Update state
    state_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json"
    with open(state_path) as f:
        state = json.load(f)
    if "GRASS/USDT" in state.get("coins", {}):
        g = state["coins"]["GRASS/USDT"]
        g["tp_order_id"] = None
        g["tp_limit_price"] = None
        g["tp_type"] = None
        g["tp_activation_price"] = None
        g["trailing_callback_pct"] = None
        eng = g.get("engine_state", {})
        for k in ["long_coins","long_avg_entry","long_layers","long_tp","long_cost"]:
            eng[k] = 0
        eng["long_trailing_active"] = False
        eng["long_trailing_peak"] = 0.0
        g["engine_state"] = eng
        tmp = state_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp, state_path)
        print("State file updated")

# Check balance
balance = exchange.fetch_balance()
usdt_free = float(balance.get("USDT", {}).get("free", 0))
print(f"\nFree USDT: ${usdt_free:.2f}")
