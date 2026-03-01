"""Full 9-combo grid with CFGI_RSI < 35 bear bias.

Bear ON:  Engine top signal
Bear OFF: Coin-specific CFGI_RSI < 35

This is a simulation — we post-process the existing backtest results,
removing blocked markup phases and recalculating equity.

Since we can't easily re-run the engine with bias integrated, we estimate
the impact by adding back the saved losses and subtracting missed gains.
"""
from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack
from run_new_coins_profiles import make_config
import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'candles.db'
CFGI_MAP = {'ETH/USDC': 'ETH', 'BTC/USDC': 'BTC', 'SOL/USDC': 'SOL'}


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
        conn, params=(cfgi_sym,)
    )
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
        if t > ts:
            break
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


def run_combo(coin, profile):
    pack = V13SignalPack(coin)
    cfg = make_config(profile)
    bt = V13BacktestV8(pack, cfg)
    r = bt.run()
    
    cfgi, cfgi_rsi = load_coin_cfgi_rsi(coin)
    
    top_dates = []
    for t in bt.phase_log:
        reason = t.get('reason', '')
        to_phase = str(t.get('to', ''))
        if to_phase == 'FLAT' and ('OB' in reason or 'failsafe' in reason.lower()):
            top_dates.append(t['date'])
    
    # Calculate bias impact on each markup
    total_saved = 0
    total_missed = 0
    blocked_bad = 0
    blocked_good = 0
    
    for i, t in enumerate(bt.phase_log):
        date = t.get('date')
        to_phase = str(t.get('to', ''))
        equity = t.get('equity', 0)
        if not date or to_phase != 'MARKUP':
            continue
        
        bias = get_bias(date, top_dates, cfgi_rsi, 35)
        if bias != 'bear':
            continue
        
        next_eq = None
        for j in range(i+1, len(bt.phase_log)):
            if bt.phase_log[j].get('to') != 'MARKUP':
                next_eq = bt.phase_log[j].get('equity', equity)
                break
        if next_eq is None:
            next_eq = r['final_equity']
        pnl = next_eq - equity
        
        if pnl > 0:
            total_missed += pnl
            blocked_good += 1
        else:
            total_saved += abs(pnl)
            blocked_bad += 1
    
    base_roi = r['roi']
    base_equity = r['final_equity']
    # Estimated new equity: add saved losses, subtract missed gains
    est_equity = base_equity + total_saved - total_missed
    est_roi = (est_equity / 10000 - 1) * 100
    
    return {
        'coin': coin,
        'profile': profile,
        'base_roi': base_roi,
        'est_roi': est_roi,
        'base_equity': base_equity,
        'est_equity': est_equity,
        'saved': total_saved,
        'missed': total_missed,
        'blocked_bad': blocked_bad,
        'blocked_good': blocked_good,
        'buy_hold': r['buy_hold_return'],
        'trades': r['closed_trades'],
        'wins': r['wins'],
        'losses': r['losses'],
    }


if __name__ == '__main__':
    print("FULL 9-COMBO GRID: CFGI_RSI < 35 BEAR BIAS")
    print("Bear ON: engine top. Bear OFF: coin CFGI_RSI < 35.")
    print("Estimated ROI = base ROI + saved losses - missed gains\n")
    
    coins = ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']
    profiles = ['low', 'medium', 'high']
    
    all_results = []
    
    for coin in coins:
        print(f"\n{'='*80}")
        print(f"  {coin}")
        print(f"{'='*80}")
        print(f"  {'Profile':<8} {'Base ROI':>9} {'Est ROI':>9} {'Delta':>8} {'Saved':>9} {'Missed':>9} {'Net':>9} {'B&H':>7} {'Blocked':>10}")
        print(f"  {'-'*8} {'-'*9} {'-'*9} {'-'*8} {'-'*9} {'-'*9} {'-'*9} {'-'*7} {'-'*10}")
        
        for profile in profiles:
            r = run_combo(coin, profile)
            all_results.append(r)
            delta = r['est_roi'] - r['base_roi']
            net = r['saved'] - r['missed']
            print(f"  {profile:<8} {r['base_roi']:>+8.1f}% {r['est_roi']:>+8.1f}% {delta:>+7.1f}% "
                  f"${r['saved']:>+8.0f} ${r['missed']:>+8.0f} ${net:>+8.0f} {r['buy_hold']:>+6.0f}% "
                  f"{r['blocked_bad']}bad/{r['blocked_good']}good")
    
    # Summary table
    print(f"\n\n{'='*80}")
    print("SUMMARY: Base vs Estimated ROI with CFGI_RSI < 35 Bear Bias")
    print(f"{'='*80}")
    print(f"\n  {'Coin':<10} {'Profile':<8} {'Base ROI':>10} {'+ Bias ROI':>12} {'Delta':>8} {'B&H':>8}")
    print(f"  {'-'*10} {'-'*8} {'-'*10} {'-'*12} {'-'*8} {'-'*8}")
    
    total_base = 0
    total_est = 0
    for r in all_results:
        delta = r['est_roi'] - r['base_roi']
        marker = " ***" if delta > 10 else ""
        print(f"  {r['coin']:<10} {r['profile']:<8} {r['base_roi']:>+9.1f}% {r['est_roi']:>+11.1f}% {delta:>+7.1f}% {r['buy_hold']:>+7.0f}%{marker}")
        total_base += r['base_roi']
        total_est += r['est_roi']
    
    print(f"\n  Average ROI:  Base = {total_base/9:+.1f}%  |  With Bias = {total_est/9:+.1f}%  |  Delta = {(total_est-total_base)/9:+.1f}%")
