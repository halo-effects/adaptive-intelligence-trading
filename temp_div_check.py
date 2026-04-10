"""Check which division risks have zero-guards within 5 lines above"""
import re
from pathlib import Path

WORKSPACE = Path(r"C:\Users\Never\.openclaw\workspace")

# Critical division risks from Phase 1
risks = [
    ("trading/spot/v14_lifecycle_engine.py", 173, "peak"),
    ("trading/spot/v14_capital_manager.py", 352, "total_score"),
    ("trading/spot/v14_cycle_scanner.py", 196, "total_qty"),
    ("trading/spot/v14_cycle_scanner.py", 220, "total_qty"),
    ("trading/spot/v14_cycle_scanner.py", 306, "total_weeks"),
    ("trading/spot/v14_cycle_scanner.py", 307, "n_deals"),
    ("trading/spot/v14_cycle_scanner.py", 323, "alloc"),
    ("trading/spot/engine/v14_dca_engine.py", 409, "price"),
    ("trading/spot/engine/v14_dca_engine.py", 525, "price"),
    ("trading/spot/engine/v14_dca_engine.py", 950, "capital"),
    ("trading/spot/engine/v13_router_engine_v2.py", 116, "loss"),
    ("trading/spot/engine/v13_signals.py", 36, "avg_loss"),
    ("trading/spot/engine/v13_signals.py", 42, "denom"),
    ("trading/spot/coin_scanner.py", 179, "max_dd"),
    ("trading/spot/generate_daily_equity.py", 90, "total_csv_pnl"),
    ("trading/spot/generate_daily_equity.py", 158, "INITIAL_CAPITAL"),
]

print("DIVISION RISK ANALYSIS (checking for zero-guards)")
print("=" * 70)

for rel_path, line_num, var_name in risks:
    full = WORKSPACE / rel_path
    lines = full.read_text(encoding="utf-8").splitlines()
    
    # Check 5 lines above for zero-guard
    context_start = max(0, line_num - 6)
    context = lines[context_start:line_num]
    target_line = lines[line_num - 1].strip()
    
    guarded = False
    for ctx_line in context:
        ctx = ctx_line.strip()
        # Check for zero guards
        if any(pat in ctx for pat in [
            f'{var_name} > 0', f'{var_name} != 0', f'{var_name} == 0',
            f'{var_name} <= 0', f'{var_name} < 0',
            f'if {var_name}', f'if not {var_name}',
            f'{var_name} or ', f'max({var_name}',
            '> 0:', '!= 0:', '== 0:',
        ]):
            guarded = True
            break
        # Also check for "if n_deals" style
        if var_name in ctx and ('if ' in ctx or 'or ' in ctx or '> 0' in ctx):
            guarded = True
            break

    status = "GUARDED" if guarded else "UNGUARDED"
    flag = "" if guarded else " *** RISK"
    print(f"  [{status}] {rel_path.split('/')[-1]}:{line_num} / {var_name}{flag}")
    if not guarded:
        # Print context for unguarded ones
        for i, ctx_line in enumerate(context):
            ln = context_start + i + 1
            print(f"    {ln}: {ctx_line.rstrip()[:100]}")
        print(f"    {line_num}: {target_line[:100]}")
        print()
