#!/usr/bin/env python3
"""V12e Backtest Runner — ReversalDetector + graduated F&G tiers.

Runs ETH and SOL backtests across all 3 profiles (low/medium/high).
"""
import sys, json, subprocess
from pathlib import Path

PYTHON = r"C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe"
RUNNER = str(Path(__file__).resolve().parent / "run_v12_chained.py")
RESULTS_DIR = Path(__file__).resolve().parent / "backtest_results" / "v12_lifecycle"

RUNS = [
    {"preset": "eth", "profile": "low"},
    {"preset": "eth", "profile": "medium"},
    {"preset": "eth", "profile": "high"},
    {"preset": "sol", "profile": "low"},
    {"preset": "sol", "profile": "medium"},
    {"preset": "sol", "profile": "high"},
]

def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    for run in RUNS:
        preset = run["preset"]
        profile = run["profile"]
        out_file = RESULTS_DIR / f"{preset}_1h_v12e_{profile}.json"
        
        print(f"\n{'='*60}")
        print(f"  V12e: {preset.upper()} {profile}")
        print(f"  Output: {out_file}")
        print(f"{'='*60}\n")
        
        cmd = [
            PYTHON, RUNNER,
            "--preset", preset,
            "--profile", profile,
            "--timeframe", "1h",
        ]
        
        env = dict(__import__('os').environ)
        env["PYTHONIOENCODING"] = "utf-8"
        
        result = subprocess.run(cmd, env=env, capture_output=False)
        
        # The runner saves as v12d — rename to v12e
        v12d_file = RESULTS_DIR / f"{preset}_1h_v12d_{profile}.json"
        if v12d_file.exists():
            # Read, update, and save as v12e
            data = json.loads(v12d_file.read_text())
            v12d_file.rename(out_file)
            print(f"  Saved: {out_file}")
        
        if result.returncode != 0:
            print(f"  ERROR: returncode={result.returncode}")

if __name__ == "__main__":
    main()
