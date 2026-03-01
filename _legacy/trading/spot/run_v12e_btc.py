#!/usr/bin/env python3
"""V12e BTC Backtest Runner — all 3 profiles."""
import sys, json, subprocess, os
from pathlib import Path

PYTHON = r"C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe"
RUNNER = str(Path(__file__).resolve().parent / "run_v12_chained.py")
RESULTS_DIR = Path(__file__).resolve().parent / "backtest_results" / "v12_lifecycle"

PROFILES = ["low", "medium", "high"]

def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    for profile in PROFILES:
        out_file = RESULTS_DIR / f"btc_1h_v12e_{profile}.json"
        
        print(f"\n{'='*60}")
        print(f"  V12e: BTC {profile}")
        print(f"  Output: {out_file}")
        print(f"{'='*60}\n", flush=True)
        
        cmd = [
            PYTHON, RUNNER,
            "--preset", "btc",
            "--profile", profile,
            "--timeframe", "1h",
        ]
        
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        
        result = subprocess.run(cmd, env=env, capture_output=False)
        
        # The runner saves as v12d — rename to v12e
        v12d_file = RESULTS_DIR / f"btc_1h_v12d_{profile}.json"
        if v12d_file.exists():
            if out_file.exists():
                out_file.unlink()
            v12d_file.rename(out_file)
            print(f"  Saved: {out_file}")
        
        if result.returncode != 0:
            print(f"  ERROR: returncode={result.returncode}")
            
    # Print summaries
    print(f"\n{'='*60}")
    print("  BTC V12e RESULTS SUMMARY")
    print(f"{'='*60}\n")
    for profile in PROFILES:
        f = RESULTS_DIR / f"btc_1h_v12e_{profile}.json"
        if f.exists():
            d = json.loads(f.read_text())
            print(f"  {profile}: PnL={d.get('total_pnl_pct','?')}% | MaxDD={d.get('max_drawdown_pct','?')}% | Sharpe={d.get('sharpe_ratio','?')}")
        else:
            print(f"  {profile}: NOT FOUND")

if __name__ == "__main__":
    main()
