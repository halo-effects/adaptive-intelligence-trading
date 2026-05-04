"""Check trailing stop config values in engine."""
path = r"C:\Users\Never\.openclaw\workspace\trading\spot\engine\v14_dca_engine.py"
with open(path, encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if any(k in line for k in ["TRAILING_STOP", "TRAILING_CALLBACK", "BO_PCT", "TAKER_FEE", "DCA_TP_PCT"]):
            print(f"L{i}: {line.rstrip()}")

print("\n--- Scanner ---")
path2 = r"C:\Users\Never\.openclaw\workspace\trading\spot\v14_cycle_scanner.py"
with open(path2, encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if any(k in line for k in ["BO_PCT", "TAKER_FEE", "FEE", "0.40", "0.00025"]):
            if not line.strip().startswith("#"):
                print(f"L{i}: {line.rstrip()}")

print("\n--- Paper PM bot scanner usage ---")
path3 = r"C:\Users\Never\.openclaw\workspace\trading\spot\run_v14_portfolio_paper.py"
with open(path3, encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if "scanner" in line.lower() or "cycle_scanner" in line.lower() or "hurdle" in line.lower():
            print(f"L{i}: {line.rstrip()}")
