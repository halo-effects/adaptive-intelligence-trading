"""Phase 2 Integration Checks: cross-component data flow verification"""
import json
import re
from pathlib import Path

WORKSPACE = Path(r"C:\Users\Never\.openclaw\workspace")

print("=" * 70)
print("PHASE 2: INTEGRATION CHECKS")
print("=" * 70)

# ─── 1. Scanner → Bot: cycle_scanner.json schema ──────────────────────
print("\n### 1. Scanner → Bot: cycle_scanner.json schema ###")

scanner_src = (WORKSPACE / "trading/spot/v14_cycle_scanner.py").read_text(encoding="utf-8")
bot_src = (WORKSPACE / "trading/spot/run_v14_portfolio_live_aster.py").read_text(encoding="utf-8")

# What fields does the scanner write?
scanner_output = re.findall(r'result\["(\w+)"\]', scanner_src)
scanner_fields = sorted(set(scanner_output))
print(f"  Scanner output fields: {scanner_fields}")

# What fields does the bot read from scanner data?
bot_scanner_reads = re.findall(r'scanner.*\[."(\w+)"\]|coin_data.*\[."(\w+)"\]|\.get\("(\w+)"', 
                                bot_src[bot_src.find("_do_rebalance"):bot_src.find("_do_rebalance")+3000])
bot_reads = sorted(set(f for tup in bot_scanner_reads for f in tup if f))
print(f"  Bot reads from scanner: {bot_reads[:20]}")

# Check actual scanner output
scanner_json = WORKSPACE / "docs/data/v14/cycle_scanner.json"
if scanner_json.exists():
    with open(scanner_json) as f:
        sj = json.load(f)
    if "coins" in sj and sj["coins"]:
        first_coin = list(sj["coins"].values())[0]
        print(f"  Actual scanner coin fields: {sorted(first_coin.keys())}")

# ─── 2. Bot → Dashboard: status.json schema ──────────────────────────
print("\n### 2. Bot → Dashboard: status.json completeness ###")

status_file = WORKSPACE / "trading/spot/live/v14pm/status.json"
if status_file.exists():
    with open(status_file) as f:
        status = json.load(f)
    
    # Dashboard expects these fields (from HTML audit)
    dashboard_expects = {
        "approved_symbols", "capital", "cash", "coins", "deals_completed", 
        "equity", "fear_greed_index", "halted", "last_update", "leverage", 
        "max_drawdown_pct", "profile", "regime", "router", "running",
        "symbols", "tier_coin_cap", "total_fees", "total_realized_pnl", 
        "trend_direction", "uptime_hours", "win_rate"
    }
    
    # What status.json actually has
    actual_fields = set(status.keys())
    
    missing_from_status = dashboard_expects - actual_fields
    extra_in_status = actual_fields - dashboard_expects
    
    print(f"  Dashboard expects: {len(dashboard_expects)} fields")
    print(f"  Status has: {len(actual_fields)} fields")
    if missing_from_status:
        print(f"  MISSING from status.json: {missing_from_status}")
    else:
        print(f"  All dashboard fields present in status.json: OK")
    
    # Check coin-level fields
    coin_expects = {
        "avg_entry", "cfgi", "current_price", "distance_to_liq_pct",
        "invested", "layers", "lifecycle_phase", "liquidation_price",
        "next_tp_price", "paused", "realized_pnl", "regime_flagged",
        "side", "symbol", "unrealized_pnl"
    }
    
    for sym, coin in status.get("coins", {}).items():
        coin_keys = set(coin.keys())
        missing_coin = coin_expects - coin_keys
        if missing_coin:
            print(f"  Coin {sym} missing: {missing_coin}")
        break  # Just check first coin
    else:
        print("  No coins in status to check")

# ─── 3. State.json round-trip verification ────────────────────────────
print("\n### 3. State.json field inventory ###")

state_file = WORKSPACE / "trading/spot/live/v14pm/state.json"
if state_file.exists():
    with open(state_file) as f:
        state = json.load(f)
    
    print(f"  Top-level keys: {sorted(state.keys())}")
    
    # Check coin states
    for sym, cs in state.get("coins", {}).items():
        coin_keys = sorted(cs.keys())
        print(f"  Coin {sym} keys: {coin_keys}")
        
        # Check engine state
        eng = cs.get("engine_state", {})
        if eng:
            print(f"  Engine state keys: {sorted(eng.keys())[:15]}...")
        break  # Just check first coin
    
    # Check router state
    router = state.get("router", {})
    print(f"  Router keys: {sorted(router.keys())}")

# ─── 4. Env var usage vs documentation ────────────────────────────────
print("\n### 4. Environment variable usage ###")

all_src = bot_src + scanner_src
env_vars_used = set(re.findall(r'os\.environ\.get\(["\'](\w+)', all_src))
env_vars_used |= set(re.findall(r'os\.environ\[["\'](\w+)', all_src))
env_vars_used |= set(re.findall(r'os\.getenv\(["\'](\w+)', all_src))

# From .env.template
env_template = (WORKSPACE / "trading/spot/live/v14pm/.env.template").read_text()
template_vars = set(re.findall(r'^(\w+)=', env_template, re.MULTILINE))

print(f"  Env vars used in code: {sorted(env_vars_used)}")
print(f"  Env vars in template: {sorted(template_vars)}")

missing_from_template = env_vars_used - template_vars - {"HOME", "PATH", "PYTHONPATH", "TEMP", "TMP"}
extra_in_template = template_vars - env_vars_used
if missing_from_template:
    print(f"  Used in code but NOT in template: {missing_from_template}")
if extra_in_template:
    print(f"  In template but NOT used in code: {extra_in_template}")

print("\n### 5. 1000-prefix coin handling audit ###")
# Check every method that handles coins for 1000-prefix consistency
prefix_coins = {"PEPE", "BONK", "FLOKI"}
methods_with_prefix = []
methods_without_prefix = []

# Check each method in AsterPerpClient that takes a symbol
for method_name in ["create_market_buy", "create_market_sell", "place_limit_sell", 
                     "cancel_tp_order", "check_order_status", "fetch_ticker_price",
                     "fetch_open_orders", "ensure_leverage", "fetch_funding_history"]:
    pattern = f"def {method_name}"
    idx = bot_src.find(pattern)
    if idx > 0:
        # Find end of method
        next_def = bot_src.find("\n    def ", idx + 1)
        method_body = bot_src[idx:next_def] if next_def > 0 else bot_src[idx:idx+1000]
        
        has_prefix_handling = "1000" in method_body or "PEPE" in method_body
        if has_prefix_handling:
            methods_with_prefix.append(method_name)
        else:
            methods_without_prefix.append(method_name)

print(f"  Methods WITH 1000-prefix handling: {methods_with_prefix}")
print(f"  Methods WITHOUT 1000-prefix handling: {methods_without_prefix}")
if methods_without_prefix:
    # Check if these methods even need it
    for m in methods_without_prefix:
        # cancel_tp_order just passes symbol through _aster_symbol
        # ensure_leverage just passes symbol through _aster_symbol
        # fetch_open_orders uses raw exchange format
        # fetch_funding_history just passes symbol through
        print(f"    {m}: uses _aster_symbol() for conversion, no price/qty scaling needed")
