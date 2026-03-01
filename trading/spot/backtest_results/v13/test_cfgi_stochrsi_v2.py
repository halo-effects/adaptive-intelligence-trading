"""Test CFGI StochRSI as bear-clearing signal — replacing plain RSI(14).

Same bias system:
  Bear ON:  Engine top signal
  Bear OFF: CFGI StochRSI K < threshold (sentiment capitulation)

StochRSI calculation:
  1. RSI(rsi_period) on CFGI values
  2. Stochastic formula over stoch_period: (RSI - RSI_low) / (RSI_high - RSI_low) * 100
  3. K = SMA(k_smooth) of raw stochastic
  4. D = SMA(d_smooth) of K

Sweep:
  - RSI periods: 7, 14, 21
  - Stoch periods: 7, 14, 21
  - K smoothing: 3, 5
  - Thresholds: 10, 15, 20, 25, 30, 35
  - Also test K/D cross in oversold zone

Compare all against baseline: plain RSI(14) < 35
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


def compute_stochrsi_k(series, rsi_period=14, stoch_period=14, k_smooth=3):
    """Compute StochRSI K line on any series."""
    rsi = compute_rsi(series, rsi_period)
    rsi_low = rsi.rolling(stoch_period, min_periods=stoch_period).min()
    rsi_high = rsi.rolling(stoch_period, min_periods=stoch_period).max()
    denom = rsi_high - rsi_low
    stoch_raw = ((rsi - rsi_low) / denom.replace(0, np.nan)) * 100
    k = stoch_raw.rolling(k_smooth, min_periods=k_smooth).mean()
    return k


def load_cfgi(coin):
    """Load coin-specific CFGI series."""
    cfgi_sym = CFGI_MAP.get(coin, coin.split('/')[0])
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT date, cfgi FROM cfgi_daily WHERE symbol=? ORDER BY date",
        conn, params=(cfgi_sym,)
    )
    conn.close()
    if df.empty:
        return pd.Series(dtype=float)
    df['date'] = pd.to_datetime(df['date'], format='mixed')
    df = df.set_index('date').sort_index()
    df = df[~df.index.duplicated(keep='last')]
    return df['cfgi']


def build_weekly_cfgi(daily_cfgi):
    """Resample daily CFGI to weekly (Friday close)."""
    return daily_cfgi.resample('W-FRI').last().dropna()


def build_3d_cfgi(daily_cfgi):
    """Resample daily CFGI to 3-day periods."""
    return daily_cfgi.resample('3D').last().dropna()


def get_bias(date, top_dates, indicator, thresh):
    """Bear after top, clears when indicator < thresh."""
    ts = pd.Timestamp(date)
    tops = sorted([pd.Timestamp(d) for d in top_dates])

    last_top = None
    for t in tops:
        if t > ts:
            break
        last_top = t

    if last_top is None:
        return 'neutral'

    mask = (indicator.index > last_top) & (indicator.index <= ts)
    if not mask.any():
        return 'bear'

    sub = indicator[mask].dropna()
    below = sub[sub < thresh]

    if len(below) == 0:
        return 'bear'

    clear_date = below.index[0]

    # Check for subsequent tops after clear
    for t in tops:
        if t > clear_date and t <= ts:
            mask2 = (indicator.index > t) & (indicator.index <= ts)
            if mask2.any():
                sub2 = indicator[mask2].dropna()
                below2 = sub2[sub2 < thresh]
                if len(below2) > 0:
                    clear_date = below2.index[0]
                    continue
                return 'bear'
            return 'bear'

    return 'neutral'


def evaluate_variant(label, indicator, thresh, top_dates, phase_log, final_equity):
    """Evaluate a single bias variant. Returns (label, bad_blocked, good_blocked, saved, missed, net)."""
    blocked_good = []
    blocked_bad = []

    for i, t in enumerate(phase_log):
        date = t.get('date')
        to_phase = str(t.get('to', ''))
        equity = t.get('equity', 0)
        if not date or to_phase != 'MARKUP':
            continue

        bias = get_bias(date, top_dates, indicator, thresh)

        next_eq = None
        for j in range(i + 1, len(phase_log)):
            if phase_log[j].get('to') != 'MARKUP':
                next_eq = phase_log[j].get('equity', equity)
                break
        if next_eq is None:
            next_eq = final_equity
        pnl = next_eq - equity
        good = pnl > 0

        if bias == 'bear':
            if good:
                blocked_good.append((date, pnl))
            else:
                blocked_bad.append((date, pnl))

    saved = abs(sum(p for _, p in blocked_bad))
    missed = sum(p for _, p in blocked_good)
    net = saved - missed
    return (label, len(blocked_bad), len(blocked_good), saved, missed, net)


def analyze(coin, profile='high'):
    pack = V13SignalPack(coin)
    cfg = make_config(profile)
    bt = V13BacktestV8(pack, cfg)
    r = bt.run()

    cfgi = load_cfgi(coin)
    csym = CFGI_MAP.get(coin, '?')

    # Get top dates
    top_dates = []
    for t in bt.phase_log:
        reason = t.get('reason', '')
        to_phase = str(t.get('to', ''))
        if to_phase == 'FLAT' and ('OB' in reason or 'failsafe' in reason.lower()):
            top_dates.append(t['date'])

    print(f"\n{'=' * 90}")
    print(f"{coin} ({profile}) -- ROI: {r['roi']:+.1f}% | Tops: {len(top_dates)} | CFGI days: {len(cfgi)}")
    print(f"{'=' * 90}")
    print(f"  Top dates: {[str(d)[:10] for d in top_dates]}")

    # Build multi-timeframe CFGI
    weekly_cfgi = build_weekly_cfgi(cfgi)
    three_d_cfgi = build_3d_cfgi(cfgi)

    results = []

    # --- BASELINE: plain RSI(14) < 35 on daily CFGI ---
    baseline_rsi = compute_rsi(cfgi, 14)
    results.append(evaluate_variant(
        "BASELINE: Daily RSI(14) < 35", baseline_rsi, 35,
        top_dates, bt.phase_log, r['final_equity']
    ))

    # --- DAILY CFGI StochRSI sweeps ---
    timeframes = [
        ("Daily", cfgi),
        ("3-Day", three_d_cfgi),
        ("Weekly", weekly_cfgi),
    ]

    param_combos = [
        (7, 7, 3),
        (7, 14, 3),
        (14, 7, 3),
        (14, 14, 3),
        (14, 14, 5),
        (14, 21, 3),
        (21, 14, 3),
        (21, 21, 3),
    ]

    thresholds = [10, 15, 20, 25, 30, 35]

    for tf_name, tf_cfgi in timeframes:
        for rsi_p, stoch_p, k_s in param_combos:
            k = compute_stochrsi_k(tf_cfgi, rsi_p, stoch_p, k_s)
            valid = k.dropna()
            if len(valid) < 30:
                continue

            for thresh in thresholds:
                label = f"{tf_name} StoRSI({rsi_p},{stoch_p},K{k_s}) < {thresh}"
                results.append(evaluate_variant(
                    label, k, thresh,
                    top_dates, bt.phase_log, r['final_equity']
                ))

    # --- Also test plain RSI on different timeframes ---
    for tf_name, tf_cfgi in [("3-Day", three_d_cfgi), ("Weekly", weekly_cfgi)]:
        for rsi_p in [7, 14, 21]:
            rsi = compute_rsi(tf_cfgi, rsi_p)
            valid = rsi.dropna()
            if len(valid) < 20:
                continue
            for thresh in [25, 30, 35, 40]:
                label = f"{tf_name} RSI({rsi_p}) < {thresh}"
                results.append(evaluate_variant(
                    label, rsi, thresh,
                    top_dates, bt.phase_log, r['final_equity']
                ))

    # Sort by net $ descending
    results.sort(key=lambda x: x[5], reverse=True)

    # Print header
    print(f"\n  {'Signal':<45} {'Bad':>4} {'Good':>5} {'Saved':>9} {'Missed':>9} {'Net':>9} Verdict")
    print(f"  {'-' * 45} {'-' * 4} {'-' * 5} {'-' * 9} {'-' * 9} {'-' * 9} -------")

    for label, bb, bg, saved, missed, net in results:
        if net == 0 and bb == 0 and bg == 0:
            continue  # skip completely neutral (no interaction)
        tag = "HELPS" if net > 0 else "HURTS" if net < 0 else "NEUTRAL"
        is_baseline = "BASELINE" in label
        marker = " <<<" if is_baseline else ""
        print(f"  {label:<45} {bb:>4} {bg:>5} ${saved:>+8.0f} ${missed:>+8.0f} ${net:>+8.0f} {tag}{marker}")

    # Show top 5 and baseline for quick comparison
    print(f"\n  TOP 5:")
    shown = 0
    for label, bb, bg, saved, missed, net in results:
        if shown >= 5:
            break
        if net > 0 or bb > 0:
            print(f"    {label:<45} bad={bb} good={bg} net=${net:+.0f}")
            shown += 1

    return results


if __name__ == '__main__':
    print("CFGI StochRSI BIAS TEST v2")
    print("Replace plain RSI(14) with StochRSI on CFGI, sweep params + timeframes.")
    print("Bear ON: engine top. Bear OFF: indicator < threshold.")
    print()

    all_results = {}
    for coin in ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']:
        all_results[coin] = analyze(coin, 'high')

    # Cross-coin summary: find variants that HELP or NEUTRAL on ALL coins
    print(f"\n{'=' * 90}")
    print("CROSS-COIN SUMMARY")
    print(f"{'=' * 90}")

    # Collect all labels
    label_map = {}
    for coin, results in all_results.items():
        for label, bb, bg, saved, missed, net in results:
            if label not in label_map:
                label_map[label] = {}
            label_map[label][coin] = (bb, bg, net)

    print(f"\n  {'Signal':<45} {'ETH net':>9} {'BTC net':>9} {'SOL net':>9} {'Total':>9}")
    print(f"  {'-' * 45} {'-' * 9} {'-' * 9} {'-' * 9} {'-' * 9}")

    scored = []
    for label, coins in label_map.items():
        eth = coins.get('ETH/USDC', (0, 0, 0))
        btc = coins.get('BTC/USDC', (0, 0, 0))
        sol = coins.get('SOL/USDC', (0, 0, 0))
        total = eth[2] + btc[2] + sol[2]
        hurts_any = eth[2] < -500 or btc[2] < -500 or sol[2] < -500
        scored.append((label, eth, btc, sol, total, hurts_any))

    scored.sort(key=lambda x: x[4], reverse=True)

    for label, eth, btc, sol, total, hurts_any in scored[:30]:
        if total == 0 and eth[0] == 0 and btc[0] == 0 and sol[0] == 0:
            continue
        flag = " *HURTS*" if hurts_any else ""
        marker = " <<<" if "BASELINE" in label else ""
        print(f"  {label:<45} ${eth[2]:>+8.0f} ${btc[2]:>+8.0f} ${sol[2]:>+8.0f} ${total:>+8.0f}{flag}{marker}")
