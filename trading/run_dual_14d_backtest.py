"""14-day HYPE/USDT backtest: Long-only vs Dual-tracking vs Dual+Dynamic+VolAdj."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from trading.config import MartingaleConfig
from trading.martingale_engine import MartingaleBot, DualMartingaleBot, BacktestResult
from trading.data_fetcher import fetch_multiple_symbols
from trading.regime_detector import classify_regime_v2, is_martingale_friendly_v2

SYMBOL = "HYPE/USDT"
TIMEFRAME = "5m"
DAYS = 14

cfg = MartingaleConfig(
    base_order_size=200,
    safety_order_size=200,
    safety_order_multiplier=2.0,
    price_deviation_pct=1.5,
    deviation_multiplier=1.0,
    max_safety_orders=8,
    max_active_deals=3,
    take_profit_pct=4.0,
    fee_pct=0.05,
    slippage_pct=0.05,
    initial_capital=10000,
)

def print_result(name: str, r: BacktestResult):
    ds = r.direction_stats
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    print(f"  Total Trades:    {r.total_trades}")
    print(f"  Long / Short:    {ds['long_count']} / {ds['short_count']}")
    print(f"  Long PnL:        ${ds['long_pnl']:,.2f}")
    print(f"  Short PnL:       ${ds['short_pnl']:,.2f}")
    print(f"  Total PnL:       ${r.total_profit:,.2f}")
    print(f"  PnL %:           {r.total_profit_pct:,.2f}%")
    print(f"  Win Rate:        {r.win_rate:.1f}%")
    print(f"  Max Drawdown:    {r.max_drawdown:.2f}%")
    print(f"  Profit Factor:   {r.profit_factor:.2f}")
    print(f"  Sharpe Ratio:    {r.sharpe_ratio:.2f}")
    print(f"  Avg SO/Deal:     {np.mean([d.so_count for d in r.closed_deals]):.1f}" if r.closed_deals else "  Avg SO/Deal:     N/A")
    if ds['long_count']:
        print(f"  Long Win Rate:   {ds['long_win_rate']:.1f}%")
    if ds['short_count']:
        print(f"  Short Win Rate:  {ds['short_win_rate']:.1f}%")
    if r.open_deals:
        open_pnl = sum(d.pnl for d in r.open_deals)
        print(f"  Open Deals:      {len(r.open_deals)} (unrealized: ${open_pnl:,.2f})")

def main():
    print(f"Fetching {DAYS}d of {SYMBOL} {TIMEFRAME} data...")
    data = fetch_multiple_symbols([SYMBOL], TIMEFRAME, days_back=DAYS)
    if SYMBOL not in data:
        print(f"ERROR: Could not fetch {SYMBOL}")
        return
    df = data[SYMBOL]
    # Trim to last 14 days
    cutoff = df['timestamp'].max() - pd.Timedelta(days=DAYS)
    df = df[df['timestamp'] >= cutoff].reset_index(drop=True)
    print(f"Trimmed to last {DAYS} days: {len(df)} candles")
    print(f"Got {len(df)} candles: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")

    # Price stats
    price_high = df['high'].max()
    price_low = df['low'].min()
    print(f"\nPrice Range: ${price_low:.2f} — ${price_high:.2f} (range: ${price_high-price_low:.2f}, {(price_high-price_low)/price_low*100:.1f}%)")
    print(f"Open: ${df['close'].iloc[0]:.2f}  Close: ${df['close'].iloc[-1]:.2f}  Change: {(df['close'].iloc[-1]/df['close'].iloc[0]-1)*100:.1f}%")

    # Regime detection
    print("\nComputing regimes (v2)...")
    regimes = classify_regime_v2(df, TIMEFRAME)
    regime_counts = regimes.value_counts()
    print("\nRegime Distribution:")
    for regime, count in regime_counts.sort_values(ascending=False).items():
        pct = count / len(regimes) * 100
        print(f"  {regime:25s} {count:5d} candles ({pct:.1f}%)")

    # --- Run backtests ---
    # 1) Long-only
    print("\n\nRunning Long-Only backtest...")
    bot_long = MartingaleBot(cfg, bidirectional=False)
    r_long = bot_long.run(df, SYMBOL, TIMEFRAME, precomputed_regimes=regimes, friendly_fn=is_martingale_friendly_v2)
    print_result("LONG-ONLY", r_long)

    # 2) Dual-tracking (static 50/50)
    print("\n\nRunning Dual-Tracking (static 50/50) backtest...")
    bot_dual = DualMartingaleBot(cfg, long_alloc=0.5, dynamic_alloc=False, vol_adjusted_so=False)
    r_dual = bot_dual.run(df, SYMBOL, TIMEFRAME, precomputed_regimes=regimes, friendly_fn=is_martingale_friendly_v2)
    print_result("DUAL-TRACKING (Static 50/50)", r_dual)

    # 3) Dual + dynamic regime alloc + vol-adjusted SOs
    print("\n\nRunning Dual-Tracking (Dynamic Regime + Vol-Adjusted SO) backtest...")
    bot_dyn = DualMartingaleBot(cfg, dynamic_alloc=True, vol_adjusted_so=True)
    r_dyn = bot_dyn.run(df, SYMBOL, TIMEFRAME, precomputed_regimes=regimes, friendly_fn=is_martingale_friendly_v2)
    pass  # debug removed
    print_result("DUAL-TRACKING (Dynamic + VolAdj)", r_dyn)

    # Summary comparison
    print(f"\n\n{'='*70}")
    print(f"  COMPARISON SUMMARY")
    print(f"{'='*70}")
    print(f"  {'Strategy':<35s} {'Trades':>6s} {'PnL':>10s} {'PnL%':>7s} {'WR':>6s} {'MDD':>7s} {'PF':>6s}")
    print(f"  {'-'*35} {'-'*6} {'-'*10} {'-'*7} {'-'*6} {'-'*7} {'-'*6}")
    for name, r in [("Long-Only", r_long), ("Dual Static 50/50", r_dual), ("Dual Dynamic+VolAdj", r_dyn)]:
        print(f"  {name:<35s} {r.total_trades:>6d} ${r.total_profit:>8,.2f} {r.total_profit_pct:>6.2f}% {r.win_rate:>5.1f}% {r.max_drawdown:>6.2f}% {r.profit_factor:>5.2f}")

if __name__ == "__main__":
    main()
