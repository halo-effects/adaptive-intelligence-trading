"""
Replace existing limit-sell TP orders with trailing stops on Aster.
Reads current state, cancels each limit TP, places a TRAILING_STOP_MARKET.
Does NOT touch the bot process — just swaps the exchange orders.
"""
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

# Read current state to get TP order IDs and positions
state_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json"
with open(state_path) as f:
    state = json.load(f)

CALLBACK_RATE = 0.5  # 0.5% trail
TP_PCT = 0.015       # 1.5%

# Map of coins with active TP orders
coins_to_replace = []
for sym, cs_data in state.get("coins", {}).items():
    tp_id = cs_data.get("tp_order_id")
    if not tp_id:
        continue
    eng = cs_data.get("engine_state", {})
    if eng.get("long_coins", 0) <= 0:
        continue
    coins_to_replace.append({
        "symbol": sym,
        "tp_order_id": tp_id,
        "tp_limit_price": cs_data.get("tp_limit_price"),
    })

print(f"Found {len(coins_to_replace)} TP orders to replace:\n")

for coin in coins_to_replace:
    sym = coin["symbol"]
    old_tp_id = coin["tp_order_id"]
    base = sym.split("/")[0]
    aster_sym = f"{sym}:USDT"
    
    # Get actual exchange position for qty and entry price
    positions = exchange.fetch_positions([aster_sym])
    pos = None
    for p in positions:
        if p.get("symbol") == aster_sym and abs(float(p.get("contracts", 0))) > 0:
            pos = p
            break
    
    if not pos:
        print(f"  {sym}: No position found, skipping")
        continue
    
    qty = abs(float(pos.get("contracts", 0)))
    entry_price = float(pos.get("entryPrice", 0))
    activation_price = round(entry_price * (1 + TP_PCT), 6)
    
    print(f"  {sym}:")
    print(f"    Position: {qty} @ ${entry_price}")
    print(f"    Old TP (limit): order {old_tp_id}")
    print(f"    New activation: ${activation_price}")
    print(f"    Trail callback: {CALLBACK_RATE}%")
    
    # Step 1: Cancel old limit TP
    try:
        exchange.cancel_order(old_tp_id, aster_sym)
        print(f"    ✅ Cancelled old limit TP {old_tp_id}")
    except Exception as e:
        print(f"    ❌ Cancel failed: {e}")
        continue
    
    time.sleep(1)
    
    # Step 2: Place trailing stop
    try:
        order = exchange.create_order(
            symbol=aster_sym,
            type="TRAILING_STOP_MARKET",
            side="sell",
            amount=qty,
            params={
                "quantity": str(qty),
                "activationPrice": str(activation_price),
                "callbackRate": str(CALLBACK_RATE),
                "positionSide": "BOTH",
                "reduceOnly": "true",
            }
        )
        new_id = order.get("id")
        print(f"    ✅ Trailing stop placed: order {new_id}")
        print(f"    activatePrice={order.get('info', {}).get('activatePrice')}, "
              f"priceRate={order.get('info', {}).get('priceRate')}%")
        
        # Update state file so bot picks up new order ID on next cycle
        state["coins"][sym]["tp_order_id"] = new_id
        state["coins"][sym]["tp_limit_price"] = activation_price
        state["coins"][sym]["tp_type"] = "trailing"
        state["coins"][sym]["tp_activation_price"] = activation_price
        state["coins"][sym]["trailing_callback_pct"] = CALLBACK_RATE
        
    except Exception as e:
        print(f"    ❌ Trailing stop failed: {e}")
        print(f"    ⚠️  Position has NO TP order! Placing limit sell as fallback...")
        try:
            fb = exchange.create_limit_sell_order(
                aster_sym, qty, activation_price,
                params={"timeInForce": "GTC", "positionSide": "BOTH", "reduceOnly": True}
            )
            fb_id = fb.get("id")
            print(f"    ✅ Fallback limit TP placed: {fb_id}")
            state["coins"][sym]["tp_order_id"] = fb_id
            state["coins"][sym]["tp_limit_price"] = activation_price
            state["coins"][sym]["tp_type"] = "limit"
        except Exception as e2:
            print(f"    ❌ CRITICAL: Fallback also failed: {e2}")
    
    time.sleep(1)

# Save updated state
tmp_path = state_path + ".tmp"
with open(tmp_path, "w") as f:
    json.dump(state, f, indent=2)
os.replace(tmp_path, state_path)
print(f"\n✅ State file updated with new order IDs")

# Verify all orders are on exchange
print(f"\n--- Verification ---")
for sym in [c["symbol"] for c in coins_to_replace]:
    aster_sym = f"{sym}:USDT"
    try:
        orders = exchange.fetch_open_orders(aster_sym)
        for o in orders:
            otype = o.get("info", {}).get("type", o.get("type", "?"))
            print(f"  {sym}: order {o['id']} type={otype} status={o.get('status')}")
    except Exception as e:
        print(f"  {sym}: verify failed: {e}")

print("\nDone.")
