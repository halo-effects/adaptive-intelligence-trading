"""Test CFGI RSI as bottom signal — RSI applied to CFGI values.

CFGI RSI < 30 = sentiment itself is oversold (fear dropping fast relative to recent)
CFGI RSI > 70 = sentiment itself is overbought (greed peaking)

This is adaptive — works regardless of absolute CFGI level.

Bear ON:  Engine top signal
Bear OFF: Coin-specific CFGI RSI < threshold (sentiment capitulation)

Also test combined: CFGI RSI < 30 AND raw CFGI < 30 (double confirmation)
"""
from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack
from run_new_coins_profiles import make_config
import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'candles.db'

CFGI_MAP = {
    'ETH/USDC': 'ETH',
    'BTC/USDC': 'BTC',
    'SOL/USDC': 'SOL',
}


def compute_rsi(series, period=14):
    """Compute RSI on any series."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).ewm(alpha=1/period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def load_coin_cfgi_with_rsi(coin):
    """Load coin-specific CFGI and compute RSI on it."""
    cfgi_sym = CFGI_MAP.get(coin, coin.split('/')[0])
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT date, cfgi FROM cfgi_daily WHERE symbol=? ORDER BY date",
        conn, params=(cfgi_sym,)
    )
    conn.close()
    
    if df.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    
    df['date'] = pd.to_datetime(df['date'], format='mixed')
    df = df.set_index('date').sort_index()
    df = df[~df.index.duplicated(keep='last')]
    
    cfgi = df['cfgi']
    cfgi_rsi = compute_rsi(cfgi, period=14)
    
    return cfgi, cfgi_rsi


def get_bias(date, top_dates, cfgi, cfgi_rsi, rsi_thresh=30, cfgi_thresh=None):
    """Bear after top, clears when CFGI RSI < rsi_thresh (and optionally raw CFGI < cfgi_thresh)."""
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
    
    mask = (cfgi_rsi.index > last_top) & (cfgi_rsi.index <= ts)
    if not mask.any():
        return 'bear'
    
    sub_rsi = cfgi_rsi[mask]
    below_rsi = sub_rsi[sub_rsi < rsi_thresh]
    
    if len(below_rsi) == 0:
        return 'bear'
    
    clear_date = below_rsi.index[0]
    
    # If also requiring raw CFGI threshold
    if cfgi_thresh is not None:
        sub_cfgi = cfgi[(cfgi.index > last_top) & (cfgi.index <= ts)]
        below_cfgi = sub_cfgi[sub_cfgi < cfgi_thresh]
        if len(below_cfgi) == 0:
            return 'bear'
        # Both must fire — use the later of the two
        clear_date = max(clear_date, below_cfgi.index[0])
    
    # Check if another top fired after clear
    for t in tops:
        if t > clear_date and t <= ts:
            mask2 = (cfgi_rsi.index > t) & (cfgi_rsi.index <= ts)
            if mask2.any():
                sub2 = cfgi_rsi[mask2]
                below2 = sub2[sub2 < rsi_thresh]
                if len(below2) > 0:
                    cd2 = below2.index[0]
                    if cfgi_thresh is not None:
                        sc2 = cfgi[(cfgi.index > t) & (cfgi.index <= ts)]
                        bc2 = sc2[sc2 < cfgi_thresh]
                        if len(bc2) > 0:
                            continue
                        return 'bear'
                    continue
                return 'bear'
            return 'bear'
    
    return 'neutral'


def analyze(coin, profile='high'):
    pack = V13SignalPack(coin)
    cfg = make_config(profile)
    bt = V13BacktestV8(pack, cfg)
    r = bt.run()
    
    cfgi, cfgi_rsi = load_coin_cfgi_with_rsi(coin)
    csym = CFGI_MAP.get(coin, '?')
    
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
    print(f"  {csym} CFGI: {len(cfgi)} days")
    
    # Show CFGI RSI extreme events
    for thresh in [20, 25, 30, 35]:
        extreme = cfgi_rsi[cfgi_rsi < thresh].dropna()
        if len(extreme) > 0:
            groups = []
            cs, ce, cm = extreme.index[0], extreme.index[0], extreme.iloc[0]
            for idx, val in extreme.items():
                if (idx - ce).days <= 3:
                    ce = idx
                    cm = min(cm, val)
                else:
                    groups.append((cs.date(), f"{cm:.0f}"))
                    cs, ce, cm = idx, idx, val
            groups.append((cs.date(), f"{cm:.0f}"))
            print(f"  {csym} CFGI_RSI < {thresh}: {len(groups)} episodes")
    
    variants = [
        (f"CFGI_RSI < 20", 20, None),
        (f"CFGI_RSI < 25", 25, None),
        (f"CFGI_RSI < 30", 30, None),
        (f"CFGI_RSI < 35", 35, None),
        (f"CFGI_RSI<30 + CFGI<30", 30, 30),
        (f"CFGI_RSI<30 + CFGI<40", 30, 40),
        (f"CFGI_RSI<35 + CFGI<30", 35, 30),
    ]
    
    for label, rsi_t, cfgi_t in variants:
        blocked_good = []
        blocked_bad = []
        
        for i, t in enumerate(bt.phase_log):
            date = t.get('date')
            to_phase = str(t.get('to', ''))
            equity = t.get('equity', 0)
            if not date or to_phase != 'MARKUP':
                continue
            
            bias = get_bias(date, top_dates, cfgi, cfgi_rsi, rsi_t, cfgi_t)
            
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
        bb, bg = len(blocked_bad), len(blocked_good)
        print(f"  {label:<30} Blocked: {bb}bad/{bg}good  Saved: ${saved:>+8.0f}  Missed: ${missed:>+8.0f}  Net: ${net:>+8.0f} {tag}")
    
    # Detailed for CFGI_RSI < 30
    print(f"\n  DETAIL (CFGI_RSI < 30):")
    for i, t in enumerate(bt.phase_log):
        date = t.get('date')
        to_phase = str(t.get('to', ''))
        equity = t.get('equity', 0)
        if not date or to_phase != 'MARKUP':
            continue
        
        bias = get_bias(date, top_dates, cfgi, cfgi_rsi, 30, None)
        
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
        
        cfgi_at = cfgi.loc[:pd.Timestamp(date)]
        cfgi_val = cfgi_at.iloc[-1] if len(cfgi_at) > 0 else float('nan')
        rsi_at = cfgi_rsi.loc[:pd.Timestamp(date)]
        rsi_val = rsi_at.iloc[-1] if len(rsi_at) > 0 else float('nan')
        
        quality = "GOOD" if good else "BAD"
        marker = " ** BLOCKED" if blocked else ""
        print(f"    {str(date)[:10]}: bias={bias:>7}, CFGI={cfgi_val:>5.1f}, CFGI_RSI={rsi_val:>5.1f}, pnl={pnl:>+8.0f} ({pnl_pct:>+5.1f}%) [{quality}]{marker}")


if __name__ == '__main__':
    print("CFGI RSI BIAS TEST")
    print("RSI applied to CFGI values — sentiment momentum indicator.")
    print("Bear ON: engine top. Bear OFF: CFGI RSI < threshold.\n")
    
    for coin in ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']:
        analyze(coin, 'high')
