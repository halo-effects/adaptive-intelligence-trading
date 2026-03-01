"""Run CFGI_RSI < 35 bear bias test on LINK and XRP."""
import sys
sys.path.insert(0, '.')

from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack
from run_new_coins_profiles import make_config
import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'candles.db'
CFGI_MAP = {'ETH/USDC': 'ETH', 'BTC/USDC': 'BTC', 'SOL/USDC': 'SOL', 'LINK/USDC': 'LINK', 'XRP/USDC': 'XRP'}


def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).ewm(alpha=1/period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def load_coin_cfgi_rsi(coin):
    cfgi_sym = CFGI_MAP.get(coin, coin.split('/')[0])
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT date, cfgi FROM cfgi_daily WHERE symbol=? ORDER BY date",
        conn, params=(cfgi_sym,))
    conn.close()
    if df.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    df['date'] = pd.to_datetime(df['date'], format='mixed')
    df = df.set_index('date').sort_index()
    df = df[~df.index.duplicated(keep='last')]
    cfgi = df['cfgi']
    cfgi_rsi = compute_rsi(cfgi, 14)
    return cfgi, cfgi_rsi


def get_bias(date, top_dates, cfgi_rsi, threshold=35):
    ts = pd.Timestamp(date)
    tops = sorted([pd.Timestamp(d) for d in top_dates])
    bear_active = False
    last_top = None
    for t in tops:
        if t > ts: break
        bear_active = True
        last_top = t
    if not bear_active or last_top is None:
        return 'neutral'
    mask = (cfgi_rsi.index > last_top) & (cfgi_rsi.index <= ts)
    if not mask.any():
        return 'bear'
    sub = cfgi_rsi[mask]
    below = sub[sub < threshold]
    if len(below) == 0:
        return 'bear'
    clear_date = below.index[0]
    for t in tops:
        if t > clear_date and t <= ts:
            mask2 = (cfgi_rsi.index > t) & (cfgi_rsi.index <= ts)
            if mask2.any():
                sub2 = cfgi_rsi[mask2]
                below2 = sub2[sub2 < threshold]
                if len(below2) > 0:
                    clear_date = below2.index[0]
                    continue
                return 'bear'
            return 'bear'
    return 'neutral'


def analyze(coin, profile='high'):
    try:
        pack = V13SignalPack(coin)
    except Exception as e:
        print(f"  {coin}: Cannot load signal pack: {e}")
        return
    
    cfg = make_config(profile)
    bt = V13BacktestV8(pack, cfg)
    r = bt.run()
    cfgi, cfgi_rsi = load_coin_cfgi_rsi(coin)
    csym = CFGI_MAP.get(coin, '?')
    
    top_dates = []
    for t in bt.phase_log:
        reason = t.get('reason', '')
        to_phase = str(t.get('to', ''))
        if to_phase == 'FLAT' and ('OB' in reason or 'failsafe' in reason.lower()):
            top_dates.append(t['date'])
    
    print(f"\n{'='*70}")
    print(f"{coin} ({profile}) -- ROI: {r['roi']:+.1f}%, B&H: {r['buy_hold_return']:+.0f}%")
    print(f"{'='*70}")
    print(f"  Tops: {[str(d)[:10] for d in top_dates]}")
    print(f"  {csym} CFGI: {len(cfgi)} days ({cfgi.index[0].date()} to {cfgi.index[-1].date()})" if len(cfgi) > 0 else f"  {csym} CFGI: no data")
    
    for thresh in [30, 35]:
        blocked_good = []
        blocked_bad = []
        
        for i, t in enumerate(bt.phase_log):
            date = t.get('date')
            to_phase = str(t.get('to', ''))
            equity = t.get('equity', 0)
            if not date or to_phase != 'MARKUP':
                continue
            
            bias = get_bias(date, top_dates, cfgi_rsi, thresh)
            
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
        print(f"  CFGI_RSI < {thresh:>2}  Blocked: {bb}bad/{bg}good  Saved: ${saved:>+8.0f}  Missed: ${missed:>+8.0f}  Net: ${net:>+8.0f} {tag}")
    
    # Detailed for CFGI_RSI < 35
    print(f"\n  DETAIL (CFGI_RSI < 35):")
    for i, t in enumerate(bt.phase_log):
        date = t.get('date')
        to_phase = str(t.get('to', ''))
        equity = t.get('equity', 0)
        if not date or to_phase != 'MARKUP':
            continue
        bias = get_bias(date, top_dates, cfgi_rsi, 35)
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
    print("CFGI_RSI BEAR BIAS: LINK and XRP")
    print("Bear ON: engine top. Bear OFF: coin CFGI_RSI < threshold.\n")
    
    for coin in ['LINK/USDC', 'XRP/USDC']:
        for profile in ['high']:
            analyze(coin, profile)
