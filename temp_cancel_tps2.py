"""Cancel specific TP orders and verify."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
os.chdir(os.path.dirname(__file__))

from trading.spot.exchange_client import SpotExchangeClient

client = SpotExchangeClient()
client.connect("aster")

# These are the TP order IDs from bot log
orders_to_cancel = {
    "TAOUSDT": "214700406",
    "HYPEUSDT": "1882176575",
    "JTOUSDT": "10466980",
}

# First fetch all open orders to confirm they exist
print("Fetching open orders...")
all_orders = client.fetch_open_orders()
print(f"Found {len(all_orders)} open orders")
for o in all_orders:
    sym = o.get("symbol", "?")
    oid = o.get("id", "?")
    side = o.get("side", "?")
    otype = o.get("type", "?")
    price = o.get("price", "?")
    print(f"  {sym} {side} {otype} #{oid} @ {price}")

# Cancel each one
for sym, oid in orders_to_cancel.items():
    try:
        # CCXT uses symbol format like TAO/USDT:USDT for perps
        ccxt_sym = sym.replace("USDT", "/USDT:USDT")
        result = client.cancel_order(oid, ccxt_sym)
        print(f"CANCELLED: {sym} #{oid}")
    except Exception as e:
        print(f"Cancel {sym} #{oid}: {e}")

# Verify
print("\nVerifying no orders remain...")
remaining = client.fetch_open_orders()
print(f"Remaining orders: {len(remaining)}")
for o in remaining:
    print(f"  {o.get('symbol')} {o.get('side')} #{o.get('id')}")
