"""Trace the TP catch-up bug: find where TP gets set to 0.0000"""
import re
from pathlib import Path

# Read the lifecycle engine
lce = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\v14_lifecycle_engine.py").read_text(encoding="utf-8")
paper = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\run_v14_portfolio_paper.py").read_text(encoding="utf-8")

print("=== TP CATCH-UP CODE in v14_lifecycle_engine.py ===\n")

# Find the TP catch-up method
idx = lce.find("tp_catch")
if idx < 0:
    idx = lce.find("TP catch")
if idx < 0:
    idx = lce.find("tp_catchup")
if idx < 0:
    # Search for the log message we saw
    idx = lce.find("Live TP catch-up")

if idx > 0:
    # Find the method that contains this
    # Go backwards to find def
    method_start = lce.rfind("\n    def ", 0, idx)
    if method_start < 0:
        method_start = lce.rfind("\ndef ", 0, idx)
    # Go forward to find next def
    next_def = lce.find("\n    def ", idx)
    if next_def < 0:
        next_def = lce.find("\ndef ", idx)
    if next_def < 0:
        next_def = idx + 2000
    
    block = lce[method_start:next_def]
    lines = block.split("\n")
    for i, l in enumerate(lines[:80]):
        print(f"  {l}")
else:
    print("  'TP catch-up' not found in lifecycle engine")
    # Search all files
    for pattern in ["tp_catch", "TP catch", "daily boundary", "catch_up_tp"]:
        matches = [(i+1, l.strip()) for i, l in enumerate(lce.splitlines()) if pattern.lower() in l.lower()]
        if matches:
            print(f"\n  Pattern '{pattern}' found:")
            for ln, l in matches:
                print(f"    L{ln}: {l[:150]}")

print("\n\n=== TP PRICE INITIALIZATION ===")
# Find where long_tp or tp_price is set
tp_sets = [(i+1, l.strip()) for i, l in enumerate(lce.splitlines()) 
           if ("tp_price" in l or "long_tp" in l or "_tp " in l) and ("=" in l) and not l.strip().startswith("#")]
for ln, l in tp_sets[:20]:
    print(f"  L{ln}: {l[:150]}")

print("\n\n=== TP IN PAPER BOT ===")
tp_paper = [(i+1, l.strip()) for i, l in enumerate(paper.splitlines())
            if ("tp" in l.lower() and ("catch" in l.lower() or "price" in l.lower() or "target" in l.lower()))
            and not l.strip().startswith("#")]
for ln, l in tp_paper[:20]:
    safe = l.encode("ascii", "replace").decode()
    print(f"  L{ln}: {safe[:150]}")
