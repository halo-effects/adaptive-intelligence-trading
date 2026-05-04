"""Restore protected source files from git history."""
import subprocess, os

base = r"C:\Users\Never\.openclaw\workspace"
os.chdir(base)

# Files to restore and the commit that has the known good version
restores = {
    "trading/spot/v14_capital_manager.py": "f4526ff15",
    "trading/spot/engine/v14_dca_engine.py": "f4526ff15",
    "trading/spot/v14_lifecycle_engine.py": "f4526ff15",
}

for fpath, commit in restores.items():
    result = subprocess.run(
        ["git", "show", f"{commit}:{fpath}"],
        capture_output=True
    )
    if result.returncode != 0:
        print(f"ERROR: {fpath} from {commit}: {result.stderr.decode()}")
        continue
    
    full_path = os.path.join(base, fpath.replace("/", os.sep))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "wb") as f:
        f.write(result.stdout)
    print(f"Restored {fpath} ({len(result.stdout)} bytes)")

# Verify compile
import py_compile
for fpath in restores:
    full_path = os.path.join(base, fpath.replace("/", os.sep))
    try:
        py_compile.compile(full_path, doraise=True)
        print(f"  Compiles OK: {fpath}")
    except py_compile.PyCompileError as e:
        print(f"  COMPILE ERROR: {fpath}: {e}")
