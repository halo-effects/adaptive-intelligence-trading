"""Test StochRSI applied to CFGI as bear-clearing signal.

StochRSI = (RSI - RSI_low) / (RSI_high - RSI_low) over N periods
Then smooth with K (fast) and D (slow) lines.

Signals tested:
1. StochRSI K < threshold (simple level, like RSI < 35)
2. StochRSI K crosses above D in oversold zone (classic StochRSI signal)
3. StochRSI K crosses above threshold from below (level cross)

Bear ON:  Engine top signal
Bear OFF: StochRSI-based clearing

Compare directly against baseline CFGI_RSI < 35.
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
    """Wilder's RSI."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).ewm(alpha=1/period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_stochrsi(series, rsi_period=14, stoch_period=14, k_smooth=3, d_smooth=3):
    """Compute StochRSI with K and D lines.
    
    1. Compute RSI(rsi_period) on the series
    2. Apply stochastic formula: (RSI - RSI_low) / (RSI_high - RSI_low) over stoch_period
    3. K = SMA(k_smooth) of raw StochRSI
    4. D = SMA(d_smooth) of K
    
    Returns K and D as 0-100 scale.
    """
    rsi = compute_rsi(series, rsi_period)
    
    rsi_low = rsi.rolling(stoch_period, min_periods=stoch_period).min()
    rsi_high = rsi.rolling(stoch_period, min_periods=stoch_period).max()
    
    denom = rsi_high - rsi_low
    stoch_raw = ((rsi - rsi_low) / denom.replace(0, np.nan)) * 100
    
    k = stoch_raw.rolling(k_smooth, min_periods=k_smooth).mean()
    d = k.rolling(d_smooth, min_periods=d_smooth).mean()
    
    return rsi, k, d


def load_coin_cfgi_stochrsi(coin, rsi_period=14, stoch_period=14, k_smooth=3, d_smooth=3):
    """Load coin-specific CFGI and compute StochRSI on it."""
    cfgi_sym = CFGI_MAP.get(coin, coin.split('/')[0])
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT date, cfgi FROM cfgi_daily WHERE symbol=? ORDER BY date",
        conn, params=(cfgi_sym,)
    )
    conn.close()
    
    if df.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)
    
    df['date'] = pd.to_datetime(df['date'], format='mixed')
    df = df.set_index('date').sort_index()
    df = df[~df.index.duplicated(keep='last')]
    
    cfgi = df['cfgi']
    rsi, k, d = compute_stochrsi(cfgi, rsi_period, stoch_period, k_smooth, d_smooth)
    
    return cfgi, rsi, k, d


def detect_kd_cross_up(k, d, before_date, after_date, os_thresh=20):
    """Find first K/D bullish cross in oversold zone between two dates."""
    mask = (k.index > pd.Timestamp(after_date)) & (k.index <= pd.Timestamp(before_date))
    k_sub = k[mask]
    d_sub = d[mask]
    
    for i in range(1, len(k_sub)):
        curr_k = k_sub.iloc[i]
        prev_k = k_sub.iloc[i-1]
        curr_d = d_sub.iloc[i]
        prev_d = d_sub.iloc[i-1]
        
        if np.isnan(curr_k) or np.isnan(prev_k) or np.isnan(curr_d) or np.isnan(prev_d):
            continue
        
        # K crosses above D while in oversold territory
        if prev_k <= prev_d and curr_k > curr_d and curr_k < os_thresh:
            return k_sub.index[i]
    
    return None


def get_bias_stochrsi_level(date, top_dates, k, thresh=20):
    """Bear clears when StochRSI K drops below threshold (simple level)."""
    ts = pd.Timestamp(date)
    tops = sorted([pd.Timestamp(d) for d in top_dates])
    
    last_top = None
    for t in tops:
        if t > ts:
            break
        last_top = t
    
    if last_top is None:
        return 'neutral'
    
    mask = (k.index > last_top) & (k.index <= ts)
    if not mask.any():
        return 'bear'
    
    sub_k = k[mask]
    below = sub_k[sub_k < thresh]
    
    if len(below) == 0:
        return 'bear'
    
    clear_date = below.index[0]
    
    # Check for subsequent tops after clear
    for t in tops:
        if t > clear_date and t <= ts:
            mask2 = (k.index > t) & (k.index <= ts)
            if mask2.any():
                sub2 = k[mask2]
                below2 = sub2[sub2 < thresh]
                if len(below2) > 0:
                    clear_date = below2.index[0]
                    continue
                return 'bear'
            return 'bear'
    
    return 'neutral'


def get_bias_stochrsi_cross(date, top_dates, k, d, os_thresh=20):
    """Bear clears when StochRSI K crosses above D in oversold zone."""
    ts = pd.Timestamp(date)
    tops = sorted([pd.Timestamp(d_) for d_ in top_dates])
    
    last_top = None
    for t in tops:
        if t > ts:
            break
        last_top = t
    
    if last_top is None:
        return 'neutral'
    
    cross_date = detect_kd_cross_up(k, d, date, last_top, os_thresh)
    
    if cross_date is None:
        return 'bear'
    
    # Check for subsequent tops after cross
    for t in tops:
        if t > cross_date and t <= ts:
            cross2 = detect_kd_cross_up(k, d, date, t, os_thresh)
            if cross2 is None:
                return 'bear'
            cross_date = cross2
    
    return 'neutral'


def get_bias_stochrsi_cross_up(date, top_dates, k, thresh=20):
    """Bear clears when StochRSI K crosses above threshold from below."""
    ts = pd.Timestamp(date)
    tops = sorted([pd.Timestamp(d) for d in top_dates])
    
    last_top = None
    for t in tops:
        if t > ts:
            break
        last_top = t
    
    if last_top is None:
        return 'neutral'
    
    mask = (k.index > last_top) & (k.index <= ts)
    if not mask.any():
        return 'bear'
    
    sub_k = k[mask]
    
    # Find first time K goes below thresh, then comes back above
    went_below = False
    clear_date = None
    for i in range(len(sub_k)):
        val = sub_k.iloc[i]
        if np.isnan(val):
            continue
        if val < thresh:
            went_below = True
        elif went_below and val >= thresh:
            clear_date = sub_k.index[i]
            break
    
    if clear_date is None:
        return 'bear'
    
    # Check for subsequent tops after clear
    for t in tops:
        if t > clear_date and t <= ts:
            mask2 = (k.index > t) & (k.index <= ts)
            if mask2.any():
                sub2 = k[mask2]
                wb = False
                cd2 = None
                for i in range(len(sub2)):
                    v = sub2.iloc[i]
                    if np.isnan(v): continue
                    if v < thresh: wb = True
                    elif wb and v >= thresh:
                        cd2 = sub2.index[i]
                        break
                if cd2 is None:
                    return 'bear'
                clear_date = cd2
            else:
                return 'bear'
    
    return 'neutral'


# Also include baseline RSI < 35 for direct comparison
def compute_plain_rsi(series, period=14):
    return compute_rsi(series, period)


def get_bias_rsi_level(date, top_dates, cfgi_rsi, thresh=35):
    """Baseline: plain RSI < thresh."""
    ts = pd.Timestamp(date)
    tops = sorted([pd.Timestamp(d) for d in top_dates])
    
    last_top = None
    for t in tops:
        if t > ts: break
        last_top = t
    
    if last_top is None:
        return 'neutral'
    
    mask = (cfgi_rsi.index > last_top) & (cfgi_rsi.index <= ts)
    if not mask.any():
        return 'bear'
    
    sub = cfgi_rsi[mask]
    below = sub[sub < thresh]
    if len(below) == 0:
        return 'bear'
    
    clear_date = below.index[0]
    for t in tops:
        if t > clear_date and t <= ts:
            mask2 = (cfgi_rsi.index > t) & (cfgi_rsi.index <= ts)
            if mask2.any():
                sub2 = cfgi_rsi[mask2]
                below2 = sub2[sub2 < thresh]
                if len(below2) > 0:
                    clear_date = below2.index[0]
                    continue
                return 'bear'
            return 'bear'
    
    return 'neutral'


def analyze(coin, profile='high'):
    pack = V13SignalPack(coin)
    cfg = make_config(profile)
    bt = V13BacktestV8(pack, cfg)
    r = bt.run()
    
    # Load CFGI data
    cfgi, plain_rsi, stoch_k, stoch_d = load_coin_cfgi_stochrsi(coin)
    # Also get plain RSI for baseline
    cfgi_sym = CFGI_MAP.get(coin, '?')
    
    # Get top dates from engine
    top_dates = []
    for t in bt.phase_log:
        reason = t.get('reason', '')
        to_phase = str(t.get('to', ''))
        if to_phase == 'FLAT' and ('OB' in reason or 'failsafe' in reason.lower()):
            top_dates.append(t['date'])
    
    print(f"\n{'='*80}")
    print(f"{coin} ({profile}) — ROI: {r['roi']:+.1f}% | Tops: {len(top_dates)} | CFGI days: {len(cfgi)}")
    print(f"{'='*80}")
    print(f"  Top dates: {[str(d)[:10] for d in top_dates]}")
    
    # Also compute different StochRSI parameter combos
    param_sets = [
        (14, 14, 3, 3, "StochRSI(14,14,3,3)"),  # Standard
        (14, 14, 5, 5, "StochRSI(14,14,5,5)"),  # More smoothing
        (14, 21, 3, 3, "StochRSI(14,21,3,3)"),  # Longer lookback
        (7, 14, 3, 3,  "StochRSI(7,14,3,3)"),   # Faster RSI
        (14, 14, 3, 3, None),  # default for detailed tests
    ]
    
    # Build all variants
    variants = []
    
    # Baseline: plain CFGI RSI < 35
    variants.append(("BASELINE: RSI(14) < 35", lambda date: get_bias_rsi_level(date, top_dates, plain_rsi, 35)))
    
    # StochRSI K level tests (standard params)
    for thresh in [10, 15, 20, 25, 30]:
        label = f"StochRSI K < {thresh} (level)"
        thresh_copy = thresh
        variants.append((label, lambda date, t=thresh_copy: get_bias_stochrsi_level(date, top_dates, stoch_k, t)))
    
    # StochRSI K/D cross in oversold zone
    for os_t in [20, 25, 30, 35]:
        label = f"StochRSI K×D cross (OS<{os_t})"
        os_copy = os_t
        variants.append((label, lambda date, o=os_copy: get_bias_stochrsi_cross(date, top_dates, stoch_k, stoch_d, o)))
    
    # StochRSI K cross-up above threshold
    for thresh in [15, 20, 25, 30]:
        label = f"StochRSI K cross-up {thresh}"
        thresh_copy = thresh
        variants.append((label, lambda date, t=thresh_copy: get_bias_stochrsi_cross_up(date, top_dates, stoch_k, t)))
    
    # Different StochRSI parameters (K < 20 level only, to compare params)
    for rsi_p, stoch_p, k_s, d_s, plabel in param_sets[1:4]:
        _, _, alt_k, alt_d = load_coin_cfgi_stochrsi(coin, rsi_p, stoch_p, k_s, d_s)
        label = f"{plabel} K < 20"
        variants.append((label, lambda date, ak=alt_k: get_bias_stochrsi_level(date, top_dates, ak, 20)))
        label2 = f"{plabel} K×D (OS<25)"
        variants.append((label2, lambda date, ak=alt_k, ad=alt_d: get_bias_stochrsi_cross(date, top_dates, ak, ad, 25)))
    
    # Run all variants
    print(f"\n  {'Signal':<40} {'Bad':>4} {'Good':>5} {'Saved':>9} {'Missed':>9} {'Net':>9} Verdict")
    print(f"  {'-'*40} {'-'*4} {'-'*5} {'-'*9} {'-'*9} {'-'*9} -------")
    
    for label, bias_fn in variants:
        blocked_good = []
        blocked_bad = []
        
        for i, t in enumerate(bt.phase_log):
            date = t.get('date')
            to_phase = str(t.get('to', ''))
            equity = t.get('equity', 0)
            if not date or to_phase != 'MARKUP':
                continue
            
            bias = bias_fn(date)
            
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
        
        saved = abs(sum(p for _, p in blocked_bad))
        missed = sum(p for _, p in blocked_good)
        net = saved - missed
        bb, bg = len(blocked_bad), len(blocked_good)
        tag = "HELPS" if net > 0 else "HURTS" if net < 0 else "NEUTRAL"
        print(f"  {label:<40} {bb:>4} {bg:>5} ${saved:>+8.0f} ${missed:>+8.0f} ${net:>+8.0f} {tag}")
    
    # Detailed entry analysis with StochRSI values
    print(f"\n  ENTRY DETAIL (StochRSI 14,14,3,3):")
    print(f"  {'Date':<12} {'CFGI':>5} {'RSI14':>6} {'K':>6} {'D':>6} {'PnL':>9} {'Quality':<5} {'RSI Bias':>9} {'K<20 Bias':>10} {'K×D<25':>10}")
    print(f"  {'-'*12} {'-'*5} {'-'*6} {'-'*6} {'-'*6} {'-'*9} {'-'*5} {'-'*9} {'-'*10} {'-'*10}")
    
    for i, t in enumerate(bt.phase_log):
        date = t.get('date')
        to_phase = str(t.get('to', ''))
        equity = t.get('equity', 0)
        if not date or to_phase != 'MARKUP':
            continue
        
        next_eq = None
        for j in range(i+1, len(bt.phase_log)):
            if bt.phase_log[j].get('to') != 'MARKUP':
                next_eq = bt.phase_log[j].get('equity', equity)
                break
        if next_eq is None:
            next_eq = r['final_equity']
        pnl = next_eq - equity
        quality = "GOOD" if pnl > 0 else "BAD"
        
        ts = pd.Timestamp(date)
        cfgi_val = cfgi.loc[:ts].iloc[-1] if len(cfgi.loc[:ts]) > 0 else float('nan')
        rsi_val = plain_rsi.loc[:ts].iloc[-1] if len(plain_rsi.loc[:ts]) > 0 else float('nan')
        k_val = stoch_k.loc[:ts].iloc[-1] if len(stoch_k.loc[:ts]) > 0 else float('nan')
        d_val = stoch_d.loc[:ts].iloc[-1] if len(stoch_d.loc[:ts]) > 0 else float('nan')
        
        rsi_bias = get_bias_rsi_level(date, top_dates, plain_rsi, 35)
        k_bias = get_bias_stochrsi_level(date, top_dates, stoch_k, 20)
        kd_bias = get_bias_stochrsi_cross(date, top_dates, stoch_k, stoch_d, 25)
        
        print(f"  {str(date)[:10]:<12} {cfgi_val:>5.1f} {rsi_val:>6.1f} {k_val:>6.1f} {d_val:>6.1f} ${pnl:>+8.0f} {quality:<5} {rsi_bias:>9} {k_bias:>10} {kd_bias:>10}")


if __name__ == '__main__':
    print("CFGI StochRSI BIAS TEST")
    print("StochRSI applied to CFGI values — stochastic momentum of sentiment.")
    print("Compare against baseline CFGI RSI(14) < 35.")
    print()
    print("StochRSI K/D cross = classic signal: K crosses above D in oversold zone.")
    print("StochRSI K level = simple: K drops below threshold (like RSI < 35).")
    print("StochRSI K cross-up = K goes below thresh then comes back above.\n")
    
    for coin in ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']:
        analyze(coin, 'high')
