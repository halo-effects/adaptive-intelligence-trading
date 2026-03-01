#!/usr/bin/env python3
"""V12e Extended Backtest — Oct 2020 to Feb 2026 for all 3 coins, all 3 profiles.

Apples-to-apples comparison with uniform start date to capture additional Wyckoff cycles.
"""
import sys, json, subprocess, os
from pathlib import Path

PYTHON = r"C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe"
RUNNER = str(Path(__file__).resolve().parent / "run_v12_chained.py")
RESULTS_DIR = Path(__file__).resolve().parent / "backtest_results" / "v12_lifecycle"

START = "2020-10-01"
END = "2026-02-21"

RUNS = []
for coin in ["eth", "sol", "btc"]:
    for profile in ["low", "medium", "high"]:
        RUNS.append({"preset": coin, "profile": profile})


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    for run in RUNS:
        preset = run["preset"]
        profile = run["profile"]
        out_file = RESULTS_DIR / f"{preset}_1h_v12e_ext_{profile}.json"
        
        if out_file.exists():
            print(f"  SKIP (exists): {out_file.name}")
            continue
        
        print(f"\n{'='*60}")
        print(f"  V12e EXTENDED: {preset.upper()} {profile}")
        print(f"  Period: {START} -> {END}")
        print(f"  Output: {out_file}")
        print(f"{'='*60}\n")
        
        cmd = [
            PYTHON, RUNNER,
            "--preset", preset,
            "--profile", profile,
            "--timeframe", "1h",
            "--start", START,
            "--end", END,
        ]
        
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        
        result = subprocess.run(cmd, env=env, capture_output=False)
        
        # The runner saves as v12d — rename to v12e_ext
        v12d_file = RESULTS_DIR / f"{preset}_1h_v12d_{profile}.json"
        if v12d_file.exists():
            data = json.loads(v12d_file.read_text())
            with open(out_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
            v12d_file.unlink()
            print(f"  Saved: {out_file}")
        
        if result.returncode != 0:
            print(f"  ERROR: returncode={result.returncode}")

    # Summary
    print(f"\n\n{'='*60}")
    print("  SUMMARY — V12e Extended Backtests")
    print(f"{'='*60}")
    for coin in ["eth", "sol", "btc"]:
        for profile in ["low", "medium", "high"]:
            f = RESULTS_DIR / f"{coin}_1h_v12e_ext_{profile}.json"
            if f.exists():
                d = json.loads(f.read_text())[0]
                print(f"  {coin.upper()} {profile:7s}: PnL={d['pnl_pct']:+.1f}%  MaxDD={d['max_dd']:.1f}%  Sharpe={d['sharpe']:.2f}  Deals={d['total_deals']}")
            else:
                print(f"  {coin.upper()} {profile:7s}: MISSING")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
