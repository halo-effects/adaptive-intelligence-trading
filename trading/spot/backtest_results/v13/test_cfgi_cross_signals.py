"""Test CFGI_RSI crossover signals as bear-clearing mechanisms.

Cross 1: CFGI_RSI(14) × Price RSI(14) — sentiment vs price momentum cross
Cross 2: Fast CFGI_RSI(7) × Slow CFGI_RSI(14) — sentiment MACD
Cross 3: CFGI_RSI(14) × SMA(9) of CFGI_RSI — mean reversion cross
Cross 4: CFGI_RSI vs Price RSI divergence — bottom detection

Baseline: CFGI_RSI < 35 (simple threshold)
"""
import sys
import numpy as np
import pandas as pd
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8
from v13_signals import V13SignalPack
from run_new_coins_profiles import make_config

DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'candles.db'
CFGI_MAP = {'ETH/USDC': 'ETH', 'BTC/USDC': 'BTC', 'SOL/USDC': 'SOL'}


def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).ewm(alpha=1/period, min_periods=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def load_data(coin):
    """Load CFGI RSI variants and Price RSI for a coin."""
    cfgi_sym = CFGI_MAP.get(coin, coin.split('/')[0])
    conn = sqlite3.connect(DB_PATH)

    # CFGI
    cfgi_df = pd.read_sql_query(
        "SELECT date, cfgi FROM cfgi_daily WHERE symbol=? ORDER BY date",
        conn, params=(cfgi_sym,)
    )
    cfgi_df['date'] = pd.to_datetime(cfgi_df['date'], format='mixed')
    cfgi_df = cfgi_df.set_index('date').sort_index()
    cfgi_df = cfgi_df[~cfgi_df.index.duplicated(keep='last')]
    cfgi = cfgi_df['cfgi'].astype(float)

    # Price RSI from candles
    candle_df = pd.read_sql_query(
        "SELECT date, rsi14 FROM candles_daily WHERE symbol=? ORDER BY date",
        conn, params=(coin,)
    )
    conn.close()
    candle_df['date'] = pd.to_datetime(candle_df['date'], format='mixed')
    candle_df = candle_df.set_index('date').sort_index()
    candle_df = candle_df[~candle_df.index.duplicated(keep='last')]
    price_rsi = candle_df['rsi14'].astype(float)

    # Compute indicators
    cfgi_rsi_14 = compute_rsi(cfgi, 14)
    cfgi_rsi_7 = compute_rsi(cfgi, 7)
    cfgi_rsi_sma9 = cfgi_rsi_14.rolling(9).mean()

    return {
        'cfgi': cfgi,
        'cfgi_rsi_14': cfgi_rsi_14,
        'cfgi_rsi_7': cfgi_rsi_7,
        'cfgi_rsi_sma9': cfgi_rsi_sma9,
        'price_rsi': price_rsi,
    }


def run_backtest(coin, profile='high'):
    pack = V13SignalPack(coin)
    cfg = make_config(profile)
    bt = V13BacktestV8(pack, cfg)
    r = bt.run()

    top_dates = []
    for t in bt.phase_log:
        reason = t.get('reason', '')
        to_phase = str(t.get('to', ''))
        if to_phase == 'FLAT' and ('OB' in reason or 'failsafe' in reason.lower()):
            top_dates.append(pd.Timestamp(t['date']))

    markups = []
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
        markups.append({'date': pd.Timestamp(date), 'pnl': pnl, 'equity': equity})

    return top_dates, markups, r


def get_val(series, date):
    """Get the most recent value on or before date."""
    ts = pd.Timestamp(date)
    mask = series.index <= ts
    if not mask.any():
        return np.nan
    return series[mask].iloc[-1]


def check_cross_above(series_a, series_b, start_date, end_date):
    """Check if series_a crosses above series_b between start_date and end_date.
    Returns the first cross date, or None."""
    mask = (series_a.index > start_date) & (series_a.index <= end_date)
    idx = series_a.index[mask]
    common = idx.intersection(series_b.index)
    if len(common) < 2:
        return None
    a = series_a.reindex(common)
    b = series_b.reindex(common)
    # Cross above: a was <= b, now a > b
    below = a.shift(1) <= b.shift(1)
    above = a > b
    crosses = common[below & above]
    if len(crosses) > 0:
        return crosses[0]
    return None


def check_threshold_below(series, threshold, start_date, end_date):
    """Check if series goes below threshold between start and end. Returns first date."""
    mask = (series.index > start_date) & (series.index <= end_date)
    sub = series[mask]
    below = sub[sub < threshold]
    if len(below) > 0:
        return below.index[0]
    return None


def check_divergence_clear(cfgi_rsi, price_rsi, start_date, end_date, lookback=20):
    """Check for bullish divergence: CFGI_RSI makes lower low but Price RSI doesn't.
    Returns first date where divergence is detected."""
    mask = (cfgi_rsi.index > start_date) & (cfgi_rsi.index <= end_date)
    idx = cfgi_rsi.index[mask]
    
    for dt in idx:
        # Look back `lookback` days for prior low
        lb_start = dt - pd.Timedelta(days=lookback*2)
        lb_mask = (cfgi_rsi.index >= lb_start) & (cfgi_rsi.index < dt - pd.Timedelta(days=5))
        
        if lb_mask.sum() < 5:
            continue
        
        cr_recent = cfgi_rsi.index[(cfgi_rsi.index > dt - pd.Timedelta(days=5)) & (cfgi_rsi.index <= dt)]
        if len(cr_recent) == 0:
            continue
        
        cr_prior = cfgi_rsi[lb_mask]
        pr_prior_mask = (price_rsi.index >= lb_start) & (price_rsi.index < dt - pd.Timedelta(days=5))
        pr_recent_mask = (price_rsi.index > dt - pd.Timedelta(days=5)) & (price_rsi.index <= dt)
        
        if pr_prior_mask.sum() == 0 or pr_recent_mask.sum() == 0:
            continue
        
        cr_low_now = cfgi_rsi[cr_recent].min()
        cr_low_prior = cr_prior.min()
        pr_low_now = price_rsi[pr_recent_mask].min()
        pr_low_prior = price_rsi[pr_prior_mask].min()
        
        # Bullish divergence: CFGI_RSI lower low, Price RSI higher low
        if cr_low_now < cr_low_prior and pr_low_now > pr_low_prior:
            return dt
        # Also: Price RSI lower low, CFGI_RSI higher low (sentiment bottomed first)
        if pr_low_now < pr_low_prior and cr_low_now > cr_low_prior:
            return dt
    
    return None


def get_bias_for_signal(date, top_dates, clear_func, data):
    """Generic bias checker. Bear ON at top, OFF when clear_func fires.
    clear_func(start_date, end_date, data) -> clear_date or None"""
    ts = pd.Timestamp(date)
    tops = sorted(top_dates)
    
    # Find most recent top before this date
    relevant_tops = [t for t in tops if t <= ts]
    if not relevant_tops:
        return 'neutral', {}
    
    # Walk through tops, checking if each gets cleared
    bear_active = False
    for t in tops:
        if t > ts:
            break
        bear_active = True
        # Check if cleared between this top and the query date (or next top)
        clear_date = clear_func(t, ts, data)
        if clear_date is not None and clear_date <= ts:
            bear_active = False
            # But check if a newer top re-activated
    
    # More precise: track state chronologically
    bear_since = None
    for t in tops:
        if t > ts:
            break
        if bear_since is None:
            bear_since = t
        else:
            # Already in bear, new top resets
            bear_since = t
        # Check clear from this top
        clear_date = clear_func(t, ts, data)
        if clear_date is not None and clear_date <= ts:
            # Check if another top fires after clear
            next_top = None
            for t2 in tops:
                if t2 > clear_date and t2 <= ts:
                    next_top = t2
                    break
            if next_top is not None:
                bear_since = next_top
            else:
                bear_since = None
    
    return ('bear' if bear_since is not None else 'neutral'), {}


# ── Define clear functions for each cross signal ──

def make_cross1_clear(data):
    """Cross 1: CFGI_RSI(14) crosses above Price RSI(14)"""
    cfgi_rsi = data['cfgi_rsi_14']
    price_rsi = data['price_rsi']
    def clear(start, end, d):
        return check_cross_above(cfgi_rsi, price_rsi, start, end)
    return clear


def make_cross2_clear(data):
    """Cross 2: Fast CFGI_RSI(7) crosses above Slow CFGI_RSI(14)"""
    fast = data['cfgi_rsi_7']
    slow = data['cfgi_rsi_14']
    def clear(start, end, d):
        return check_cross_above(fast, slow, start, end)
    return clear


def make_cross3_clear(data):
    """Cross 3: CFGI_RSI(14) crosses above its SMA(9)"""
    cfgi_rsi = data['cfgi_rsi_14']
    sma9 = data['cfgi_rsi_sma9']
    def clear(start, end, d):
        return check_cross_above(cfgi_rsi, sma9, start, end)
    return clear


def make_cross4_clear(data):
    """Cross 4: Divergence between CFGI_RSI and Price RSI"""
    cfgi_rsi = data['cfgi_rsi_14']
    price_rsi = data['price_rsi']
    def clear(start, end, d):
        return check_divergence_clear(cfgi_rsi, price_rsi, start, end)
    return clear


def make_baseline_clear(data, threshold=35):
    """Baseline: CFGI_RSI(14) < threshold"""
    cfgi_rsi = data['cfgi_rsi_14']
    def clear(start, end, d):
        return check_threshold_below(cfgi_rsi, threshold, start, end)
    return clear


def make_cross1_filtered_clear(data):
    """Cross 1 + filter: only clear if CFGI_RSI < 45 at time of cross"""
    cfgi_rsi = data['cfgi_rsi_14']
    price_rsi = data['price_rsi']
    def clear(start, end, d):
        cross_date = check_cross_above(cfgi_rsi, price_rsi, start, end)
        if cross_date is not None:
            val = get_val(cfgi_rsi, cross_date)
            if val < 45:
                return cross_date
        return None
    return clear


def make_cross3_filtered_clear(data):
    """Cross 3 + filter: only if CFGI_RSI < 40 at cross"""
    cfgi_rsi = data['cfgi_rsi_14']
    sma9 = data['cfgi_rsi_sma9']
    def clear(start, end, d):
        cross_date = check_cross_above(cfgi_rsi, sma9, start, end)
        if cross_date is not None:
            val = get_val(cfgi_rsi, cross_date)
            if val < 40:
                return cross_date
        return None
    return clear


SIGNALS = [
    ("Baseline: CFGI_RSI<35", lambda d: make_baseline_clear(d, 35)),
    ("Cross1: CFGI_RSI×PriceRSI", make_cross1_clear),
    ("Cross1+Filter: cross<45", make_cross1_filtered_clear),
    ("Cross2: FastCFGI(7)×Slow(14)", make_cross2_clear),
    ("Cross3: CFGI_RSI×SMA9", make_cross3_clear),
    ("Cross3+Filter: cross<40", make_cross3_filtered_clear),
    ("Cross4: Divergence", make_cross4_clear),
]


def test_coin(coin, profile='high'):
    print(f"\n{'='*80}")
    print(f"  {coin} ({profile})")
    print(f"{'='*80}")

    top_dates, markups, r = run_backtest(coin, profile)
    data = load_data(coin)
    
    cfgi_start = data['cfgi'].index.min() if len(data['cfgi']) > 0 else pd.Timestamp('2099-01-01')
    
    print(f"  ROI: {r['roi']:+.1f}%  |  Tops: {len(top_dates)}  |  Markups: {len(markups)}")
    print(f"  CFGI data from: {cfgi_start.date()}")
    print(f"  Top dates: {[str(d.date()) for d in top_dates]}")
    print()

    results = {}

    for sig_name, make_clear in SIGNALS:
        clear_func = make_clear(data)
        blocked_bad = []
        blocked_good = []
        passed = []

        for m in markups:
            dt = m['date']
            # Pre-CFGI: neutral
            if dt < cfgi_start:
                passed.append(m)
                continue

            bias, _ = get_bias_for_signal(dt, top_dates, clear_func, data)
            if bias == 'bear':
                if m['pnl'] > 0:
                    blocked_good.append(m)
                else:
                    blocked_bad.append(m)
            else:
                passed.append(m)

        saved = abs(sum(m['pnl'] for m in blocked_bad))
        missed = sum(m['pnl'] for m in blocked_good)
        net = saved - missed
        tag = "HELPS" if net > 0 else ("HURTS" if net < 0 else "NEUTRAL")
        bb, bg = len(blocked_bad), len(blocked_good)

        results[sig_name] = {
            'blocked_bad': bb, 'blocked_good': bg,
            'saved': saved, 'missed': missed, 'net': net, 'tag': tag,
            'blocked_bad_list': blocked_bad, 'blocked_good_list': blocked_good,
        }

        print(f"  {sig_name:<35} {bb}bad/{bg}good blocked  "
              f"Saved:${saved:>+9.0f}  Missed:${missed:>+9.0f}  Net:${net:>+9.0f} {tag}")

    # Detail for each signal
    print(f"\n  --- Entry-by-entry detail ---")
    for m in markups:
        dt = m['date']
        quality = "GOOD" if m['pnl'] > 0 else "BAD"
        cr14 = get_val(data['cfgi_rsi_14'], dt)
        cr7 = get_val(data['cfgi_rsi_7'], dt)
        pr = get_val(data['price_rsi'], dt)
        sma9 = get_val(data['cfgi_rsi_sma9'], dt)

        biases = []
        for sig_name, make_clear in SIGNALS:
            if dt < cfgi_start:
                biases.append('n')
            else:
                clear_func = make_clear(data)
                b, _ = get_bias_for_signal(dt, top_dates, clear_func, data)
                biases.append('B' if b == 'bear' else 'n')

        bias_str = ' '.join(biases)
        print(f"    {str(dt.date()):>10}: pnl={m['pnl']:>+8.0f} [{quality:>4}]  "
              f"CR14={cr14:>5.1f} CR7={cr7:>5.1f} PR={pr:>5.1f} SMA9={sma9:>5.1f}  "
              f"Biases: {bias_str}")

    print(f"    Legend: {'  '.join(s[0][:6] for s,_ in SIGNALS)}")
    return results


def main():
    print("CFGI RSI CROSS SIGNAL RESEARCH")
    print("Testing crossover bear-clearing signals vs baseline threshold")
    print("=" * 80)
    sys.stdout.flush()

    all_results = {}
    for coin in ['ETH/USDC', 'BTC/USDC']:
        all_results[coin] = test_coin(coin, 'high')
        sys.stdout.flush()

    # Summary ranking
    print(f"\n\n{'='*80}")
    print("  RANKING SUMMARY")
    print(f"{'='*80}")
    print(f"  {'Signal':<35} {'ETH Net':>10} {'BTC Net':>10} {'Total':>10} {'Verdict':>10}")
    print(f"  {'-'*35} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")

    ranking = []
    for sig_name, _ in SIGNALS:
        eth = all_results.get('ETH/USDC', {}).get(sig_name, {})
        btc = all_results.get('BTC/USDC', {}).get(sig_name, {})
        eth_net = eth.get('net', 0)
        btc_net = btc.get('net', 0)
        total = eth_net + btc_net
        ranking.append((sig_name, eth_net, btc_net, total))

    ranking.sort(key=lambda x: -x[3])
    for sig, en, bn, tot in ranking:
        verdict = "BEST" if tot == ranking[0][3] else ("OK" if tot > 0 else "BAD")
        print(f"  {sig:<35} ${en:>+9.0f} ${bn:>+9.0f} ${tot:>+9.0f} {verdict:>10}")

    # Write markdown report
    write_report(all_results, ranking)
    print(f"\nReport written to cfgi_cross_results.md")


def write_report(all_results, ranking):
    lines = []
    lines.append("# CFGI RSI Cross Signal Research Results")
    lines.append(f"\nGenerated: 2026-02-26")
    lines.append(f"\n## Baseline")
    lines.append("CFGI_RSI < 35 (simple threshold, no crossover)")
    lines.append("- ETH High: blocks 4 bad / 0 good markups")
    lines.append("- BTC High: blocks 2 bad / 1 good markups")
    lines.append("")
    lines.append("## Cross Signals Tested")
    lines.append("")
    lines.append("| # | Signal | Description |")
    lines.append("|---|--------|-------------|")
    lines.append("| 1 | CFGI_RSI × Price RSI | Bear clears when CFGI_RSI crosses above Price RSI (sentiment recovering faster than price) |")
    lines.append("| 1b | Cross1 + Filter<45 | Same but only clears if CFGI_RSI < 45 at cross point |")
    lines.append("| 2 | Fast CFGI_RSI(7) × Slow(14) | Sentiment MACD — fast crosses above slow |")
    lines.append("| 3 | CFGI_RSI × SMA(9) | CFGI_RSI crosses above its 9-period moving average |")
    lines.append("| 3b | Cross3 + Filter<40 | Same but only clears if CFGI_RSI < 40 at cross point |")
    lines.append("| 4 | Divergence | Bullish divergence between CFGI_RSI and Price RSI |")
    lines.append("")
    lines.append("## Results by Coin")
    lines.append("")

    for coin in ['ETH/USDC', 'BTC/USDC']:
        lines.append(f"### {coin}")
        lines.append("")
        lines.append(f"| Signal | Bad Blocked | Good Blocked | $ Saved | $ Missed | Net $ | Verdict |")
        lines.append(f"|--------|-------------|--------------|---------|----------|-------|---------|")
        res = all_results.get(coin, {})
        for sig_name, _ in SIGNALS:
            r = res.get(sig_name, {})
            lines.append(f"| {sig_name} | {r.get('blocked_bad',0)} | {r.get('blocked_good',0)} | "
                        f"${r.get('saved',0):,.0f} | ${r.get('missed',0):,.0f} | "
                        f"${r.get('net',0):+,.0f} | {r.get('tag','?')} |")
        lines.append("")

    lines.append("## Overall Ranking")
    lines.append("")
    lines.append("| Rank | Signal | ETH Net | BTC Net | Total Net |")
    lines.append("|------|--------|---------|---------|-----------|")
    for i, (sig, en, bn, tot) in enumerate(ranking):
        lines.append(f"| {i+1} | {sig} | ${en:+,.0f} | ${bn:+,.0f} | ${tot:+,.0f} |")

    lines.append("")
    lines.append("## Key Takeaways")
    lines.append("")
    lines.append("*To be filled based on results*")
    lines.append("")

    report_path = Path(__file__).parent / 'cfgi_cross_results.md'
    report_path.write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
