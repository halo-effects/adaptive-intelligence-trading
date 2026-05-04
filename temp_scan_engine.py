import re
for path in [
    r"C:\Users\Never\.openclaw\workspace\trading\spot\engine\v14_dca_engine.py",
    r"C:\Users\Never\.openclaw\workspace\trading\spot\v14_lifecycle_engine.py",
]:
    print(f"\n=== {path.split('spot\\\\')[-1] if '\\\\' in path else path.split('spot/')[-1]} ===")
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if any(p in line.lower() for p in ["trailing", "callback", "trail"]):
                print(f"  {i}: {line.rstrip()[:120]}")
