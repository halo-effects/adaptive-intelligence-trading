"""Calculate average daily returns from backtest results."""
import sys
sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")

from trading.data_fetcher import fetch_multiple_symbols
from trading.config import MartingaleConfig
from trading.martingale_engine import MartingaleBot
from trading.regime_detector import classify_regime, classify_regime_v2, is_martingale_friendly_v2
import pandas as pd
import numpy as np

def v2_friendly(regime):
    result = is_martingale_friendly_v2(regime)
    return result in (True, "cautious")

configs = [
    {"name": "Aggressive", "tf": "5m", "tp": 4.0, "so": 8, "dev": 1.0, "dm": 1.0, "sm": 2.0},
    {"name": "Sweet Spot", "tf": "5m", "tp": 4.0, "so": 8, "dev": 1.5, "dm": 1.0, "sm": 2.0},
    {"name": "Balanced", "tf": "15m", "tp": 4.0, "so": 8, "dev": 1.0, "dm": 1.0, "sm": 2.0},
    {"name": "Conservative", "tf": "15m", "tp": 4.0, "so": 8, "dev": 1.5, "dm": 1.0, "sm": 1.5},
]

# Load data and precompute regimes
data = {}
regimes = {}
for tf in ['5m', '15m']:
    d = fetch_multiple_symbols(['HYPE/USDT'], tf, 60)
    if 'HYPE/USDT' in d:
        data[tf] = d['HYPE/USDT']
        print(f"Computing v2 regime for {tf}...")
        regimes[tf] = classify_regime_v2(data[tf], tf)

print(f"\n{'Config':<16} {'TF':<5} {'Days':>5} {'Trades':>7} {'Total%':>8} {'Daily%':>8} {'Compound':>10}")
print("=" * 75)

for c in configs:
    tf = c["tf"]
    if tf not in data:
        continue
    cfg = MartingaleConfig(
        take_profit_pct=c["tp"],
        max_safety_orders=c["so"],
        price_deviation_pct=c["dev"],
        deviation_multiplier=c["dm"],
        safety_order_multiplier=c["sm"],
    )
    bot = MartingaleBot(cfg)
    res = bot.run(data[tf], 'HYPE/USDT', tf, precomputed_regimes=regimes[tf], friendly_fn=v2_friendly)
    
    eq = res.equity_curve
    if len(eq) > 1:
        start_ts = pd.Timestamp(eq["timestamp"].iloc[0])
        end_ts = pd.Timestamp(eq["timestamp"].iloc[-1])
        days = max((end_ts - start_ts).total_seconds() / 86400, 1)
        total_pct = res.total_profit_pct
        
        # Simple daily avg (total / days)
        simple_daily = total_pct / days
        
        # Compound daily rate: (1 + total)^(1/days) - 1
        if total_pct > 0:
            compound_daily = ((1 + total_pct/100) ** (1/days) - 1) * 100
        else:
            compound_daily = 0
        
        print(f"{c['name']:<16} {tf:<5} {days:>5.0f} {res.total_trades:>7} {total_pct:>7.1f}% {simple_daily:>7.2f}% {compound_daily:>9.3f}%")

print("\nNote: 'Daily%' = simple average (total/days). 'Compound' = compound daily growth rate.")
print("Profits ARE compounding — closed deal proceeds return to trading pool.")
