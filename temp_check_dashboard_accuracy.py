"""Compare status.json (dashboard source) against exchange truth."""
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

# Exchange state
positions = exchange.fetch_positions()
ex_pos = {}
for p in positions:
    if abs(float(p.get("contracts", 0))) > 0:
        sym = p["symbol"].replace(":USDT", "").replace("/USDT", "")
        ex_pos[sym] = {
            "qty": float(p["contracts"]),
            "entry": float(p["entryPrice"]),
            "upnl": float(p.get("unrealizedPnl", 0)),
            "notional": abs(float(p.get("notional", 0))),
        }

orders = exchange.fetch_open_orders()
ex_orders = {}
for o in orders:
    sym = o["symbol"].replace(":USDT", "").replace("/USDT", "")
    ex_orders[sym] = {
        "type": o.get("info", {}).get("type", "?"),
        "activate": o.get("info", {}).get("activatePrice", ""),
        "id": o["id"],
    }

balance = exchange.fetch_balance()
total_usdt = float(balance.get("USDT", {}).get("total", 0))

# Status.json
status_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json"
with open(status_path) as f:
    status = json.load(f)

print("DASHBOARD vs EXCHANGE COMPARISON")
print("=" * 60)

# Check each coin in status
status_coins = status.get("coins", {})
print(f"\nStatus.json coins: {len(status_coins)}")
print(f"Exchange positions: {len(ex_pos)}")

if set(c.replace("/USDT","") for c in status_coins) != set(ex_pos.keys()):
    print(f"  ❌ MISMATCH: status={list(status_coins.keys())}, exchange={list(ex_pos.keys())}")
else:
    print(f"  ✅ Coins match")

for sym, sc in status_coins.items():
    base = sym.replace("/USDT", "")
    ex = ex_pos.get(base)
    eo = ex_orders.get(base)
    print(f"\n  {sym}:")
    
    if not ex:
        print(f"    ❌ Not on exchange!")
        continue
    
    # Entry price
    s_entry = sc.get("avg_entry", 0)
    if abs(s_entry - ex["entry"]) > 0.01:
        print(f"    ❌ Entry: status={s_entry}, exchange={ex['entry']}")
    else:
        print(f"    ✅ Entry: ${s_entry}")
    
    # Layers
    print(f"    Layers: {sc.get('layers', '?')}")
    
    # TP type
    s_tp_type = sc.get("tp_type", "?")
    e_tp_type = eo.get("type", "?") if eo else "NO ORDER"
    tp_match = (s_tp_type == "trailing" and "TRAILING" in e_tp_type) or (s_tp_type == "limit" and e_tp_type == "LIMIT")
    if tp_match:
        print(f"    ✅ TP type: {s_tp_type} (exchange: {e_tp_type})")
    else:
        print(f"    ❌ TP type: status={s_tp_type}, exchange={e_tp_type}")
    
    # TP price
    s_tp = sc.get("next_tp_price", 0)
    print(f"    TP price: ${s_tp}")

# Overall equity
s_equity = status.get("equity", 0)
print(f"\nEquity: status=${s_equity}, exchange_total=${total_usdt:.2f}")

# Check staleness
updated = status.get("updated_at", status.get("timestamp", "?"))
print(f"Status.json last updated: {updated}")

# Check GitHub Pages version
print(f"\nDashboard URL: https://halo-effects.github.io/adaptive-intelligence-trading/d-984ae0d4ab9dc1a5.html")
