"""
V13 Signal Matrix Test — Sweep individual signals and combinations.

Tests each signal (S1-S10) against ground truth phase transitions.
Scores by accuracy, false positive rate, timing lag, and coverage.
Then tests combinations per transition type.

Ground truth: manually verified phase transitions from charts.
Coins: BTC, ETH, SOL (BNB, XRP pending Brett validation).

Usage:
    python v13_signal_matrix.py
"""

import sys, os
import pandas as pd
import numpy as np
from datetime import timedelta
from pathlib import Path
from collections import defaultdict

# Add parent paths
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_signals import (
    V13SignalPack, StochRSISignal, BullMarketSupportBand,
    DailyStructure, CFGISignal, SMA200Overextension,
    load_daily, load_cfgi
)

# ── Ground Truth Phase Transitions ──────────────────────────────────────
# Format: (date, transition_type)
# transition_type: 'markup_start', 'markup_end', 'markdown_start', 'markdown_end'
# 'markup_start' = bottom → markup begins (DCA → MARKUP or MARKDOWN → MARKUP)
# 'markup_end' = top → distribution begins (MARKUP → DCA or MARKUP → MARKDOWN)
# 'markdown_start' = distribution → markdown begins (DCA → MARKDOWN or MARKUP → MARKDOWN)
# 'markdown_end' = accumulation → ranging begins (MARKDOWN → DCA)

GROUND_TRUTH = {
    'BTC': [
        ('2024-10-15', 'markup_start'),    # Oct 2024: breakout from ranging, strong rally begins
        ('2024-12-17', 'markup_end'),       # Dec 2024: ~108K top, distribution starts
        ('2025-01-20', 'markdown_start'),   # Jan 2025: confirmed breakdown
        ('2025-04-10', 'markdown_end'),     # Apr 2025: selling exhaustion, accumulation starts
        ('2025-05-01', 'markup_start'),     # May 2025: new markup confirmed
        ('2025-10-01', 'markup_end'),       # Oct 2025: distribution
        ('2025-11-01', 'markdown_start'),   # Nov 2025: markdown confirmed
    ],
    'ETH': [
        ('2024-10-15', 'markup_start'),    # Oct 2024: markup begins
        ('2024-12-06', 'markup_end'),       # Dec 2024: ~4000 area top
        ('2025-01-10', 'markdown_start'),   # Jan 2025: markdown confirmed
        ('2025-05-01', 'markup_start'),     # May 2025: new markup
        ('2025-09-15', 'markup_end'),       # Sep 2025: distribution
        ('2025-10-15', 'markdown_start'),   # Oct 2025: markdown confirmed
    ],
    'SOL': [
        ('2024-10-15', 'markup_start'),    # Oct 2024: markup begins
        ('2024-11-22', 'markup_end'),       # Nov 2024: ~260 top
        ('2025-01-10', 'markdown_start'),   # Jan 2025: markdown confirmed
        ('2025-04-10', 'markdown_end'),     # Apr 2025: accumulation
        ('2025-04-25', 'markup_start'),     # Apr 2025: new markup
        ('2025-10-15', 'markup_end'),       # Oct 2025: distribution
        ('2025-11-01', 'markdown_start'),   # Nov 2025: markdown confirmed
    ],
}

# Tolerance for timing: signal within N days of ground truth = "hit"
TIMING_TOLERANCE_DAYS = 21  # 3 weeks tolerance for weekly signals


# ── Signal Testing Framework ───────────────────────────────────────────

class SignalTester:
    """Test a signal against ground truth transitions."""

    def __init__(self, pack: V13SignalPack, coin: str):
        self.pack = pack
        self.coin = coin
        self.gt = [(pd.Timestamp(d), t) for d, t in GROUND_TRUTH.get(coin, [])]

    def _match_signal_to_gt(self, signal_dates, gt_types, tolerance_days=TIMING_TOLERANCE_DAYS):
        """
        Match signal fire dates to ground truth transitions.
        Returns: hits (correct signals), misses (GT not caught), false_positives (wrong signals)
        """
        gt_events = [(d, t) for d, t in self.gt if t in gt_types]
        hits = []
        misses = []
        matched_gt = set()

        for gt_date, gt_type in gt_events:
            best_match = None
            best_lag = None
            for sig_date in signal_dates:
                lag = (sig_date - gt_date).days
                if abs(lag) <= tolerance_days:
                    if best_lag is None or abs(lag) < abs(best_lag):
                        best_match = sig_date
                        best_lag = lag
            if best_match is not None:
                hits.append({
                    'gt_date': gt_date, 'gt_type': gt_type,
                    'signal_date': best_match, 'lag_days': best_lag
                })
                matched_gt.add(gt_date)
            else:
                misses.append({'gt_date': gt_date, 'gt_type': gt_type})

        # False positives: signals that didn't match any GT
        matched_signals = {h['signal_date'] for h in hits}
        false_positives = [d for d in signal_dates if d not in matched_signals]

        return hits, misses, false_positives

    def score(self, hits, misses, false_positives, total_gt):
        """Compute accuracy, FP rate, coverage, avg lag."""
        n_hits = len(hits)
        n_fp = len(false_positives)
        n_total_signals = n_hits + n_fp

        accuracy = n_hits / n_total_signals * 100 if n_total_signals > 0 else 0
        fp_rate = n_fp / n_total_signals * 100 if n_total_signals > 0 else 0
        coverage = n_hits / total_gt * 100 if total_gt > 0 else 0
        avg_lag = np.mean([abs(h['lag_days']) for h in hits]) if hits else float('nan')

        return {
            'accuracy': accuracy,
            'fp_rate': fp_rate,
            'coverage': coverage,
            'avg_lag_days': avg_lag,
            'hits': n_hits,
            'misses': len(misses),
            'false_positives': n_fp,
            'total_signals': n_total_signals,
            'total_gt': total_gt,
        }


# ── Individual Signal Tests ────────────────────────────────────────────

def test_stoch_rsi_ob_exit(pack, tester, n_weeks, threshold):
    """S1: StochRSI OB exit for TOP detection."""
    stoch = pack.get_stoch(n_weeks)
    exits = stoch.ob_exits(threshold=threshold)
    exits = exits[exits.index >= '2024-06-01']
    signal_dates = list(exits.index)
    gt_types = ['markup_end']
    hits, misses, fps = tester._match_signal_to_gt(signal_dates, gt_types)
    total_gt = len([d for d, t in tester.gt if t in gt_types])
    return tester.score(hits, misses, fps, total_gt), signal_dates, hits, fps


def test_stoch_rsi_os_exit(pack, tester, n_weeks, threshold):
    """S2: StochRSI OS exit for BOTTOM detection."""
    stoch = pack.get_stoch(n_weeks)
    exits = stoch.os_exits(threshold=threshold)
    exits = exits[exits.index >= '2024-06-01']
    signal_dates = list(exits.index)
    gt_types = ['markup_start', 'markdown_end']
    hits, misses, fps = tester._match_signal_to_gt(signal_dates, gt_types)
    total_gt = len([d for d, t in tester.gt if t in gt_types])
    return tester.score(hits, misses, fps, total_gt), signal_dates, hits, fps


def test_bmsb_loss(pack, tester, sustained_weeks):
    """S4: Bull Market Support Band loss for MARKDOWN detection."""
    # Find dates where price broke below BMSB and stayed for N weeks
    daily = pack.daily
    bmsb = pack.bmsb
    signal_dates = []

    # Check every week
    weekly_dates = pd.date_range(start='2024-06-01', end=daily.index[-1], freq='W')
    for d in weekly_dates:
        if d > daily.index[-1]:
            break
        if bmsb.sustained_below(d, weeks=sustained_weeks):
            # Only fire once per sustained break (not every week)
            if not signal_dates or (d - signal_dates[-1]).days > 30:
                signal_dates.append(d)

    gt_types = ['markdown_start']
    hits, misses, fps = tester._match_signal_to_gt(signal_dates, gt_types)
    total_gt = len([d for d, t in tester.gt if t in gt_types])
    return tester.score(hits, misses, fps, total_gt), signal_dates, hits, fps


def test_bmsb_reclaim(pack, tester, sustained_weeks):
    """S4b: Bull Market Support Band reclaim for MARKUP detection."""
    daily = pack.daily
    bmsb = pack.bmsb
    signal_dates = []

    weekly_dates = pd.date_range(start='2024-06-01', end=daily.index[-1], freq='W')
    prev_below = False
    for d in weekly_dates:
        if d > daily.index[-1]:
            break
        currently_below = bmsb.sustained_below(d, weeks=1)
        status = bmsb.status_at(d)
        if prev_below and status == 'ABOVE':
            if not signal_dates or (d - signal_dates[-1]).days > 30:
                signal_dates.append(d)
        prev_below = currently_below

    gt_types = ['markup_start']
    hits, misses, fps = tester._match_signal_to_gt(signal_dates, gt_types)
    total_gt = len([d for d, t in tester.gt if t in gt_types])
    return tester.score(hits, misses, fps, total_gt), signal_dates, hits, fps


def test_sma50_slope(pack, tester, window, direction='negative'):
    """S5: Daily SMA50 slope for confirmation."""
    daily = pack.daily
    structure = pack.structure
    signal_dates = []

    # Check every 3 days to reduce computation
    check_dates = pd.date_range(start='2024-06-01', end=daily.index[-1], freq='3D')
    prev_sign = None
    for d in check_dates:
        if d > daily.index[-1]:
            break
        slope = structure.sma50_slope_at(d, window)
        if np.isnan(slope):
            continue
        curr_sign = 'pos' if slope > 0 else 'neg'
        if prev_sign is not None and prev_sign != curr_sign:
            if (direction == 'negative' and curr_sign == 'neg') or \
               (direction == 'positive' and curr_sign == 'pos'):
                if not signal_dates or (d - signal_dates[-1]).days > 21:
                    signal_dates.append(d)
        prev_sign = curr_sign

    if direction == 'negative':
        gt_types = ['markup_end', 'markdown_start']
    else:
        gt_types = ['markup_start', 'markdown_end']

    hits, misses, fps = tester._match_signal_to_gt(signal_dates, gt_types)
    total_gt = len([d for d, t in tester.gt if t in gt_types])
    return tester.score(hits, misses, fps, total_gt), signal_dates, hits, fps


def test_adx_ranging(pack, tester, threshold):
    """S7: ADX below threshold for ranging detection."""
    daily = pack.daily
    structure = pack.structure
    signal_dates = []

    check_dates = pd.date_range(start='2024-06-01', end=daily.index[-1], freq='3D')
    prev_ranging = None
    for d in check_dates:
        if d > daily.index[-1]:
            break
        ranging = structure.is_ranging(d, threshold)
        if prev_ranging is not None and not prev_ranging and ranging:
            if not signal_dates or (d - signal_dates[-1]).days > 21:
                signal_dates.append(d)
        prev_ranging = ranging

    gt_types = ['markup_end', 'markdown_end']  # Distribution/accumulation = ranging
    hits, misses, fps = tester._match_signal_to_gt(signal_dates, gt_types)
    total_gt = len([d for d, t in tester.gt if t in gt_types])
    return tester.score(hits, misses, fps, total_gt), signal_dates, hits, fps


def test_cfgi_level(pack, tester, fear_threshold, greed_threshold, direction='greed_exit'):
    """S8: CFGI level for phase gating."""
    cfgi = pack.cfgi
    if cfgi.cfgi is None:
        return {'accuracy': 0, 'fp_rate': 0, 'coverage': 0, 'avg_lag_days': float('nan'),
                'hits': 0, 'misses': 0, 'false_positives': 0, 'total_signals': 0, 'total_gt': 0}, [], [], []

    signal_dates = []
    check_dates = pd.date_range(start='2024-06-01', end=pack.daily.index[-1], freq='3D')

    if direction == 'greed_exit':
        # CFGI drops from greed → distribution signal
        prev_greedy = False
        for d in check_dates:
            v = cfgi.value_at(d)
            if np.isnan(v):
                continue
            if v > greed_threshold:
                prev_greedy = True
            elif prev_greedy and v < greed_threshold - 10:
                if not signal_dates or (d - signal_dates[-1]).days > 21:
                    signal_dates.append(d)
                prev_greedy = False
        gt_types = ['markup_end']
    else:
        # CFGI rises from fear → accumulation signal
        prev_fearful = False
        for d in check_dates:
            v = cfgi.value_at(d)
            if np.isnan(v):
                continue
            if v < fear_threshold:
                prev_fearful = True
            elif prev_fearful and v > fear_threshold + 10:
                if not signal_dates or (d - signal_dates[-1]).days > 21:
                    signal_dates.append(d)
                prev_fearful = False
        gt_types = ['markup_start', 'markdown_end']

    hits, misses, fps = tester._match_signal_to_gt(signal_dates, gt_types)
    total_gt = len([d for d, t in tester.gt if t in gt_types])
    return tester.score(hits, misses, fps, total_gt), signal_dates, hits, fps


def test_cfgi_direction(pack, tester, roc_period, direction='declining'):
    """S9: CFGI rate of change."""
    cfgi = pack.cfgi
    if cfgi.cfgi is None:
        return {'accuracy': 0, 'fp_rate': 0, 'coverage': 0, 'avg_lag_days': float('nan'),
                'hits': 0, 'misses': 0, 'false_positives': 0, 'total_signals': 0, 'total_gt': 0}, [], [], []

    signal_dates = []
    check_dates = pd.date_range(start='2024-06-01', end=pack.daily.index[-1], freq='3D')
    prev_sign = None

    for d in check_dates:
        roc = cfgi.roc(d, roc_period)
        if np.isnan(roc):
            continue
        curr_sign = 'falling' if roc < -10 else ('rising' if roc > 10 else 'flat')
        if prev_sign is not None and curr_sign != prev_sign:
            if (direction == 'declining' and curr_sign == 'falling') or \
               (direction == 'rising' and curr_sign == 'rising'):
                if not signal_dates or (d - signal_dates[-1]).days > 21:
                    signal_dates.append(d)
        prev_sign = curr_sign

    if direction == 'declining':
        gt_types = ['markup_end', 'markdown_start']
    else:
        gt_types = ['markup_start', 'markdown_end']

    hits, misses, fps = tester._match_signal_to_gt(signal_dates, gt_types)
    total_gt = len([d for d, t in tester.gt if t in gt_types])
    return tester.score(hits, misses, fps, total_gt), signal_dates, hits, fps


def test_sma200_overext(pack, tester, threshold):
    """S10: SMA200 overextension as markup entry FILTER (blocks bad entries)."""
    # This is a filter, not a signal. Test: does blocking entries >threshold% above SMA200
    # improve markup_start accuracy?
    # We'll report: how many GT markup_starts would be blocked vs allowed
    structure = pack.structure
    blocked = []
    allowed = []
    for gt_date, gt_type in tester.gt:
        if gt_type != 'markup_start':
            continue
        overext = structure.price_vs_sma200(gt_date)
        if np.isnan(overext):
            continue
        if overext > threshold:
            blocked.append(gt_date)
        else:
            allowed.append(gt_date)

    return {
        'threshold': threshold,
        'gt_blocked': len(blocked),
        'gt_allowed': len(allowed),
        'blocked_dates': blocked,
        'allowed_dates': allowed,
    }


# ── Combination Tests ──────────────────────────────────────────────────

def test_combo_markup_exit(pack, tester, stoch_weeks, stoch_threshold,
                           require_daily_confirm=False, require_cfgi_decline=False,
                           require_bmsb_loss=False, sma50_window=10):
    """Combo test for MARKUP → DCA transition."""
    stoch = pack.get_stoch(stoch_weeks)
    exits = stoch.ob_exits(threshold=stoch_threshold)
    exits = exits[exits.index >= '2024-06-01']

    signal_dates = []
    for dt in exits.index:
        # Apply additional filters
        if require_daily_confirm:
            if not pack.structure.sma50_slope_negative(dt, sma50_window) and \
               not pack.structure.lh_ll_streak(dt, 2):
                continue
        if require_cfgi_decline:
            if not pack.cfgi.declining_from_greed(dt):
                continue
        if require_bmsb_loss:
            if pack.bmsb.status_at(dt) != 'BELOW':
                continue
        signal_dates.append(dt)

    gt_types = ['markup_end']
    hits, misses, fps = tester._match_signal_to_gt(signal_dates, gt_types)
    total_gt = len([d for d, t in tester.gt if t in gt_types])
    return tester.score(hits, misses, fps, total_gt), signal_dates, hits, fps


def test_combo_markup_entry(pack, tester, stoch_weeks, stoch_threshold,
                            require_daily_confirm=False, require_bmsb_above=False,
                            require_cfgi_rising=False, block_overextension=None,
                            sma50_window=10):
    """Combo test for DCA → MARKUP transition."""
    stoch = pack.get_stoch(stoch_weeks)
    exits = stoch.os_exits(threshold=stoch_threshold)
    exits = exits[exits.index >= '2024-06-01']

    signal_dates = []
    for dt in exits.index:
        if require_daily_confirm:
            if not pack.structure.sma50_slope_positive(dt, sma50_window) and \
               not pack.structure.hh_hl_streak(dt, 2):
                continue
        if require_bmsb_above:
            status = pack.bmsb.status_at(dt)
            if status not in ('ABOVE', 'IN_BAND'):
                continue
        if require_cfgi_rising:
            if not pack.cfgi.rising_from_fear(dt):
                continue
        if block_overextension is not None:
            if pack.sma200.is_overextended(dt, block_overextension):
                continue
        signal_dates.append(dt)

    gt_types = ['markup_start', 'markdown_end']
    hits, misses, fps = tester._match_signal_to_gt(signal_dates, gt_types)
    total_gt = len([d for d, t in tester.gt if t in gt_types])
    return tester.score(hits, misses, fps, total_gt), signal_dates, hits, fps


def test_combo_markdown_entry(pack, tester, stoch_weeks, stoch_threshold,
                              require_bmsb_below=False, require_cfgi_fear=False,
                              require_daily_confirm=False, sustained_bmsb_weeks=2,
                              sma50_window=10):
    """Combo test for DCA → MARKDOWN or MARKUP → MARKDOWN transition."""
    stoch = pack.get_stoch(stoch_weeks)
    exits = stoch.ob_exits(threshold=stoch_threshold)
    exits = exits[exits.index >= '2024-06-01']

    signal_dates = []
    for dt in exits.index:
        if require_bmsb_below:
            if not pack.bmsb.sustained_below(dt, weeks=sustained_bmsb_weeks):
                continue
        if require_cfgi_fear:
            v = pack.cfgi.value_at(dt)
            if np.isnan(v) or v > 30:
                continue
        if require_daily_confirm:
            if not pack.structure.sma50_slope_negative(dt, sma50_window) and \
               not pack.structure.lh_ll_streak(dt, 2):
                continue
        signal_dates.append(dt)

    gt_types = ['markdown_start']
    hits, misses, fps = tester._match_signal_to_gt(signal_dates, gt_types)
    total_gt = len([d for d, t in tester.gt if t in gt_types])
    return tester.score(hits, misses, fps, total_gt), signal_dates, hits, fps


def test_combo_markdown_exit(pack, tester, stoch_weeks, stoch_threshold,
                             require_daily_confirm=False, require_cfgi_rising=False,
                             sma50_window=10):
    """Combo test for MARKDOWN → DCA transition."""
    stoch = pack.get_stoch(stoch_weeks)
    exits = stoch.os_exits(threshold=stoch_threshold)
    exits = exits[exits.index >= '2024-06-01']

    signal_dates = []
    for dt in exits.index:
        if require_daily_confirm:
            if not pack.structure.sma50_slope_positive(dt, sma50_window) and \
               not pack.structure.hh_hl_streak(dt, 2):
                continue
        if require_cfgi_rising:
            if not pack.cfgi.rising_from_fear(dt):
                continue
        signal_dates.append(dt)

    gt_types = ['markdown_end']
    hits, misses, fps = tester._match_signal_to_gt(signal_dates, gt_types)
    total_gt = len([d for d, t in tester.gt if t in gt_types])
    return tester.score(hits, misses, fps, total_gt), signal_dates, hits, fps


# ── Correction Filter Test ─────────────────────────────────────────────

def test_correction_filter(pack, tester, require_not_ob=True, require_bmsb_above=False,
                           require_cfgi_above=None, stoch_weeks=1, ob_threshold=80):
    """Test: drops that pass the correction filter (should NOT be exited) — how many recover?"""
    daily = pack.daily
    # Find all >10% drops
    drops = []
    for i in range(len(daily) - 30):
        if daily.index[i] < pd.Timestamp('2024-06-01'):
            continue
        price = daily['close'].iloc[i]
        future_30 = daily['close'].iloc[i:i+30]
        min_future = future_30.min()
        drop_pct = (min_future - price) / price * 100
        if drop_pct < -10:
            # Check if this drop is within 14 days of a previous drop (dedup)
            if drops and (daily.index[i] - drops[-1]['date']).days < 30:
                continue
            drops.append({
                'date': daily.index[i],
                'drop_pct': drop_pct,
                'min_price': min_future,
            })

    # Check recovery
    filtered_drops = []
    for drop in drops:
        d = drop['date']
        passes_filter = True

        if require_not_ob:
            stoch = pack.get_stoch(stoch_weeks)
            if stoch.was_ob_recently(d, lookback_weeks=4, threshold=ob_threshold):
                passes_filter = False

        if require_bmsb_above and passes_filter:
            if pack.bmsb.status_at(d) == 'BELOW':
                passes_filter = False

        if require_cfgi_above is not None and passes_filter:
            v = pack.cfgi.value_at(d)
            if not np.isnan(v) and v < require_cfgi_above:
                passes_filter = False

        if passes_filter:
            # Check if it recovered within 60 days
            future = daily[daily.index >= d].head(60)
            if len(future) > 10:
                recovery = (future['close'].iloc[-1] - drop['min_price']) / drop['min_price'] * 100
                drop['recovered'] = recovery > 5
                drop['recovery_pct'] = recovery
                filtered_drops.append(drop)

    n_recovered = sum(1 for d in filtered_drops if d['recovered'])
    return {
        'total_drops': len(filtered_drops),
        'recovered': n_recovered,
        'accuracy': n_recovered / len(filtered_drops) * 100 if filtered_drops else 0,
        'drops': filtered_drops,
    }


# ── Main Runner ────────────────────────────────────────────────────────

def format_score(score, label=""):
    """Format a score dict as a readable line."""
    if 'accuracy' not in score:
        return f"  {label}: {score}"
    return (f"  {label}: Acc={score['accuracy']:.0f}% FP={score['fp_rate']:.0f}% "
            f"Cov={score['coverage']:.0f}% Lag={score['avg_lag_days']:.1f}d "
            f"({score['hits']}/{score['total_gt']} hits, {score['false_positives']} FP)")


def weighted_score(score):
    """Compute weighted composite score (higher = better)."""
    if 'accuracy' not in score or score['total_signals'] == 0:
        return 0
    acc = score['accuracy']
    fp = score['fp_rate']
    cov = score['coverage']
    lag = score['avg_lag_days'] if not np.isnan(score['avg_lag_days']) else 30
    # Weights from spec: 40% accuracy, 30% FP, 15% timing, 15% coverage
    # Normalize lag: 0 days = 100, 30+ days = 0
    lag_score = max(0, 100 - (lag / 30 * 100))
    return acc * 0.40 + (100 - fp) * 0.30 + lag_score * 0.15 + cov * 0.15


def run_individual_tests(coins=['BTC', 'ETH', 'SOL']):
    """Run all individual signal tests with parameter sweeps."""
    print("=" * 80)
    print("  V13 SIGNAL MATRIX — INDIVIDUAL SIGNAL TESTS")
    print("=" * 80)

    all_results = defaultdict(list)

    for coin in coins:
        print(f"\n{'─' * 60}")
        print(f"  {coin}")
        print(f"{'─' * 60}")

        try:
            pack = V13SignalPack(coin)
        except ValueError as e:
            print(f"  SKIP: {e}")
            continue

        tester = SignalTester(pack, coin)

        # ── S1: StochRSI OB Exit (TOP detection) ──
        print(f"\n  S1: StochRSI OB Exit (TOP detection)")
        for n_weeks in [1, 2, 3]:
            for threshold in [80, 85, 90, 95]:
                score, dates, hits, fps = test_stoch_rsi_ob_exit(pack, tester, n_weeks, threshold)
                label = f"{n_weeks}W th={threshold}"
                print(format_score(score, label))
                all_results[f'S1_OB_{n_weeks}W_th{threshold}'].append({
                    'coin': coin, 'score': score, 'weighted': weighted_score(score)
                })

        # ── S2: StochRSI OS Exit (BOTTOM detection) ──
        print(f"\n  S2: StochRSI OS Exit (BOTTOM detection)")
        for n_weeks in [1, 2, 3]:
            for threshold in [10, 15, 20, 25]:
                score, dates, hits, fps = test_stoch_rsi_os_exit(pack, tester, n_weeks, threshold)
                label = f"{n_weeks}W th={threshold}"
                print(format_score(score, label))
                all_results[f'S2_OS_{n_weeks}W_th{threshold}'].append({
                    'coin': coin, 'score': score, 'weighted': weighted_score(score)
                })

        # ── S4: BMSB Loss (MARKDOWN detection) ──
        print(f"\n  S4: BMSB Loss (MARKDOWN detection)")
        for weeks in [1, 2, 3]:
            score, dates, hits, fps = test_bmsb_loss(pack, tester, weeks)
            label = f"sustained={weeks}W"
            print(format_score(score, label))
            all_results[f'S4_BMSB_loss_{weeks}W'].append({
                'coin': coin, 'score': score, 'weighted': weighted_score(score)
            })

        # ── S4b: BMSB Reclaim (MARKUP detection) ──
        print(f"\n  S4b: BMSB Reclaim (MARKUP detection)")
        for weeks in [1, 2, 3]:
            score, dates, hits, fps = test_bmsb_reclaim(pack, tester, weeks)
            label = f"sustained={weeks}W"
            print(format_score(score, label))
            all_results[f'S4b_BMSB_reclaim_{weeks}W'].append({
                'coin': coin, 'score': score, 'weighted': weighted_score(score)
            })

        # ── S5: SMA50 Slope ──
        print(f"\n  S5: SMA50 Slope (bearish turn = top/markdown)")
        for window in [5, 10, 14]:
            score, dates, hits, fps = test_sma50_slope(pack, tester, window, 'negative')
            label = f"window={window}d neg"
            print(format_score(score, label))
            all_results[f'S5_SMA50_neg_w{window}'].append({
                'coin': coin, 'score': score, 'weighted': weighted_score(score)
            })

        print(f"\n  S5b: SMA50 Slope (bullish turn = bottom/markup)")
        for window in [5, 10, 14]:
            score, dates, hits, fps = test_sma50_slope(pack, tester, window, 'positive')
            label = f"window={window}d pos"
            print(format_score(score, label))
            all_results[f'S5b_SMA50_pos_w{window}'].append({
                'coin': coin, 'score': score, 'weighted': weighted_score(score)
            })

        # ── S7: ADX Ranging ──
        print(f"\n  S7: ADX Ranging (distribution/accumulation)")
        for threshold in [15, 20, 25]:
            score, dates, hits, fps = test_adx_ranging(pack, tester, threshold)
            label = f"th={threshold}"
            print(format_score(score, label))
            all_results[f'S7_ADX_ranging_th{threshold}'].append({
                'coin': coin, 'score': score, 'weighted': weighted_score(score)
            })

        # ── S8: CFGI Level ──
        print(f"\n  S8: CFGI Greed Exit (distribution)")
        for greed_th in [60, 70, 75]:
            score, dates, hits, fps = test_cfgi_level(pack, tester, 25, greed_th, 'greed_exit')
            label = f"greed>{greed_th}"
            print(format_score(score, label))
            all_results[f'S8_CFGI_greed_exit_{greed_th}'].append({
                'coin': coin, 'score': score, 'weighted': weighted_score(score)
            })

        print(f"\n  S8b: CFGI Fear Exit (accumulation)")
        for fear_th in [25, 30, 35]:
            score, dates, hits, fps = test_cfgi_level(pack, tester, fear_th, 70, 'fear_exit')
            label = f"fear<{fear_th}"
            print(format_score(score, label))
            all_results[f'S8b_CFGI_fear_exit_{fear_th}'].append({
                'coin': coin, 'score': score, 'weighted': weighted_score(score)
            })

        # ── S9: CFGI Direction ──
        print(f"\n  S9: CFGI Direction (declining = bearish)")
        for roc_period in [3, 5, 7]:
            score, dates, hits, fps = test_cfgi_direction(pack, tester, roc_period, 'declining')
            label = f"ROC-{roc_period}d declining"
            print(format_score(score, label))
            all_results[f'S9_CFGI_declining_roc{roc_period}'].append({
                'coin': coin, 'score': score, 'weighted': weighted_score(score)
            })

        print(f"\n  S9b: CFGI Direction (rising = bullish)")
        for roc_period in [3, 5, 7]:
            score, dates, hits, fps = test_cfgi_direction(pack, tester, roc_period, 'rising')
            label = f"ROC-{roc_period}d rising"
            print(format_score(score, label))
            all_results[f'S9b_CFGI_rising_roc{roc_period}'].append({
                'coin': coin, 'score': score, 'weighted': weighted_score(score)
            })

        # ── S10: SMA200 Overextension (filter) ──
        print(f"\n  S10: SMA200 Overextension (markup entry FILTER)")
        for threshold in [15, 20, 25, 30]:
            result = test_sma200_overext(pack, tester, threshold)
            print(f"  th={threshold}%: {result['gt_allowed']} allowed, {result['gt_blocked']} blocked")

    return all_results


def run_combination_tests(coins=['BTC', 'ETH', 'SOL']):
    """Run combination tests for each transition type."""
    print("\n" + "=" * 80)
    print("  V13 SIGNAL MATRIX — COMBINATION TESTS")
    print("=" * 80)

    combo_results = defaultdict(list)

    for coin in coins:
        print(f"\n{'─' * 60}")
        print(f"  {coin} — COMBINATIONS")
        print(f"{'─' * 60}")

        try:
            pack = V13SignalPack(coin)
        except ValueError as e:
            print(f"  SKIP: {e}")
            continue

        tester = SignalTester(pack, coin)

        # ── MARKUP EXIT (top detection) ──
        print(f"\n  === MARKUP → DCA (Top Detection) ===")
        combos = [
            ("2W OB>80 alone", dict(stoch_weeks=2, stoch_threshold=80)),
            ("2W OB>80 + daily confirm", dict(stoch_weeks=2, stoch_threshold=80, require_daily_confirm=True)),
            ("2W OB>80 + CFGI decline", dict(stoch_weeks=2, stoch_threshold=80, require_cfgi_decline=True)),
            ("2W OB>80 + BMSB loss", dict(stoch_weeks=2, stoch_threshold=80, require_bmsb_loss=True)),
            ("2W OB>80 + daily + CFGI", dict(stoch_weeks=2, stoch_threshold=80, require_daily_confirm=True, require_cfgi_decline=True)),
            ("1W OB>80 alone", dict(stoch_weeks=1, stoch_threshold=80)),
            ("1W OB>80 + daily confirm", dict(stoch_weeks=1, stoch_threshold=80, require_daily_confirm=True)),
            ("1W OB>97 alone", dict(stoch_weeks=1, stoch_threshold=97)),
            ("1W OB>97 + daily confirm", dict(stoch_weeks=1, stoch_threshold=97, require_daily_confirm=True)),
        ]
        for label, kwargs in combos:
            score, dates, hits, fps = test_combo_markup_exit(pack, tester, **kwargs)
            print(format_score(score, label))
            combo_results[f'MARKUP_EXIT_{label}'].append({
                'coin': coin, 'score': score, 'weighted': weighted_score(score)
            })

        # ── MARKUP ENTRY (bottom detection) ──
        print(f"\n  === DCA → MARKUP (Bottom Detection) ===")
        combos = [
            ("2W OS<20 alone", dict(stoch_weeks=2, stoch_threshold=20)),
            ("2W OS<20 + daily confirm", dict(stoch_weeks=2, stoch_threshold=20, require_daily_confirm=True)),
            ("2W OS<20 + BMSB above", dict(stoch_weeks=2, stoch_threshold=20, require_bmsb_above=True)),
            ("2W OS<20 + CFGI rising", dict(stoch_weeks=2, stoch_threshold=20, require_cfgi_rising=True)),
            ("2W OS<20 + overext<20%", dict(stoch_weeks=2, stoch_threshold=20, block_overextension=20)),
            ("2W OS<20 + daily + BMSB", dict(stoch_weeks=2, stoch_threshold=20, require_daily_confirm=True, require_bmsb_above=True)),
            ("1W OS<20 alone", dict(stoch_weeks=1, stoch_threshold=20)),
            ("1W OS<20 + daily confirm", dict(stoch_weeks=1, stoch_threshold=20, require_daily_confirm=True)),
        ]
        for label, kwargs in combos:
            score, dates, hits, fps = test_combo_markup_entry(pack, tester, **kwargs)
            print(format_score(score, label))
            combo_results[f'MARKUP_ENTRY_{label}'].append({
                'coin': coin, 'score': score, 'weighted': weighted_score(score)
            })

        # ── MARKDOWN ENTRY ──
        print(f"\n  === DCA → MARKDOWN (Markdown Entry) ===")
        combos = [
            ("2W OB>80 alone", dict(stoch_weeks=2, stoch_threshold=80)),
            ("2W OB>80 + BMSB below 2W", dict(stoch_weeks=2, stoch_threshold=80, require_bmsb_below=True)),
            ("2W OB>80 + CFGI<30", dict(stoch_weeks=2, stoch_threshold=80, require_cfgi_fear=True)),
            ("2W OB>80 + daily confirm", dict(stoch_weeks=2, stoch_threshold=80, require_daily_confirm=True)),
            ("2W OB>80 + BMSB + CFGI", dict(stoch_weeks=2, stoch_threshold=80, require_bmsb_below=True, require_cfgi_fear=True)),
            ("2W OB>80 + BMSB + daily", dict(stoch_weeks=2, stoch_threshold=80, require_bmsb_below=True, require_daily_confirm=True)),
            ("1W OB>80 + BMSB below 2W", dict(stoch_weeks=1, stoch_threshold=80, require_bmsb_below=True)),
        ]
        for label, kwargs in combos:
            score, dates, hits, fps = test_combo_markdown_entry(pack, tester, **kwargs)
            print(format_score(score, label))
            combo_results[f'MARKDOWN_ENTRY_{label}'].append({
                'coin': coin, 'score': score, 'weighted': weighted_score(score)
            })

        # ── MARKDOWN EXIT ──
        print(f"\n  === MARKDOWN → DCA (Markdown Exit) ===")
        combos = [
            ("2W OS<20 alone", dict(stoch_weeks=2, stoch_threshold=20)),
            ("2W OS<20 + daily confirm", dict(stoch_weeks=2, stoch_threshold=20, require_daily_confirm=True)),
            ("2W OS<20 + CFGI rising", dict(stoch_weeks=2, stoch_threshold=20, require_cfgi_rising=True)),
            ("2W OS<20 + daily + CFGI", dict(stoch_weeks=2, stoch_threshold=20, require_daily_confirm=True, require_cfgi_rising=True)),
            ("1W OS<20 alone", dict(stoch_weeks=1, stoch_threshold=20)),
            ("1W OS<20 + daily confirm", dict(stoch_weeks=1, stoch_threshold=20, require_daily_confirm=True)),
        ]
        for label, kwargs in combos:
            score, dates, hits, fps = test_combo_markdown_exit(pack, tester, **kwargs)
            print(format_score(score, label))
            combo_results[f'MARKDOWN_EXIT_{label}'].append({
                'coin': coin, 'score': score, 'weighted': weighted_score(score)
            })

        # ── CORRECTION FILTER ──
        print(f"\n  === Correction Filter (hold through) ===")
        for stoch_weeks in [1, 2]:
            for ob_th in [80, 85]:
                result = test_correction_filter(pack, tester,
                    require_not_ob=True, stoch_weeks=stoch_weeks, ob_threshold=ob_th)
                label = f"{stoch_weeks}W NOT OB>{ob_th}"
                print(f"  {label}: {result['recovered']}/{result['total_drops']} recovered ({result['accuracy']:.0f}%)")

    return combo_results


def print_rankings(all_results, top_n=5):
    """Print ranked results across all coins."""
    print("\n" + "=" * 80)
    print("  CROSS-COIN RANKINGS (averaged across coins)")
    print("=" * 80)

    rankings = []
    for signal_key, coin_results in all_results.items():
        if not coin_results:
            continue
        avg_weighted = np.mean([r['weighted'] for r in coin_results])
        avg_acc = np.mean([r['score']['accuracy'] for r in coin_results if 'accuracy' in r['score']])
        avg_fp = np.mean([r['score']['fp_rate'] for r in coin_results if 'fp_rate' in r['score']])
        avg_cov = np.mean([r['score']['coverage'] for r in coin_results if 'coverage' in r['score']])
        avg_lag = np.nanmean([r['score']['avg_lag_days'] for r in coin_results if 'avg_lag_days' in r['score']])
        rankings.append({
            'signal': signal_key,
            'weighted': avg_weighted,
            'accuracy': avg_acc,
            'fp_rate': avg_fp,
            'coverage': avg_cov,
            'avg_lag': avg_lag,
            'n_coins': len(coin_results),
        })

    rankings.sort(key=lambda x: x['weighted'], reverse=True)

    # Group by signal category
    categories = defaultdict(list)
    for r in rankings:
        cat = r['signal'].split('_')[0] + '_' + r['signal'].split('_')[1]
        categories[cat].append(r)

    for cat, items in categories.items():
        items.sort(key=lambda x: x['weighted'], reverse=True)
        print(f"\n  {cat}:")
        for r in items[:top_n]:
            print(f"    {r['signal']}: W={r['weighted']:.1f} "
                  f"Acc={r['accuracy']:.0f}% FP={r['fp_rate']:.0f}% "
                  f"Cov={r['coverage']:.0f}% Lag={r['avg_lag']:.1f}d")


def main():
    print("V13 Signal Matrix Test")
    print(f"Ground truth coins: {list(GROUND_TRUTH.keys())}")
    print(f"Test period: Jun 2024 -> present")
    print()

    # Phase 1: Individual signals
    individual_results = run_individual_tests()
    print_rankings(individual_results)

    # Phase 2: Combinations
    combo_results = run_combination_tests()
    print_rankings(combo_results)

    # Summary
    print("\n" + "=" * 80)
    print("  SUMMARY — TOP SIGNALS PER TRANSITION")
    print("=" * 80)

    # Aggregate combo results
    all_combos = {}
    for key, coin_results in combo_results.items():
        if coin_results:
            avg_w = np.mean([r['weighted'] for r in coin_results])
            all_combos[key] = avg_w

    for transition in ['MARKUP_EXIT', 'MARKUP_ENTRY', 'MARKDOWN_ENTRY', 'MARKDOWN_EXIT']:
        relevant = {k: v for k, v in all_combos.items() if k.startswith(transition)}
        if relevant:
            sorted_combos = sorted(relevant.items(), key=lambda x: x[1], reverse=True)
            print(f"\n  {transition}:")
            for k, v in sorted_combos[:3]:
                short_name = k.replace(f'{transition}_', '')
                print(f"    {short_name}: weighted={v:.1f}")


if __name__ == '__main__':
    main()
