"""Restore the scanner from f4526ff15 which has all corrections."""
import subprocess, os

base = r"C:\Users\Never\.openclaw\workspace"
os.chdir(base)

result = subprocess.run(
    ["git", "show", "f4526ff15:trading/spot/v14_cycle_scanner.py"],
    capture_output=True
)
if result.returncode != 0:
    print(f"ERROR: {result.stderr.decode()}")
    exit(1)

path = os.path.join(base, "trading", "spot", "v14_cycle_scanner.py")
with open(path, "wb") as f:
    f.write(result.stdout)
print(f"Restored ({len(result.stdout)} bytes)")

# Verify key features
content = result.stdout.decode("utf-8")
checks = {
    "BO_PCT 0.30": "BO_PCT = 0.30" in content,
    "TAKER_FEE 0.00035": "0.00035" in content,
    "TRADEABLE": "TRADEABLE" in content,
    "hurdle": "hurdle" in content.lower() or "5.0" in content,
}
for k, v in checks.items():
    print(f"  {'✅' if v else '❌'} {k}")

import py_compile
py_compile.compile(path, doraise=True)
print("Compiles OK")
