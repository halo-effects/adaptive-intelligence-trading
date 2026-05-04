"""Scan all relevant files for trailing callback references."""
import os, re

base = r"C:\Users\Never\.openclaw\workspace"
files_to_scan = []

# Trading code
for root, dirs, files in os.walk(os.path.join(base, "trading", "spot")):
    for f in files:
        if f.endswith(".py"):
            files_to_scan.append(os.path.join(root, f))

# Dashboard
files_to_scan.append(os.path.join(base, "docs", "dashboardV14PM.html"))
files_to_scan.append(os.path.join(base, "docs", "d-984ae0d4ab9dc1a5.html"))

# Architecture docs
for f in os.listdir(os.path.join(base, "projects", "ait-product")):
    if f.endswith(".md"):
        files_to_scan.append(os.path.join(base, "projects", "ait-product", f))

# HEARTBEAT
files_to_scan.append(os.path.join(base, "HEARTBEAT.md"))

patterns = [
    r"TRAILING_CALLBACK",
    r"callback_pct",
    r"callbackRate",
    r"CALLBACK_PCT",
    r"trailing.*0\.5",
    r"0\.5%.*trail",
    r"trail.*0\.5%",
    r"TRAIL 0\.5",
    r"priceRate",
]

for fpath in files_to_scan:
    if not os.path.exists(fpath):
        continue
    try:
        with open(fpath, encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                for pat in patterns:
                    if re.search(pat, line, re.IGNORECASE):
                        fname = os.path.relpath(fpath, base)
                        print(f"{fname}:{i}: {line.rstrip()[:120]}")
                        break
    except:
        pass
