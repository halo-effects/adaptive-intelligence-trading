"""Test Steve Courtney (CCU) "Bottom Is In" indicator as bear-clearing signal.

CCU 3-Checkmark Bottom (original: 2D candles, BTCUSD):
  1. Price < 200-period MA
  2. RSI(14) < 26
  3. StochRSI K < 20 AND D < 20

We test on:
  - 2D candles (original)
  - 3D candles (Brett's preferred timeframe)
  - Daily candles (for comparison)

Also test:
  - CCU standalone as bear-OFF
  - CCU OR CFGI RSI (either clears bear)
  - CCU AND CFGI RSI (both must fire)
  - Relaxed CCU variants (RSI < 30, StochRSI < 25, etc.)

Bear ON: Engine top signal (unchanged)
Bear OFF: CCU bottom fires after top
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
}


def compute_rsi(series, period=14):
    """Wilder's RSI."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).ewm(alpha=1/period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_stochrsi(series, rsi_period=14, stoch_period=14, k_smooth=3, d_smooth=3):
    """StochRSI with K and D lines."""
    rsi = compute_rsi(series, rsi_period)
    rsi_low = rsi.rolling(stoch_period, min_periods=stoch_period).min()
    rsi_high = rsi.rolling(stoch_period, min_periods=stoch_period).max()
    denom = rsi_high - rsi_low
    stoch_raw = ((rsi - rsi_low) / denom.replace(0, np.nan)) * 100
    k = stoch_raw.rolling(k_smooth, min_periods=k_smooth).mean()
    d = k.rolling(d_smooth, min_periods=d_smooth).mean()
    return rsi, k, d


def load_daily_candles(coin):
    """Load daily OHLCV candles."""
    conn = sqlite3.connect(DB_PATH)
    # Try USDC first, fall back to USDT
    symbol = coin
    df = pd.read_sql_query(
        "SELECT date, open, high, low, close, volume FROM candles_daily WHERE symbol=? ORDER BY date",
        conn, params=(symbol,)
    )
    if df.empty:
        symbol = coin.replace('/USDC', '/USDT')
        df = pd.read_sql_query(
            "SELECT date, open, high, low, close, volume FROM candles_daily WHERE symbol=? ORDER BY date",
            conn, params=(symbol,)
        )
    conn.close()
    if df.empty:
        return pd.DataFrame()
    df['date'] = pd.to_datetime(df['date'], format='mixed')
    df = df.set_index('date').sort_index()
    df = df[~df.index.duplicated(keep='last')]
    return df


def resample_candles(daily, period='2D'):
    """Resample daily candles to multi-day periods."""
    ohlcv = daily.resample(period).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    return ohlcv


def compute_ccu_signals(candles, ma_period=200, rsi_period=14, stoch_rsi_period=14,
                        stoch_period=14, k_smooth=3, d_smooth=3):
    """Compute all CCU indicator components on candle data."""
    close = candles['close']

    # 200-period MA
    ma200 = close.rolling(ma_period, min_periods=ma_period).mean()

    # RSI
    rsi = compute_rsi(close, rsi_period)

    # StochRSI K and D
    _, stoch_k, stoch_d = compute_stochrsi(close, stoch_rsi_period, stoch_period, k_smooth, d_smooth)

    return pd.DataFrame({
        'close': close,
        'ma200': ma200,
        'rsi': rsi,
        'stoch_k': stoch_k,
        'stoch_d': stoch_d,
        'below_ma200': close < ma200,
    }, index=candles.index)


def find_ccu_bottoms(signals, rsi_thresh=26, stoch_thresh=20):
    """Find dates where all 3 CCU checkmarks fire."""
    mask = (
        signals['below_ma200'] &
        (signals['rsi'] < rsi_thresh) &
        (signals['stoch_k'] < stoch_thresh) &
        (signals['stoch_d'] < stoch_thresh)
    )
    return signals.index[mask].tolist()


def load_cfgi_rsi(coin, period=14):
    """Load CFGI and compute RSI for baseline comparison."""
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
    return compute_rsi(df['cfgi'], period)


def load_cfgi_weekly_rsi(coin, period=7):
    """Load CFGI, resample to weekly, compute RSI."""
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
    weekly = df['cfgi'].resample('W-FRI').last().dropna()
    return compute_rsi(weekly, period)


def get_bias_level(date, top_dates, indicator, thresh):
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


def get_bias_ccu(date, top_dates, bottom_dates):
    """Bear after top, clears when CCU bottom fires."""
    ts = pd.Timestamp(date)
    tops = sorted([pd.Timestamp(d) for d in top_dates])

    last_top = None
    for t in tops:
        if t > ts:
            break
        last_top = t

    if last_top is None:
        return 'neutral'

    # Find first CCU bottom after last top
    for bd in sorted([pd.Timestamp(d) for d in bottom_dates]):
        if bd > last_top and bd <= ts:
            # Check no subsequent top after this clear
            re_topped = False
            for t in tops:
                if t > bd and t <= ts:
                    # Need another bottom after this top
                    found_new = False
                    for bd2 in sorted([pd.Timestamp(d) for d in bottom_dates]):
                        if bd2 > t and bd2 <= ts:
                            found_new = True
                            break
                    if not found_new:
                        re_topped = True
                    break
            if re_topped:
                return 'bear'
            return 'neutral'

    return 'bear'


def get_bias_or(date, top_dates, indicator, thresh, bottom_dates):
    """Bear clears if EITHER indicator < thresh OR CCU bottom fires."""
    b1 = get_bias_level(date, top_dates, indicator, thresh)
    b2 = get_bias_ccu(date, top_dates, bottom_dates)
    if b1 == 'neutral' or b2 == 'neutral':
        return 'neutral'
    return 'bear'


def get_bias_and(date, top_dates, indicator, thresh, bottom_dates):
    """Bear clears only if BOTH indicator < thresh AND CCU bottom fires."""
    b1 = get_bias_level(date, top_dates, indicator, thresh)
    b2 = get_bias_ccu(date, top_dates, bottom_dates)
    if b1 == 'neutral' and b2 == 'neutral':
        return 'neutral'
    return 'bear'


def evaluate(label, bias_fn, top_dates, phase_log, final_equity):
    """Evaluate a bias variant."""
    blocked_good = []
    blocked_bad = []

    for i, t in enumerate(phase_log):
        date = t.get('date')
        to_phase = str(t.get('to', ''))
        equity = t.get('equity', 0)
        if not date or to_phase != 'MARKUP':
            continue

        bias = bias_fn(date)

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
    return (label, len(blocked_bad), len(blocked_good), saved, missed, net,
            blocked_bad, blocked_good)


def analyze(coin, profile='high'):
    pack = V13SignalPack(coin)
    cfg = make_config(profile)
    bt = V13BacktestV8(pack, cfg)
    r = bt.run()

    # Get top dates
    top_dates = []
    for t in bt.phase_log:
        reason = t.get('reason', '')
        to_phase = str(t.get('to', ''))
        if to_phase == 'FLAT' and ('OB' in reason or 'failsafe' in reason.lower()):
            top_dates.append(t['date'])

    print(f"\n{'=' * 95}")
    print(f"{coin} ({profile}) -- ROI: {r['roi']:+.1f}% | Tops: {len(top_dates)}")
    print(f"{'=' * 95}")
    print(f"  Top dates: {[str(d)[:10] for d in top_dates]}")

    # Load price candles
    daily = load_daily_candles(coin)
    if daily.empty:
        print(f"  NO DAILY CANDLES FOR {coin}")
        return []
    print(f"  Daily candles: {len(daily)} ({daily.index[0].date()} to {daily.index[-1].date()})")

    # Build multi-day candles
    candles_2d = resample_candles(daily, '2D')
    candles_3d = resample_candles(daily, '3D')
    print(f"  2D candles: {len(candles_2d)}, 3D candles: {len(candles_3d)}")

    # Compute CCU signals on each timeframe
    timeframes = {
        'Daily': daily,
        '2D': candles_2d,
        '3D': candles_3d,
    }

    # CCU parameter variants
    ccu_variants = [
        # (label_suffix, rsi_thresh, stoch_thresh)
        ("strict", 26, 20),       # Original CCU
        ("relaxed1", 30, 25),     # Slightly relaxed
        ("relaxed2", 35, 30),     # More relaxed
    ]

    # Load CFGI signals for comparison/combination
    cfgi_rsi_daily = load_cfgi_rsi(coin, 14)
    cfgi_rsi_weekly = load_cfgi_weekly_rsi(coin, 7)

    results = []

    # --- BASELINES ---
    results.append(evaluate(
        "BASELINE: Daily CFGI RSI(14) < 35",
        lambda d: get_bias_level(d, top_dates, cfgi_rsi_daily, 35),
        top_dates, bt.phase_log, r['final_equity']
    ))
    results.append(evaluate(
        "BASELINE: Weekly CFGI RSI(7) < 40",
        lambda d: get_bias_level(d, top_dates, cfgi_rsi_weekly, 40),
        top_dates, bt.phase_log, r['final_equity']
    ))

    # --- CCU STANDALONE on each timeframe ---
    for tf_name, candles in timeframes.items():
        signals = compute_ccu_signals(candles)

        for var_name, rsi_t, stoch_t in ccu_variants:
            bottoms = find_ccu_bottoms(signals, rsi_t, stoch_t)
            label = f"CCU {tf_name} {var_name} (RSI<{rsi_t},Sto<{stoch_t})"

            if bottoms:
                bottom_strs = [str(b.date()) if hasattr(b, 'date') else str(b)[:10] for b in bottoms]
                # Only print for first coin to save space
                pass

            results.append(evaluate(
                label,
                lambda d, bd=bottoms: get_bias_ccu(d, top_dates, bd),
                top_dates, bt.phase_log, r['final_equity']
            ))

            # --- CCU OR CFGI RSI(14) < 35 ---
            results.append(evaluate(
                f"CCU {tf_name} {var_name} OR CFGI_RSI<35",
                lambda d, bd=bottoms: get_bias_or(d, top_dates, cfgi_rsi_daily, 35, bd),
                top_dates, bt.phase_log, r['final_equity']
            ))

            # --- CCU OR Weekly CFGI RSI(7) < 40 ---
            results.append(evaluate(
                f"CCU {tf_name} {var_name} OR W_CFGI<40",
                lambda d, bd=bottoms: get_bias_or(d, top_dates, cfgi_rsi_weekly, 40, bd),
                top_dates, bt.phase_log, r['final_equity']
            ))

    # Print CCU bottom dates for reference
    print(f"\n  CCU Bottom Dates:")
    for tf_name, candles in timeframes.items():
        signals = compute_ccu_signals(candles)
        for var_name, rsi_t, stoch_t in ccu_variants:
            bottoms = find_ccu_bottoms(signals, rsi_t, stoch_t)
            if bottoms:
                dates = [str(b.date()) if hasattr(b, 'date') else str(b)[:10] for b in bottoms]
                print(f"    {tf_name} {var_name}: {dates}")
            else:
                print(f"    {tf_name} {var_name}: NONE")

    # Sort by net
    results.sort(key=lambda x: x[5], reverse=True)

    # Print results
    print(f"\n  {'Signal':<50} {'Bad':>4} {'Good':>5} {'Saved':>9} {'Missed':>9} {'Net':>9} Verdict")
    print(f"  {'-' * 50} {'-' * 4} {'-' * 5} {'-' * 9} {'-' * 9} {'-' * 9} -------")

    for label, bb, bg, saved, missed, net, _, _ in results:
        if net == 0 and bb == 0 and bg == 0:
            continue
        tag = "HELPS" if net > 0 else "HURTS" if net < 0 else "NEUTRAL"
        marker = " <<<" if "BASELINE" in label else ""
        print(f"  {label:<50} {bb:>4} {bg:>5} ${saved:>+8.0f} ${missed:>+8.0f} ${net:>+8.0f} {tag}{marker}")

    # Entry detail
    print(f"\n  ENTRY DETAIL:")
    print(f"  {'Date':<12} {'PnL':>9} {'Q':<4} {'CFGI_RSI':>8} {'W_CFGI':>7} ", end='')
    for tf_name in timeframes:
        print(f"{'CCU_'+tf_name:>10} ", end='')
    print()

    for tf_name, candles in timeframes.items():
        signals = compute_ccu_signals(candles)
        # Store for detail
        timeframes[tf_name] = (candles, signals)

    for i, t in enumerate(bt.phase_log):
        date = t.get('date')
        to_phase = str(t.get('to', ''))
        equity = t.get('equity', 0)
        if not date or to_phase != 'MARKUP':
            continue

        next_eq = None
        for j in range(i + 1, len(bt.phase_log)):
            if bt.phase_log[j].get('to') != 'MARKUP':
                next_eq = bt.phase_log[j].get('equity', equity)
                break
        if next_eq is None:
            next_eq = r['final_equity']
        pnl = next_eq - equity
        quality = "GOOD" if pnl > 0 else "BAD"

        ts = pd.Timestamp(date)
        cr = cfgi_rsi_daily
        cr_val = cr.loc[:ts].iloc[-1] if len(cr.loc[:ts]) > 0 else float('nan')
        wr = cfgi_rsi_weekly
        wr_val = wr.loc[:ts].iloc[-1] if len(wr.loc[:ts]) > 0 else float('nan')

        print(f"  {str(date)[:10]:<12} ${pnl:>+8.0f} {quality:<4} {cr_val:>8.1f} {wr_val:>7.1f} ", end='')

        for tf_name in ['Daily', '2D', '3D']:
            candles, signals = timeframes[tf_name]
            sig_at = signals.loc[:ts]
            if len(sig_at) > 0:
                row = sig_at.iloc[-1]
                below = 'Y' if row['below_ma200'] else 'N'
                rsi_v = row['rsi']
                sk = row['stoch_k']
                sd = row['stoch_d']
                checks = sum([
                    row['below_ma200'],
                    rsi_v < 26 if not np.isnan(rsi_v) else False,
                    (sk < 20 and sd < 20) if not (np.isnan(sk) or np.isnan(sd)) else False,
                ])
                print(f"  {checks}/3 R{rsi_v:>4.0f} ", end='')
            else:
                print(f"  {'n/a':>10} ", end='')
        print()

    return results


if __name__ == '__main__':
    print("CCU BOTTOM INDICATOR TEST")
    print("Steve Courtney's 3-Checkmark Bottom: Price<MA200 + RSI<26 + StochRSI<20")
    print("Test on 2D, 3D, Daily candles. Compare and combine with CFGI RSI signals.")
    print("SOL excluded (no early CFGI data).\n")

    all_results = {}
    for coin in ['ETH/USDC', 'BTC/USDC']:
        all_results[coin] = analyze(coin, 'high')

    # Cross-coin summary
    print(f"\n{'=' * 95}")
    print("CROSS-COIN SUMMARY (ETH + BTC)")
    print(f"{'=' * 95}")

    label_map = {}
    for coin, results in all_results.items():
        for label, bb, bg, saved, missed, net, _, _ in results:
            if label not in label_map:
                label_map[label] = {}
            label_map[label][coin] = (bb, bg, net)

    scored = []
    for label, coins in label_map.items():
        eth = coins.get('ETH/USDC', (0, 0, 0))
        btc = coins.get('BTC/USDC', (0, 0, 0))
        total = eth[2] + btc[2]
        hurts = eth[2] < -500 or btc[2] < -500
        scored.append((label, eth, btc, total, hurts))

    scored.sort(key=lambda x: x[3], reverse=True)

    print(f"\n  {'Signal':<50} {'ETH net':>9} {'BTC net':>9} {'Total':>9}")
    print(f"  {'-' * 50} {'-' * 9} {'-' * 9} {'-' * 9}")

    for label, eth, btc, total, hurts in scored:
        if total == 0 and eth[0] == 0 and btc[0] == 0:
            continue
        flag = " *HURTS*" if hurts else ""
        marker = " <<<" if "BASELINE" in label else ""
        print(f"  {label:<50} ${eth[2]:>+8.0f} ${btc[2]:>+8.0f} ${total:>+8.0f}{flag}{marker}")
