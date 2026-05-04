"""Verify the callback changes."""
path = r"C:\Users\Never\.openclaw\workspace\trading\spot\run_v14_portfolio_live_aster.py"
with open(path, encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if "TRAILING_CALLBACK_PCT" in line and "import" not in line:
            print(f"L{i}: {line.rstrip()}")
        if "callback_rate" in line and "float" in line:
            print(f"L{i}: {line.rstrip()}")
