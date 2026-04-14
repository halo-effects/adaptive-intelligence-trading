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

# Exchange balance
balance = exchange.fetch_balance()
usdt_free = float(balance.get("USDT", {}).get("free", 0))
usdt_total = float(balance.get("USDT", {}).get("total", 0))
usdt_used = float(balance.get("USDT", {}).get("used", 0))
print(f"Exchange USDT: free=${usdt_free:.2f}, used=${usdt_used:.2f}, total=${usdt_total:.2f}")

# All positions
positions = exchange.fetch_positions()
open_pos = [p for p in positions if abs(float(p.get("contracts", 0))) > 0]
total_invested = 0
print(f"\nOpen positions: {len(open_pos)}")
for p in open_pos:
    sym = p.get("symbol", "?")
    notional = abs(float(p.get("notional", 0)))
    margin = float(p.get("initialMargin", 0))
    total_invested += notional
    print(f"  {sym}: notional=${notional:.2f}, margin=${margin:.2f}")

print(f"\nTotal notional: ${total_invested:.2f}")
print(f"Free for new orders: ${usdt_free:.2f}")

# State file — check allocations
state_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json"
with open(state_path) as f:
    state = json.load(f)

print(f"\nState file capital: ${state.get('capital', '?')}")
print(f"Tracked capital: ${state.get('tracked_capital', '?')}")

# Check how many coins have engines and their allocation
print(f"\nCoin engines:")
for sym, cs in state.get("coins", {}).items():
    eng = cs.get("engine_state", {})
    alloc = cs.get("allocated_capital", 0)
    coins_held = eng.get("long_coins", 0)
    eng_cap = eng.get("capital", 0)
    layers = eng.get("long_layers", 0)
    cost = eng.get("long_cost", 0)
    print(f"  {sym}: alloc=${alloc:.2f}, eng_cap=${eng_cap:.2f}, coins={coins_held}, L{layers}, cost=${cost:.2f}")

# Router state
router = state.get("router_state", {})
print(f"\nRouter: active_pool=${router.get('active_pool_total', '?')}, reserve=${router.get('reserve_pool_total', '?')}")
print(f"Cap tier index: {router.get('cap_tier_index', '?')}")
print(f"Split tier index: {router.get('split_tier_index', '?')}")
