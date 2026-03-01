import json
from pathlib import Path

base = Path(__file__).resolve().parent / "backtest_results" / "v12_lifecycle"

for version in ["v12e", "v12f"]:
    print(f"\n=== {version.upper()} ===")
    for coin in ["eth", "sol", "btc"]:
        for profile in ["low", "medium", "high"]:
            f = base / f"{coin}_1h_{version}_{profile}.json"
            if f.exists():
                data = json.loads(f.read_text())
                d = data[0] if isinstance(data, list) else data
                pnl = d.get("pnl_pct", 0)
                dd = d.get("max_dd", 0)
                sharpe = d.get("sharpe", 0)
                short = d.get("short_pnl", 0)
                exits = d.get("exit_phases", 0)
                spring = d.get("spring_pnl", 0)
                print(f"  {coin:3s} {profile:6s}  PnL={pnl:+8.2f}%  DD={dd:5.1f}%  Sharpe={sharpe:.2f}  Short=${short:+.0f}  Spring=${spring:+.0f}  Exits={exits}")
            else:
                print(f"  {coin:3s} {profile:6s}  NOT FOUND")

if __name__ == "__main__":
    pass
