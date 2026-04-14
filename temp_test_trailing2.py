"""Test TRAILING_STOP_MARKET on Aster — try different param formats."""
import os, sys, json, time
sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")
from dotenv import load_dotenv
load_dotenv(r"C:\Users\Never\.openclaw\workspace\.env")
import ccxt

ex = ccxt.aster({
    "apiKey": os.getenv("ASTER_API_KEY"),
    "secret": os.getenv("ASTER_API_SECRET"),
    "options": {"defaultType": "swap"},
})
ex.load_markets()

symbol = "GRASS/USDT:USDT"
ticker = ex.fetch_ticker(symbol)
price = ticker["last"]
print(f"GRASS price: ${price}")

activation = round(price * 1.20, 4)
qty = 10.0

# Attempt 1: Use create_order with quantity in params explicitly
print("\n--- Attempt 1: quantity in params ---")
try:
    order = ex.create_order(
        symbol=symbol,
        type="TRAILING_STOP_MARKET",
        side="sell",
        amount=qty,
        params={
            "quantity": str(qty),
            "activationPrice": str(activation),
            "callbackRate": "0.5",
            "positionSide": "BOTH",
            "reduceOnly": "true",
        }
    )
    print(f"✅ SUCCESS: {order.get('id')}")
    print(json.dumps(order, indent=2, default=str))
    # Cancel immediately
    ex.cancel_order(order["id"], symbol)
    print("Cancelled.")
    sys.exit(0)
except Exception as e:
    print(f"❌ Failed: {e}")

# Attempt 2: Use private API directly
print("\n--- Attempt 2: private fapiPrivatePostOrder ---")
try:
    aster_sym = "GRASSUSDT"
    params = {
        "symbol": aster_sym,
        "side": "SELL",
        "type": "TRAILING_STOP_MARKET",
        "quantity": "10",
        "activationPrice": str(activation),
        "callbackRate": "0.5",
        "positionSide": "BOTH",
        "reduceOnly": "true",
        "timestamp": str(int(time.time() * 1000)),
    }
    result = ex.fapiPrivatePostOrder(params)
    print(f"✅ SUCCESS: {result}")
    # Cancel
    if result.get("orderId"):
        ex.fapiPrivateDeleteOrder({
            "symbol": aster_sym,
            "orderId": result["orderId"],
            "timestamp": str(int(time.time() * 1000)),
        })
        print("Cancelled.")
    sys.exit(0)
except Exception as e:
    print(f"❌ Failed: {e}")

# Attempt 3: Try STOP_MARKET first to see if basic stop orders work
print("\n--- Attempt 3: STOP_MARKET (simpler) ---")
try:
    stop_price = round(price * 0.80, 4)  # 20% below
    order = ex.create_order(
        symbol=symbol,
        type="STOP_MARKET",
        side="sell",
        amount=qty,
        params={
            "stopPrice": str(stop_price),
            "positionSide": "BOTH",
            "reduceOnly": "true",
        }
    )
    print(f"✅ STOP_MARKET works: {order.get('id')}")
    ex.cancel_order(order["id"], symbol)
    print("Cancelled.")
except Exception as e:
    print(f"❌ STOP_MARKET also failed: {e}")

print("\nDone.")
