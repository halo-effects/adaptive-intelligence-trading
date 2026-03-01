#!/usr/bin/env python3
"""Batch V12e CFGI gate backtest: 3 coins × 3 profiles.
Runs 3 at a time (one per coin) to balance parallelism and CPU."""
import sys, json, os, subprocess, re, time
from pathlib import Path

PYTHON = r"C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe"
SCRIPT = str(Path(__file__).resolve().parent / "run_v12_chained.py")
RESULTS_DIR = Path(__file__).resolve().parent / "backtest_results" / "v12e_cfgi_gate"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

COINS = ["btc", "eth", "sol"]
PROFILES = ["low", "medium", "high"]

def run_profile_batch(profile):
    """Run all 3 coins for one profile in parallel."""
    procs = {}
    for coin in COINS:
        key = f"{coin}_{profile}"
        out_f = open(RESULTS_DIR / f"{key}_output.txt", "w")
        err_f = open(RESULTS_DIR / f"{key}_err.txt", "w")
        p = subprocess.Popen(
            [PYTHON, SCRIPT, "--preset", coin, "--profile", profile],
            stdout=out_f, stderr=err_f,
            cwd=str(Path(__file__).resolve().parent.parent.parent)
        )
        procs[key] = {"proc": p, "out_f": out_f, "err_f": err_f}
        print(f"  Started {key} (PID {p.pid})", flush=True)
    
    # Wait for all
    for key, info in procs.items():
        info["proc"].wait()
        info["out_f"].close()
        info["err_f"].close()
        print(f"  Finished {key} (exit={info['proc'].returncode})", flush=True)

def parse_output(filepath):
    """Extract key metrics from run_v12_chained.py stdout."""
    try:
        output = open(filepath).read()
    except:
        return {}
    metrics = {}
    patterns = {
        "roi_pct": r"PnL:\s+([\+\-]?\d+\.?\d*)%",
        "max_dd": r"Max DD:\s+(\d+\.?\d*)%",
        "sharpe": r"Sharpe:\s+([\-]?\d+\.?\d*)",
        "final_equity": r"Final equity:\s+\$([0-9,]+\.?\d*)",
        "deals": r"Deals:\s+(\d+)",
        "win_rate": r"Win\s+(\d+\.?\d*)%",
        "exit_phases": r"Exit phases:\s+(\d+)",
        "short_pnl": r"Short PnL:\s+\$([\+\-]?[0-9,]+\.?\d*)",
        "spring_pnl": r"Spring PnL:\s+\$([\+\-]?[0-9,]+\.?\d*)",
        "markup_pnl": r"Markup PnL:\s+\$([\+\-]?[0-9,]+\.?\d*)",
        "markup_phases": r"Markup phases:\s+(\d+)",
        "spring_phases": r"Spring phases:\s+(\d+)",
        "rally_sells": r"Rally sells:\s+(\d+)",
        "trail_stops": r"Trail stops:\s+(\d+)",
        "urgency_closes": r"Urgency closes:\s+(\d+)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, output)
        if m:
            val = m.group(1).replace(",", "")
            try:
                metrics[key] = float(val)
            except:
                metrics[key] = val
    return metrics

def main():
    all_results = {}
    
    for profile in PROFILES:
        print(f"\n{'='*60}")
        print(f"  PROFILE: {profile} (running btc/eth/sol in parallel)")
        print(f"{'='*60}", flush=True)
        t0 = time.time()
        run_profile_batch(profile)
        elapsed = time.time() - t0
        print(f"  Profile {profile} done in {elapsed:.0f}s", flush=True)
        
        for coin in COINS:
            key = f"{coin}_{profile}"
            metrics = parse_output(RESULTS_DIR / f"{key}_output.txt")
            if metrics:
                metrics["coin"] = coin.upper()
                metrics["profile"] = profile
                all_results[key] = metrics
                print(f"  {key}: ROI={metrics.get('roi_pct')}% MaxDD={metrics.get('max_dd')}% Sharpe={metrics.get('sharpe')}")
            else:
                # Check error file
                err = ""
                try:
                    err = open(RESULTS_DIR / f"{key}_err.txt").read()[-300:]
                except:
                    pass
                all_results[key] = {"error": "no metrics", "err_tail": err}
                print(f"  {key}: FAILED")

    with open(RESULTS_DIR / "all_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n\nResults saved to {RESULTS_DIR / 'all_results.json'}")
    print(json.dumps(all_results, indent=2))

if __name__ == "__main__":
    main()
