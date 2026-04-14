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

# All open positions
positions = exchange.fetch_positions()
open_pos = [p for p in positions if abs(float(p.get("contracts", 0))) > 0]
print(f"Open positions: {len(open_pos)}\n")
for p in open_pos:
    sym = p.get("symbol", "?")
    qty = float(p.get("contracts", 0))
    entry = float(p.get("entryPrice", 0))
    upnl = float(p.get("unrealizedPnl", 0))
    notional = float(p.get("notional", 0))
    print(f"  {sym}: qty={qty}, entry=${entry:.4f}, notional=${abs(notional):.2f}, uPnL=${upnl:.2f}")

# All open orders
all_orders = exchange.fetch_open_orders()
print(f"\nOpen orders: {len(all_orders)}")
for o in all_orders:
    otype = o.get("info", {}).get("type", "?")
    sym = o.get("symbol", "?")
    act_price = o.get("info", {}).get("activatePrice", "")
    print(f"  {sym}: id={o['id']} type={otype} side={o['side']} qty={o.get('amount')} activate={act_price}")

# Check state file
print("\n--- State file coins ---")
state_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\state.json"
with open(state_path) as f:
    state = json.load(f)
for sym, cs in state.get("coins", {}).items():
    eng = cs.get("engine_state", {})
    coins = eng.get("long_coins", 0)
    if coins > 0:
        print(f"  {sym}: coins={coins}, layers={eng.get('long_layers')}, cost=${eng.get('long_cost', 0):.2f}, tp_type={cs.get('tp_type')}")

# Check tier config
equity = float(state.get("equity", 0))
capital = float(state.get("capital", 0))
print(f"\nEquity: ${equity:.2f}, Capital: ${capital:.2f}")
print(f"Tier cap from state: {state.get('tier_coin_cap', '?')}")
print(f"Active symbols: {state.get('symbols', '?')}")
