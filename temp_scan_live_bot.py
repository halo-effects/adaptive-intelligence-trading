"""Scan live bot file for all trailing stop references."""
path = r"C:\Users\Never\.openclaw\workspace\trading\spot\run_v14_portfolio_live_aster.py"
import re
patterns = ["TRAILING", "callback", "CALLBACK", "trail", "0.5", "priceRate", "activat"]
with open(path, encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        for p in patterns:
            if p.lower() in line.lower() and "test" not in line.lower():
                print(f"{i}: {line.rstrip()[:130]}")
                break
