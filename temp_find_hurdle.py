"""Find where the 5.0 hurdle rate is enforced."""
import os, re

base = r"C:\Users\Never\.openclaw\workspace\trading\spot"
for root, dirs, files in os.walk(base):
    for f in files:
        if not f.endswith(".py"):
            continue
        path = os.path.join(root, f)
        try:
            with open(path, encoding="utf-8") as fh:
                for i, line in enumerate(fh, 1):
                    if any(k in line.lower() for k in ["hurdle", "min_score", "score_threshold", ">= 5", "< 5"]):
                        rel = os.path.relpath(path, base)
                        print(f"{rel}:{i}: {line.rstrip()[:100]}")
        except:
            pass
