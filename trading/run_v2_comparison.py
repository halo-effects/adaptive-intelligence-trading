"""Compare v1 vs v2 regime detector on top HYPE/USDT configurations."""
import sys
sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")

from trading.data_fetcher import fetch_multiple_symbols
from trading.config import MartingaleConfig
from trading.martingale_engine import MartingaleBot
from trading.regime_detector import classify_regime, classify_regime_v2, is_martingale_friendly, is_martingale_friendly_v2
from trading import indicators

def v2_friendly(regime):
    """Wrapper that treats 'cautious' as True for v2."""
    result = is_martingale_friendly_v2(regime)
    return result in (True, "cautious")

# Load data
data = {}
for tf in ['5m', '15m', '1h', '4h']:
    d = fetch_multiple_symbols(['HYPE/USDT'], tf, 60)
    if 'HYPE/USDT' in d:
        data[tf] = d['HYPE/USDT']
        print(f"Loaded {tf}: {len(data[tf])} candles")

# Top configurations to test
configs = [
    {"name": "Aggressive", "tf": "5m", "tp": 4.0, "so": 8, "dev": 1.0, "dm": 1.0, "sm": 2.0},
    {"name": "Sweet Spot", "tf": "5m", "tp": 4.0, "so": 8, "dev": 1.5, "dm": 1.0, "sm": 2.0},
    {"name": "Balanced", "tf": "15m", "tp": 4.0, "so": 8, "dev": 1.0, "dm": 1.0, "sm": 2.0},
    {"name": "Conservative", "tf": "15m", "tp": 4.0, "so": 8, "dev": 1.5, "dm": 1.0, "sm": 1.5},
    {"name": "Safe", "tf": "5m", "tp": 4.0, "so": 6, "dev": 2.0, "dm": 1.0, "sm": 2.0},
]

print("\nPrecomputing regimes...")
regimes_v1 = {}
regimes_v2 = {}
for tf in ['5m', '15m']:
    if tf in data:
        print(f"  v1 {tf}...")
        regimes_v1[tf] = classify_regime(data[tf], tf)
        print(f"  v2 {tf}...")
        regimes_v2[tf] = classify_regime_v2(data[tf], tf)
        
        # Show regime distribution
        v1_counts = regimes_v1[tf].value_counts()
        v2_counts = regimes_v2[tf].value_counts()
        print(f"  v1 {tf} regimes: {dict(v1_counts)}")
        print(f"  v2 {tf} regimes: {dict(v2_counts)}")

print("\n" + "=" * 90)
print(f"{'Config':<16} {'TF':<5} {'Version':<4} {'Trades':>7} {'Profit%':>9} {'MaxDD%':>9} {'PF':>8} {'AvgSO':>6}")
print("=" * 90)

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
    
    # v1
    bot1 = MartingaleBot(cfg)
    r1 = bot1.run(data[tf], 'HYPE/USDT', tf, precomputed_regimes=regimes_v1[tf])
    s1 = r1.summary_dict()
    
    # v2
    bot2 = MartingaleBot(cfg)
    r2 = bot2.run(data[tf], 'HYPE/USDT', tf, precomputed_regimes=regimes_v2[tf], friendly_fn=v2_friendly)
    s2 = r2.summary_dict()
    
    pf1 = f"{s1['profit_factor']:.1f}" if s1['profit_factor'] < 999 else "inf"
    pf2 = f"{s2['profit_factor']:.1f}" if s2['profit_factor'] < 999 else "inf"
    
    print(f"{c['name']:<16} {tf:<5} {'v1':<4} {s1['total_trades']:>7} {s1['total_profit_pct']:>8.1f}% {s1['max_drawdown_pct']:>8.1f}% {pf1:>8} {s1['avg_so_per_deal']:>5.1f}")
    print(f"{'':.<16} {'':<5} {'v2':<4} {s2['total_trades']:>7} {s2['total_profit_pct']:>8.1f}% {s2['max_drawdown_pct']:>8.1f}% {pf2:>8} {s2['avg_so_per_deal']:>5.1f}")
    
    # Improvement
    dd_improve = abs(s1['max_drawdown_pct']) - abs(s2['max_drawdown_pct'])
    profit_diff = s2['total_profit_pct'] - s1['total_profit_pct']
    print(f"{'  DELTA':<16} {'':<5} {'':<4} {'':>7} {profit_diff:>+8.1f}% {dd_improve:>+8.1f}%")
    print("-" * 90)
