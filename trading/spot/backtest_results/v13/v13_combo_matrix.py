"""
V13 Combination Matrix — Test signal combos for each phase transition.

Uses winning individual signals from matrix test, combines them,
and scores composites against ground truth.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import timedelta
from itertools import combinations

sys.path.insert(0, str(Path(__file__).parent))
from v13_signals import V13SignalPack
from v13_signal_matrix import GROUND_TRUTH, CORRECTIONS

# We scan daily: for each day in the test period, check if combo fires.
# Then score those fire dates against ground truth.


def daily_signal_check(pack, date, signal_name):
    """Check if a specific signal is active at a date. Returns True/False."""

    # StochRSI OB exits — check if exit happened in the enclosing period
    if signal_name.startswith('stoch_ob_'):
        parts = signal_name.split('_')  # stoch_ob_2W_95
        n_weeks = int(parts[2].replace('W', ''))
        thresh = int(parts[3])
        stoch = pack.get_stoch(n_weeks)
        exits = stoch.ob_exits(threshold=thresh)
        # Was there an exit in the last n_weeks*7 days?
        window = n_weeks * 7 + 3  # small buffer
        return any(abs((date - d).days) <= window for d in exits.index)

    if signal_name.startswith('stoch_os_'):
        parts = signal_name.split('_')
        n_weeks = int(parts[2].replace('W', ''))
        thresh = int(parts[3])
        stoch = pack.get_stoch(n_weeks)
        exits = stoch.os_exits(threshold=thresh)
        window = n_weeks * 7 + 3
        return any(abs((date - d).days) <= window for d in exits.index)

    if signal_name == 'bmsb_below':
        return pack.bmsb.status_at(date) == 'BELOW'

    if signal_name == 'bmsb_below_2w':
        return pack.bmsb.sustained_below(date, weeks=2)

    if signal_name == 'bmsb_above':
        return pack.bmsb.status_at(date) == 'ABOVE'

    if signal_name == 'sma50_slope_neg':
        return pack.structure.sma50_slope_negative(date, window=10)

    if signal_name == 'sma50_slope_pos':
        return pack.structure.sma50_slope_positive(date, window=10)

    if signal_name == 'lh_ll_2':
        return pack.structure.lh_ll_streak(date, min_streak=2)

    if signal_name == 'hh_hl_2':
        return pack.structure.hh_hl_streak(date, min_streak=2)

    if signal_name == 'adx_trending':
        return pack.structure.is_trending(date, threshold=25)

    if signal_name == 'adx_ranging':
        return pack.structure.is_ranging(date, threshold=20)

    if signal_name == 'cfgi_declining_greed':
        return pack.cfgi.declining_from_greed(date)

    if signal_name == 'cfgi_rising_fear':
        return pack.cfgi.rising_from_fear(date)

    if signal_name == 'cfgi_fear':
        return pack.cfgi.in_fear(date, threshold=35)

    if signal_name == 'cfgi_greed':
        return pack.cfgi.in_greed(date, threshold=65)

    if signal_name == 'sma200_not_overext':
        return not pack.sma200.is_overextended(date, threshold=20)

    if signal_name == 'below_sma50':
        v = pack.structure.price_vs_sma50(date)
        return v < 0 if not np.isnan(v) else False

    if signal_name == 'above_sma50':
        v = pack.structure.price_vs_sma50(date)
        return v > 0 if not np.isnan(v) else False

    if signal_name.startswith('stoch_1w_not_ob'):
        # 1W StochRSI is NOT overbought — correction filter
        return not pack.stoch_1w.was_ob_recently(date, lookback_weeks=4, threshold=80)

    return False


def find_combo_fire_dates(pack, combo, start='2024-06-01', end='2026-02-17'):
    """Find all dates where ALL signals in combo fire simultaneously."""
    dates = pack.daily.index
    dates = dates[(dates >= start) & (dates <= end)]

    fire_dates = []
    prev_fired = False

    for dt in dates:
        all_fire = all(daily_signal_check(pack, dt, sig) for sig in combo)
        # Only record the FIRST day of a consecutive firing
        if all_fire and not prev_fired:
            fire_dates.append(dt)
        prev_fired = all_fire

    return fire_dates


def score_combo_tops(pack, fire_dates, gt, corr, window_days=21):
    """Score combo fire dates against known tops."""
    tops = [(pd.Timestamp(d), desc) for d, fr, to, desc in gt if fr == 'MARKUP']
    correction_dates = [pd.Timestamp(d) for d, _ in corr]

    true_pos = 0
    false_pos = 0
    timing = []

    for fd in fire_dates:
        matched = False
        for td, _ in tops:
            diff = (fd - td).days
            if -7 <= diff <= window_days:  # Signal can fire up to 7 days before or 21 after
                true_pos += 1
                timing.append(abs(diff))
                matched = True
                break
        if not matched:
            false_pos += 1

    tops_caught = 0
    for td, _ in tops:
        for fd in fire_dates:
            if -7 <= (fd - td).days <= window_days:
                tops_caught += 1
                break

    n = len(fire_dates)
    nt = len(tops)
    return {
        'true_pos': true_pos, 'false_pos': false_pos,
        'n_signals': n, 'n_tops': nt, 'tops_caught': tops_caught,
        'accuracy': true_pos / max(n, 1) * 100,
        'fp_rate': false_pos / max(n, 1) * 100,
        'coverage': tops_caught / max(nt, 1) * 100,
        'avg_timing': np.mean(timing) if timing else np.nan,
    }


def score_combo_bottoms(pack, fire_dates, gt, window_days=28):
    """Score combo fire dates against known bottoms."""
    bottoms = [(pd.Timestamp(d), desc) for d, fr, to, desc in gt
               if to == 'MARKUP' and fr in ('MARKDOWN', 'RANGING')]

    true_pos = 0
    false_pos = 0
    timing = []

    for fd in fire_dates:
        matched = False
        for bd, _ in bottoms:
            diff = (fd - bd).days
            if -7 <= diff <= window_days:
                true_pos += 1
                timing.append(abs(diff))
                matched = True
                break
        if not matched:
            false_pos += 1

    bots_caught = 0
    for bd, _ in bottoms:
        for fd in fire_dates:
            if -7 <= (fd - bd).days <= window_days:
                bots_caught += 1
                break

    n = len(fire_dates)
    nb = len(bottoms)
    return {
        'true_pos': true_pos, 'false_pos': false_pos,
        'n_signals': n, 'n_bottoms': nb, 'bottoms_caught': bots_caught,
        'accuracy': true_pos / max(n, 1) * 100,
        'fp_rate': false_pos / max(n, 1) * 100,
        'coverage': bots_caught / max(nb, 1) * 100,
        'avg_timing': np.mean(timing) if timing else np.nan,
    }


def score_correction_filter(pack, combo, gt, corr):
    """Score: does the combo correctly NOT fire during corrections?"""
    corrections = [(pd.Timestamp(d), desc) for d, desc in corr]
    tops = [(pd.Timestamp(d), desc) for d, fr, to, desc in gt if fr == 'MARKUP']

    correct_holds = 0
    incorrect_exits = 0

    for cd, desc in corrections:
        # Check if combo fires within 7 days of correction
        fires = any(daily_signal_check(pack, cd + timedelta(days=i), sig)
                    for i in range(-3, 8) for sig in combo
                    if daily_signal_check(pack, cd + timedelta(days=i), sig) is False) is False
        # Simpler: does the full combo fire at correction date?
        all_fire = all(daily_signal_check(pack, cd, sig) for sig in combo)
        if all_fire:
            incorrect_exits += 1
        else:
            correct_holds += 1

    return {
        'correct_holds': correct_holds,
        'incorrect_exits': incorrect_exits,
        'total_corrections': len(corrections),
        'hold_rate': correct_holds / max(len(corrections), 1) * 100,
    }


# ── Combo Definitions ──────────────────────────────────────────────────

TOP_COMBOS = {
    # Primary: 2W StochRSI at 95
    'T1_2W95': ['stoch_ob_2W_95'],
    'T2_2W95+cfgi': ['stoch_ob_2W_95', 'cfgi_declining_greed'],
    'T3_2W95+sma50neg': ['stoch_ob_2W_95', 'sma50_slope_neg'],
    'T4_2W95+belowSMA50': ['stoch_ob_2W_95', 'below_sma50'],
    'T5_2W95+lhll': ['stoch_ob_2W_95', 'lh_ll_2'],

    # Early warning: 1W at 97
    'T6_1W97': ['stoch_ob_1W_97'],
    'T7_1W97+cfgi': ['stoch_ob_1W_97', 'cfgi_declining_greed'],
    'T8_1W97+belowSMA50': ['stoch_ob_1W_97', 'below_sma50'],
    'T9_1W97+sma50neg': ['stoch_ob_1W_97', 'sma50_slope_neg'],

    # Layered: 1W 97 + 2W 95
    'T10_1W97+2W95': ['stoch_ob_1W_97', 'stoch_ob_2W_95'],
    'T11_1W97+2W95+cfgi': ['stoch_ob_1W_97', 'stoch_ob_2W_95', 'cfgi_declining_greed'],

    # Standard 1W 80
    'T12_1W80': ['stoch_ob_1W_80'],
    'T13_1W80+sma50neg': ['stoch_ob_1W_80', 'sma50_slope_neg'],
    'T14_1W80+lhll': ['stoch_ob_1W_80', 'lh_ll_2'],
    'T15_1W80+cfgi': ['stoch_ob_1W_80', 'cfgi_declining_greed'],

    # BMSB combos
    'T16_1W97+bmsb_below': ['stoch_ob_1W_97', 'bmsb_below'],
    'T17_2W95+bmsb_below': ['stoch_ob_2W_95', 'bmsb_below'],

    # Triple combos
    'T18_1W97+sma50neg+cfgi': ['stoch_ob_1W_97', 'sma50_slope_neg', 'cfgi_declining_greed'],
    'T19_1W80+lhll+cfgi': ['stoch_ob_1W_80', 'lh_ll_2', 'cfgi_declining_greed'],
    'T20_2W95+below50+cfgi': ['stoch_ob_2W_95', 'below_sma50', 'cfgi_declining_greed'],
}

BOTTOM_COMBOS = {
    # 1W StochRSI OS
    'B1_1W10': ['stoch_os_1W_10'],
    'B2_1W15': ['stoch_os_1W_15'],
    'B3_1W15+sma50pos': ['stoch_os_1W_15', 'sma50_slope_pos'],
    'B4_1W15+aboveSMA50': ['stoch_os_1W_15', 'above_sma50'],
    'B5_1W15+hhhl': ['stoch_os_1W_15', 'hh_hl_2'],
    'B6_1W10+sma50pos': ['stoch_os_1W_10', 'sma50_slope_pos'],
    'B7_1W10+cfgi_rising': ['stoch_os_1W_10', 'cfgi_rising_fear'],

    # 2W OS
    'B8_2W5': ['stoch_os_2W_5'],
    'B9_2W10': ['stoch_os_2W_10'],
    'B10_2W5+sma50pos': ['stoch_os_2W_5', 'sma50_slope_pos'],

    # With BMSB
    'B11_1W15+bmsb_above': ['stoch_os_1W_15', 'bmsb_above'],
    'B12_1W10+bmsb_above': ['stoch_os_1W_10', 'bmsb_above'],

    # Triple
    'B13_1W15+sma50pos+cfgi': ['stoch_os_1W_15', 'sma50_slope_pos', 'cfgi_rising_fear'],
    'B14_1W10+above50+sma200ok': ['stoch_os_1W_10', 'above_sma50', 'sma200_not_overext'],

    # With no-overextension
    'B15_1W15+sma200ok': ['stoch_os_1W_15', 'sma200_not_overext'],
}

CORRECTION_FILTER_COMBOS = {
    # These should NOT fire during corrections
    'CF1_1W_not_ob': ['stoch_1w_not_ob'],
    'CF2_above_sma50': ['above_sma50'],
    'CF3_sma50_pos': ['sma50_slope_pos'],
    'CF4_not_ob+above50': ['stoch_1w_not_ob', 'above_sma50'],
    'CF5_not_ob+sma50pos': ['stoch_1w_not_ob', 'sma50_slope_pos'],
    'CF6_bmsb_above': ['bmsb_above'],
    'CF7_not_ob+bmsb': ['stoch_1w_not_ob', 'bmsb_above'],
}


def run_combo_tests():
    print("V13 COMBINATION MATRIX — COMPOSITE SIGNAL TESTS")
    print("=" * 110)

    top_results = []
    bot_results = []
    corr_results = []

    for coin in ['BTC', 'ETH', 'SOL']:
        pack = V13SignalPack(coin)
        gt = GROUND_TRUTH[coin]
        corr = CORRECTIONS.get(coin, [])

        print(f"\n{'='*90}")
        print(f"  {coin}")
        print(f"{'='*90}")

        # ── TOP DETECTION COMBOS ──
        print(f"\n  --- TOP DETECTION COMBOS ---")
        print(f"  {'Combo':<30} {'Sigs':>5} {'TP':>4} {'FP':>4} {'Acc':>6} {'FP%':>6} {'Cov':>6} {'Time':>7}")

        for name, signals in TOP_COMBOS.items():
            fire_dates = find_combo_fire_dates(pack, signals)
            result = score_combo_tops(pack, fire_dates, gt, corr)

            print(f"  {name:<30} {result['n_signals']:>4}  {result['true_pos']:>3}  "
                  f"{result['false_pos']:>3}  {result['accuracy']:>5.0f}% {result['fp_rate']:>5.0f}% "
                  f"{result['coverage']:>5.0f}% {result['avg_timing']:>6.1f}d")

            top_results.append({'coin': coin, 'combo': name, **result})

        # ── BOTTOM DETECTION COMBOS ──
        print(f"\n  --- BOTTOM DETECTION COMBOS ---")
        print(f"  {'Combo':<30} {'Sigs':>5} {'TP':>4} {'FP':>4} {'Acc':>6} {'FP%':>6} {'Cov':>6} {'Time':>7}")

        for name, signals in BOTTOM_COMBOS.items():
            fire_dates = find_combo_fire_dates(pack, signals)
            result = score_combo_bottoms(pack, fire_dates, gt)

            print(f"  {name:<30} {result['n_signals']:>4}  {result['true_pos']:>3}  "
                  f"{result['false_pos']:>3}  {result['accuracy']:>5.0f}% {result['fp_rate']:>5.0f}% "
                  f"{result['coverage']:>5.0f}% {result['avg_timing']:>6.1f}d")

            bot_results.append({'coin': coin, 'combo': name, **result})

        # ── CORRECTION FILTER ──
        print(f"\n  --- CORRECTION FILTER (should HOLD, not exit) ---")
        for name, signals in CORRECTION_FILTER_COMBOS.items():
            result = score_correction_filter(pack, signals, gt, corr)
            print(f"  {name:<30} Hold: {result['correct_holds']}/{result['total_corrections']} "
                  f"({result['hold_rate']:.0f}%), Bad exits: {result['incorrect_exits']}")
            corr_results.append({'coin': coin, 'combo': name, **result})

    # ── AGGREGATE RANKINGS ──
    print("\n\n" + "=" * 110)
    print("AGGREGATE RANKINGS")
    print("=" * 110)

    def composite_score(row):
        timing_score = max(0, (30 - row['avg_timing']) / 30 * 100) if not np.isnan(row['avg_timing']) else 0
        return row['accuracy'] * 0.4 + (100 - row['fp_rate']) * 0.3 + row['coverage'] * 0.15 + timing_score * 0.15

    # Top combos
    df_top = pd.DataFrame(top_results)
    if len(df_top) > 0:
        agg = df_top.groupby('combo').agg({
            'accuracy': 'mean', 'fp_rate': 'mean', 'coverage': 'mean',
            'avg_timing': 'mean', 'n_signals': 'sum', 'true_pos': 'sum', 'false_pos': 'sum',
        }).round(1)
        agg['score'] = agg.apply(composite_score, axis=1).round(1)
        agg = agg.sort_values('score', ascending=False)

        print("\n  TOP DETECTION — BEST COMBOS:")
        print(f"  {'Combo':<30} {'Acc':>6} {'FP%':>6} {'Cov':>6} {'Time':>7} {'Score':>7} {'Sigs':>5}")
        for name, row in agg.head(10).iterrows():
            print(f"  {name:<30} {row['accuracy']:>5.0f}% {row['fp_rate']:>5.0f}% "
                  f"{row['coverage']:>5.0f}% {row['avg_timing']:>6.1f}d {row['score']:>6.1f} {int(row['n_signals']):>5}")

    # Bottom combos
    df_bot = pd.DataFrame(bot_results)
    if len(df_bot) > 0:
        agg = df_bot.groupby('combo').agg({
            'accuracy': 'mean', 'fp_rate': 'mean', 'coverage': 'mean',
            'avg_timing': 'mean', 'n_signals': 'sum', 'true_pos': 'sum', 'false_pos': 'sum',
        }).round(1)
        agg['score'] = agg.apply(composite_score, axis=1).round(1)
        agg = agg.sort_values('score', ascending=False)

        print("\n  BOTTOM DETECTION — BEST COMBOS:")
        print(f"  {'Combo':<30} {'Acc':>6} {'FP%':>6} {'Cov':>6} {'Time':>7} {'Score':>7} {'Sigs':>5}")
        for name, row in agg.head(10).iterrows():
            print(f"  {name:<30} {row['accuracy']:>5.0f}% {row['fp_rate']:>5.0f}% "
                  f"{row['coverage']:>5.0f}% {row['avg_timing']:>6.1f}d {row['score']:>6.1f} {int(row['n_signals']):>5}")

    # Correction filter
    df_corr = pd.DataFrame(corr_results)
    if len(df_corr) > 0:
        agg = df_corr.groupby('combo').agg({
            'hold_rate': 'mean', 'correct_holds': 'sum', 'incorrect_exits': 'sum',
            'total_corrections': 'sum',
        }).round(1)
        agg = agg.sort_values('hold_rate', ascending=False)

        print("\n  CORRECTION FILTER — BEST (highest hold rate = fewest false exits):")
        print(f"  {'Combo':<30} {'HoldRate':>9} {'Holds':>6} {'BadExits':>9}")
        for name, row in agg.iterrows():
            print(f"  {name:<30} {row['hold_rate']:>8.0f}% {int(row['correct_holds']):>5} "
                  f"{int(row['incorrect_exits']):>8}")


if __name__ == '__main__':
    run_combo_tests()
