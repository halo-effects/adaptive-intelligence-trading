"""
Build weekly candles from daily data and compute weekly structure signals.
Weekly HH/HL and LH/LL — the missing piece from Test 6.
"""
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from v13_signals import V13SignalPack
import pandas as pd
import numpy as np


def build_weekly_candles(daily):
    """Aggregate daily OHLCV into weekly candles (Mon-Sun weeks)."""
    weekly = daily.resample('W-SUN').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
    }).dropna(subset=['open'])
    return weekly


def compute_weekly_structure(weekly):
    """Compute consecutive higher highs/higher lows and lower highs/lower lows on weekly candles."""
    weekly = weekly.copy()
    
    # Weekly HH/HL detection
    hh = weekly['high'] > weekly['high'].shift(1)  # Higher high
    hl = weekly['low'] > weekly['low'].shift(1)     # Higher low
    hh_hl = hh & hl  # Both conditions
    
    # Weekly LH/LL detection
    lh = weekly['high'] < weekly['high'].shift(1)  # Lower high
    ll = weekly['low'] < weekly['low'].shift(1)     # Lower low
    lh_ll = lh & ll  # Both conditions
    
    # Count consecutive streaks
    weekly['weekly_hh_hl'] = 0
    weekly['weekly_lh_ll'] = 0
    
    hh_streak = 0
    ll_streak = 0
    for i in range(len(weekly)):
        if hh_hl.iloc[i]:
            hh_streak += 1
        else:
            hh_streak = 0
        if lh_ll.iloc[i]:
            ll_streak += 1
        else:
            ll_streak = 0
        weekly.iloc[i, weekly.columns.get_loc('weekly_hh_hl')] = hh_streak
        weekly.iloc[i, weekly.columns.get_loc('weekly_lh_ll')] = ll_streak
    
    # Also compute: weekly bearish/bullish engulfing
    weekly['body'] = weekly['close'] - weekly['open']
    weekly['prev_body'] = weekly['body'].shift(1)
    weekly['bearish_engulf'] = (
        (weekly['prev_body'] > 0) &  # Prev week was bullish
        (weekly['body'] < 0) &        # This week bearish
        (weekly['open'] >= weekly['close'].shift(1)) &  # Opens at/above prev close
        (weekly['close'] <= weekly['open'].shift(1))     # Closes at/below prev open
    )
    weekly['bullish_engulf'] = (
        (weekly['prev_body'] < 0) &  # Prev week was bearish
        (weekly['body'] > 0) &        # This week bullish
        (weekly['open'] <= weekly['close'].shift(1)) &  # Opens at/below prev close
        (weekly['close'] >= weekly['open'].shift(1))     # Closes at/above prev open
    )
    
    # Weekly SMA20 (roughly 5-month trend)
    weekly['wsma20'] = weekly['close'].rolling(20).mean()
    weekly['above_wsma20'] = weekly['close'] > weekly['wsma20']
    
    return weekly


def map_weekly_to_daily(daily, weekly, columns):
    """Map weekly signal values to daily dates (forward-fill within each week)."""
    result = pd.DataFrame(index=daily.index)
    for col in columns:
        weekly_series = weekly[col]
        vals = []
        for idx in daily.index:
            mask = weekly.index <= idx
            if mask.any():
                vals.append(weekly_series[mask].iloc[-1])
            else:
                vals.append(np.nan)
        result[col] = vals
    return result


# ═══════════════════════════════════════════════════════════
# Test weekly signals against ground truth
# ═══════════════════════════════════════════════════════════

from test_signal_candidates import GROUND_TRUTH, evaluate_signal, evaluate_correction_filter
from datetime import timedelta

COINS = ['ETH', 'BTC', 'SOL']

for coin in COINS:
    pack = V13SignalPack(coin)
    daily = pack.daily
    
    # Build weekly
    weekly = build_weekly_candles(daily)
    weekly = compute_weekly_structure(weekly)
    
    print(f"\n{'═'*120}")
    print(f"  {coin} — Weekly Structure Signals")
    print(f"{'═'*120}")
    
    print(f"  Weekly candles: {len(weekly)} (from {weekly.index[0].strftime('%Y-%m-%d')} to {weekly.index[-1].strftime('%Y-%m-%d')})")
    
    # Map to daily for evaluation
    weekly_cols = ['weekly_hh_hl', 'weekly_lh_ll', 'bearish_engulf', 'bullish_engulf', 'above_wsma20']
    mapped = map_weekly_to_daily(daily, weekly, weekly_cols)
    
    # Build signal DataFrame with boolean columns
    signals = pd.DataFrame(index=daily.index)
    signals['close'] = daily['close']
    signals['w_hh_hl_1'] = mapped['weekly_hh_hl'] >= 1
    signals['w_hh_hl_2'] = mapped['weekly_hh_hl'] >= 2
    signals['w_lh_ll_1'] = mapped['weekly_lh_ll'] >= 1
    signals['w_lh_ll_2'] = mapped['weekly_lh_ll'] >= 2
    signals['w_bearish_engulf'] = mapped['bearish_engulf'].fillna(False).astype(bool)
    signals['w_bullish_engulf'] = mapped['bullish_engulf'].fillna(False).astype(bool)
    signals['w_above_sma20'] = mapped['above_wsma20'].fillna(False).astype(bool)
    signals['w_below_sma20'] = ~signals['w_above_sma20']
    
    # Also add daily signals for composite testing
    signals['d_lh_ll_2'] = daily.get('consec_lh_ll', pd.Series(0, index=daily.index)) >= 2
    signals['d_hh_hl_2'] = daily.get('consec_hh_hl', pd.Series(0, index=daily.index)) >= 2
    signals['adx_20'] = daily['adx'] > 20
    
    # Composites: daily + weekly
    signals['d_lh_ll_AND_w_lh_ll'] = signals['d_lh_ll_2'] & signals['w_lh_ll_1']
    signals['d_lh_ll_AND_w_lh_ll_2'] = signals['d_lh_ll_2'] & signals['w_lh_ll_2']
    signals['d_hh_hl_AND_w_hh_hl'] = signals['d_hh_hl_2'] & signals['w_hh_hl_1']
    signals['full_markdown'] = signals['d_lh_ll_2'] & signals['w_lh_ll_1'] & signals['adx_20']
    signals['full_markdown_w2'] = signals['d_lh_ll_2'] & signals['w_lh_ll_2'] & signals['adx_20']
    
    gt = GROUND_TRUTH[coin]
    
    # ── Markup signals ──
    print(f"\n  ── MARKUP Confirmation (weekly) ──")
    markup_sigs = [
        ('w_hh_hl_1', 'Weekly HH+HL ≥ 1'),
        ('w_hh_hl_2', 'Weekly HH+HL ≥ 2'),
        ('w_bullish_engulf', 'Weekly bullish engulfing'),
        ('w_above_sma20', 'Price > Weekly SMA20'),
        ('d_hh_hl_AND_w_hh_hl', 'Daily HH_HL + Weekly HH_HL'),
    ]
    print(f"  {'Signal':<40} {'Recall':>7} {'Precision':>10} {'AvgLat':>7} {'Fires':>6} {'FP':>5}")
    print(f"  {'-'*40} {'-'*7} {'-'*10} {'-'*7} {'-'*6} {'-'*5}")
    for sig_name, sig_desc in markup_sigs:
        if sig_name not in signals.columns:
            continue
        r = evaluate_signal(signals, gt['markup_starts'], sig_name)
        print(f"  {sig_desc:<40} {r['recall']:>6.0f}% {r['precision']:>9.1f}% {r['avg_latency']:>+6.0f}d {r['total_fires']:>6} {r['false_fires']:>5}")
    
    # ── Markdown signals ──
    print(f"\n  ── MARKDOWN Confirmation (weekly) ──")
    markdown_sigs = [
        ('w_lh_ll_1', 'Weekly LH+LL ≥ 1'),
        ('w_lh_ll_2', 'Weekly LH+LL ≥ 2'),
        ('w_bearish_engulf', 'Weekly bearish engulfing'),
        ('w_below_sma20', 'Price < Weekly SMA20'),
        ('d_lh_ll_AND_w_lh_ll', 'Daily LH_LL + Weekly LH_LL≥1'),
        ('d_lh_ll_AND_w_lh_ll_2', 'Daily LH_LL + Weekly LH_LL≥2'),
        ('full_markdown', 'Daily LH_LL + Weekly LH_LL≥1 + ADX>20'),
        ('full_markdown_w2', 'Daily LH_LL + Weekly LH_LL≥2 + ADX>20'),
    ]
    print(f"  {'Signal':<40} {'Recall':>7} {'Precision':>10} {'AvgLat':>7} {'Fires':>6} {'FP':>5}")
    print(f"  {'-'*40} {'-'*7} {'-'*10} {'-'*7} {'-'*6} {'-'*5}")
    for sig_name, sig_desc in markdown_sigs:
        if sig_name not in signals.columns:
            continue
        r = evaluate_signal(signals, gt['markdown_starts'], sig_name)
        print(f"  {sig_desc:<40} {r['recall']:>6.0f}% {r['precision']:>9.1f}% {r['avg_latency']:>+6.0f}d {r['total_fires']:>6} {r['false_fires']:>5}")
    
    # ── Correction filter ──
    if gt.get('corrections'):
        print(f"\n  ── CORRECTION FILTER (should NOT fire) ──")
        all_sigs = [
            ('d_lh_ll_2', 'Daily LH_LL ≥ 2 (current)'),
            ('w_lh_ll_1', 'Weekly LH+LL ≥ 1'),
            ('w_lh_ll_2', 'Weekly LH+LL ≥ 2'),
            ('d_lh_ll_AND_w_lh_ll', 'Daily LH_LL + Weekly LH_LL≥1'),
            ('d_lh_ll_AND_w_lh_ll_2', 'Daily LH_LL + Weekly LH_LL≥2'),
            ('full_markdown', 'Daily LH_LL + Weekly LH_LL≥1 + ADX>20'),
            ('full_markdown_w2', 'Daily LH_LL + Weekly LH_LL≥2 + ADX>20'),
            ('w_bearish_engulf', 'Weekly bearish engulfing'),
        ]
        print(f"  {'Signal':<45} {'FalseAlarm%':>11} {'Alarms'}")
        print(f"  {'-'*45} {'-'*11} {'-'*50}")
        for sig_name, sig_desc in all_sigs:
            if sig_name not in signals.columns:
                continue
            r = evaluate_correction_filter(signals, gt['corrections'], sig_name)
            alarms = ','.join([f[0] for f in r['false_alarms']])
            print(f"  {sig_desc:<45} {r['false_alarm_rate']:>10.0f}% {alarms}")
