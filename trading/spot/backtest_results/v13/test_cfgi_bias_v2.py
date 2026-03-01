"""CFGI Bias V2: Coin-specific CFGI + ROC confirmation.

Uses per-coin CFGI from DB (not market average).
Tests:
  1. Coin-specific CFGI < threshold as bottom signal
  2. CFGI ROC (rate of change) as momentum confirmation
  3. Combined: CFGI < threshold AND ROC turning positive (sentiment recovering)

ROC idea: A falling CFGI hitting extreme fear is the bottom.
But the CLEAR signal should be when CFGI starts recovering (ROC > 0 after extreme).
This avoids clearing bear too early (while still falling) or too late.
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

# Map backtest coin symbols to CFGI symbols
CFGI_MAP = {
    'ETH/USDC': 'ETH',
    'BTC/USDC': 'BTC', 
    'SOL/USDC': 'SOL',
}


def load_coin_cfgi(coin):
    """Load coin-specific CFGI data."""
    cfgi_sym = CFGI_MAP.get(coin, coin.split('/')[0])
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        f"SELECT date, cfgi FROM cfgi_daily WHERE symbol=? ORDER BY date",
        conn, params=(cfgi_sym,)
    )
    conn.close()
    
    if df.empty:
        # Try market average as fallback
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(
            "SELECT date, AVG(cfgi) as cfgi FROM cfgi_daily GROUP BY date ORDER BY date", conn
        )
        conn.close()
        print(f"  WARNING: No coin-specific CFGI for {cfgi_sym}, using market average")
    
    if df.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    
    df['date'] = pd.to_datetime(df['date'], format='mixed')
    df = df.set_index('date').sort_index()
    # Remove duplicates
    df = df[~df.index.duplicated(keep='last')]
    
    cfgi = df['cfgi']
    
    # Compute ROC (7-day rate of change)
    roc_7 = cfgi.diff(7)
    # Also 14-day ROC for smoother signal
    roc_14 = cfgi.diff(14)
    
    return cfgi, roc_7, roc_14


def load_market_cfgi():
    """Load market-level CFGI (average across all coins)."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT date, AVG(cfgi) as cfgi FROM cfgi_daily GROUP BY date ORDER BY date", conn
    )
    conn.close()
    if df.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    df['date'] = pd.to_datetime(df['date'], format='mixed')
    df = df.set_index('date').sort_index()
    df = df[~df.index.duplicated(keep='last')]
    cfgi = df['cfgi']
    roc_7 = cfgi.diff(7)
    roc_14 = cfgi.diff(14)
    return cfgi, roc_7, roc_14


def get_bias(date, top_dates, cfgi, roc, threshold, roc_confirm=False):
    """Bear after top, clears when CFGI < threshold (optionally + ROC turning positive)."""
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
    
    # Check if clear condition met after last top
    mask = (cfgi.index > last_top) & (cfgi.index <= ts)
    if not mask.any():
        return 'bear'
    
    sub_cfgi = cfgi[mask]
    below = sub_cfgi[sub_cfgi < threshold]
    
    if len(below) == 0:
        return 'bear'
    
    # CFGI hit extreme fear
    extreme_date = below.index[0]
    
    if roc_confirm and roc is not None:
        # Wait for ROC to turn positive AFTER the extreme fear
        roc_mask = (roc.index > extreme_date) & (roc.index <= ts)
        if roc_mask.any():
            roc_after = roc[roc_mask]
            positive_roc = roc_after[roc_after > 0]
            if len(positive_roc) == 0:
                return 'bear'  # Still falling
            clear_date = positive_roc.index[0]
        else:
            return 'bear'
    else:
        clear_date = extreme_date
    
    # Check if another top fired after the clear
    for t in tops:
        if t > clear_date and t <= ts:
            # Re-engaged bear — check for another clear
            mask2 = (cfgi.index > t) & (cfgi.index <= ts)
            if mask2.any():
                sub2 = cfgi[mask2]
                below2 = sub2[sub2 < threshold]
                if len(below2) > 0:
                    ext2 = below2.index[0]
                    if roc_confirm and roc is not None:
                        rm2 = (roc.index > ext2) & (roc.index <= ts)
                        if rm2.any():
                            pr2 = roc[rm2][roc[rm2] > 0]
                            if len(pr2) > 0:
                                continue  # Cleared again
                        return 'bear'
                    else:
                        continue  # Cleared again
                else:
                    return 'bear'
            else:
                return 'bear'
    
    return 'neutral'


def analyze(coin, profile='high'):
    pack = V13SignalPack(coin)
    cfg = make_config(profile)
    bt = V13BacktestV8(pack, cfg)
    r = bt.run()
    
    # Load both coin-specific and market CFGI
    coin_cfgi, coin_roc7, coin_roc14 = load_coin_cfgi(coin)
    mkt_cfgi, mkt_roc7, mkt_roc14 = load_market_cfgi()
    
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
    
    csym = CFGI_MAP.get(coin, '?')
    print(f"  Coin CFGI ({csym}): {len(coin_cfgi)} days, {coin_cfgi.index[0].date()} to {coin_cfgi.index[-1].date()}")
    
    # Show extreme fear episodes for coin-specific
    for thresh in [15, 20, 25, 30]:
        extreme = coin_cfgi[coin_cfgi < thresh]
        if len(extreme) > 0:
            groups = []
            cs, ce, cm = extreme.index[0], extreme.index[0], extreme.iloc[0]
            for idx, val in extreme.items():
                if (idx - ce).days <= 3:
                    ce = idx
                    cm = min(cm, val)
                else:
                    groups.append((cs, cm))
                    cs, ce, cm = idx, idx, val
            groups.append((cs, cm))
            print(f"  {csym} CFGI < {thresh}: {len(groups)} episodes")
    
    variants = [
        # (label, cfgi_series, roc_series, threshold, roc_confirm)
        (f"{csym} CFGI < 25", coin_cfgi, None, 25, False),
        (f"{csym} CFGI < 30", coin_cfgi, None, 30, False),
        (f"{csym} CFGI < 25 + ROC7>0", coin_cfgi, coin_roc7, 25, True),
        (f"{csym} CFGI < 30 + ROC7>0", coin_cfgi, coin_roc7, 30, True),
        (f"{csym} CFGI < 25 + ROC14>0", coin_cfgi, coin_roc14, 25, True),
        (f"MKT CFGI < 25", mkt_cfgi, None, 25, False),
        (f"MKT CFGI < 25 + ROC7>0", mkt_cfgi, mkt_roc7, 25, True),
    ]
    
    for label, cfgi, roc, thresh, roc_conf in variants:
        blocked_good = []
        blocked_bad = []
        
        for i, t in enumerate(bt.phase_log):
            date = t.get('date')
            to_phase = str(t.get('to', ''))
            equity = t.get('equity', 0)
            if not date or to_phase != 'MARKUP':
                continue
            
            bias = get_bias(date, top_dates, cfgi, roc, thresh, roc_conf)
            
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
    
    # Detailed for best variant
    print(f"\n  DETAIL ({csym} CFGI < 25 + ROC7>0):")
    for i, t in enumerate(bt.phase_log):
        date = t.get('date')
        to_phase = str(t.get('to', ''))
        equity = t.get('equity', 0)
        if not date or to_phase != 'MARKUP':
            continue
        
        bias = get_bias(date, top_dates, coin_cfgi, coin_roc7, 25, True)
        
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
        
        # Get coin CFGI and ROC at entry
        cfgi_at = coin_cfgi.loc[:pd.Timestamp(date)]
        cfgi_val = cfgi_at.iloc[-1] if len(cfgi_at) > 0 else float('nan')
        roc_at = coin_roc7.loc[:pd.Timestamp(date)]
        roc_val = roc_at.iloc[-1] if len(roc_at) > 0 else float('nan')
        
        quality = "GOOD" if good else "BAD"
        marker = " ** BLOCKED" if blocked else ""
        print(f"    {str(date)[:10]}: bias={bias:>7}, CFGI={cfgi_val:>5.1f}, ROC7={roc_val:>+5.1f}, pnl={pnl:>+8.0f} ({pnl_pct:>+5.1f}%) [{quality}]{marker}")


if __name__ == '__main__':
    print("CFGI BIAS V2: COIN-SPECIFIC + ROC CONFIRMATION")
    print("Bear ON: engine top. Bear OFF: coin CFGI < threshold (+ optional ROC>0).")
    print("Only blocks MARKUP during bear.\n")
    
    for coin in ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']:
        analyze(coin, 'high')
