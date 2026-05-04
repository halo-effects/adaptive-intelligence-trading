"""Restore architecture docs from git history."""
import subprocess, os

base = r"C:\Users\Never\.openclaw\workspace"
os.chdir(base)
commit = "f4526ff15"

docs = [
    "projects/ait-product/TRAILING_STOP_DESIGN.md",
    "projects/ait-product/TRAILING_STOP_IMPLEMENTATION_PLAN.md",
    "projects/ait-product/V14PM_ARCHITECTURE_INDEX.md",
    "projects/ait-product/V14PM_CHANGE_CONTROL.md",
    "projects/ait-product/V14PM_COMPREHENSIVE_AUDIT_REPORT.md",
    "projects/ait-product/V14PM_PHASE1_AUDIT_RESULTS.md",
    "projects/ait-product/V14PM_PHASE2_AUDIT_RESULTS.md",
    "projects/ait-product/V14PM_PHASE3_AUDIT_RESULTS.md",
    "projects/ait-product/V14PM_PRODUCTION_CLONE_GUIDE.md",
    "projects/ait-product/V14PM_SYSTEM_ARCHITECTURE.md",
    "projects/ait-product/V14PM_UPGRADE_SCOPE.md",
]

restored = 0
for fpath in docs:
    result = subprocess.run(["git", "show", f"{commit}:{fpath}"], capture_output=True)
    if result.returncode != 0:
        print(f"SKIP: {fpath}")
        continue
    full = os.path.join(base, fpath.replace("/", os.sep))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as f:
        f.write(result.stdout)
    print(f"OK: {fpath} ({len(result.stdout)} bytes)")
    restored += 1

print(f"\nRestored {restored} docs")
