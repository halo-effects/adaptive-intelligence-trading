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

# Exchange positions
positions = exchange.fetch_positions()
open_pos = [p for p in positions if abs(float(p.get("contracts", 0))) > 0]
print(f"Exchange positions: {len(open_pos)}")
for p in open_pos:
    sym = p.get("symbol", "?")
    qty = float(p.get("contracts", 0))
    entry = float(p.get("entryPrice", 0))
    notional = abs(float(p.get("notional", 0)))
    upnl = float(p.get("unrealizedPnl", 0))
    print(f"  {sym}: qty={qty}, entry=${entry:.4f}, notional=${notional:.2f}, uPnL=${upnl:.2f}")

# State file engines
state_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json"
with open(state_path) as f:
    state = json.load(f)

coins = state.get("coins", {})
print(f"\nState file engines: {len(coins)}")
active_with_pos = 0
idle = 0
for sym, cs in coins.items():
    eng = cs.get("engine_state", {})
    lc = eng.get("long_coins", 0)
    layers = eng.get("long_layers", 0)
    cost = eng.get("long_cost", 0)
    alloc = cs.get("allocated_capital", 0)
    tp_type = cs.get("tp_type", "?")
    if lc > 0:
        active_with_pos += 1
        print(f"  {sym}: ACTIVE L{layers}, coins={lc}, cost=${cost:.2f}, alloc=${alloc:.2f}, tp={tp_type}")
    else:
        idle += 1
        print(f"  {sym}: IDLE, alloc=${alloc:.2f}, eng_cap=${eng.get('capital', 0):.2f}")

print(f"\nActive with positions: {active_with_pos}")
print(f"Idle engines: {idle}")
print(f"Total engines: {len(coins)}")

# Open orders
all_orders = exchange.fetch_open_orders()
print(f"\nOpen orders: {len(all_orders)}")
for o in all_orders:
    sym = o.get("symbol", "?")
    otype = o.get("info", {}).get("type", "?")
    side = o.get("side", "?")
    qty = o.get("amount", "?")
    act = o.get("info", {}).get("activatePrice", "")
    print(f"  {sym}: {otype} {side} qty={qty} activate={act}")

# Balance
balance = exchange.fetch_balance()
free = float(balance.get("USDT", {}).get("free", 0))
total = float(balance.get("USDT", {}).get("total", 0))
print(f"\nUSDT: free=${free:.2f}, total=${total:.2f}")

# Check bot log for recent rebalance
print("\n--- Recent bot log (rebalance/engine creation) ---")
