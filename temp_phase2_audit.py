"""Phase 2: Component-Level Logic Audit"""
import ast
import re
from pathlib import Path
from collections import defaultdict

WORKSPACE = Path(r"C:\Users\Never\.openclaw\workspace")
BOT = WORKSPACE / "trading" / "spot" / "run_v14_portfolio_live_aster.py"

findings = []

def add(severity, component, title, detail, line=None):
    findings.append({
        "severity": severity,
        "component": component, 
        "title": title,
        "detail": detail,
        "line": line,
    })

# ═══════════════════════════════════════════════════════════════════════
# COMPONENT 1: AsterPerpClient (embedded in main bot)
# ═══════════════════════════════════════════════════════════════════════
print("=== COMPONENT 1: AsterPerpClient ===")
bot_src = BOT.read_text(encoding="utf-8")
bot_lines = bot_src.splitlines()

# Check: create_market_buy returns {} on failure — caller must check
print("  Checking buy/sell failure returns...")
# The caller does: if result and result.get("status") in ("filled", "dry_run")
# Empty dict {} is falsy, so `if result` catches it. GOOD.

# Check: fetch_balance returns 0.0 on error — not distinguishable from actual 0 balance
print("  Checking fetch_balance error handling...")
add("P3", "AsterPerpClient", "fetch_balance returns 0.0 on error",
    "Cannot distinguish between 'API call failed' and 'wallet is actually empty'. "
    "Both return 0.0. The BUY pre-check would skip buying (correct behavior) but "
    "wouldn't alert that the API itself is down.", line=337)

# Check: fetch_ticker_price returns 0.0 on error — used for TP calculation
print("  Checking fetch_ticker_price error path...")
add("P3", "AsterPerpClient", "fetch_ticker_price returns 0.0 on error",
    "If API fails, returns 0.0. Used in TP calculation fallback path. "
    "Could cause 0-price TP. Mitigated by exchange-as-truth TP (uses exchange entry price, "
    "not ticker).", line=371)

# Check: 1000-prefix coin handling consistency
print("  Checking 1000-prefix scaling consistency...")
prefix_methods = ["create_market_buy", "create_market_sell", "place_limit_sell", 
                  "fetch_open_positions", "check_order_status", "fetch_ticker_price"]
for method in prefix_methods:
    pattern = f"def {method}"
    idx = bot_src.find(pattern)
    if idx > 0:
        chunk = bot_src[idx:idx+800]
        has_prefix = "PEPE" in chunk or "1000" in chunk
        if not has_prefix:
            add("P2", "AsterPerpClient", f"{method} missing 1000-prefix handling",
                f"Method doesn't handle PEPE/BONK/FLOKI prefix scaling", 
                line=bot_src[:idx].count('\n')+1)

# Check: timeout is set
if "timeout" in bot_src[bot_src.find("class AsterPerpClient"):bot_src.find("class AsterPerpClient")+500]:
    print("  Timeout configured: YES")
else:
    add("P2", "AsterPerpClient", "No timeout on exchange API", "Calls could hang indefinitely")

# ═══════════════════════════════════════════════════════════════════════
# COMPONENT 2: Exception Handler Classification (main bot)
# ═══════════════════════════════════════════════════════════════════════
print("\n=== COMPONENT 2: Exception Handler Classification ===")

# Parse the AST to find all try/except blocks
tree = ast.parse(bot_src)

silent_catches = []  # except: pass or except Exception: pass
swallowing = []      # except that doesn't re-raise or return
appropriate = []     # exchange/telegram/file I/O catches

for node in ast.walk(tree):
    if isinstance(node, ast.ExceptHandler):
        # Get the body
        body = node.body
        if len(body) == 1 and isinstance(body[0], ast.Pass):
            silent_catches.append(node.lineno)
        elif len(body) == 1 and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            silent_catches.append(node.lineno)

# Check which handlers just log and continue vs log and return
for i, line in enumerate(bot_lines, 1):
    stripped = line.strip()
    if stripped.startswith("except Exception") or stripped == "except:":
        # Look at the next few lines for the handler body
        handler_lines = []
        for j in range(i, min(i+5, len(bot_lines))):
            handler_lines.append(bot_lines[j].strip())
        
        has_pass = any(l == "pass" for l in handler_lines)
        has_return = any("return" in l for l in handler_lines)
        has_log = any("logger." in l or "log(" in l for l in handler_lines)
        has_raise = any("raise" in l for l in handler_lines)
        
        if has_pass and not has_log:
            silent_catches.append(i)

print(f"  Silent catches (except: pass without logging): {len(set(silent_catches))}")
for ln in sorted(set(silent_catches)):
    ctx = bot_lines[ln-1].strip() if ln <= len(bot_lines) else ""
    print(f"    line {ln}: {ctx[:100]}")

# ═══════════════════════════════════════════════════════════════════════
# COMPONENT 3: State Save/Restore Fidelity
# ═══════════════════════════════════════════════════════════════════════
print("\n=== COMPONENT 3: State Save/Restore Fidelity ===")

# Extract fields saved in _save_state
save_start = bot_src.find("def _save_state(self):")
save_end = bot_src.find("\n    def ", save_start + 1)
save_block = bot_src[save_start:save_end]

# Extract fields restored in _load_state
load_start = bot_src.find("def _load_state(self)")
load_end = bot_src.find("\n    def ", load_start + 1)
load_block = bot_src[load_start:load_end]

# Check for fields saved but not loaded (or vice versa)
# Simple approach: look for key names in both blocks
save_keys = set(re.findall(r'"(\w+)":', save_block))
load_keys = set(re.findall(r'\.get\("(\w+)"', load_block))

saved_not_loaded = save_keys - load_keys - {"saved_at", "_code_version"}
loaded_not_saved = load_keys - save_keys

print(f"  Keys in save: {len(save_keys)}")
print(f"  Keys in load: {len(load_keys)}")
if saved_not_loaded:
    print(f"  SAVED but NOT LOADED: {saved_not_loaded}")
    add("P2", "State Persistence", "Fields saved but not restored",
        f"These fields are written to state.json but not read back on restart: {saved_not_loaded}")
if loaded_not_saved:
    print(f"  LOADED but NOT SAVED: {loaded_not_saved}")
    add("P2", "State Persistence", "Fields loaded but not saved",
        f"These fields are expected in state.json but not written: {loaded_not_saved}")
if not saved_not_loaded and not loaded_not_saved:
    print("  All keys round-trip correctly.")

# ═══════════════════════════════════════════════════════════════════════
# COMPONENT 4: Candle Dedup Check
# ═══════════════════════════════════════════════════════════════════════
print("\n=== COMPONENT 4: Candle Dedup Logic ===")

# Check if there's a dedup mechanism
if "last_candle_ts" in bot_src:
    print("  last_candle_ts field exists: YES")
    # Check where it's compared
    dedup_lines = [i+1 for i, l in enumerate(bot_lines) if "last_candle_ts" in l]
    print(f"  Referenced at lines: {dedup_lines}")
    # Check the comparison logic
    for ln in dedup_lines:
        print(f"    {ln}: {bot_lines[ln-1].strip()[:120]}")
else:
    add("P1", "Candle Processing", "No candle dedup mechanism",
        "Known issue: candles are processed multiple times per hour")

# ═══════════════════════════════════════════════════════════════════════
# COMPONENT 5: Telegram Command Parsing Safety
# ═══════════════════════════════════════════════════════════════════════
print("\n=== COMPONENT 5: Telegram Command Parsing ===")

# Find the command handler
cmd_start = bot_src.find("def _process_telegram_commands")
if cmd_start > 0:
    cmd_end = bot_src.find("\n    def ", cmd_start + 1)
    cmd_block = bot_src[cmd_start:cmd_end]
    
    # Check for command injection risks
    if "eval(" in cmd_block or "exec(" in cmd_block:
        add("P1", "Telegram Commands", "Code injection risk", 
            "eval() or exec() used on Telegram input")
    else:
        print("  No eval/exec on user input: SAFE")
    
    # Check authorized user validation
    if "AIT_TG_CHAT_ID" in cmd_block or "chat_id" in cmd_block:
        print("  Chat ID authorization: YES")
    else:
        add("P1", "Telegram Commands", "No authorization check",
            "Commands not validated against authorized chat ID")
    
    # List all recognized commands
    commands = re.findall(r'text\s*==\s*["\'](\w+)', cmd_block)
    commands += re.findall(r'text\.startswith\(["\'](\w+)', cmd_block)
    commands += re.findall(r'upper\(\)\s*==\s*["\'](\w+)', cmd_block)
    commands += re.findall(r'\.upper\(\)\.startswith\(["\'](\w+)', cmd_block)
    print(f"  Recognized commands: {sorted(set(commands))}")

# ═══════════════════════════════════════════════════════════════════════
# COMPONENT 6: Main Loop Error Recovery
# ═══════════════════════════════════════════════════════════════════════
print("\n=== COMPONENT 6: Main Loop Error Recovery ===")

# Find the main loop
main_loop_start = bot_src.find("def run(self):")
if main_loop_start > 0:
    main_block = bot_src[main_loop_start:main_loop_start+2000]
    
    # Check for outer try/except
    if "while True:" in main_block or "while self" in main_block:
        print("  Main loop found")
        if "except Exception" in main_block or "except:" in main_block:
            print("  Outer exception handler: YES (loop continues on error)")
        else:
            add("P2", "Main Loop", "No outer exception handler",
                "Unhandled exception in main loop would crash the bot")
    
    # Check for graceful shutdown
    if "signal.signal" in bot_src or "SIGTERM" in bot_src or "SIGINT" in bot_src:
        print("  Signal handler for graceful shutdown: YES")
    else:
        add("P2", "Main Loop", "No signal handler",
            "SIGTERM/SIGINT not caught — systemd stop may not save state")

# ═══════════════════════════════════════════════════════════════════════
# COMPONENT 7: CapitalRouter Edge Cases
# ═══════════════════════════════════════════════════════════════════════
print("\n=== COMPONENT 7: CapitalRouter Edge Cases ===")
cm_src = (WORKSPACE / "trading/spot/v14_capital_manager.py").read_text(encoding="utf-8")

# Check: What happens when equity drops below minimum tier?
if "< 100" in cm_src or "below minimum" in cm_src.lower():
    print("  Below-minimum-tier handling: present")
else:
    # Check the tier table
    tier_lines = [l for l in cm_src.splitlines() if "100" in l and "tier" in l.lower()]
    print(f"  Minimum tier threshold check: needs verification")
    add("P3", "CapitalRouter", "Below-minimum tier behavior unclear",
        "If equity drops below $100, tier_coin_cap = 0. Verify bot handles 0-coin allocation gracefully.")

# Check: negative allocation handling
if "< 0" in cm_src or "negative" in cm_src.lower() or "max(0" in cm_src:
    print("  Negative allocation guard: present")
    
# Check: rounding errors in allocation
if "round(" in cm_src:
    print("  Rounding in allocation: present (check for dust)")

# ═══════════════════════════════════════════════════════════════════════
# COMPONENT 8: DCA Engine Edge Cases
# ═══════════════════════════════════════════════════════════════════════
print("\n=== COMPONENT 8: DCA Engine Edge Cases ===")
dca_src = (WORKSPACE / "trading/spot/engine/v14_dca_engine.py").read_text(encoding="utf-8")

# Check: max layers guard
if "max_layers" in dca_src.lower() or "MAX_LAYERS" in dca_src or "DCA_MAX_ORDERS" in dca_src:
    print("  Max layers limit: present")
else:
    add("P2", "DCA Engine", "No max layers guard", "Could add infinite layers")

# Check: TP price validation
tp_lines = [i+1 for i, l in enumerate(dca_src.splitlines()) if "long_tp" in l and "=" in l]
print(f"  TP price assignments at lines: {tp_lines[:10]}")

# Check: fee deduction
if "fee" in dca_src.lower() and ("taker" in dca_src.lower() or "maker" in dca_src.lower()):
    print("  Fee simulation: present (taker/maker)")

# ═══════════════════════════════════════════════════════════════════════
# COMPONENT 9: Lifecycle Engine
# ═══════════════════════════════════════════════════════════════════════
print("\n=== COMPONENT 9: Lifecycle Engine ===")
lce_src = (WORKSPACE / "trading/spot/v14_lifecycle_engine.py").read_text(encoding="utf-8")

# Check: warmup period
if "warmup" in lce_src.lower():
    print("  Warmup period: implemented")

# Check: reject_action covers all action types
reject_start = lce_src.find("def reject_action")
reject_block = lce_src[reject_start:reject_start+1500]
supported = re.findall(r"action_type\s*(?:not\s+)?in\s*\(([^)]+)\)", reject_block)
print(f"  reject_action supports: {supported}")

# Check: snapshot_state / restore_state round-trip
if "snapshot_state" in lce_src and "restore_state" in lce_src:
    print("  State snapshot/restore: both present")

# ═══════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("PHASE 2 FINDINGS SUMMARY")
print("=" * 70)

by_sev = defaultdict(list)
for f in findings:
    by_sev[f["severity"]].append(f)

for sev in ["P1", "P2", "P3", "P4"]:
    items = by_sev.get(sev, [])
    if items:
        print(f"\n  {sev} ({len(items)} findings):")
        for f in items:
            line_str = f" (line {f['line']})" if f['line'] else ""
            print(f"    [{f['component']}] {f['title']}{line_str}")
            print(f"      {f['detail'][:150]}")

total = len(findings)
print(f"\n  Total: {total} findings ({len(by_sev.get('P1',[]))} P1, {len(by_sev.get('P2',[]))} P2, {len(by_sev.get('P3',[]))} P3)")
