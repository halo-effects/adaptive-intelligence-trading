#!/usr/bin/env python3
"""V12e Feature Isolation Test — A/B test CFGI gate and Price Discovery mode.

Runs 4 configurations x 3 coins x 3 profiles = 36 backtests:
  A: Baseline (no CFGI gate, no price discovery)
  B: Price discovery only
  C: CFGI gate only
  D: Both (already have these results)

Uses run_v12_chained.py infrastructure via direct engine calls.
"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from trading.spot.run_v12_chained import run_chained, PRESETS, DEFAULT_V12_PARAMS
from trading.spot.macro_indicators import load_historical_fear_greed
import logging

logging.basicConfig(level=logging.WARNING)  # Suppress INFO noise

def main():
    parser = argparse.ArgumentParser(description="V12e Feature Isolation Test")
    parser.add_argument("--config", choices=["A", "B", "C", "D", "all"], default="all")
    parser.add_argument("--coin", choices=["btc", "eth", "sol", "all"], default="all")
    parser.add_argument("--profile", choices=["low", "medium", "high", "all"], default="all")
    args = parser.parse_args()

    configs = {
        "A": {"v12_cfgi_exit_gate": False, "v12_price_discovery_mode": False},
        "B": {"v12_cfgi_exit_gate": False, "v12_price_discovery_mode": True},
        "C": {"v12_cfgi_exit_gate": True,  "v12_price_discovery_mode": False},
        "D": {"v12_cfgi_exit_gate": True,  "v12_price_discovery_mode": True},
    }

    coins = ["btc", "eth", "sol"] if args.coin == "all" else [args.coin]
    profiles = ["low", "medium", "high"] if args.profile == "all" else [args.profile]
    config_keys = list(configs.keys()) if args.config == "all" else [args.config]

    results = {}
    total = len(config_keys) * len(coins) * len(profiles)
    done = 0

    for cfg_name in config_keys:
        cfg = configs[cfg_name]
        results[cfg_name] = {}
        for coin in coins:
            results[cfg_name][coin] = {}
            for profile in profiles:
                done += 1
                label = f"[{done}/{total}] Config {cfg_name} | {coin.upper()} {profile}"
                print(f"\n{'='*60}")
                print(f"  {label}")
                print(f"  CFGI gate: {cfg['v12_cfgi_exit_gate']}, Price discovery: {cfg['v12_price_discovery_mode']}")
                print(f"{'='*60}")

                preset = PRESETS[coin]
                fg = load_historical_fear_greed()

                # Build v12_params with feature toggles
                v12_params = DEFAULT_V12_PARAMS.copy()
                v12_params["v12_cfgi_exit_gate"] = cfg["v12_cfgi_exit_gate"]
                v12_params["v12_price_discovery_mode"] = cfg["v12_price_discovery_mode"]
                v12_params["v12_slippage_pct"] = 0.0005

                try:
                    result, _ = run_chained(
                        symbol=preset["symbol"],
                        timeframe="1h",
                        start=preset["start"],
                        end=preset["end"],
                        exchange="aster",
                        profile=profile,
                        capital=10000,
                        fg=fg,
                        v12_params=v12_params,
                    )
                    r = {
                        "roi": result.total_return_pct,
                        "max_dd": result.max_drawdown_pct,
                        "sharpe": result.sharpe_ratio,
                        "deals": result.total_deals_completed,
                        "win_rate": result.win_rate,
                        "final_equity": result.final_equity,
                    }
                except Exception as e:
                    print(f"  ERROR: {e}")
                    r = {"roi": None, "error": str(e)}

                results[cfg_name][coin][profile] = r
                if r.get("roi") is not None:
                    print(f"  Result: ROI={r['roi']:.1f}%, DD={r['max_dd']:.1f}%, Sharpe={r['sharpe']:.2f}")

    # Save raw results
    out_dir = os.path.join("backtest_results", "v12e_isolation")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "raw_results.json"), "w") as f:
        json.dump(results, f, indent=2)

    # Print comparison table
    print("\n\n" + "="*80)
    print("  V12e FEATURE ISOLATION RESULTS")
    print("="*80)
    print(f"{'Coin':<6} {'Profile':<8} {'A (base)':<12} {'B (PD only)':<12} {'C (CFGI only)':<14} {'D (both)':<12}")
    print("-"*80)
    for coin in coins:
        for profile in profiles:
            row = f"{coin.upper():<6} {profile:<8}"
            for cfg_name in ["A", "B", "C", "D"]:
                r = results.get(cfg_name, {}).get(coin, {}).get(profile, {})
                roi = r.get("roi")
                if roi is not None:
                    row += f" {roi:>+8.1f}%   "
                else:
                    row += f" {'N/A':>8}    "
            print(row)

    # Save markdown report
    with open(os.path.join(out_dir, "ISOLATION_RESULTS.md"), "w") as f:
        f.write("# V12e Feature Isolation Test Results\n")
        f.write(f"*Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
        f.write("## Configurations\n")
        f.write("- **A**: Baseline (no CFGI gate, no price discovery)\n")
        f.write("- **B**: Price discovery only (weekly bearish confirmation when price > ATH)\n")
        f.write("- **C**: CFGI >=75 gate only\n")
        f.write("- **D**: Both CFGI gate + price discovery\n\n")
        f.write("## ROI Comparison\n\n")
        f.write("| Coin | Profile | A (base) | B (PD only) | C (CFGI only) | D (both) |\n")
        f.write("|------|---------|----------|-------------|---------------|----------|\n")
        for coin in coins:
            for profile in profiles:
                row = f"| {coin.upper()} | {profile} |"
                for cfg_name in ["A", "B", "C", "D"]:
                    r = results.get(cfg_name, {}).get(coin, {}).get(profile, {})
                    roi = r.get("roi")
                    row += f" {roi:+.1f}% |" if roi is not None else " N/A |"
                f.write(row + "\n")

        f.write("\n## Max Drawdown Comparison\n\n")
        f.write("| Coin | Profile | A (base) | B (PD only) | C (CFGI only) | D (both) |\n")
        f.write("|------|---------|----------|-------------|---------------|----------|\n")
        for coin in coins:
            for profile in profiles:
                row = f"| {coin.upper()} | {profile} |"
                for cfg_name in ["A", "B", "C", "D"]:
                    r = results.get(cfg_name, {}).get(coin, {}).get(profile, {})
                    dd = r.get("max_dd")
                    row += f" {dd:.1f}% |" if dd is not None else " N/A |"
                f.write(row + "\n")

        f.write("\n## Sharpe Ratio Comparison\n\n")
        f.write("| Coin | Profile | A (base) | B (PD only) | C (CFGI only) | D (both) |\n")
        f.write("|------|---------|----------|-------------|---------------|----------|\n")
        for coin in coins:
            for profile in profiles:
                row = f"| {coin.upper()} | {profile} |"
                for cfg_name in ["A", "B", "C", "D"]:
                    r = results.get(cfg_name, {}).get(coin, {}).get(profile, {})
                    s = r.get("sharpe")
                    row += f" {s:.2f} |" if s is not None else " N/A |"
                f.write(row + "\n")

    print(f"\nResults saved to {out_dir}/")


if __name__ == "__main__":
    main()
