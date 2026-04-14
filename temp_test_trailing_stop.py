"""
Test TRAILING_STOP_MARKET order on Aster Perps.
Places a tiny trailing stop sell on GRASS/USDT with activation price
well above market so it never triggers. Then checks status and cancels.
"""
import os
import sys
import json
import time
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

# GRASS/USDT — we have a position, current price ~$0.33
symbol = "GRASS/USDT:USDT"

# Get current price
ticker = exchange.fetch_ticker(symbol)
current_price = ticker["last"]
print(f"GRASS current price: ${current_price}")

# Set activation price well above market (won't trigger)
activation_price = round(current_price * 1.20, 4)  # 20% above market
callback_rate = 0.5  # 0.5% trail
qty = 10.0  # 10 GRASS = ~$3.30 (min lot = 0.1)

print(f"\nTest order:")
print(f"  Type: TRAILING_STOP_MARKET")
print(f"  Side: SELL")
print(f"  Symbol: {symbol}")
print(f"  Qty: {qty}")
print(f"  Activation: ${activation_price} (20% above market)")
print(f"  Callback: {callback_rate}%")
print(f"  reduceOnly: True")

# Attempt to place the order
try:
    order = exchange.create_order(
        symbol=symbol,
        type="TRAILING_STOP_MARKET",
        side="sell",
        amount=qty,
        params={
            "activationPrice": activation_price,
            "callbackRate": callback_rate,
            "positionSide": "BOTH",
            "reduceOnly": True,
        }
    )
    order_id = order.get("id")
    print(f"\n✅ Order placed successfully!")
    print(f"  Order ID: {order_id}")
    print(f"  Status: {order.get('status')}")
    print(f"  Type: {order.get('type')}")
    print(f"  Full response:")
    print(json.dumps(order, indent=2, default=str))
except Exception as e:
    print(f"\n❌ Order FAILED: {e}")
    print(f"  Error type: {type(e).__name__}")
    if hasattr(e, 'args') and len(e.args) > 0:
        print(f"  Details: {e.args[0]}")
    sys.exit(1)

# Check order status
print(f"\n--- Checking order status ---")
time.sleep(2)
try:
    status = exchange.fetch_order(order_id, symbol)
    print(f"  Status: {status.get('status')}")
    print(f"  Type: {status.get('type')}")
    print(f"  Info keys: {list(status.get('info', {}).keys())}")
except Exception as e:
    print(f"  Status check failed: {e}")

# Check if it shows in open orders
print(f"\n--- Checking open orders ---")
try:
    open_orders = exchange.fetch_open_orders(symbol)
    trailing_orders = [o for o in open_orders if o.get("id") == order_id]
    print(f"  Found in open orders: {len(trailing_orders) > 0}")
    if trailing_orders:
        print(f"  Order type: {trailing_orders[0].get('type')}")
except Exception as e:
    print(f"  Open orders check failed: {e}")

# Cancel the test order
print(f"\n--- Cancelling test order ---")
try:
    cancel = exchange.cancel_order(order_id, symbol)
    print(f"  ✅ Cancelled successfully")
    print(f"  Cancel status: {cancel.get('status')}")
except Exception as e:
    print(f"  ❌ Cancel failed: {e}")

# Verify it's gone
print(f"\n--- Verifying cancellation ---")
time.sleep(1)
try:
    final = exchange.fetch_order(order_id, symbol)
    print(f"  Final status: {final.get('status')}")
except Exception as e:
    print(f"  Verification: {e}")

print(f"\n{'='*60}")
print("TEST COMPLETE")
