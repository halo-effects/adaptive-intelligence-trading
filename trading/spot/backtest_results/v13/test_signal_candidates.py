"""
V13 Signal Candidate Evaluation — Full Test Matrix
Tests all untested candidates from v13-gate-test-plan.md Tests 2-6.
Evaluates each signal's ability to predict phase transitions on ETH, BTC, SOL.

For each signal we measure:
  - Precision: % of times signal fires that correspond to a real transition
  - Recall: % of real transitions the signal catches
  - Latency: days between actual transition and signal fire
  - False positive rate: fires during wrong phase
"""
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from v13_signals import V13SignalPack
import pandas as pd
import numpy as np
from datetime import timedelta

# ═══════════════════════════════════════════════════════════
# GROUND TRUTH: Known phase transitions from chart inspection
# ═══════════════════════════════════════════════════════════

GROUND_TRUTH = {
    'BTC': {
        'markup_starts': [
            ('2020-10-01', 'Post-halving accumulation breakout'),
            ('2023-01-09', 'Bear market bottom, recovery begins'),
            ('2024-01-29', 'ETF approval rally'),
            ('2024-06-04', 'Post-halving accumulation'),
            ('2025-06-24', 'Recovery rally'),
        ],
        'tops': [
            ('2021-01-25', 'First leg top ~$42K'),
            ('2021-04-27', 'Second leg, pre-China ban'),
            ('2024-04-15', 'ETF sell-the-news'),
            ('2025-01-12', '$109K top'),
        ],
        'markdown_starts': [
            ('2022-05-09', 'Luna crash accelerates'),
            ('2022-08-19', 'Bear continuation'),
            ('2023-08-22', 'Summer selloff'),
            ('2025-02-26', 'Post-ATH correction'),
        ],
        'corrections': [  # NOT real tops — should not trigger distribution signals
            ('2021-09-07', 'El Salvador dip, recovered'),
            ('2024-08-05', 'Yen carry trade unwind, recovered'),
        ],
    },
    'ETH': {
        'markup_starts': [
            ('2020-10-05', 'DeFi summer recovery'),
            ('2022-09-27', 'Bear market bottom attempt'),
            ('2023-10-22', 'Recovery rally begins'),
            ('2024-10-15', 'Q4 rally'),
        ],
        'tops': [
            ('2021-03-07', '1W K<50 failsafe exit'),
            ('2021-11-21', 'Nov 2021 blow-off top'),
            ('2024-04-15', 'Rejection at $3.6K'),
            ('2024-12-22', '1W OB85 exit'),
        ],
        'markdown_starts': [
            ('2022-03-04', 'Bear continuation'),
            ('2025-02-02', 'Post-top decline'),
            ('2025-11-12', 'Year-end decline'),
        ],
        'corrections': [
            ('2021-05-26', 'China ban dip — BUT this was markup_fail'),
            ('2024-06-16', 'Summer range — BUT this was markup_fail'),
        ],
    },
    'SOL': {
        'markup_starts': [
            ('2023-10-02', 'Big recovery rally $23→$100'),
            ('2024-04-18', 'Spring rally'),
            ('2025-08-05', 'Recovery'),
        ],
        'tops': [
            ('2024-01-09', '2W OB93 exit at $99'),
            ('2025-09-28', '1W OB85 exit'),
        ],
        'markdown_starts': [
            ('2021-07-20', 'Early bear'),
            ('2024-08-04', 'Summer selloff'),
            ('2025-10-17', 'Year-end decline'),
        ],
        'corrections': [
            ('2022-03-28', 'Bear bounce — was MARKUP_FAIL'),
            ('2022-07-29', 'Bear bounce — was MARKUP_FAIL'),
            ('2022-11-05', 'FTX collapse — was MARKUP_FAIL'),
        ],
    },
}


def compute_all_signals(pack):
    """Compute all candidate signals for a coin. Returns DataFrame with daily signals."""
    daily = pack.daily.copy()
    
    # Already computed in daily: close, high, low, open, volume
    # sma50, sma200, adx, consec_hh_hl, consec_lh_ll, price_vs_sma200, sma50_slope
    
    signals = pd.DataFrame(index=daily.index)
    signals['close'] = daily['close']
    
    # ── Test 2: Ranging Detection Signals ──
    
    # ADX < 20 (already in engine)
    signals['adx'] = daily['adx']
    signals['adx_ranging'] = daily['adx'] < 20
    
    # Bollinger Band Width (if not computed, compute now)
    if 'bb_width' not in daily.columns:
        bb_mid = daily['close'].rolling(20).mean()
        bb_std = daily['close'].rolling(20).std()
        signals['bb_width'] = (2 * bb_std) / bb_mid * 100  # as percentage
    else:
        signals['bb_width'] = daily['bb_width']
    
    # BB width low = ranging (below 25th percentile of rolling 60d)
    signals['bb_narrow'] = signals['bb_width'] < signals['bb_width'].rolling(60).quantile(0.25)
    
    # ATR % (volatility as % of price)
    if 'atr' not in daily.columns:
        tr = pd.DataFrame({
            'hl': daily['high'] - daily['low'],
            'hc': abs(daily['high'] - daily['close'].shift(1)),
            'lc': abs(daily['low'] - daily['close'].shift(1))
        }).max(axis=1)
        signals['atr_pct'] = tr.rolling(14).mean() / daily['close'] * 100
    else:
        signals['atr_pct'] = daily['atr'] / daily['close'] * 100
    
    # Low ATR = ranging
    signals['atr_low'] = signals['atr_pct'] < signals['atr_pct'].rolling(60).quantile(0.25)
    
    # Price between SMA50 and SMA200 with flat SMAs
    if 'sma50' in daily.columns and 'sma200' in daily.columns:
        between = ((daily['close'] > daily[['sma50', 'sma200']].min(axis=1)) & 
                   (daily['close'] < daily[['sma50', 'sma200']].max(axis=1)))
        sma50_flat = abs(daily.get('sma50_slope', pd.Series(0, index=daily.index))) < 0.5
        signals['sma_sandwich'] = between & sma50_flat
    
    # CFGI stability (change < ±5 for 5 days)
    cfgi_vals = pd.Series(index=daily.index, dtype=float)
    for idx in daily.index:
        v = pack.cfgi.value_at(idx)
        cfgi_vals[idx] = v
    signals['cfgi'] = cfgi_vals
    signals['cfgi_change'] = cfgi_vals.diff().abs()
    signals['cfgi_stable'] = signals['cfgi_change'].rolling(5).max() < 5
    
    # ── Test 3: Markup Confirmation Signals ──
    
    # Golden cross (SMA50 > SMA200)
    if 'sma50' in daily.columns and 'sma200' in daily.columns:
        signals['golden_cross'] = daily['sma50'] > daily['sma200']
        # Just crossed (was below, now above)
        signals['golden_cross_new'] = signals['golden_cross'] & ~signals['golden_cross'].shift(1).fillna(False)
    
    # HH_HL streak (already in engine)
    signals['hh_hl'] = daily.get('consec_hh_hl', 0)
    signals['hh_hl_2'] = signals['hh_hl'] >= 2
    
    # CFGI rising + above 50
    signals['cfgi_bullish'] = (cfgi_vals > 50) & (cfgi_vals > cfgi_vals.shift(7))
    
    # Price > SMA50
    if 'sma50' in daily.columns:
        signals['above_sma50'] = daily['close'] > daily['sma50']
    
    # Volume expansion (above 20d average)
    if 'volume' in daily.columns:
        vol_avg = daily['volume'].rolling(20).mean()
        signals['volume_expansion'] = daily['volume'] > vol_avg * 1.5
    
    # Price > SMA200
    if 'sma200' in daily.columns:
        signals['above_sma200'] = daily['close'] > daily['sma200']
    
    # ── Test 4+5: Distribution / Markdown Signals ──
    
    # Death cross (SMA50 < SMA200)
    if 'sma50' in daily.columns and 'sma200' in daily.columns:
        signals['death_cross'] = daily['sma50'] < daily['sma200']
        signals['death_cross_new'] = signals['death_cross'] & ~signals['death_cross'].shift(1).fillna(False)
    
    # LH_LL streak (just added to engine)
    signals['lh_ll'] = daily.get('consec_lh_ll', 0)
    signals['lh_ll_2'] = signals['lh_ll'] >= 2
    
    # CFGI declining from greed (was ≥70, now <50)
    cfgi_max_30d = cfgi_vals.rolling(30).max()
    signals['cfgi_bearish'] = (cfgi_max_30d >= 70) & (cfgi_vals < 50)
    
    # Price < SMA50
    if 'sma50' in daily.columns:
        signals['below_sma50'] = daily['close'] < daily['sma50']
    
    # Price < SMA200
    if 'sma200' in daily.columns:
        signals['below_sma200'] = daily['close'] < daily['sma200']
    
    # SMA50 declining for 5+ days
    if 'sma50_slope' in daily.columns:
        neg_slope = daily['sma50_slope'] < 0
        streak = neg_slope.astype(int)
        # Count consecutive days of negative slope
        groups = (streak != streak.shift()).cumsum()
        signals['sma50_decline_streak'] = streak.groupby(groups).cumsum()
        signals['sma50_declining_5d'] = signals['sma50_decline_streak'] >= 5
    
    # CFGI < 30 (deep fear)
    signals['cfgi_fear'] = cfgi_vals < 30
    
    # CFGI < 40 (moderate fear)
    signals['cfgi_below40'] = cfgi_vals < 40
    
    # ADX > 20 (trending - already in engine)
    signals['adx_trending'] = daily['adx'] > 20
    
    # ADX > 25 (strongly trending)
    signals['adx_strong'] = daily['adx'] > 25
    
    # ── Test 6: Composite Correction vs Distribution ──
    
    # Composite: multiple bearish signals
    signals['bear_composite_3'] = (
        signals.get('lh_ll_2', False) & 
        signals.get('below_sma50', False) & 
        signals.get('adx_trending', False)
    )
    
    signals['bear_composite_4'] = (
        signals.get('lh_ll_2', False) & 
        signals.get('below_sma50', False) & 
        signals.get('adx_trending', False) & 
        (signals.get('cfgi_fear', False) | signals.get('cfgi_below40', False))
    )
    
    # Composite: multiple bullish signals
    signals['bull_composite_3'] = (
        signals.get('hh_hl_2', False) & 
        signals.get('above_sma50', False) & 
        signals.get('adx_trending', False)
    )
    
    return signals


def evaluate_signal(signals, ground_truth_dates, signal_name, window_days=30):
    """
    Evaluate how well a signal predicts ground truth transition dates.
    
    Returns:
        hits: transitions where signal fired within window
        misses: transitions where signal didn't fire
        latency: average days between transition and signal fire
        false_fires: signal fires outside any transition window
    """
    sig = signals[signal_name].fillna(False)
    
    hits = []
    misses = []
    latencies = []
    
    for date_str, desc in ground_truth_dates:
        target = pd.Timestamp(date_str)
        window_start = target - timedelta(days=window_days)
        window_end = target + timedelta(days=window_days)
        
        # Check if signal fired within window
        window_mask = (signals.index >= window_start) & (signals.index <= window_end)
        window_fires = sig[window_mask]
        
        if window_fires.any():
            first_fire = window_fires[window_fires].index[0]
            latency = (first_fire - target).days  # negative = early, positive = late
            hits.append((date_str, desc, latency))
            latencies.append(latency)
        else:
            misses.append((date_str, desc))
    
    # Count total signal fires outside any transition window
    all_windows = pd.Series(False, index=signals.index)
    for date_str, desc in ground_truth_dates:
        target = pd.Timestamp(date_str)
        ws = target - timedelta(days=window_days)
        we = target + timedelta(days=window_days)
        all_windows |= (signals.index >= ws) & (signals.index <= we)
    
    total_fires = sig.sum()
    fires_in_window = sig[all_windows].sum()
    false_fires = total_fires - fires_in_window
    
    precision = fires_in_window / total_fires * 100 if total_fires > 0 else 0
    recall = len(hits) / (len(hits) + len(misses)) * 100 if (len(hits) + len(misses)) > 0 else 0
    avg_latency = np.mean(latencies) if latencies else float('nan')
    
    return {
        'hits': hits,
        'misses': misses,
        'precision': precision,
        'recall': recall,
        'avg_latency': avg_latency,
        'total_fires': int(total_fires),
        'false_fires': int(false_fires),
    }


def evaluate_correction_filter(signals, corrections, signal_name, window_days=30):
    """Check if a signal fires during known corrections (should NOT fire)."""
    sig = signals[signal_name].fillna(False)
    false_alarms = []
    correctly_silent = []
    
    for date_str, desc in corrections:
        target = pd.Timestamp(date_str)
        window_start = target - timedelta(days=window_days)
        window_end = target + timedelta(days=window_days)
        
        window_mask = (signals.index >= window_start) & (signals.index <= window_end)
        window_fires = sig[window_mask]
        
        if window_fires.any():
            false_alarms.append((date_str, desc))
        else:
            correctly_silent.append((date_str, desc))
    
    return {
        'false_alarms': false_alarms,
        'correctly_silent': correctly_silent,
        'false_alarm_rate': len(false_alarms) / (len(false_alarms) + len(correctly_silent)) * 100 
            if (len(false_alarms) + len(correctly_silent)) > 0 else 0,
    }


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

COINS = ['ETH', 'BTC', 'SOL']

# Signal groups to test
MARKUP_SIGNALS = [
    ('hh_hl_2', 'HH_HL ≥ 2 (IN ENGINE)'),
    ('golden_cross', 'Golden Cross (SMA50 > SMA200)'),
    ('golden_cross_new', 'Golden Cross — new crossing'),
    ('cfgi_bullish', 'CFGI > 50 + rising 7d'),
    ('above_sma50', 'Price > SMA50'),
    ('above_sma200', 'Price > SMA200'),
    ('volume_expansion', 'Volume > 1.5× 20d avg'),
    ('bull_composite_3', 'HH_HL + above_SMA50 + ADX>20'),
]

MARKDOWN_SIGNALS = [
    ('lh_ll_2', 'LH_LL ≥ 2 (JUST ADDED)'),
    ('adx_trending', 'ADX > 20 (IN ENGINE)'),
    ('death_cross', 'Death Cross (SMA50 < SMA200)'),
    ('death_cross_new', 'Death Cross — new crossing'),
    ('cfgi_bearish', 'CFGI was ≥70, now <50'),
    ('cfgi_fear', 'CFGI < 30'),
    ('cfgi_below40', 'CFGI < 40'),
    ('below_sma50', 'Price < SMA50'),
    ('below_sma200', 'Price < SMA200'),
    ('sma50_declining_5d', 'SMA50 declining 5+ days'),
    ('bear_composite_3', 'LH_LL + below_SMA50 + ADX>20'),
    ('bear_composite_4', 'LH_LL + below_SMA50 + ADX>20 + CFGI<40'),
]

RANGING_SIGNALS = [
    ('adx_ranging', 'ADX < 20 (IN ENGINE)'),
    ('bb_narrow', 'BB Width below 25th pctile'),
    ('atr_low', 'ATR% below 25th pctile'),
    ('sma_sandwich', 'Price between SMAs + flat SMA50'),
    ('cfgi_stable', 'CFGI change < ±5 for 5d'),
]


for coin in COINS:
    pack = V13SignalPack(coin)
    signals = compute_all_signals(pack)
    gt = GROUND_TRUTH[coin]
    
    print(f"\n{'═'*120}")
    print(f"  {coin} — Signal Candidate Evaluation")
    print(f"{'═'*120}")
    
    # ── Test 3: Markup Confirmation ──
    print(f"\n  ── TEST 3: Markup Confirmation ──")
    print(f"  Ground truth: {len(gt['markup_starts'])} known markup starts")
    print(f"  {'Signal':<40} {'Recall':>7} {'Precision':>10} {'AvgLat':>7} {'Fires':>6} {'FP':>5} {'Details'}")
    print(f"  {'-'*40} {'-'*7} {'-'*10} {'-'*7} {'-'*6} {'-'*5} {'-'*40}")
    
    for sig_name, sig_desc in MARKUP_SIGNALS:
        if sig_name not in signals.columns:
            continue
        result = evaluate_signal(signals, gt['markup_starts'], sig_name)
        hits_str = ','.join([f"{h[0]}({h[2]:+d}d)" for h in result['hits']])
        misses_str = ','.join([m[0] for m in result['misses']])
        detail = f"H:[{hits_str}]" if result['hits'] else ""
        if result['misses']:
            detail += f" M:[{misses_str}]"
        print(f"  {sig_desc:<40} {result['recall']:>6.0f}% {result['precision']:>9.1f}% {result['avg_latency']:>+6.0f}d {result['total_fires']:>6} {result['false_fires']:>5} {detail}")
    
    # ── Test 5: Markdown Confirmation ──
    print(f"\n  ── TEST 5: Markdown Confirmation ──")
    print(f"  Ground truth: {len(gt['markdown_starts'])} known markdown starts")
    print(f"  {'Signal':<40} {'Recall':>7} {'Precision':>10} {'AvgLat':>7} {'Fires':>6} {'FP':>5} {'Details'}")
    print(f"  {'-'*40} {'-'*7} {'-'*10} {'-'*7} {'-'*6} {'-'*5} {'-'*40}")
    
    for sig_name, sig_desc in MARKDOWN_SIGNALS:
        if sig_name not in signals.columns:
            continue
        result = evaluate_signal(signals, gt['markdown_starts'], sig_name)
        hits_str = ','.join([f"{h[0]}({h[2]:+d}d)" for h in result['hits']])
        misses_str = ','.join([m[0] for m in result['misses']])
        detail = f"H:[{hits_str}]" if result['hits'] else ""
        if result['misses']:
            detail += f" M:[{misses_str}]"
        print(f"  {sig_desc:<40} {result['recall']:>6.0f}% {result['precision']:>9.1f}% {result['avg_latency']:>+6.0f}d {result['total_fires']:>6} {result['false_fires']:>5} {detail}")
    
    # ── Test 6: Correction Filter ──
    if gt.get('corrections'):
        print(f"\n  ── TEST 6: Correction Filter (should NOT fire) ──")
        print(f"  Known corrections (false positives are BAD): {len(gt['corrections'])}")
        print(f"  {'Signal':<40} {'FalseAlarm%':>11} {'Alarms':<50}")
        print(f"  {'-'*40} {'-'*11} {'-'*50}")
        
        for sig_name, sig_desc in MARKDOWN_SIGNALS:
            if sig_name not in signals.columns:
                continue
            result = evaluate_correction_filter(signals, gt['corrections'], sig_name)
            alarms = ','.join([f[0] for f in result['false_alarms']])
            print(f"  {sig_desc:<40} {result['false_alarm_rate']:>10.0f}% {alarms:<50}")


# ═══════════════════════════════════════════════════════════
# CROSS-COIN SUMMARY
# ═══════════════════════════════════════════════════════════

print(f"\n{'═'*120}")
print(f"  CROSS-COIN SUMMARY — Best Signal Candidates")
print(f"{'═'*120}")
print(f"""
  Scoring: Recall (weight 40%) + Precision (20%) + Low false alarm on corrections (40%)
  The ideal signal has: high recall, decent precision, zero false alarms on corrections.
  
  Current engine gates:
    MARKUP:   HH_HL ≥ 2 + Fib support
    MARKDOWN: LH_LL ≥ 2 + ADX > 20 + Fib break
  
  Question: Which untested candidates should be ADDED as additional gates?
""")
