import re
from pathlib import Path
bot = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\run_v14_portfolio_live_aster.py").read_text(encoding="utf-8")
cap = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\v14_capital_manager.py").read_text(encoding="utf-8")

# Q3: Per-coin pause capital behavior
print("Q3 - Paused coin capital:")
for i, l in enumerate(bot.splitlines()):
    s = l.strip()
    if "paused" in s.lower() and ("skip" in s.lower() or "alloc" in s.lower()):
        safe = s.encode("ascii", "replace").decode()[:120]
        print(f"  L{i+1}: {safe}")

for i, l in enumerate(cap.splitlines()):
    s = l.strip()
    if "paused" in s.lower():
        safe = s.encode("ascii", "replace").decode()[:120]
        print(f"  cap L{i+1}: {safe}")

# Check what happens to paused coin's allocation in rebalance
print("\nRebalance paused handling:")
rebal_start = bot.find("_do_rebalance")
rebal_block = bot[rebal_start:rebal_start+2000]
for l in rebal_block.splitlines():
    if "paused" in l.lower() or "skip" in l.lower():
        safe = l.strip().encode("ascii", "replace").decode()[:120]
        print(f"  {safe}")
