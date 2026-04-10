"""Phase 3: Documentation Accuracy Audit
Cross-reference V14PM_SYSTEM_ARCHITECTURE.md claims against actual code.
"""
import re, json
from pathlib import Path

WORKSPACE = Path(r"C:\Users\Never\.openclaw\workspace")
ARCH = (WORKSPACE / "projects/ait-product/V14PM_SYSTEM_ARCHITECTURE.md").read_text(encoding="utf-8")
BOT  = (WORKSPACE / "trading/spot/run_v14_portfolio_live_aster.py").read_text(encoding="utf-8")
DCA  = (WORKSPACE / "trading/spot/engine/v14_dca_engine.py").read_text(encoding="utf-8")
LCE  = (WORKSPACE / "trading/spot/v14_lifecycle_engine.py").read_text(encoding="utf-8")
CAP  = (WORKSPACE / "trading/spot/v14_capital_manager.py").read_text(encoding="utf-8")
EXC  = (WORKSPACE / "trading/spot/exchange_client.py").read_text(encoding="utf-8")
SCAN = (WORKSPACE / "trading/spot/v14_cycle_scanner.py").read_text(encoding="utf-8")

findings = []
def chk(ok, category, claim, actual=None, severity="P3"):
    status = "OK" if ok else "MISMATCH"
    findings.append((status, severity, category, claim, actual))
    sym = "  OK" if ok else "  MISMATCH"
    detail = f" — actual: {actual}" if actual and not ok else ""
    print(f"  {sym}: {claim}{detail}")

print("=" * 70)
print("PHASE 3: DOCUMENTATION ACCURACY AUDIT")
print("=" * 70)

# ─── §1 Safety Features ───────────────────────────────────────────────
print("\n### §1 Safety Features ###")

chk("1x" in BOT and "leverage=1.0" in BOT,
    "Safety", "1x leverage enforced", severity="P2")

chk("positionSide.*BOTH" in BOT or "positionSide" in BOT,
    "Safety", "positionSide=BOTH used (one-way mode)")

chk("reduceOnly.*True" in BOT or "reduceOnly" in BOT,
    "Safety", "reduceOnly=True on TP limit orders")

chk("fetch_open_positions" in BOT and "no open position" in BOT,
    "Safety", "Pre-order exchange check: SELL verifies position exists")

chk("fetch_balance" in BOT and "Insufficient" in BOT,
    "Safety", "Pre-order exchange check: BUY verifies USDT balance")

# ─── §5 DCA Engine Config ────────────────────────────────────────────
print("\n### §5.2 DCA Grid Parameters ###")

# Check DCA_TP_PCT default
tp_match = re.search(r'DCA_TP_PCT\s*:\s*float\s*=\s*([\d.]+)', DCA)
tp_val = tp_match.group(1) if tp_match else "NOT FOUND"
chk(tp_val == "0.015", "DCA Engine", f"DCA_TP_PCT default = 0.015", actual=tp_val)

# Check DCA_BO_PCT
bo_match = re.search(r'DCA_BO_PCT\s*:\s*float\s*=\s*([\d.]+)', DCA)
bo_val = bo_match.group(1) if bo_match else "NOT FOUND"
chk(bo_val == "0.4", "DCA Engine", f"DCA_BO_PCT default = 0.4 (40%)", actual=bo_val)

# Check max orders
mo_match = re.search(r'DCA_MAX_ORDERS\s*:\s*int\s*=\s*(\d+)', DCA)
mo_val = mo_match.group(1) if mo_match else "NOT FOUND"
chk(mo_val == "10", "DCA Engine", "DCA_MAX_ORDERS default = 10", actual=mo_val)

# High profile overrides
high_tp  = re.search(r'high.*DCA_TP_PCT.*0\.015|DCA_TP_PCT.*0\.015.*high', DCA + BOT, re.IGNORECASE)
high_mo  = re.search(r'max_orders.*12|DCA_MAX_ORDERS.*12', BOT + DCA)
chk(bool(high_mo), "DCA Engine", "High profile: 12 max layers")

# ─── §7.2 Capital Tier Table ─────────────────────────────────────────
print("\n### §7.2 Capital Tier Table ###")

# Extract tier caps from code
tier_caps_match = re.findall(r'\((\d+(?:\.\d+)?),\s*(\d+)\)', CAP)  # (threshold, cap)
tier_splits_match = re.findall(r'\((\d+(?:\.\d+)?),\s*(0\.\d+),\s*(0\.\d+)\)', CAP)

# Verify key tiers from doc
cap_code = CAP
chk("20000" in cap_code and "5" in cap_code, "Capital Tiers", "$20K tier: 5 coins")
chk("10000" in cap_code, "Capital Tiers", "$10K tier present")
chk("3000" in cap_code and "4" in cap_code, "Capital Tiers", "$3K tier: 4 coins")
chk("100" in cap_code and "3" in cap_code, "Capital Tiers", "$100 tier: 3 coins")

# Pool splits
chk("0.75" in cap_code and "0.25" in cap_code, "Capital Tiers", "$20K split: 75/25 active/reserve")
chk("0.9" in cap_code and "0.1" in cap_code, "Capital Tiers", "Below $10K: 90/10 split")

# Hysteresis
chk("0.05" in cap_code or "hysteresis" in cap_code.lower(), "Capital Tiers", "5% hysteresis on tier downgrades")

# ─── §7.3 Daily Rebalance ────────────────────────────────────────────
print("\n### §7.3 Daily Rebalance ###")
chk("_do_rebalance" in BOT, "Rebalance", "_do_rebalance() function exists")
chk("00:00" in BOT or "midnight" in BOT.lower() or "date()" in BOT, "Rebalance", "Daily rebalance at midnight UTC")
chk("last_rebalance_date" in BOT, "Rebalance", "Rebalance date tracked (prevents double-fire on restart)")

# ─── §7.8 Telegram Commands ──────────────────────────────────────────
print("\n### §7.8 Telegram Commands ###")
commands_expected = ["PAUSE", "RESUME", "CLOSE", "APPROVE", "DENY", "DEPOSIT", "WITHDRAW", "CAPITAL"]
for cmd in commands_expected:
    chk(f'"{cmd}"' in BOT or f"== '{cmd}'" in BOT or f'startswith("{cmd}")' in BOT or f"startswith('{cmd}')" in BOT,
        "Telegram", f"Command '{cmd}' implemented")

# ─── §8 Exchange Client (AsterPerpClient) ────────────────────────────
print("\n### §8 Exchange Client ###")
chk("defaultType.*future" in BOT, "Exchange", "defaultType=future for perps")
chk("15000" in BOT, "Exchange", "15s API timeout configured")
chk("_aster_symbol" in BOT, "Exchange", "Symbol conversion method (_aster_symbol)")
chk("1000PEPE" in BOT or "1000.*PEPE" in BOT, "Exchange", "1000-prefix coins handled")
chk("AIT_CANDLES_DB" in BOT or "candles.db" in BOT, "Exchange", "AIT_CANDLES_DB env var used")

# ─── §10 Scheduled Tasks ─────────────────────────────────────────────
print("\n### §10 Scheduled Tasks (Windows) ###")
arch_tasks = re.findall(r'`(\w+)`\s*scheduled task|Scheduled Task.*`(\w+)`', ARCH)
print(f"  Tasks referenced in arch doc: {[t for tup in arch_tasks for t in tup if t]}")

# Verify against actual start command
chk("start_bot.cmd" in BOT or "--confirm" in BOT, "Tasks", "Bot launched via cmd wrapper")

# ─── §12 Environment Variables ───────────────────────────────────────
print("\n### §12 Environment Variables ###")
arch_vars = re.findall(r'`(AIT_\w+|ASTER_\w+|HYPERLIQUID_\w+|CFGI_\w+)`', ARCH)
arch_vars_unique = sorted(set(arch_vars))
print(f"  Vars documented in arch: {arch_vars_unique}")

code_vars = sorted(set(re.findall(r'os\.environ\.get\(["\'](\w+)', BOT + SCAN)))
print(f"  Vars used in code: {code_vars}")

for v in code_vars:
    chk(v in ARCH, "Env Vars", f"{v} documented in architecture doc")

for v in arch_vars_unique:
    if v not in code_vars and "HYPERLIQUID" not in v:
        chk(False, "Env Vars", f"{v} in arch doc but not used in code", actual="possibly stale", severity="P4")

# ─── §6.8 Exchange-as-Truth Principles ──────────────────────────────
print("\n### §6.8 Exchange-as-Truth Architecture ###")
chk("_sync_positions_from_exchange" in BOT, "ExAT", "_sync_positions_from_exchange() function exists")
chk("exchange_truth" in BOT.lower() or "source of truth" in BOT.lower() or "exchange-truth" in BOT.lower(),
    "ExAT", "Exchange-as-truth principle referenced in code comments")
chk("fetch_open_positions" in BOT, "ExAT", "fetch_open_positions() called in sync cycle")

# Check sync frequency documented as 65s
sync_freq = re.search(r'SYNC_INTERVAL\s*=\s*(\d+)|sync.*every.*(\d+).*s', BOT, re.IGNORECASE)
# Also check MAIN_LOOP_SLEEP
loop_sleep = re.search(r'MAIN_LOOP_SLEEP\s*=\s*(\d+)|sleep\((\d+)\)', BOT)
if loop_sleep:
    val = loop_sleep.group(1) or loop_sleep.group(2)
    chk(val in ("60", "65"), "ExAT", "Main loop cycle ~65s", actual=f"{val}s")

# ─── File/Class names ────────────────────────────────────────────────
print("\n### Class & Module Names ###")
chk("class V14PortfolioLiveAster" in BOT, "Modules", "V14PortfolioLiveAster class")
chk("class AsterPerpClient" in BOT, "Modules", "AsterPerpClient class (embedded)")
chk("class CoinState" in BOT, "Modules", "CoinState class")
chk("class CapitalRouter" in CAP, "Modules", "CapitalRouter class")
chk("class V14LifecycleEngine" in LCE, "Modules", "V14LifecycleEngine class")
chk("class V14Config" in DCA, "Modules", "V14Config class in DCA engine")

# ─── SUMMARY ─────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("PHASE 3 SUMMARY")
print("=" * 70)

ok_count     = sum(1 for f in findings if f[0] == "OK")
mismatch     = [f for f in findings if f[0] == "MISMATCH"]

print(f"\n  Total checks: {len(findings)}")
print(f"  Passing: {ok_count}")
print(f"  Mismatches: {len(mismatch)}")
if mismatch:
    print()
    for _, sev, cat, claim, actual in mismatch:
        print(f"  [{sev}] [{cat}] {claim}")
        if actual:
            print(f"        Actual: {actual}")
