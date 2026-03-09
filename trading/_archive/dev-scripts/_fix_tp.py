"""One-shot: cancel old LONG TP and place new one at 1.5%."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from trading.aster_trader import AsterAPI, round_price

api = AsterAPI()

# Cancel old LONG TP
try:
    r = api.cancel_order("HYPEUSDT", 1396474252)
    print(f"Cancelled old TP: {r.get('status','')}")
except Exception as e:
    print(f"Cancel error: {e}")

# Place new TP at 1.5% above avg entry
avg_entry = 31.412781818181816
new_tp = round_price(avg_entry * 1.015)
print(f"New TP price: ${new_tp}")

try:
    r = api.place_order("HYPEUSDT", "SELL", "LIMIT", 0.55, price=new_tp)
    print(f"New TP placed: id={r.get('orderId','')} status={r.get('status','')}")
except Exception as e:
    print(f"Place error: {e}")
