"""Comprehensive dual-tracking parameter sweep for HYPE/USDT."""
import sys, os, time, math
import itertools
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading.data_fetcher import fetch_multiple_symbols
from trading.regime_detector import classify_regime
from trading.martingale_engine import DualMartingaleBot
from trading.config import MartingaleConfig


def run_sweep():
    print("=" * 80)
    print("DUAL-TRACKING PARAMETER SWEEP -- HYPE/USDT")
    print("=" * 80)

    # Fetch data
    print("\n[1] Fetching data...")
    timeframes = ["1m", "5m"]
    data = {}
    for tf in timeframes:
        d = fetch_multiple_symbols(["HYPE/USDT"], tf, days_back=14)
        if "HYPE/USDT" in d:
            data[tf] = d["HYPE/USDT"]
            print(f"  {tf}: {len(data[tf])} candles")
        else:
            print(f"  {tf}: FAILED to fetch")
            return

    # Pre-compute regimes
    print("\n[2] Pre-computing regimes...")
    regimes = {}
    for tf in timeframes:
        regimes[tf] = classify_regime(data[tf], tf)
        print(f"  {tf}: {regimes[tf].value_counts().to_dict()}")

    # Parameter grid
    tp_values = [0.5, 1.0, 1.5, 2.0, 3.0]
    dev_values = [1.0, 1.5, 2.5]
    leverage = {"1x": (200, 200), "2x": (400, 400)}
    max_so_values = [4, 8, 12]
    so_mult_values = [1.5, 2.0, 2.5]

    # Phase 1: TP x Dev x TF x Lev with fixed max_so=8, so_mult=2.0
    print("\n[3] Phase 1: TP × Dev × TF × Lev sweep (60 combos)...")
    results = []
    t0 = time.time()
    
    combos = list(itertools.product(timeframes, leverage.keys(), tp_values, dev_values))
    for idx, (tf, lev, tp, dev) in enumerate(combos):
        bo, so = leverage[lev]
        cfg = MartingaleConfig(
            base_order_size=bo, safety_order_size=so,
            safety_order_multiplier=2.0, price_deviation_pct=dev,
            deviation_multiplier=1.0, max_safety_orders=8,
            max_active_deals=3, take_profit_pct=tp,
            fee_pct=0.05, slippage_pct=0.05, initial_capital=10000,
        )
        bot = DualMartingaleBot(cfg, dynamic_alloc=True, vol_adjusted_so=True)
        res = bot.run(data[tf], "HYPE/USDT", tf, precomputed_regimes=regimes[tf])
        ds = res.direction_stats
        trades = res.total_trades
        pnl = res.total_profit
        pnl_pct = res.total_profit_pct
        maxdd = res.max_drawdown
        score = (pnl_pct / max(abs(maxdd), 1)) * math.sqrt(max(trades, 1))
        results.append({
            "tf": tf, "lev": lev, "tp": tp, "dev": dev, "max_so": 8, "so_mult": 2.0,
            "trades": trades, "long": ds["long_count"], "short": ds["short_count"],
            "pnl": round(pnl, 2), "pnl_pct": round(pnl_pct, 2),
            "maxdd": round(maxdd, 2), "score": round(score, 2),
            "short_pnl": round(ds["short_pnl"], 2),
        })
        if (idx + 1) % 10 == 0:
            elapsed = time.time() - t0
            print(f"  {idx+1}/{len(combos)} done ({elapsed:.1f}s)")

    elapsed1 = time.time() - t0
    print(f"  Phase 1 complete: {len(combos)} combos in {elapsed1:.1f}s")

    # Phase 2: Take top 5 from phase 1, sweep max_so x so_mult
    df1 = pd.DataFrame(results)
    top5 = df1.nlargest(5, "score")
    print(f"\n[4] Phase 2: Sweeping max_so × so_mult on top 5 configs...")
    
    phase2_results = []
    for _, row in top5.iterrows():
        for max_so in max_so_values:
            for so_mult in so_mult_values:
                if max_so == 8 and so_mult == 2.0:
                    continue  # already have this
                tf, lev, tp, dev = row["tf"], row["lev"], row["tp"], row["dev"]
                bo, so = leverage[lev]
                cfg = MartingaleConfig(
                    base_order_size=bo, safety_order_size=so,
                    safety_order_multiplier=so_mult, price_deviation_pct=dev,
                    deviation_multiplier=1.0, max_safety_orders=max_so,
                    max_active_deals=3, take_profit_pct=tp,
                    fee_pct=0.05, slippage_pct=0.05, initial_capital=10000,
                )
                bot = DualMartingaleBot(cfg, dynamic_alloc=True, vol_adjusted_so=True)
                res = bot.run(data[tf], "HYPE/USDT", tf, precomputed_regimes=regimes[tf])
                ds = res.direction_stats
                trades = res.total_trades
                pnl = res.total_profit
                pnl_pct = res.total_profit_pct
                maxdd = res.max_drawdown
                score = (pnl_pct / max(abs(maxdd), 1)) * math.sqrt(max(trades, 1))
                phase2_results.append({
                    "tf": tf, "lev": lev, "tp": tp, "dev": dev, "max_so": max_so, "so_mult": so_mult,
                    "trades": trades, "long": ds["long_count"], "short": ds["short_count"],
                    "pnl": round(pnl, 2), "pnl_pct": round(pnl_pct, 2),
                    "maxdd": round(maxdd, 2), "score": round(score, 2),
                    "short_pnl": round(ds["short_pnl"], 2),
                })

    all_results = results + phase2_results
    df = pd.DataFrame(all_results)
    df = df.drop_duplicates(subset=["tf", "lev", "tp", "dev", "max_so", "so_mult"])
    df = df.sort_values("score", ascending=False).reset_index(drop=True)

    # Print Top 20
    print("\n" + "=" * 120)
    print("TOP 20 CONFIGURATIONS BY COMPOSITE SCORE")
    print("Score = (PnL% / max(|MaxDD%|, 1)) * sqrt(trades)")
    print("=" * 120)
    header = f"{'Rank':>4} {'TF':>3} {'Lev':>3} {'TP%':>5} {'Dev%':>5} {'MSO':>3} {'SOMlt':>5} {'Trades':>6} {'L/S':>7} {'PnL':>10} {'PnL%':>7} {'MaxDD%':>7} {'Score':>8}"
    print(header)
    print("-" * 120)
    for i, row in df.head(20).iterrows():
        rank = df.index.get_loc(i) + 1
        ls = f"{int(row['long'])}/{int(row['short'])}"
        print(f"{rank:>4} {row['tf']:>3} {row['lev']:>3} {row['tp']:>5.1f} {row['dev']:>5.1f} {int(row['max_so']):>3} {row['so_mult']:>5.1f} {int(row['trades']):>6} {ls:>7} {row['pnl']:>10.2f} {row['pnl_pct']:>7.2f} {row['maxdd']:>7.2f} {row['score']:>8.2f}")

    # Special configs
    print("\n" + "=" * 80)
    best_pnl = df.loc[df["pnl_pct"].idxmax()]
    print(f"BEST PnL: TF={best_pnl['tf']} Lev={best_pnl['lev']} TP={best_pnl['tp']}% Dev={best_pnl['dev']}% MSO={int(best_pnl['max_so'])} SOMlt={best_pnl['so_mult']} → PnL={best_pnl['pnl_pct']:.2f}% MaxDD={best_pnl['maxdd']:.2f}%")

    df_pos = df[df["maxdd"] < 0]
    if len(df_pos):
        df_pos = df_pos.copy()
        df_pos["risk_adj"] = df_pos["pnl_pct"] / df_pos["maxdd"].abs()
        best_risk = df_pos.loc[df_pos["risk_adj"].idxmax()]
        print(f"BEST RISK-ADJ: TF={best_risk['tf']} Lev={best_risk['lev']} TP={best_risk['tp']}% Dev={best_risk['dev']}% MSO={int(best_risk['max_so'])} SOMlt={best_risk['so_mult']} → PnL/DD={best_risk['risk_adj']:.2f}")

    best_trades = df.loc[df["trades"].idxmax()]
    print(f"MOST TRADES: TF={best_trades['tf']} Lev={best_trades['lev']} TP={best_trades['tp']}% Dev={best_trades['dev']}% → {int(best_trades['trades'])} trades")

    best_short = df.loc[df["short_pnl"].idxmax()]
    print(f"BEST SHORT: TF={best_short['tf']} Lev={best_short['lev']} TP={best_short['tp']}% Dev={best_short['dev']}% → Short PnL=${best_short['short_pnl']:.2f}")

    # Sensitivity analysis
    print("\n" + "=" * 80)
    print("PARAMETER SENSITIVITY (Average PnL% by parameter)")
    print("=" * 80)
    for param, label in [("tf", "Timeframe"), ("lev", "Leverage"), ("tp", "TP%"), ("dev", "Dev%"), ("max_so", "Max SO"), ("so_mult", "SO Mult")]:
        grouped = df.groupby(param)["pnl_pct"].mean().sort_index()
        print(f"\n  {label}:")
        for val, avg in grouped.items():
            print(f"    {val}: {avg:+.2f}%")

    total_time = time.time() - t0
    print(f"\n\nTotal sweep time: {total_time:.1f}s")


if __name__ == "__main__":
    run_sweep()
