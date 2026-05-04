"""Audit what each bot file imports from the protected source files."""
import re, os

base = r"C:\Users\Never\.openclaw\workspace\trading\spot"
bots = {
    "V14PM Live": "run_v14_portfolio_live_aster.py",
    "V14 Paper": "run_v14_paper.py",
    "V14PM Paper": "run_v14_portfolio_paper.py",
}

# Find ETF runner
for f in os.listdir(base):
    if f.startswith("run_v14etf") and f.endswith(".py"):
        bots["V14-ETF Paper"] = f

protected = ["v14_dca_engine", "v14_lifecycle_engine", "v14_capital_manager", "v14_cycle_scanner"]

for label, filename in bots.items():
    path = os.path.join(base, filename)
    if not os.path.exists(path):
        print(f"\n{label} ({filename}): FILE MISSING")
        continue
    print(f"\n{label} ({filename}):")
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if line.startswith(("import ", "from ")) and any(p in line for p in protected):
                print(f"  L{i}: {line}")
