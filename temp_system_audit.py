"""Full system audit: what's actually running, what files exist, what state says."""
import os, sys, json, subprocess

print("=" * 70)
print("  V14PM LIVE SYSTEM AUDIT")
print("=" * 70)

# 1. PROCESSES
print("\n1. RUNNING PROCESSES")
print("-" * 40)
result = subprocess.run(
    ["powershell", "-Command",
     "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
     "ForEach-Object { \"PID $($_.ProcessId): $($_.CommandLine)\" }"],
    capture_output=True, text=True
)
for line in result.stdout.strip().split("\n"):
    if "v14" in line.lower() or "trading" in line.lower():
        print(f"  {line.strip()[:120]}")

# 2. SOURCE FILES
print("\n2. SOURCE FILES")
print("-" * 40)
critical_files = [
    "trading/spot/run_v14_portfolio_live_aster.py",
    "trading/spot/v14_capital_manager.py",
    "trading/spot/v14_lifecycle_engine.py",
    "trading/spot/engine/v14_dca_engine.py",
    "trading/spot/v14_cycle_scanner.py",
]
base = r"C:\Users\Never\.openclaw\workspace"
for f in critical_files:
    full = os.path.join(base, f)
    if os.path.exists(full):
        size = os.path.getsize(full)
        print(f"  ✅ {f} ({size:,} bytes)")
    else:
        print(f"  ❌ MISSING: {f}")

# 3. GITIGNORE CHECK
print("\n3. GITIGNORE PROTECTION")
print("-" * 40)
gi_path = os.path.join(base, ".gitignore")
if os.path.exists(gi_path):
    with open(gi_path) as f:
        gi = f.read()
    for cf in critical_files[:2]:
        if cf in gi:
            print(f"  ✅ {cf} in .gitignore")
        else:
            print(f"  ❌ {cf} NOT in .gitignore")

# 4. STATE FILE
print("\n4. STATE FILE")
print("-" * 40)
state_path = os.path.join(base, "trading/spot/live/v14pm/state.json")
if os.path.exists(state_path):
    with open(state_path) as f:
        state = json.load(f)
    coins = state.get("coins", {})
    print(f"  Coins in state: {len(coins)} -> {list(coins.keys())}")
    print(f"  Capital: ${state.get('capital', '?')}")
    print(f"  Tracked capital: ${state.get('tracked_capital', '?')}")
    for sym, cs in coins.items():
        eng = cs.get("engine_state", {})
        lc = eng.get("long_coins", 0)
        layers = eng.get("long_layers", 0)
        cost = eng.get("long_cost", 0)
        tp = cs.get("tp_type", "?")
        tp_id = cs.get("tp_order_id", "?")
        print(f"    {sym}: L{layers}, coins={lc}, cost=${cost:.2f}, tp_type={tp}, tp_order={tp_id}")
else:
    print(f"  ❌ State file missing!")

# 5. EXCHANGE STATE
print("\n5. EXCHANGE STATE")
print("-" * 40)
sys.path.insert(0, base)
from dotenv import load_dotenv
load_dotenv(os.path.join(base, ".env"))
import ccxt
exchange = ccxt.aster({
    "apiKey": os.getenv("ASTER_API_KEY"),
    "secret": os.getenv("ASTER_API_SECRET"),
    "options": {"defaultType": "swap"},
})
exchange.load_markets()

positions = exchange.fetch_positions()
open_pos = [(p["symbol"], float(p["contracts"]), float(p.get("entryPrice",0)), float(p.get("unrealizedPnl",0)))
            for p in positions if abs(float(p.get("contracts", 0))) > 0]
print(f"  Open positions: {len(open_pos)}")
for sym, qty, entry, upnl in open_pos:
    print(f"    {sym}: qty={qty}, entry=${entry:.4f}, uPnL=${upnl:.2f}")

all_orders = exchange.fetch_open_orders()
print(f"  Open orders: {len(all_orders)}")
for o in all_orders:
    otype = o.get("info", {}).get("type", "?")
    sym = o.get("symbol", "?")
    act = o.get("info", {}).get("activatePrice", "")
    print(f"    {sym}: {otype} {o['side']} qty={o.get('amount')} activate={act}")

balance = exchange.fetch_balance()
free = float(balance.get("USDT", {}).get("free", 0))
total = float(balance.get("USDT", {}).get("total", 0))
print(f"  USDT: free=${free:.2f}, total=${total:.2f}")

# 6. TIER MATH
print("\n6. TIER MATH")
print("-" * 40)
from trading.spot.v14_capital_manager import EQUITY_TIER_CAPS, CapitalRouter
for min_eq, max_coins in EQUITY_TIER_CAPS:
    if total >= min_eq:
        print(f"  Equity ${total:.2f} -> tier {max_coins} coins (threshold ${min_eq})")
        break

# 7. MISMATCHES
print("\n7. MISMATCHES")
print("-" * 40)
state_syms = set(coins.keys()) if os.path.exists(state_path) else set()
exchange_syms = {sym.replace(":USDT","").replace("/USDT","") for sym, _, _, _ in open_pos}
state_bases = {s.replace("/USDT","") for s in state_syms}

in_state_not_exchange = state_bases - exchange_syms
in_exchange_not_state = exchange_syms - state_bases
if in_state_not_exchange:
    print(f"  ⚠️  In state but not on exchange: {in_state_not_exchange}")
if in_exchange_not_state:
    print(f"  ⚠️  On exchange but not in state: {in_exchange_not_state}")
if not in_state_not_exchange and not in_exchange_not_state:
    print(f"  ✅ State and exchange match: {state_bases}")

# Check tier compliance
if len(open_pos) > 3:
    print(f"  ❌ TIER VIOLATION: {len(open_pos)} positions open, tier cap = 3")
else:
    print(f"  ✅ Tier compliant: {len(open_pos)} positions, cap = 3")
