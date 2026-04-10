import re
from pathlib import Path
bot = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\run_v14_portfolio_live_aster.py").read_text(encoding="utf-8")
cap = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\v14_capital_manager.py").read_text(encoding="utf-8")

# Q1: Deposit threshold
drift_pct = re.findall(r'CAPITAL_DRIFT_MIN_PCT\s*=\s*([\d.]+)', bot)
drift_abs = re.findall(r'CAPITAL_DRIFT_MIN_ABS\s*=\s*([\d.]+)', bot)
print(f"Q1 - Drift PCT: {drift_pct}, Drift ABS: {drift_abs}")
idx = bot.find("_detect_capital")
if idx > 0:
    block = bot[idx:idx+600]
    for l in block.splitlines():
        if "drift" in l.lower() or "threshold" in l.lower() or "min_" in l.lower():
            print(f"  {l.strip()[:120]}")

# Q2: Withdrawal safety
print("\nQ2 - Withdrawal safety:")
for i, l in enumerate(bot.splitlines()):
    if "Cannot withdraw" in l or ("withdraw" in l.lower() and "invested" in l.lower()):
        print(f"  L{i+1}: {l.strip()[:120]}")

# Q3: Per-coin pause capital behavior
print("\nQ3 - Paused coin capital:")
for i, l in enumerate(bot.splitlines()):
    s = l.strip()
    if "paused" in s.lower() and ("skip" in s.lower() or "capital" in s.lower() or "alloc" in s.lower()):
        print(f"  L{i+1}: {s[:120]}")
# Also check CapitalRouter
for i, l in enumerate(cap.splitlines()):
    s = l.strip()
    if "paused" in s.lower() and ("skip" in s.lower() or "capital" in s.lower() or "alloc" in s.lower()):
        print(f"  cap L{i+1}: {s[:120]}")
