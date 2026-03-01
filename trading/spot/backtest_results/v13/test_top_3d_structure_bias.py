"""Test Top + 3D Structure bias system.

Bear bias ON:  Engine top signal fires (2W OB93 / 1W OB85 / 1W K<50)
Bear bias OFF: 3D HH_HL >= N (bullish structure confirmed on 3D candles)

When bear bias is active: block MARKUP entries (daily gates can't fire)
When bear bias is off: normal operation (daily HH_HL + Fib gates apply)

Test variants:
  - 3D HH_HL >= 1 (fast clear - 3 days of bullish structure)
  - 3D HH_HL >= 2 (moderate - 6 days)
  - 3D HH_HL >= 3 (conservative - 9 days)
"""
from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack
from build_3d_signals import build_3d_signals
from run_new_coins_profiles import make_config
import pandas as pd
import numpy as np


def get_bias(date, top_dates, df_3d, min_streak=2):
    """Get bias at date. BEAR after top, clears when 3D HH_HL >= min_streak."""
    ts = pd.Timestamp(date)
    bear_active = False
    
    # Sort top dates
    tops = sorted([pd.Timestamp(d) for d in top_dates])
    
    # Find most recent top before this date
    last_top = None
    for t in tops:
        if t <= ts:
            last_top = t
            bear_active = True
    
    if not bear_active or last_top is None:
        return 'neutral'
    
    # Check if 3D HH_HL >= min_streak occurred AFTER the last top
    mask = (df_3d.index > last_top) & (df_3d.index <= ts)
    if mask.any():
        streaks_after_top = df_3d.loc[mask, 'hh_hl_streak']
        if (streaks_after_top >= min_streak).any():
            # Find first date where streak cleared
            clear_date = streaks_after_top[streaks_after_top >= min_streak].index[0]
            # But check if another top fired after that clear
            for t in tops:
                if t > clear_date and t <= ts:
                    # Re-engaged bear after clear
                    # Check again for clear after THIS top
                    mask2 = (df_3d.index > t) & (df_3d.index <= ts)
                    if mask2.any():
                        s2 = df_3d.loc[mask2, 'hh_hl_streak']
                        if (s2 >= min_streak).any():
                            return 'neutral'
                    return 'bear'
            return 'neutral'
    
    return 'bear'


def analyze(coin, profile='high'):
    pack = V13SignalPack(coin)
    cfg = make_config(profile)
    bt = V13BacktestV8(pack, cfg)
    r = bt.run()
    df_3d = build_3d_signals(coin)
    
    # Extract top dates
    top_dates = []
    for t in bt.phase_log:
        reason = t.get('reason', '')
        to_phase = str(t.get('to', ''))
        if to_phase == 'FLAT' and ('OB' in reason or 'failsafe' in reason.lower()):
            top_dates.append(t['date'])
    
    print(f"\n{'='*70}")
    print(f"{coin} ({profile}) -- ROI: {r['roi']:+.1f}%, B&H: {r['buy_hold_return']:+.0f}%")
    print(f"{'='*70}")
    print(f"  Top signals: {[str(d)[:10] for d in top_dates]}")
    
    for min_streak in [1, 2, 3]:
        print(f"\n  --- 3D HH_HL >= {min_streak} clears bear bias ---")
        
        blocked_good = []
        blocked_bad = []
        
        for i, t in enumerate(bt.phase_log):
            date = t.get('date')
            to_phase = str(t.get('to', ''))
            equity = t.get('equity', 0)
            
            if not date or to_phase != 'MARKUP':
                continue
            
            bias = get_bias(date, top_dates, df_3d, min_streak)
            
            # Get trade PnL
            next_eq = None
            for j in range(i+1, len(bt.phase_log)):
                if bt.phase_log[j].get('to') != 'MARKUP':
                    next_eq = bt.phase_log[j].get('equity', equity)
                    break
            if next_eq is None:
                next_eq = r['final_equity']
            pnl = next_eq - equity
            pnl_pct = (next_eq / equity - 1) * 100 if equity > 0 else 0
            good = pnl > 0
            would_block = (bias == 'bear')
            
            marker = " ** BLOCKED" if would_block else ""
            quality = "GOOD" if good else "BAD"
            print(f"    MARKUP {str(date)[:10]}: bias={bias:>7}, pnl={pnl:>+8.0f} ({pnl_pct:>+5.1f}%) [{quality}]{marker}")
            
            if would_block:
                if good: blocked_good.append((date, pnl))
                else: blocked_bad.append((date, pnl))
        
        saved = sum(p for _,p in blocked_bad)
        missed = sum(p for _,p in blocked_good)
        net = abs(saved) - missed
        label = "HELPS" if net > 0 else "HURTS"
        print(f"    >> Saved: ${saved:>+9.0f} ({len(blocked_bad)} bad)  Missed: ${missed:>+9.0f} ({len(blocked_good)} good)  Net: ${net:>+9.0f} ({label})")


if __name__ == '__main__':
    print("TOP + 3D STRUCTURE BIAS TEST")
    print("Bear activates on engine top. Clears on 3D HH_HL >= N.")
    print("Only blocks MARKUP during bear. Shorts always allowed.\n")
    
    for coin in ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']:
        analyze(coin, 'high')
