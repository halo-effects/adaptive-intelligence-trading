"""60-day backtest: 4-way Martingale comparison."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading.data_fetcher import fetch_multiple_symbols
from trading.regime_detector import classify_regime_v2, is_martingale_friendly_v2
from trading.martingale_engine import MartingaleBot, DualMartingaleBot, BacktestResult
from trading.config import MartingaleConfig


def extract_stats(label: str, res: BacktestResult, cfg: MartingaleConfig):
    trades = res.closed_deals
    longs = [d for d in trades if d.direction == "LONG"]
    shorts = [d for d in trades if d.direction == "SHORT"]
    long_pnl = sum(d.pnl for d in longs)
    short_pnl = sum(d.pnl for d in shorts)
    total_pnl = long_pnl + short_pnl
    pct = total_pnl / cfg.initial_capital * 100
    wins = sum(1 for d in trades if d.pnl > 0)
    wr = wins / len(trades) * 100 if trades else 0
    gross_profit = sum(d.pnl for d in trades if d.pnl > 0)
    gross_loss = abs(sum(d.pnl for d in trades if d.pnl < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    return {
        "label": label,
        "total": len(trades),
        "longs": len(longs),
        "shorts": len(shorts),
        "long_pnl": long_pnl,
        "short_pnl": short_pnl,
        "total_pnl": total_pnl,
        "pnl_pct": pct,
        "win_rate": wr,
        "max_dd": res.max_drawdown,
        "profit_factor": pf,
        "open_deals": len(res.open_deals),
    }


def main():
    print("=" * 80)
    print("  HYPE/USDT 5m — 60-Day 4-Way Backtest Comparison")
    print("=" * 80)

    print("\nFetching 60 days of data...")
    data = fetch_multiple_symbols(["HYPE/USDT"], "5m", days_back=60)
    df = data["HYPE/USDT"]
    df = df.tail(17280).reset_index(drop=True)
    print(f"Candles: {len(df)} | {df['timestamp'].iloc[0]} -> {df['timestamp'].iloc[-1]}")

    print("\nClassifying regimes...")
    regimes = classify_regime_v2(df, "5m")
    print(f"\nRegime Distribution:")
    for regime, count in regimes.value_counts().sort_index().items():
        pct = count / len(regimes) * 100
        print(f"  {regime:20s} {count:5d} ({pct:5.1f}%)")

    cfg = MartingaleConfig(
        base_order_size=200, safety_order_size=200, safety_order_multiplier=2.0,
        take_profit_pct=4.0, max_safety_orders=8, price_deviation_pct=1.5,
        deviation_multiplier=1.0, max_active_deals=3, fee_pct=0.05,
        slippage_pct=0.05, initial_capital=10000,
    )

    common = dict(precomputed_regimes=regimes, friendly_fn=is_martingale_friendly_v2)

    # --- Run all four ---
    print("\n[1/4] Long-Only...")
    bot1 = MartingaleBot(cfg, bidirectional=False)
    res1 = bot1.run(df, "HYPE/USDT", "5m", **common)

    print("[2/4] Dual-Tracking Fixed 50/50...")
    bot2 = DualMartingaleBot(cfg, long_alloc=0.5, dynamic_alloc=False, vol_adjusted_so=False)
    res2 = bot2.run(df, "HYPE/USDT", "5m", **common)

    print("[3/4] Dual-Tracking Dynamic Regime Alloc...")
    bot3 = DualMartingaleBot(cfg, dynamic_alloc=True, vol_adjusted_so=False)
    res3 = bot3.run(df, "HYPE/USDT", "5m", **common)

    print("[4/4] Dual-Tracking Dynamic + Vol-Adjusted SOs...")
    bot4 = DualMartingaleBot(cfg, dynamic_alloc=True, vol_adjusted_so=True)
    res4 = bot4.run(df, "HYPE/USDT", "5m", **common)

    # --- Results table ---
    rows = [
        extract_stats("Long-Only", res1, cfg),
        extract_stats("Dual Fixed", res2, cfg),
        extract_stats("Dual Dynamic", res3, cfg),
        extract_stats("Dual Dyn+Vol", res4, cfg),
    ]

    print("\n" + "=" * 120)
    print("  RESULTS COMPARISON")
    print("=" * 120)

    header = (f"{'Strategy':16s} {'Trades':>6s} {'Long':>5s} {'Short':>5s} "
              f"{'L PnL':>10s} {'S PnL':>10s} {'Total PnL':>11s} "
              f"{'PnL%':>7s} {'WR%':>6s} {'MaxDD%':>7s} {'PF':>6s} {'Open':>4s}")
    print(header)
    print("-" * len(header))
    for r in rows:
        pf_str = f"{r['profit_factor']:.2f}" if r['profit_factor'] != float('inf') else "inf"
        print(f"{r['label']:16s} {r['total']:6d} {r['longs']:5d} {r['shorts']:5d} "
              f"${r['long_pnl']:>9.2f} ${r['short_pnl']:>9.2f} ${r['total_pnl']:>10.2f} "
              f"{r['pnl_pct']:>6.1f}% {r['win_rate']:>5.1f}% {r['max_dd']:>6.1f}% {pf_str:>6s} {r['open_deals']:4d}")

    print("\n" + "=" * 120)
    print(f"  Max deal capital (all SOs): ${cfg.max_deal_capital():,.0f}")
    print(f"  Config: BO={cfg.base_order_size} SO={cfg.safety_order_size} mult={cfg.safety_order_multiplier} "
          f"TP={cfg.take_profit_pct}% dev={cfg.price_deviation_pct}% maxSO={cfg.max_safety_orders}")
    print("=" * 120)


if __name__ == "__main__":
    main()
