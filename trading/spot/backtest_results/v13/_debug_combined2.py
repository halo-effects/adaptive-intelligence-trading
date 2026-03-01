"""Debug: check ETH conviction gates during MARKDOWN"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from v13_router_engine_v2 import V13RouterV2, V13Config, V13SignalPack, Phase, HybridDetector2D
import pandas as pd

coin = 'ETH/USDC'
det = HybridDetector2D(coin, exhaustion_k_min=5.0, exhaustion_tf='2W', exhaustion_mode='k_lift')

# Check gates around Jun 2025
dates_to_check = pd.date_range('2025-05-01', '2025-07-31', freq='W')
print("Date           | 3D_DX | 2W_Exh | Score | Details")
print("-" * 80)
for d in dates_to_check:
    dx = det.in_death_cross(d, '3D')
    exh = det.has_2w_exhaustion_cross(d)
    score, details = det.check(d)
    print(f"{d.strftime('%Y-%m-%d')} | {dx:>5} | {exh:>6} | {score}/4  | sma200={details.get('below_sma200')}, rsi={details.get('rsi14',0):.1f}, stoch={details.get('stoch_ok')}, cfgi={details.get('cfgi',0):.0f}")

# Also check Dec 2025 - Feb 2026 (second markdown)
print("\n--- Second MARKDOWN period ---")
dates2 = pd.date_range('2025-11-01', '2026-02-28', freq='W')
for d in dates2:
    dx = det.in_death_cross(d, '3D')
    exh = det.has_2w_exhaustion_cross(d)
    score, details = det.check(d)
    if score >= 2:  # Only show promising dates
        print(f"{d.strftime('%Y-%m-%d')} | {dx:>5} | {exh:>6} | {score}/4  | sma200={details.get('below_sma200')}, rsi={details.get('rsi14',0):.1f}, stoch={details.get('stoch_ok')}, cfgi={details.get('cfgi',0):.0f}")
