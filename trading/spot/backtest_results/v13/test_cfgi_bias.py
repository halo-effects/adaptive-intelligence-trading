"""Test CFGI as bottom signal for bias system.

Top (bear ON): Engine top signal (2W OB93 / 1W OB85 / K<50)
Bottom (bear OFF): CFGI drops below extreme fear threshold

CFGI data starts Jul 2022, so we'll see coverage gaps for earlier periods.

Test thresholds:
  - CFGI < 10 (extreme fear)
  - CFGI < 15 
  - CFGI < 20
  - CFGI < 25
  
Also test: Top+CFGI bottom combo with 3D structure confirmation
  - CFGI < 20 AND 3D HH_HL >= 1
"""
from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack
from build_3d_signals import build_3d_signals
from run_new_coins_profiles import make_config
import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'candles.db'


def load_cfgi():
    """Load CFGI daily data. Uses BTC as market proxy (most liquid, longest history)."""
    conn = sqlite3.connect(DB_PATH)
    # Try BTC first, then average across all symbols
    df = pd.read_sql_query(
        "SELECT date, AVG(cfgi) as cfgi FROM cfgi_daily GROUP BY date ORDER BY date", conn
    )
    conn.close()
    if df.empty:
        return pd.Series(dtype=float)
    df['date'] = pd.to_datetime(df['date'], format='mixed')
    df = df.set_index('date')
    return df['cfgi']


def get_bias(date, top_dates, cfgi, threshold, df_3d=None, require_3d_hh=False):
    """Bear after top, clears when CFGI < threshold (and optionally 3D HH_HL >= 1)."""
    ts = pd.Timestamp(date)
    
    tops = sorted([pd.Timestamp(d) for d in top_dates])
    
    bear_active = False
    last_top = None
    
    for t in tops:
        if t > ts:
            break
        bear_active = True
        last_top = t
    
    if not bear_active or last_top is None:
        return 'neutral'
    
    # Check if CFGI dropped below threshold after last top
    mask = (cfgi.index > last_top) & (cfgi.index <= ts)
    if mask.any():
        low_cfgi = cfgi[mask]
        below = low_cfgi[low_cfgi < threshold]
        if len(below) > 0:
            clear_date = below.index[0]
            
            # If requiring 3D structure, check that too
            if require_3d_hh and df_3d is not None:
                mask_3d = (df_3d.index > clear_date) & (df_3d.index <= ts)
                if mask_3d.any():
                    hh_after = df_3d.loc[mask_3d, 'hh_hl_streak']
                    if not (hh_after >= 1).any():
                        return 'bear'  # CFGI bottomed but no structure yet
                else:
                    return 'bear'
            
            # Check if another top fired after the clear
            for t in tops:
                if t > clear_date and t <= ts:
                    # Re-check for another clear after this top
                    mask2 = (cfgi.index > t) & (cfgi.index <= ts)
                    if mask2.any():
                        below2 = cfgi[mask2][cfgi[mask2] < threshold]
                        if len(below2) > 0:
                            if require_3d_hh and df_3d is not None:
                                cd2 = below2.index[0]
                                m3d = (df_3d.index > cd2) & (df_3d.index <= ts)
                                if m3d.any() and (df_3d.loc[m3d, 'hh_hl_streak'] >= 1).any():
                                    return 'neutral'
                                return 'bear'
                            return 'neutral'
                    return 'bear'
            return 'neutral'
    
    return 'bear'


def analyze(coin, profile='high'):
    pack = V13SignalPack(coin)
    cfg = make_config(profile)
    bt = V13BacktestV8(pack, cfg)
    r = bt.run()
    cfgi = load_cfgi()
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
    print(f"  CFGI data: {cfgi.index[0].date()} to {cfgi.index[-1].date()} ({len(cfgi)} days)")
    
    # Show CFGI extreme fear events
    for thresh in [10, 15, 20, 25]:
        extreme = cfgi[cfgi < thresh]
        if len(extreme) > 0:
            # Group consecutive days
            groups = []
            current_start = extreme.index[0]
            current_end = extreme.index[0]
            current_min = extreme.iloc[0]
            for idx, val in extreme.items():
                if (idx - current_end).days <= 3:
                    current_end = idx
                    current_min = min(current_min, val)
                else:
                    groups.append((current_start, current_end, current_min))
                    current_start = idx
                    current_end = idx
                    current_min = val
            groups.append((current_start, current_end, current_min))
            print(f"  CFGI < {thresh}: {len(groups)} episodes — {[(str(s.date()), f'min={m:.0f}') for s,e,m in groups[:5]]}")
    
    variants = [
        ("CFGI < 10", 10, False),
        ("CFGI < 15", 15, False),
        ("CFGI < 20", 20, False),
        ("CFGI < 25", 25, False),
        ("CFGI < 20 + 3D HH_HL>=1", 20, True),
        ("CFGI < 25 + 3D HH_HL>=1", 25, True),
    ]
    
    for label, thresh, req_3d in variants:
        blocked_good = []
        blocked_bad = []
        
        for i, t in enumerate(bt.phase_log):
            date = t.get('date')
            to_phase = str(t.get('to', ''))
            equity = t.get('equity', 0)
            
            if not date or to_phase != 'MARKUP':
                continue
            
            bias = get_bias(date, top_dates, cfgi, thresh, df_3d if req_3d else None, req_3d)
            
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
        bb = len(blocked_bad)
        bg = len(blocked_good)
        print(f"  {label:<30} Blocked: {bb}bad/{bg}good  Saved: ${saved:>+8.0f}  Missed: ${missed:>+8.0f}  Net: ${net:>+8.0f} {tag}")
    
    # Detailed for CFGI < 25
    print(f"\n  DETAIL (CFGI < 25):")
    for i, t in enumerate(bt.phase_log):
        date = t.get('date')
        to_phase = str(t.get('to', ''))
        equity = t.get('equity', 0)
        if not date or to_phase != 'MARKUP':
            continue
        bias = get_bias(date, top_dates, cfgi, 25)
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
        # Get CFGI at entry
        cfgi_at = cfgi.loc[:pd.Timestamp(date)].iloc[-1] if len(cfgi.loc[:pd.Timestamp(date)]) > 0 else float('nan')
        print(f"    {str(date)[:10]}: bias={bias:>7}, CFGI={cfgi_at:>4.0f}, pnl={pnl:>+8.0f} ({pnl_pct:>+5.1f}%) [{quality}]{marker}")


if __name__ == '__main__':
    print("CFGI BOTTOM SIGNAL BIAS TEST")
    print("Bear ON: engine top. Bear OFF: CFGI drops below threshold.")
    print("Only blocks MARKUP during bear.\n")
    
    for coin in ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']:
        analyze(coin, 'high')
