"""
ROUTER Phase 3: Path Analysis
For every ROUTER entry, what path did it eventually take?
What signals at entry predicted the correct path?
Goal: build confidence scoring to route faster.

Current ROUTER exits:
  ROUTER -> DCA (ranging: ADX < 20 sustained 14d, or 42d timeout)
  ROUTER -> MARKDOWN (LH_LL >= 2 + ADX > 20 + Fib_break)
  Missing: ROUTER -> MARKUP (would need HH_HL + Fib_support, like DCA->MARKUP)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack


def analyze_coin(coin, start='2023-01-01', end='2026-02-25', capital=2500):
    pack = V13SignalPack(coin)
    cfg = V13Config()
    cfg.START_DATE = start
    cfg.END_DATE = end
    cfg.CAPITAL = capital

    bt = V13BacktestV8(pack, cfg)
    result = bt.run()
    if result is None:
        return []

    # Find all FLAT/ROUTER entries and exits
    windows = []
    for i, p in enumerate(bt.phase_log):
        if p['to'] in ('FLAT', 'ROUTER'):
            entry_date = p['date']
            entry_from = p['from']
            entry_reason = p.get('reason', '')

            # Find the exit
            exit_phase = None
            exit_date = None
            exit_reason = ''
            for j in range(i+1, len(bt.phase_log)):
                if bt.phase_log[j]['from'] in ('FLAT', 'ROUTER'):
                    exit_phase = bt.phase_log[j]['to']
                    exit_date = bt.phase_log[j]['date']
                    exit_reason = bt.phase_log[j].get('reason', '')
                    break

            if exit_date is None:
                # Still in ROUTER at end
                exit_phase = 'STILL_IN'
                exit_date = pd.Timestamp(end)

            dwell_days = (exit_date - entry_date).days

            # What happened AFTER the exit? (to judge if routing was correct)
            next_phase_outcome = None
            if exit_phase == 'DCA':
                # Did DCA eventually go to MARKUP or MARKDOWN?
                for j in range(i+1, len(bt.phase_log)):
                    if bt.phase_log[j]['from'] == 'DCA' and bt.phase_log[j]['to'] in ('MARKUP', 'MARKDOWN'):
                        next_phase_outcome = bt.phase_log[j]['to']
                        break

            # Collect signals at ROUTER entry
            try:
                daily = pack.daily
                idx = daily.index.get_indexer([entry_date], method='pad')[0]
                if idx >= 0:
                    row = daily.iloc[idx]
                    adx = row.get('adx', np.nan)
                    sma50 = row.get('sma50', np.nan)
                    sma200 = row.get('sma200', np.nan)
                    close = row.get('close', np.nan)
                    sma50_above = close > sma50 if not np.isnan(sma50) else None
                    sma200_above = close > sma200 if not np.isnan(sma200) else None
                else:
                    adx = sma50_above = sma200_above = close = np.nan
            except:
                adx = sma50_above = sma200_above = close = np.nan

            # HH_HL and LH_LL at entry
            try:
                hh_hl = pack.structure.hh_hl_streak(entry_date, cfg.HH_HL_LOOKBACK)
            except:
                hh_hl = 0
            try:
                lh_ll = pack.structure.lh_ll_streak(entry_date, cfg.HH_HL_LOOKBACK)
            except:
                lh_ll = 0

            # CFGI at entry
            try:
                from v13_signals import load_cfgi
                cfgi_df = load_cfgi(coin)
                if cfgi_df is not None and len(cfgi_df) > 0:
                    cfgi_idx = cfgi_df.index.get_indexer([entry_date], method='pad')[0]
                    cfgi = cfgi_df.iloc[cfgi_idx]['value'] if cfgi_idx >= 0 else np.nan
                else:
                    cfgi = np.nan
            except:
                cfgi = np.nan

            # Signals 7 days after entry (do they change?)
            try:
                date_7d = entry_date + pd.Timedelta(days=7)
                hh_hl_7d = pack.structure.hh_hl_streak(date_7d, cfg.HH_HL_LOOKBACK)
                lh_ll_7d = pack.structure.lh_ll_streak(date_7d, cfg.HH_HL_LOOKBACK)
            except:
                hh_hl_7d = lh_ll_7d = 0

            windows.append({
                'coin': coin,
                'entry_date': str(entry_date.date()) if hasattr(entry_date, 'date') else str(entry_date)[:10],
                'entry_from': entry_from,
                'entry_reason': entry_reason[:40],
                'exit_to': exit_phase,
                'exit_reason': exit_reason[:40],
                'dwell_days': dwell_days,
                'next_outcome': next_phase_outcome,
                # Signals at entry
                'adx': adx,
                'hh_hl': hh_hl,
                'lh_ll': lh_ll,
                'sma50_above': sma50_above,
                'sma200_above': sma200_above,
                'cfgi': cfgi,
                # Signals at +7d
                'hh_hl_7d': hh_hl_7d,
                'lh_ll_7d': lh_ll_7d,
                # Ideal path (hindsight)
                'ideal_path': _ideal_path(exit_phase, next_phase_outcome, dwell_days),
            })

    return windows


def _ideal_path(exit_to, next_outcome, dwell_days):
    """What SHOULD have happened (with hindsight)?"""
    if exit_to == 'MARKDOWN':
        return 'MARKDOWN'  # Correctly went to markdown
    elif exit_to == 'DCA':
        if next_outcome == 'MARKUP':
            return 'DCA->MARKUP'  # Correct: DCA then markup
        elif next_outcome == 'MARKDOWN':
            return 'SHOULD_MARKDOWN'  # Wrong: should have gone to markdown directly
        else:
            return 'DCA'
    return exit_to


def main():
    coins = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']
    all_windows = []

    print("=" * 120)
    print("  ROUTER PATH ANALYSIS -- What should each ROUTER window have done?")
    print("=" * 120)

    for coin in coins:
        windows = analyze_coin(coin)
        all_windows.extend(windows)

    if not all_windows:
        print("No ROUTER windows found!")
        return

    # Summary
    total_dwell = sum(w['dwell_days'] for w in all_windows)
    print(f"\nTotal ROUTER windows: {len(all_windows)}")
    print(f"Total dwell days: {total_dwell}")

    # Group by ideal path
    paths = {}
    for w in all_windows:
        p = w['ideal_path']
        if p not in paths:
            paths[p] = []
        paths[p].append(w)

    print(f"\n--- Path Distribution ---")
    for p, wins in sorted(paths.items(), key=lambda x: -len(x[1])):
        days = sum(w['dwell_days'] for w in wins)
        print(f"  {p:<20} {len(wins):>3} windows, {days:>5} total days, avg {days/len(wins):.0f}d")

    # Detailed per-window
    print(f"\n{'='*120}")
    print(f"{'Coin':<6} {'Entry':<12} {'From':<10} {'Exit':<12} {'Days':>5} {'ADX':>5} {'HH':>3} {'LL':>3} "
          f"{'HH7d':>4} {'LL7d':>4} {'SMA50':>6} {'CFGI':>5} {'Ideal Path':<20} {'Exit Reason':<30}")
    print("-" * 120)
    for w in sorted(all_windows, key=lambda x: x['entry_date']):
        adx = f"{w['adx']:.0f}" if not np.isnan(w['adx']) else "?"
        cfgi = f"{w['cfgi']:.0f}" if not np.isnan(w['cfgi']) else "?"
        sma50 = "above" if w['sma50_above'] == True else ("below" if w['sma50_above'] == False else "?")
        print(f"{w['coin']:<6} {w['entry_date']:<12} {w['entry_from']:<10} {w['exit_to']:<12} "
              f"{w['dwell_days']:>5} {adx:>5} {w['hh_hl']:>3} {w['lh_ll']:>3} "
              f"{w['hh_hl_7d']:>4} {w['lh_ll_7d']:>4} {sma50:>6} {cfgi:>5} "
              f"{w['ideal_path']:<20} {w['exit_reason']:<30}")

    # Signal analysis: what predicts correct routing?
    print(f"\n{'='*120}")
    print(f"  SIGNAL ANALYSIS -- What predicts the correct path?")
    print(f"{'='*120}")

    # Windows that went DCA but should have gone MARKDOWN
    should_md = [w for w in all_windows if w['ideal_path'] == 'SHOULD_MARKDOWN']
    correct_md = [w for w in all_windows if w['ideal_path'] == 'MARKDOWN']
    dca_markup = [w for w in all_windows if w['ideal_path'] == 'DCA->MARKUP']

    print(f"\n  SHOULD_MARKDOWN (routed to DCA, then went MARKDOWN): {len(should_md)} windows")
    for w in should_md:
        adx_s = f"{w['adx']:.0f}" if not np.isnan(w['adx']) else "?"
        print(f"    {w['coin']} {w['entry_date']}: {w['dwell_days']}d wasted, "
              f"ADX={adx_s}, LH_LL={w['lh_ll']}, LH_LL@7d={w['lh_ll_7d']}, "
              f"SMA50={'above' if w['sma50_above'] else 'below'}")

    print(f"\n  Correct MARKDOWN (went directly): {len(correct_md)} windows")
    for w in correct_md:
        adx_s = f"{w['adx']:.0f}" if not np.isnan(w['adx']) else "?"
        print(f"    {w['coin']} {w['entry_date']}: {w['dwell_days']}d dwell, "
              f"ADX={adx_s}, LH_LL={w['lh_ll']}, LH_LL@7d={w['lh_ll_7d']}")

    print(f"\n  DCA->MARKUP (DCA was correct path): {len(dca_markup)} windows")
    for w in dca_markup:
        adx_s = f"{w['adx']:.0f}" if not np.isnan(w['adx']) else "?"
        print(f"    {w['coin']} {w['entry_date']}: {w['dwell_days']}d in ROUTER, "
              f"ADX={adx_s}, HH_HL={w['hh_hl']}, HH_HL@7d={w['hh_hl_7d']}")

    # Key question: could LH_LL at 7d predict MARKDOWN routing?
    print(f"\n--- Predictive Power of LH_LL @ +7d ---")
    for threshold in [1, 2, 3]:
        would_route_md = [w for w in all_windows if w['lh_ll_7d'] >= threshold]
        correct = [w for w in would_route_md if w['ideal_path'] in ('MARKDOWN', 'SHOULD_MARKDOWN')]
        wrong = [w for w in would_route_md if w['ideal_path'] == 'DCA->MARKUP']
        days_saved = sum(w['dwell_days'] for w in correct if w['ideal_path'] == 'SHOULD_MARKDOWN')
        print(f"  LH_LL@7d >= {threshold}: would route {len(would_route_md)} windows to MARKDOWN, "
              f"{len(correct)} correct, {len(wrong)} wrong, {days_saved}d saved")

    # Key question: could HH_HL at 7d predict DCA/MARKUP routing?
    print(f"\n--- Predictive Power of HH_HL @ +7d ---")
    for threshold in [1, 2, 3]:
        would_route_dca = [w for w in all_windows if w['hh_hl_7d'] >= threshold]
        correct = [w for w in would_route_dca if w['ideal_path'] == 'DCA->MARKUP']
        wrong = [w for w in would_route_dca if w['ideal_path'] in ('MARKDOWN', 'SHOULD_MARKDOWN')]
        days_saved = sum(w['dwell_days'] for w in correct)
        print(f"  HH_HL@7d >= {threshold}: would route {len(would_route_dca)} windows to DCA, "
              f"{len(correct)} correct, {len(wrong)} wrong, {days_saved}d saved (from faster DCA entry)")


if __name__ == '__main__':
    main()
