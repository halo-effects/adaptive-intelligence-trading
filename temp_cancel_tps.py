"""Cancel all open sell orders on Aster (the limit TP orders)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
os.chdir(os.path.dirname(__file__))

from trading.spot.exchange_client import SpotExchangeClient

client = SpotExchangeClient()
client.connect("aster")

# Get all open orders
orders = client.fetch_open_orders()
print(f"Open orders: {len(orders)}")
for o in orders:
    sym = o.get("symbol", "?")
    side = o.get("side", "?")
    otype = o.get("type", "?")
    oid = o.get("id", o.get("orderId", "?"))
    price = o.get("price", o.get("stopPrice", "?"))
    print(f"  {sym} {side} {otype} #{oid} @ {price}")

# Cancel sell orders
cancelled = 0
for o in orders:
    if o.get("side", "").lower() == "sell":
        oid = o.get("id", o.get("orderId"))
        sym = o["symbol"]
        try:
            result = client.cancel_order(oid, sym)
            print(f"  CANCELLED: {sym} #{oid}")
            cancelled += 1
        except Exception as e:
            print(f"  FAILED: {sym} #{oid}: {e}")

print(f"\nTotal cancelled: {cancelled}")
