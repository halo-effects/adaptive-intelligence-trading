"""Rerun optimizer with corrected sorting — all timeframes, top 50 results."""
import sys
sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")

from trading.data_fetcher import fetch_multiple_symbols
from trading.optimizer import optimize
from trading.config import MartingaleConfig
from pathlib import Path

data = {}
for tf in ['5m', '15m', '1h', '4h']:
    d = fetch_multiple_symbols(['HYPE/USDT'], tf, 60)
    if 'HYPE/USDT' in d:
        data[tf] = d['HYPE/USDT']
        print(f"Loaded {tf}: {len(data[tf])} candles")

print("\nStarting optimization (576 runs)...")
results = optimize(data, 'HYPE/USDT', quick=True, top_n=50)

print("\n" + "=" * 80)
print("TOP 5 PER TIMEFRAME (sorted by total profit)")
print("=" * 80)
cols = ['timeframe', 'take_profit_pct', 'max_safety_orders', 'price_deviation_pct',
        'deviation_multiplier', 'safety_order_multiplier', 'total_trades',
        'total_profit_pct', 'max_drawdown_pct', 'profit_factor', 'risk_adj_score']

for tf in ['5m', '15m', '1h', '4h']:
    sub = results[results['timeframe'] == tf].head(5)
    if len(sub) > 0:
        print(f"\n--- {tf} ---")
        available = [c for c in cols if c in sub.columns]
        print(sub[available].to_string(index=False))

print("\n" + "=" * 80)
print("OVERALL TOP 10 BY PROFIT")
print("=" * 80)
available = [c for c in cols if c in results.columns]
print(results[available].head(10).to_string(index=False))

results.to_csv("trading/results/hype_optimization_v2.csv", index=False)
print("\nSaved to trading/results/hype_optimization_v2.csv")
