"""Trace when new coins entered — specifically JUP, SUI, AVAX which weren't there before."""
import json
from pathlib import Path

# Check the bot log for recent BUY actions
import subprocess
result = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     r"Select-String -Path C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\bot.log -Pattern 'BUY|new engine|Engine created|rebalance|approved|tier_cap|active_count' | Select-Object -Last 60 | ForEach-Object { $_.Line.Trim().Substring(0, [Math]::Min(150, $_.Line.Trim().Length)) }"],
    capture_output=True, text=True, timeout=15
)
if result.stdout:
    lines = result.stdout.strip().split("\n")
    print(f"Recent bot activity ({len(lines)} entries):")
    for line in lines[-40:]:
        print(f"  {line}")
else:
    print("No bot log matches found")
    # Try a different log path
    log_paths = list(Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio").glob("*.log"))
    print(f"Log files found: {[p.name for p in log_paths]}")
