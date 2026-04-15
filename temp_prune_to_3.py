"""Close 4 excess positions (keep TAO + JTO + best scorer), prune state to 3."""
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

# Current positions on exchange
positions = exchange.fetch_positions()
open_pos = {}
for p in positions:
    sym = p.get("symbol", "")
    contracts = float(p.get("contracts", 0))
    if abs(contracts) > 0:
        base = sym.replace(":USDT", "").replace("/USDT", "")
        open_pos[base] = {
            "symbol": sym,
            "qty": contracts,
            "entry": float(p.get("entryPrice", 0)),
            "notional": abs(float(p.get("notional", 0))),
            "upnl": float(p.get("unrealizedPnl", 0)),
        }

print(f"Open positions: {len(open_pos)}")
for b, p in open_pos.items():
    print(f"  {b}: qty={p['qty']}, notional=${p['notional']:.2f}, uPnL=${p['upnl']:.2f}")

# Keep TAO (L2, biggest position) + JTO (L1) + pick the smallest loss to close
# Actually let's keep TAO + JTO + the one with best uPnL among the rest
keep = {"TAO", "JTO"}
others = {b: p for b, p in open_pos.items() if b not in keep}

# Pick best (least negative uPnL) from others
best_other = max(others.items(), key=lambda x: x[1]["upnl"])
keep.add(best_other[0])
print(f"\nKeeping: {keep} (3rd slot: {best_other[0]} with uPnL=${best_other[1]['upnl']:.2f})")

to_close = {b: p for b, p in open_pos.items() if b not in keep}
print(f"Closing: {list(to_close.keys())}")

# Close positions and cancel orders
for base, pos in to_close.items():
    sym = pos["symbol"]
    qty = abs(pos["qty"])
    print(f"\n  Closing {base} ({qty} @ ${pos['entry']:.4f})...")
    
    # Cancel all open orders first
    try:
        orders = exchange.fetch_open_orders(sym)
        for o in orders:
            exchange.cancel_order(o["id"], sym)
            print(f"    Cancelled order {o['id']}")
    except Exception as e:
        print(f"    Cancel orders error: {e}")
    
    time.sleep(0.5)
    
    # Market close
    try:
        result = exchange.create_order(
            symbol=sym, type="market", side="sell", amount=qty,
            params={"positionSide": "BOTH", "reduceOnly": "true"}
        )
        avg = result.get("average") or result.get("info", {}).get("avgPrice", "?")
        print(f"    Closed at ${avg}")
    except Exception as e:
        print(f"    Close error: {e}")
    
    time.sleep(0.5)

# Update state file — keep only the 3 coins
state_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json"
with open(state_path) as f:
    state = json.load(f)

keep_syms = {f"{b}/USDT" for b in keep}
coins = state.get("coins", {})
to_remove = [s for s in coins if s not in keep_syms]
for s in to_remove:
    del coins[s]
    print(f"  Removed engine: {s}")

# Save
tmp = state_path + ".tmp"
with open(tmp, "w") as f:
    json.dump(state, f, indent=2)
os.replace(tmp, state_path)

print(f"\nState: {list(coins.keys())}")

# Final balance
balance = exchange.fetch_balance()
free = float(balance.get("USDT", {}).get("free", 0))
total = float(balance.get("USDT", {}).get("total", 0))
print(f"USDT: free=${free:.2f}, total=${total:.2f}")
