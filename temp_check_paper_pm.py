"""Check V14PM Paper bot: how many coins active, what tier, what scanner says."""
import json

# Paper PM status
status_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json"
with open(status_path) as f:
    status = json.load(f)

coins = status.get("coins", {})
active = {sym: c for sym, c in coins.items() if c.get("layers", 0) > 0}
idle = {sym: c for sym, c in coins.items() if c.get("layers", 0) == 0}

equity = status.get("equity", 0)
capital = status.get("capital", 0)

print(f"Equity: ${equity:,.2f}")
print(f"Capital: ${capital:,.2f}")
print(f"Total engines: {len(coins)}")
print(f"Active (with positions): {len(active)}")
print(f"Idle (no position): {len(idle)}")

print(f"\nActive positions:")
for sym, c in active.items():
    layers = c.get("layers", 0)
    invested = c.get("invested", 0)
    upnl = c.get("unrealized_pnl", 0)
    alloc = c.get("allocated_capital", 0)
    print(f"  {sym}: L{layers}, invested=${invested:,.2f}, uPnL=${upnl:,.2f}, alloc=${alloc:,.2f}")

print(f"\nIdle engines:")
for sym, c in idle.items():
    alloc = c.get("allocated_capital", 0)
    print(f"  {sym}: alloc=${alloc:,.2f}")

# Tier math
import sys
sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")
from trading.spot.v14_capital_manager import EQUITY_TIER_CAPS
for min_eq, max_coins in EQUITY_TIER_CAPS:
    if equity >= min_eq:
        print(f"\nTier: ${min_eq:,}+ -> {max_coins} coins")
        print(f"Active positions: {len(active)} / {max_coins} slots")
        if len(active) < max_coins:
            print(f"  ⚠️ {max_coins - len(active)} empty slot(s)")
        break

# Check engine state for more detail
engine_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\engine_state.json"
try:
    with open(engine_path) as f:
        eng_state = json.load(f)
    engines = eng_state.get("engines", {})
    print(f"\nEngine state file: {len(engines)} engines")
    active_eng = 0
    for sym, e in engines.items():
        state = e.get("state", {})
        lc = state.get("long_coins", 0)
        sc = state.get("short_coins", 0)
        if lc > 0 or sc > 0:
            active_eng += 1
    print(f"Engines with positions: {active_eng}")
except Exception as ex:
    print(f"\nCouldn't read engine_state.json: {ex}")
