"""Run optimizer on HYPE/USDT — the top performer from initial backtest."""
import sys
sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")

from trading.data_fetcher import fetch_multiple_symbols
from trading.optimizer import optimize
from trading.config import MartingaleConfig
from pathlib import Path

# Load cached HYPE data
data = {}
for tf in ['5m', '15m', '1h', '4h']:
    d = fetch_multiple_symbols(['HYPE/USDT'], tf, 60)
    if 'HYPE/USDT' in d:
        data[tf] = d['HYPE/USDT']
        print(f"Loaded {tf}: {len(data[tf])} candles")

print("\nStarting optimization...")
results = optimize(data, 'HYPE/USDT', quick=True)

print("\nTop 10 parameter combinations:")
cols = ['timeframe', 'take_profit_pct', 'max_safety_orders', 'price_deviation_pct',
        'deviation_multiplier', 'safety_order_multiplier', 'total_trades',
        'total_profit_pct', 'max_drawdown_pct', 'profit_factor']
available_cols = [c for c in cols if c in results.columns]
print(results[available_cols].head(10).to_string())

Path("trading/results").mkdir(exist_ok=True)
results.to_csv("trading/results/hype_optimization.csv", index=False)
print("\nSaved to trading/results/hype_optimization.csv")
