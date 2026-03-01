"""Test Top + 3D Structure + SMA50 combo bias.

Bear ON:  Engine top signal fires
Bear OFF: 3D HH_HL >= N AND price > 3D SMA50 (structure + trend alignment)

The SMA50 filter prevents dead cat bounces from clearing bear bias —
you need sustained bullish structure that actually moves price above
the short-term trend.

Also test variant: price > 3D SMA200 (stricter)
"""
from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack
from build_3d_signals import build_3d_signals
from run_new_coins_profiles import make_config
import pandas as pd
import numpy as np


def get_bias(date, top_dates, df_3d, min_streak=2, sma_col='sma50'):
    """Bear after top, clears when 3D HH_HL >= min_streak AND price > SMA."""
    ts = pd.Timestamp(date)
    
    tops = sorted([pd.Timestamp(d) for d in top_dates])
    
    # Walk through time tracking bear state
    bear_active = False
    last_top = None
    
    for t in tops:
        if t > ts:
            break
        bear_active = True
        last_top = t
    
    if not bear_active or last_top is None:
        return 'neutral'
    
    # Check if clear condition met after last top and before date
    mask = (df_3d.index > last_top) & (df_3d.index <= ts)
    if not mask.any():
        return 'bear'
    
    subset = df_3d.loc[mask]
    
    # Find first candle where HH_HL >= min_streak AND close > SMA
    for idx, row in subset.iterrows():
        if row['hh_hl_streak'] >= min_streak and not np.isnan(row[sma_col]) and row['close'] > row[sma_col]:
            clear_date = idx
            # Check if another top fired after this clear
            reactivated = False
            for t in tops:
                if t > clear_date and t <= ts:
                    # Bear reactivated — check for another clear after THIS top
                    mask2 = (df_3d.index > t) & (df_3d.index <= ts)
                    if mask2.any():
                        sub2 = df_3d.loc[mask2]
                        cleared_again = False
                        for idx2, row2 in sub2.iterrows():
                            if row2['hh_hl_streak'] >= min_streak and not np.isnan(row2[sma_col]) and row2['close'] > row2[sma_col]:
                                cleared_again = True
                                break
                        if not cleared_again:
                            return 'bear'
                    else:
                        return 'bear'
                    reactivated = True
            
            if not reactivated:
                return 'neutral'
    
    return 'bear'


def analyze(coin, profile='high'):
    pack = V13SignalPack(coin)
    cfg = make_config(profile)
    bt = V13BacktestV8(pack, cfg)
    r = bt.run()
    df_3d = build_3d_signals(coin)
    
    top_dates = []
    for t in bt.phase_log:
        reason = t.get('reason', '')
        to_phase = str(t.get('to', ''))
        if to_phase == 'FLAT' and ('OB' in reason or 'failsafe' in reason.lower()):
            top_dates.append(t['date'])
    
    print(f"\n{'='*70}")
    print(f"{coin} ({profile}) -- ROI: {r['roi']:+.1f}%")
    print(f"{'='*70}")
    print(f"  Tops: {[str(d)[:10] for d in top_dates]}")
    
    variants = [
        ("3D HH_HL>=1 + price>SMA50", 1, 'sma50'),
        ("3D HH_HL>=2 + price>SMA50", 2, 'sma50'),
        ("3D HH_HL>=1 + price>SMA200", 1, 'sma200'),
        ("3D HH_HL>=2 + price>SMA200", 2, 'sma200'),
    ]
    
    for label, streak, sma in variants:
        blocked_good = []
        blocked_bad = []
        
        for i, t in enumerate(bt.phase_log):
            date = t.get('date')
            to_phase = str(t.get('to', ''))
            equity = t.get('equity', 0)
            
            if not date or to_phase != 'MARKUP':
                continue
            
            bias = get_bias(date, top_dates, df_3d, streak, sma)
            
            next_eq = None
            for j in range(i+1, len(bt.phase_log)):
                if bt.phase_log[j].get('to') != 'MARKUP':
                    next_eq = bt.phase_log[j].get('equity', equity)
                    break
            if next_eq is None:
                next_eq = r['final_equity']
            pnl = next_eq - equity
            good = pnl > 0
            
            if bias == 'bear':
                if good: blocked_good.append((date, pnl))
                else: blocked_bad.append((date, pnl))
        
        saved = abs(sum(p for _,p in blocked_bad))
        missed = sum(p for _,p in blocked_good)
        net = saved - missed
        tag = "HELPS" if net > 0 else "HURTS" if net < 0 else "NEUTRAL"
        
        bg = len(blocked_good)
        bb = len(blocked_bad)
        print(f"  {label:<35} Blocked: {bb}bad/{bg}good  Saved: ${saved:>+8.0f}  Missed: ${missed:>+8.0f}  Net: ${net:>+8.0f} {tag}")


if __name__ == '__main__':
    print("TOP + 3D STRUCTURE + SMA COMBO BIAS")
    print("Bear ON: engine top. Bear OFF: 3D HH_HL>=N AND price>SMA.\n")
    
    for coin in ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']:
        analyze(coin, 'high')
    
    # Also show the detailed trade-by-trade for the best variant
    print("\n\n" + "="*70)
    print("DETAILED: Best variant trade-by-trade")
    print("="*70)
    
    for coin in ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']:
        pack = V13SignalPack(coin)
        cfg = make_config('high')
        bt = V13BacktestV8(pack, cfg)
        r = bt.run()
        df_3d = build_3d_signals(coin)
        
        top_dates = []
        for t in bt.phase_log:
            reason = t.get('reason', '')
            to_phase = str(t.get('to', ''))
            if to_phase == 'FLAT' and ('OB' in reason or 'failsafe' in reason.lower()):
                top_dates.append(t['date'])
        
        print(f"\n{coin} (HH_HL>=2 + price>SMA50):")
        for i, t in enumerate(bt.phase_log):
            date = t.get('date')
            to_phase = str(t.get('to', ''))
            equity = t.get('equity', 0)
            
            if not date or to_phase != 'MARKUP':
                continue
            
            bias = get_bias(date, top_dates, df_3d, 2, 'sma50')
            
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
            blocked = bias == 'bear'
            
            quality = "GOOD" if good else "BAD"
            marker = " ** BLOCKED" if blocked else ""
            print(f"  {str(date)[:10]}: bias={bias:>7}, pnl={pnl:>+8.0f} ({pnl_pct:>+5.1f}%) [{quality}]{marker}")
