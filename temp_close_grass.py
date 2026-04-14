"""Close GRASS position on Aster: cancel trailing TP, market sell, update state."""
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

SYM = "GRASS/USDT:USDT"
state_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json"

# 1. Get current position
positions = exchange.fetch_positions([SYM])
pos = None
for p in positions:
    if p.get("symbol") == SYM and abs(float(p.get("contracts", 0))) > 0:
        pos = p
        break

if not pos:
    print("No GRASS position found on exchange")
    sys.exit(1)

qty = abs(float(pos.get("contracts", 0)))
entry = float(pos.get("entryPrice", 0))
unrealized = float(pos.get("unrealizedPnl", 0))
print(f"GRASS position: {qty} coins @ ${entry:.6f}, unrealized PnL: ${unrealized:.2f}")

# 2. Cancel the trailing stop TP order
with open(state_path) as f:
    state = json.load(f)

grass_state = state.get("coins", {}).get("GRASS/USDT", {})
tp_id = grass_state.get("tp_order_id")

if tp_id:
    try:
        exchange.cancel_order(tp_id, SYM)
        print(f"✅ Cancelled trailing stop TP order {tp_id}")
    except Exception as e:
        print(f"⚠️  Cancel TP failed (may already be gone): {e}")
else:
    print("No TP order ID in state")

time.sleep(1)

# 3. Market sell to close
try:
    order = exchange.create_market_sell_order(SYM, qty, params={
        "positionSide": "BOTH",
        "reduceOnly": True,
    })
    fill_price = float(order.get("average", 0) or order.get("price", 0))
    fill_cost = float(order.get("cost", 0))
    print(f"✅ Market sell filled: {qty} GRASS @ ${fill_price:.6f}")
    print(f"   Proceeds: ${fill_cost:.2f}")
    pnl = fill_cost - (qty * entry)
    print(f"   Estimated PnL: ${pnl:.2f}")
except Exception as e:
    print(f"❌ Market sell failed: {e}")
    sys.exit(1)

time.sleep(1)

# 4. Verify position closed
positions2 = exchange.fetch_positions([SYM])
still_open = False
for p in positions2:
    if p.get("symbol") == SYM and abs(float(p.get("contracts", 0))) > 0:
        still_open = True
        print(f"⚠️  Position still open: {p.get('contracts')} contracts")
        break
if not still_open:
    print("✅ Position confirmed closed on exchange")

# 5. Update state — clear GRASS coin state so bot picks up the closure
if "GRASS/USDT" in state.get("coins", {}):
    grass = state["coins"]["GRASS/USDT"]
    grass["tp_order_id"] = None
    grass["tp_limit_price"] = None
    grass["tp_type"] = None
    grass["tp_activation_price"] = None
    grass["trailing_callback_pct"] = None
    eng = grass.get("engine_state", {})
    eng["long_coins"] = 0
    eng["long_avg_entry"] = 0
    eng["long_layers"] = 0
    eng["long_tp"] = 0
    eng["long_cost"] = 0
    eng["long_trailing_active"] = False
    eng["long_trailing_peak"] = 0.0
    grass["engine_state"] = eng

    tmp = state_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, state_path)
    print("✅ State file updated — GRASS cleared")

# 6. Check remaining balance
balance = exchange.fetch_balance()
usdt_free = balance.get("USDT", {}).get("free", 0)
print(f"\nFree USDT after close: ${float(usdt_free):.2f}")
print("Bot will redeploy capital on next tick cycle (~65s)")
