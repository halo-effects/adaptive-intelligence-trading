"""
V13 Threshold Sweep — Fine-tune 2W StochRSI OB threshold for top detection
+ Failsafe markdown detector (late exit if primary signal missed)

Usage:
    python v13_threshold_sweep.py
"""

import sys
import pandas as pd
import numpy as np
from datetime import timedelta
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack

# Ground truth tops and markdown starts
GROUND_TRUTH = {
    'BTC': [
        ('2024-12-17', 'markup_end'),
        ('2025-01-20', 'markdown_start'),
        ('2025-10-01', 'markup_end'),
        ('2025-11-01', 'markdown_start'),
    ],
    'ETH': [
        ('2024-12-06', 'markup_end'),
        ('2025-01-10', 'markdown_start'),
        ('2025-09-15', 'markup_end'),
        ('2025-10-15', 'markdown_start'),
    ],
    'SOL': [
        ('2024-11-22', 'markup_end'),
        ('2025-01-10', 'markdown_start'),
        ('2025-10-15', 'markup_end'),
        ('2025-11-01', 'markdown_start'),
    ],
}

TOLERANCE = 28  # 4 weeks for weekly signals


def match_signals(signal_dates, gt_dates, tolerance=TOLERANCE):
    """Match signal dates to ground truth. Returns hits, misses, false_positives."""
    hits, matched_gt, matched_sig = [], set(), set()
    for gt_d in gt_dates:
        best, best_lag = None, None
        for s_d in signal_dates:
            lag = (s_d - gt_d).days
            if abs(lag) <= tolerance and (best_lag is None or abs(lag) < abs(best_lag)):
                best, best_lag = s_d, lag
        if best is not None:
            hits.append({'gt': gt_d, 'signal': best, 'lag': best_lag})
            matched_gt.add(gt_d)
            matched_sig.add(best)
    misses = [d for d in gt_dates if d not in matched_gt]
    fps = [d for d in signal_dates if d not in matched_sig]
    return hits, misses, fps


def measure_drawdown_after(pack, date, days=90):
    """Max drawdown from date over N days."""
    future = pack.daily[pack.daily.index >= date].head(days)
    if len(future) < 5:
        return np.nan
    entry = future['close'].iloc[0]
    return (future['low'].min() - entry) / entry * 100


# ══════════════════════════════════════════════════════════════════════
# PART 1: Fine-tune 2W OB threshold for top detection
# ══════════════════════════════════════════════════════════════════════

def sweep_ob_thresholds():
    print("=" * 80)
    print("  PART 1: 2W StochRSI OB Threshold Sweep (Top Detection)")
    print("=" * 80)

    thresholds = [80, 82, 85, 87, 90, 92, 93, 94, 95, 96, 97]

    for coin in ['BTC', 'ETH', 'SOL']:
        print(f"\n{'─' * 60}")
        print(f"  {coin}")
        print(f"{'─' * 60}")

        try:
            pack = V13SignalPack(coin)
        except ValueError as e:
            print(f"  SKIP: {e}")
            continue

        gt_tops = [pd.Timestamp(d) for d, t in GROUND_TRUTH[coin] if t == 'markup_end']

        for n_weeks in [1, 2]:
            print(f"\n  {n_weeks}W StochRSI:")
            stoch = pack.get_stoch(n_weeks)

            for th in thresholds:
                exits = stoch.ob_exits(threshold=th)
                exits = exits[exits.index >= '2024-06-01']
                signal_dates = list(exits.index)

                hits, misses, fps = match_signals(signal_dates, gt_tops)

                n_sig = len(hits) + len(fps)
                acc = len(hits) / n_sig * 100 if n_sig > 0 else 0
                cov = len(hits) / len(gt_tops) * 100 if gt_tops else 0
                avg_lag = np.mean([abs(h['lag']) for h in hits]) if hits else float('nan')

                # Show what each signal date actually looks like
                sig_detail = ""
                for h in hits:
                    dd = measure_drawdown_after(pack, h['signal'], 60)
                    sig_detail += f" HIT@{h['signal'].date()}(lag={h['lag']:+d}d,dd={dd:.0f}%)"
                for fp in fps:
                    dd = measure_drawdown_after(pack, fp, 60)
                    sig_detail += f" FP@{fp.date()}(dd={dd:.0f}%)"
                for m in misses:
                    sig_detail += f" MISS@{m.date()}"

                flag = " ***" if acc >= 75 and cov >= 50 else ""
                print(f"    th={th:3d}: {len(hits)}/{len(gt_tops)} hits, {len(fps)} FP, "
                      f"acc={acc:.0f}%, cov={cov:.0f}%, lag={avg_lag:.0f}d{flag}")
                if sig_detail:
                    print(f"           {sig_detail.strip()}")


# ══════════════════════════════════════════════════════════════════════
# PART 2: Failsafe Markdown Detector
# ══════════════════════════════════════════════════════════════════════

def test_failsafe_detectors():
    print("\n" + "=" * 80)
    print("  PART 2: Failsafe Markdown Detectors")
    print("  (Late exit if primary top signal missed — better -10% than -40%)")
    print("=" * 80)

    for coin in ['BTC', 'ETH', 'SOL']:
        print(f"\n{'─' * 60}")
        print(f"  {coin}")
        print(f"{'─' * 60}")

        try:
            pack = V13SignalPack(coin)
        except ValueError as e:
            print(f"  SKIP: {e}")
            continue

        gt_md = [pd.Timestamp(d) for d, t in GROUND_TRUTH[coin] if t == 'markdown_start']
        gt_tops = [pd.Timestamp(d) for d, t in GROUND_TRUTH[coin] if t == 'markup_end']
        daily = pack.daily

        # ── Failsafe A: Price below BMSB for N days sustained ──
        print(f"\n  Failsafe A: BMSB Sustained Break")
        for days_below in [7, 10, 14, 21]:
            signal_dates = []
            check_dates = pd.date_range('2024-06-01', daily.index[-1], freq='3D')
            for d in check_dates:
                if d > daily.index[-1]:
                    break
                weeks = days_below / 7
                if pack.bmsb.sustained_below(d, weeks=weeks):
                    if not signal_dates or (d - signal_dates[-1]).days > 30:
                        signal_dates.append(d)

            hits, misses, fps = match_signals(signal_dates, gt_md, tolerance=35)
            n_sig = len(hits) + len(fps)
            acc = len(hits) / n_sig * 100 if n_sig > 0 else 0

            detail = ""
            for h in hits:
                # How much did we lose vs the top?
                top_before = [t for t in gt_tops if t < h['gt']]
                if top_before:
                    top_price = daily.loc[daily.index <= top_before[-1], 'close'].iloc[-1]
                    sig_price = daily.loc[daily.index <= h['signal'], 'close'].iloc[-1]
                    loss_from_top = (sig_price - top_price) / top_price * 100
                    dd_after = measure_drawdown_after(pack, h['signal'], 90)
                    detail += f" HIT@{h['signal'].date()} loss_from_top={loss_from_top:+.1f}% dd_avoided={dd_after:.0f}%"
            for fp in fps:
                dd = measure_drawdown_after(pack, fp, 60)
                detail += f" FP@{fp.date()} dd_after={dd:.0f}%"

            print(f"    {days_below}d below: {len(hits)}/{len(gt_md)} hits, {len(fps)} FP, acc={acc:.0f}%")
            if detail:
                print(f"           {detail.strip()}")

        # ── Failsafe B: CFGI drops below threshold + declining ──
        print(f"\n  Failsafe B: CFGI Collapse (was >60, now <threshold)")
        for drop_to in [35, 30, 25, 20]:
            signal_dates = []
            check_dates = pd.date_range('2024-06-01', daily.index[-1], freq='3D')
            prev_above = False
            for d in check_dates:
                v = pack.cfgi.value_at(d)
                if np.isnan(v):
                    continue
                if v > 60:
                    prev_above = True
                elif prev_above and v < drop_to:
                    if not signal_dates or (d - signal_dates[-1]).days > 30:
                        signal_dates.append(d)
                    prev_above = False

            hits, misses, fps = match_signals(signal_dates, gt_md, tolerance=35)
            n_sig = len(hits) + len(fps)
            acc = len(hits) / n_sig * 100 if n_sig > 0 else 0

            detail = ""
            for h in hits:
                top_before = [t for t in gt_tops if t < h['gt']]
                if top_before:
                    top_price = daily.loc[daily.index <= top_before[-1], 'close'].iloc[-1]
                    sig_price = daily.loc[daily.index <= h['signal'], 'close'].iloc[-1]
                    loss_from_top = (sig_price - top_price) / top_price * 100
                    dd_after = measure_drawdown_after(pack, h['signal'], 90)
                    detail += f" HIT@{h['signal'].date()} loss={loss_from_top:+.1f}% dd_avoided={dd_after:.0f}%"
            for fp in fps:
                dd = measure_drawdown_after(pack, fp, 60)
                detail += f" FP@{fp.date()} dd={dd:.0f}%"

            print(f"    was>60 now<{drop_to}: {len(hits)}/{len(gt_md)} hits, {len(fps)} FP, acc={acc:.0f}%")
            if detail:
                print(f"           {detail.strip()}")

        # ── Failsafe C: Daily SMA50 death cross (price below SMA50 + SMA50 declining) ──
        print(f"\n  Failsafe C: SMA50 Death Cross (price < SMA50 + slope neg for N days)")
        for confirm_days in [3, 5, 7, 10]:
            signal_dates = []
            # Check if price has been below SMA50 with neg slope for N consecutive days
            if 'sma50' not in daily.columns:
                print(f"    No SMA50 in daily data")
                break

            below_count = 0
            for i in range(len(daily)):
                if daily.index[i] < pd.Timestamp('2024-06-01'):
                    continue
                price = daily['close'].iloc[i]
                sma50 = daily['sma50'].iloc[i]
                if pd.isna(sma50):
                    below_count = 0
                    continue
                slope = pack.structure.sma50_slope_at(daily.index[i], 10)
                if price < sma50 and (not np.isnan(slope)) and slope < 0:
                    below_count += 1
                    if below_count == confirm_days:
                        d = daily.index[i]
                        if not signal_dates or (d - signal_dates[-1]).days > 30:
                            signal_dates.append(d)
                else:
                    below_count = 0

            hits, misses, fps = match_signals(signal_dates, gt_md, tolerance=35)
            n_sig = len(hits) + len(fps)
            acc = len(hits) / n_sig * 100 if n_sig > 0 else 0

            detail = ""
            for h in hits:
                top_before = [t for t in gt_tops if t < h['gt']]
                if top_before:
                    top_price = daily.loc[daily.index <= top_before[-1], 'close'].iloc[-1]
                    sig_price = daily.loc[daily.index <= h['signal'], 'close'].iloc[-1]
                    loss_from_top = (sig_price - top_price) / top_price * 100
                    dd_after = measure_drawdown_after(pack, h['signal'], 90)
                    detail += f" HIT@{h['signal'].date()} loss={loss_from_top:+.1f}% dd_avoided={dd_after:.0f}%"
            for fp in fps:
                dd = measure_drawdown_after(pack, fp, 60)
                detail += f" FP@{fp.date()} dd={dd:.0f}%"

            print(f"    {confirm_days}d confirm: {len(hits)}/{len(gt_md)} hits, {len(fps)} FP, acc={acc:.0f}%")
            if detail:
                print(f"           {detail.strip()}")

        # ── Failsafe D: Composite (BMSB break + CFGI declining + SMA50 neg) ──
        print(f"\n  Failsafe D: Composite (2+ of: BMSB below, CFGI<40, SMA50 death cross)")
        for min_signals in [2, 3]:
            signal_dates = []
            check_dates = pd.date_range('2024-06-01', daily.index[-1], freq='3D')
            for d in check_dates:
                if d > daily.index[-1]:
                    break
                score = 0
                # BMSB below
                if pack.bmsb.status_at(d) == 'BELOW':
                    score += 1
                # CFGI < 40
                v = pack.cfgi.value_at(d)
                if not np.isnan(v) and v < 40:
                    score += 1
                # SMA50 slope negative
                slope = pack.structure.sma50_slope_at(d, 10)
                if not np.isnan(slope) and slope < 0:
                    score += 1

                if score >= min_signals:
                    if not signal_dates or (d - signal_dates[-1]).days > 30:
                        signal_dates.append(d)

            hits, misses, fps = match_signals(signal_dates, gt_md, tolerance=35)
            n_sig = len(hits) + len(fps)
            acc = len(hits) / n_sig * 100 if n_sig > 0 else 0

            detail = ""
            for h in hits:
                top_before = [t for t in gt_tops if t < h['gt']]
                if top_before:
                    top_price = daily.loc[daily.index <= top_before[-1], 'close'].iloc[-1]
                    sig_price = daily.loc[daily.index <= h['signal'], 'close'].iloc[-1]
                    loss_from_top = (sig_price - top_price) / top_price * 100
                    dd_after = measure_drawdown_after(pack, h['signal'], 90)
                    detail += f" HIT@{h['signal'].date()} loss={loss_from_top:+.1f}% dd_avoided={dd_after:.0f}%"
            for fp in fps:
                dd = measure_drawdown_after(pack, fp, 60)
                detail += f" FP@{fp.date()} dd={dd:.0f}%"

            label = f"{min_signals}/3 signals"
            print(f"    {label}: {len(hits)}/{len(gt_md)} hits, {len(fps)} FP, acc={acc:.0f}%")
            if detail:
                print(f"           {detail.strip()}")

        # ── Failsafe E: 1W StochRSI crosses below 50 (momentum gone) ──
        print(f"\n  Failsafe E: 1W StochRSI K crosses below threshold (momentum collapse)")
        for th in [60, 50, 40, 30]:
            stoch = pack.stoch_1w
            # Find where K crosses below threshold
            df = stoch.df[stoch.df.index >= '2024-06-01']
            prev_k = df['K'].shift(1)
            crosses = df[(prev_k >= th) & (df['K'] < th)]
            signal_dates = []
            for d in crosses.index:
                if not signal_dates or (d - signal_dates[-1]).days > 30:
                    signal_dates.append(d)

            hits, misses, fps = match_signals(signal_dates, gt_md, tolerance=35)
            n_sig = len(hits) + len(fps)
            acc = len(hits) / n_sig * 100 if n_sig > 0 else 0

            detail = ""
            for h in hits:
                top_before = [t for t in gt_tops if t < h['gt']]
                if top_before:
                    top_price = daily.loc[daily.index <= top_before[-1], 'close'].iloc[-1]
                    sig_price = daily.loc[daily.index <= h['signal'], 'close'].iloc[-1]
                    loss_from_top = (sig_price - top_price) / top_price * 100
                    dd_after = measure_drawdown_after(pack, h['signal'], 90)
                    detail += f" HIT@{h['signal'].date()} loss={loss_from_top:+.1f}% dd_avoided={dd_after:.0f}%"
            for fp in fps:
                dd = measure_drawdown_after(pack, fp, 60)
                detail += f" FP@{fp.date()} dd={dd:.0f}%"

            print(f"    K<{th}: {len(hits)}/{len(gt_md)} hits, {len(fps)} FP, acc={acc:.0f}%")
            if detail:
                print(f"           {detail.strip()}")


if __name__ == '__main__':
    sweep_ob_thresholds()
    test_failsafe_detectors()
