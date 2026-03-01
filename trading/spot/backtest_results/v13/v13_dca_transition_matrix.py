"""
V13 DCA Transition Signal Matrix

Tests all combinations of signals for DCA → MARKUP and DCA → MARKDOWN transitions.
Focus: which signal combo detects transitions earliest with fewest false positives?

Signals tested:
  S1: HVF Composite (volume + price compression)
  S2: Channel Breakout (retest-confirmed)
  S3: Channel Breakout (run without retest)
  S4: 2W StochRSI OS exit (existing V13 primary)
  S5: 1W StochRSI direction (K slope)
  S6: BMSB status (above/below)
  S7: SMA50 slope (positive/negative)
  S8: Daily HH/HL or LH/LL structure
  S9: CFGI level (fear/neutral/greed)
  S10: ADX (trend strength)
  S11: Harmonic pattern (bullish/bearish ABCD)

Scoring: accuracy (40%), false positive rate (30%), lead time (15%), coverage (15%)
"""
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from itertools import combinations
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
from channel_breakout import ChannelBreakout
from test_hvf_daily import (
    composite_hvf_score, detect_swing_points, hvf_harmonic_pattern
)


def fibonacci_levels(df, swing_lookback=20):
    """Compute Fibonacci retracement/extension levels from the last major swing.
    Returns daily Series of fib zone status: 'at_support', 'at_resistance', 
    'above_618', 'below_618', etc."""
    swings = detect_swing_points(df, lookback=swing_lookback)
    
    # For each day, find the last significant swing high and low
    fib_support = pd.Series(False, index=df.index)  # Price near a fib support (0.382-0.786 retrace)
    fib_resist = pd.Series(False, index=df.index)   # Price near a fib resistance (extension zone)
    fib_golden = pd.Series(False, index=df.index)   # Price near 0.618 retracement specifically
    fib_bounce = pd.Series(False, index=df.index)   # Price bouncing off fib level (held + reversal)
    fib_break = pd.Series(False, index=df.index)    # Price breaking through fib level (continuation)
    
    FIB_RATIOS = [0.236, 0.382, 0.5, 0.618, 0.786]
    EXT_RATIOS = [1.0, 1.272, 1.618, 2.0, 2.618]
    TOLERANCE = 0.02  # 2% proximity to fib level
    
    for i in range(60, len(df)):
        date = df.index[i]
        price = df['close'].iloc[i]
        
        # Find last swing high and low before this date
        recent_swings = [s for s in swings if s['idx'] < i and s['idx'] > i - 120]
        if len(recent_swings) < 2:
            continue
        
        # Get the last major swing high and low
        swing_highs = [s for s in recent_swings if s['type'] == 'high']
        swing_lows = [s for s in recent_swings if s['type'] == 'low']
        
        if not swing_highs or not swing_lows:
            continue
        
        last_high = max(swing_highs, key=lambda s: s['price'])
        last_low = min(swing_lows, key=lambda s: s['price'])
        
        swing_range = last_high['price'] - last_low['price']
        if swing_range <= 0:
            continue
        
        # Compute retracement levels (from high down)
        retrace_levels = {r: last_high['price'] - swing_range * r for r in FIB_RATIOS}
        # Extension levels (from low up)
        ext_levels = {r: last_low['price'] + swing_range * r for r in EXT_RATIOS}
        
        # Check proximity to retracement levels (support zones)
        for ratio, level in retrace_levels.items():
            if level > 0 and abs(price - level) / level < TOLERANCE:
                fib_support.iloc[i] = True
                if abs(ratio - 0.618) < 0.01:
                    fib_golden.iloc[i] = True
        
        # Check proximity to extension levels (resistance zones)
        for ratio, level in ext_levels.items():
            if level > 0 and abs(price - level) / level < TOLERANCE:
                fib_resist.iloc[i] = True
        
        # Fib bounce: price was at fib support yesterday, now moving up
        if i > 0 and fib_support.iloc[i-1]:
            if price > df['close'].iloc[i-1]:
                fib_bounce.iloc[i] = True
        
        # Fib break: price was at fib support yesterday, now below
        if i > 0 and fib_support.iloc[i-1]:
            if price < df['close'].iloc[i-1]:
                fib_break.iloc[i] = True
    
    return {
        'fib_support': fib_support,
        'fib_resist': fib_resist,
        'fib_golden': fib_golden,
        'fib_bounce': fib_bounce,
        'fib_break': fib_break,
    }

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "candles.db"

# ── Ground Truth Transitions ────────────────────────────────────────────────
# (date, direction) — the date DCA SHOULD have transitioned
GROUND_TRUTH = {
    'BTC/USDC': [
        ('2024-10-15', 'MARKUP'),
        ('2025-01-20', 'MARKDOWN'),
    ],
    'ETH/USDC': [
        ('2024-11-05', 'MARKUP'),
        ('2025-01-10', 'MARKDOWN'),
    ],
    'SOL/USDC': [
        ('2024-10-15', 'MARKUP'),
        ('2025-01-20', 'MARKDOWN'),
    ],
    'BNB/USDT': [
        ('2024-11-10', 'MARKUP'),
        ('2025-02-01', 'MARKDOWN'),
    ],
    'XRP/USDT': [
        ('2024-11-10', 'MARKUP'),
        ('2025-01-20', 'MARKDOWN'),
    ],
}


class SignalComputer:
    """Compute all individual signals for a coin on daily timeframe."""

    def __init__(self, symbol):
        self.symbol = symbol
        db = sqlite3.connect(str(DB_PATH))
        self.daily = pd.read_sql(
            'SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp',
            db, params=(symbol,))
        db.close()

        if len(self.daily) == 0:
            raise ValueError(f"No data for {symbol}")

        self.daily['date'] = pd.to_datetime(self.daily['timestamp'], unit='ms')
        self.daily.set_index('date', inplace=True)

        # Skip V13SignalPack — too slow for matrix testing (loads 24K 1h candles)
        # We compute weekly StochRSI proxy from daily instead
        self.pack = None

        # Compute HVF
        self.hvf_composite, self.hvf_vuvu, self.hvf_vol, self.hvf_price = \
            composite_hvf_score(self.daily, lookback=30)

        # Compute channel breakout
        self.channel_bo = ChannelBreakout(self.daily)

        # Compute harmonic patterns
        swings = detect_swing_points(self.daily, lookback=5)
        self.harmonic_patterns = hvf_harmonic_pattern(self.daily, swings)

        # Compute Fibonacci levels
        self.fib = fibonacci_levels(self.daily)

        # Precompute daily signals
        self._compute_daily_signals()

    def _compute_stoch_rsi_from_daily(self, period_days):
        """Compute StochRSI K from daily RSI, approximating weekly periods.
        period_days=7 ≈ 1W, period_days=14 ≈ 2W."""
        df = self.daily
        if 'rsi' not in df.columns:
            return pd.Series(50.0, index=df.index)
        rsi = df['rsi']
        stoch_period = period_days
        rsi_min = rsi.rolling(stoch_period).min()
        rsi_max = rsi.rolling(stoch_period).max()
        stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min + 1e-10) * 100
        k = stoch_rsi.rolling(3).mean()  # Smooth K
        return k.fillna(50)

    def _compute_daily_signals(self):
        """Compute SMA50 slope, HH/HL, ADX, BMSB proxy from daily data."""
        df = self.daily
        
        # StochRSI approximations from daily RSI
        self.stoch_1w = self._compute_stoch_rsi_from_daily(7)
        self.stoch_2w = self._compute_stoch_rsi_from_daily(14)

        # SMA50 slope (10-day rate of change of SMA50)
        if 'sma50' in df.columns:
            sma50 = df['sma50']
            self.sma50_slope = sma50.pct_change(10) * 100  # % change over 10 days
        else:
            self.sma50_slope = pd.Series(0.0, index=df.index)

        # ADX from daily data
        self.adx = df['adx'] if 'adx' in df.columns else pd.Series(20.0, index=df.index)

        # HH/HL detection (simplified: compare last 2 swing points)
        self.hh_hl = pd.Series(False, index=df.index)
        self.lh_ll = pd.Series(False, index=df.index)
        high_20 = df['high'].rolling(20).max()
        low_20 = df['low'].rolling(20).min()
        high_10 = df['high'].rolling(10).max()
        low_10 = df['low'].rolling(10).min()
        # HH: current 10-bar high > previous 20-bar high (shifted)
        self.hh_hl = high_10 > high_20.shift(10)
        self.lh_ll = low_10 < low_20.shift(10)

        # BMSB proxy: price vs 20-week SMA (~140 daily bars) and 21-week EMA (~147)
        if 'sma200' in df.columns:
            sma_140 = df['close'].rolling(140).mean()
            ema_147 = df['close'].ewm(span=147).mean()
            bmsb_line = (sma_140 + ema_147) / 2
            self.bmsb_above = df['close'] > bmsb_line
        else:
            self.bmsb_above = pd.Series(True, index=df.index)

        # CFGI from DB
        self.cfgi = pd.Series(50.0, index=df.index)
        try:
            db = sqlite3.connect(str(DB_PATH))
            plain = self.symbol.split('/')[0]
            cfgi_df = pd.read_sql(
                'SELECT timestamp, cfgi FROM cfgi_daily WHERE symbol=? ORDER BY timestamp',
                db, params=(plain,))
            db.close()
            if len(cfgi_df) > 0:
                cfgi_df['date'] = pd.to_datetime(cfgi_df['timestamp'], unit='ms')
                cfgi_df.set_index('date', inplace=True)
                self.cfgi = cfgi_df['cfgi'].reindex(df.index, method='ffill').fillna(50)
        except Exception:
            pass

        # CFGI momentum: rate of change over 7d and 14d windows
        self.cfgi_delta_7d = self.cfgi - self.cfgi.shift(7)    # absolute change over 7 days
        self.cfgi_delta_14d = self.cfgi - self.cfgi.shift(14)  # absolute change over 14 days
        self.cfgi_delta_7d = self.cfgi_delta_7d.fillna(0)
        self.cfgi_delta_14d = self.cfgi_delta_14d.fillna(0)

    def signals_at(self, date):
        """Return dict of all signal values at a given date."""
        d = pd.Timestamp(date)
        if d not in self.daily.index:
            # Find nearest date
            mask = self.daily.index <= d
            if not mask.any():
                return None
            d = self.daily.index[mask][-1]

        sigs = {}

        # S1: HVF composite
        sigs['S1_hvf'] = self.hvf_composite.get(d, 0)

        # S2/S3: Channel breakout (check if confirmed before this date)
        sigs['S2_ch_retest'] = False
        sigs['S3_ch_run'] = False
        sigs['ch_direction'] = None
        for bo in self.channel_bo.breakouts:
            if not bo['confirmed']:
                continue
            cd = bo['retest_date'] or bo['breakout_date']
            if cd and cd <= d and (d - cd).days <= 30:
                if bo['retest_found'] and bo['retest_held'] and not bo['no_retest_run']:
                    sigs['S2_ch_retest'] = True
                    sigs['ch_direction'] = bo['direction']
                else:
                    sigs['S3_ch_run'] = True
                    sigs['ch_direction'] = bo['direction']

        # S4: 2W StochRSI OS exit (approximated from daily)
        k_2w = float(self.stoch_2w.get(d, 50))
        k_2w_prev = float(self.stoch_2w.shift(1).get(d, 50)) if d in self.stoch_2w.index else 50
        sigs['S4_2w_os'] = k_2w_prev < 20 and k_2w >= 20  # Crossing above 20
        sigs['S4_2w_ob_exit'] = k_2w_prev > 80 and k_2w <= 80  # Crossing below 80

        # S5: 1W StochRSI K value
        sigs['S5_1w_k'] = float(self.stoch_1w.get(d, 50))

        # S6: BMSB
        sigs['S6_bmsb_above'] = bool(self.bmsb_above.get(d, True))

        # S7: SMA50 slope
        sigs['S7_sma50_slope'] = float(self.sma50_slope.get(d, 0))

        # S8: HH/HL or LH/LL
        sigs['S8_hh_hl'] = bool(self.hh_hl.get(d, False))
        sigs['S8_lh_ll'] = bool(self.lh_ll.get(d, False))

        # S9: CFGI level + momentum
        sigs['S9_cfgi'] = float(self.cfgi.get(d, 50))
        sigs['S9_cfgi_d7'] = float(self.cfgi_delta_7d.get(d, 0))   # 7-day change
        sigs['S9_cfgi_d14'] = float(self.cfgi_delta_14d.get(d, 0)) # 14-day change

        # S10: ADX
        sigs['S10_adx'] = float(self.adx.get(d, 20))

        # S11: Harmonic pattern
        sigs['S11_harmonic_bull'] = False
        sigs['S11_harmonic_bear'] = False
        for p in self.harmonic_patterns:
            if abs((p['date'] - d).days) <= 14 and p['score'] > 0.3:
                if p['direction'] == 'BULLISH':
                    sigs['S11_harmonic_bull'] = True
                else:
                    sigs['S11_harmonic_bear'] = True

        # S12: Fibonacci levels
        sigs['S12_fib_support'] = bool(self.fib['fib_support'].get(d, False))
        sigs['S12_fib_resist'] = bool(self.fib['fib_resist'].get(d, False))
        sigs['S12_fib_golden'] = bool(self.fib['fib_golden'].get(d, False))
        sigs['S12_fib_bounce'] = bool(self.fib['fib_bounce'].get(d, False))
        sigs['S12_fib_break'] = bool(self.fib['fib_break'].get(d, False))

        return sigs

    def scan_signals(self, start_date, end_date, direction):
        """Scan daily for signal states in a window. Returns list of (date, signals) tuples."""
        results = []
        s = pd.Timestamp(start_date)
        e = pd.Timestamp(end_date)
        mask = (self.daily.index >= s) & (self.daily.index <= e)
        for d in self.daily.index[mask]:
            sigs = self.signals_at(d)
            if sigs:
                results.append((d, sigs))
        return results


# ── Signal Rules ────────────────────────────────────────────────────────────
# Each rule returns (fires: bool, lead_days: int or None) given signals + context

MARKUP_RULES = {
    'HVF>0.5': lambda s: s['S1_hvf'] > 0.5,
    'HVF>0.4': lambda s: s['S1_hvf'] > 0.4,
    'HVF>0.3': lambda s: s['S1_hvf'] > 0.3,
    'CH_retest_bull': lambda s: s['S2_ch_retest'] and s.get('ch_direction') == 'BULLISH',
    'CH_run_bull': lambda s: s['S3_ch_run'] and s.get('ch_direction') == 'BULLISH',
    'CH_any_bull': lambda s: (s['S2_ch_retest'] or s['S3_ch_run']) and s.get('ch_direction') == 'BULLISH',
    '2W_OS_exit': lambda s: s['S4_2w_os'],
    '1W_K>50': lambda s: s['S5_1w_k'] > 50,
    '1W_K>30': lambda s: s['S5_1w_k'] > 30,
    'BMSB_above': lambda s: s['S6_bmsb_above'],
    'SMA50_pos': lambda s: s['S7_sma50_slope'] > 0,
    'SMA50_strong': lambda s: s['S7_sma50_slope'] > 1.0,
    'HH_HL': lambda s: s['S8_hh_hl'],
    'CFGI>50': lambda s: s['S9_cfgi'] > 50,
    'CFGI>40': lambda s: s['S9_cfgi'] > 40,
    'CFGI_rising_7d': lambda s: s['S9_cfgi_d7'] > 5,      # CFGI rose >5 pts in 7 days
    'CFGI_rising_14d': lambda s: s['S9_cfgi_d14'] > 10,   # CFGI rose >10 pts in 14 days
    'CFGI_surge_7d': lambda s: s['S9_cfgi_d7'] > 10,      # CFGI rose >10 pts in 7 days (strong)
    'CFGI_recovering': lambda s: s['S9_cfgi'] > 40 and s['S9_cfgi_d7'] > 5,  # Level + momentum
    'ADX>20': lambda s: s['S10_adx'] > 20,
    'ADX>25': lambda s: s['S10_adx'] > 25,
    'Harmonic_bull': lambda s: s['S11_harmonic_bull'],
    'Fib_support': lambda s: s['S12_fib_support'],
    'Fib_golden': lambda s: s['S12_fib_golden'],
    'Fib_bounce': lambda s: s['S12_fib_bounce'],
}

MARKDOWN_RULES = {
    'HVF>0.5': lambda s: s['S1_hvf'] > 0.5,
    'HVF>0.4': lambda s: s['S1_hvf'] > 0.4,
    'HVF>0.3': lambda s: s['S1_hvf'] > 0.3,
    'CH_retest_bear': lambda s: s['S2_ch_retest'] and s.get('ch_direction') == 'BEARISH',
    'CH_run_bear': lambda s: s['S3_ch_run'] and s.get('ch_direction') == 'BEARISH',
    'CH_any_bear': lambda s: (s['S2_ch_retest'] or s['S3_ch_run']) and s.get('ch_direction') == 'BEARISH',
    '2W_OB_exit': lambda s: s.get('S4_2w_ob_exit', False),
    '1W_K<50': lambda s: s['S5_1w_k'] < 50,
    '1W_K<30': lambda s: s['S5_1w_k'] < 30,
    'BMSB_below': lambda s: not s['S6_bmsb_above'],
    'SMA50_neg': lambda s: s['S7_sma50_slope'] < 0,
    'SMA50_strong_neg': lambda s: s['S7_sma50_slope'] < -1.0,
    'LH_LL': lambda s: s['S8_lh_ll'],
    'CFGI<40': lambda s: s['S9_cfgi'] < 40,
    'CFGI<30': lambda s: s['S9_cfgi'] < 30,
    'CFGI_falling_7d': lambda s: s['S9_cfgi_d7'] < -5,     # CFGI dropped >5 pts in 7 days
    'CFGI_falling_14d': lambda s: s['S9_cfgi_d14'] < -10,  # CFGI dropped >10 pts in 14 days
    'CFGI_crash_7d': lambda s: s['S9_cfgi_d7'] < -10,      # CFGI dropped >10 pts in 7 days (strong)
    'CFGI_deteriorating': lambda s: s['S9_cfgi'] < 40 and s['S9_cfgi_d7'] < -5,  # Level + momentum
    'ADX>20': lambda s: s['S10_adx'] > 20,
    'ADX>25': lambda s: s['S10_adx'] > 25,
    'Harmonic_bear': lambda s: s['S11_harmonic_bear'],
    'Fib_resist': lambda s: s['S12_fib_resist'],
    'Fib_break': lambda s: s['S12_fib_break'],
}


def test_signal_combo(computers, combo_names, rules, ground_truths, direction):
    """Test a combination of signals against ground truth transitions.
    
    Returns: {accuracy, fp_rate, avg_lead_days, coverage, score}
    """
    total_transitions = 0
    detected = 0
    false_positives = 0
    lead_days_list = []
    total_scan_days = 0

    for symbol, transitions in ground_truths.items():
        if symbol not in computers:
            continue
        comp = computers[symbol]

        for gt_date_str, gt_dir in transitions:
            if gt_dir != direction:
                continue
            total_transitions += 1

            gt_date = pd.Timestamp(gt_date_str)
            # Scan 60 days before transition for signal firing
            scan_start = gt_date - pd.Timedelta(days=60)
            scan_data = comp.scan_signals(scan_start, gt_date, direction)

            found = False
            for d, sigs in scan_data:
                # Check if ALL signals in combo fire
                all_fire = all(rules[name](sigs) for name in combo_names)
                if all_fire:
                    lead = (gt_date - d).days
                    if lead >= 0:
                        detected += 1
                        lead_days_list.append(lead)
                        found = True
                        break

        # Count false positives: scan periods where NO transition happened
        # Use 60-day windows between transitions as "quiet" periods
        gt_dates = [pd.Timestamp(d) for d, dir_ in transitions if dir_ == direction]
        quiet_starts = []
        if len(gt_dates) >= 2:
            for i in range(len(gt_dates) - 1):
                mid = gt_dates[i] + pd.Timedelta(days=30)
                quiet_starts.append(mid)
        elif len(gt_dates) == 1:
            # One quiet period after the transition
            quiet_starts.append(gt_dates[0] + pd.Timedelta(days=60))

        for qs in quiet_starts:
            qe = qs + pd.Timedelta(days=30)
            scan_data = comp.scan_signals(qs, qe, direction)
            total_scan_days += len(scan_data)
            for d, sigs in scan_data:
                all_fire = all(rules[name](sigs) for name in combo_names)
                if all_fire:
                    false_positives += 1
                    break  # Count max 1 FP per quiet window

    # Compute metrics
    accuracy = detected / total_transitions if total_transitions > 0 else 0
    # FP rate: FPs / quiet windows scanned
    quiet_windows = len([s for s in ground_truths.values() for _ in s]) // 2 + len(ground_truths)
    fp_rate = false_positives / max(1, quiet_windows)
    avg_lead = np.mean(lead_days_list) if lead_days_list else 0
    coverage = detected / total_transitions if total_transitions > 0 else 0

    # Composite score: accuracy (40%) + (1-FP) (30%) + lead_time_norm (15%) + coverage (15%)
    lead_norm = min(1.0, avg_lead / 30)  # Normalize: 30 days = perfect lead
    score = accuracy * 40 + (1 - fp_rate) * 30 + lead_norm * 15 + coverage * 15

    return {
        'combo': '+'.join(combo_names),
        'accuracy': accuracy,
        'detected': detected,
        'total': total_transitions,
        'fp_rate': fp_rate,
        'fps': false_positives,
        'avg_lead': avg_lead,
        'coverage': coverage,
        'score': score,
    }


def main():
    print("V13 DCA Transition Signal Matrix")
    print("=" * 80)

    # Load all coins
    import sys
    computers = {}
    for symbol in ['BTC/USDC', 'ETH/USDC', 'SOL/USDC', 'BNB/USDT', 'XRP/USDT']:
        print(f"  Loading {symbol}...", flush=True)
        try:
            computers[symbol] = SignalComputer(symbol)
            print(f"    OK ({len(computers[symbol].daily)} daily candles)", flush=True)
        except Exception as e:
            print(f"    ERROR: {e}", flush=True)

    # ── Test individual signals ─────────────────────────────────────────────
    print(f"\n{'='*80}")
    print(f"  MARKUP ENTRY — Individual Signals (5 coins)")
    print(f"{'='*80}")
    print(f"  {'Signal':<25} {'Acc':>5} {'Det':>4}/{'':<4} {'FP%':>5} {'Lead':>5} {'Score':>6}")
    print(f"  {'─'*60}")

    markup_results = []
    for name in sorted(MARKUP_RULES.keys()):
        r = test_signal_combo(computers, [name], MARKUP_RULES, GROUND_TRUTH, 'MARKUP')
        markup_results.append(r)
        print(f"  {name:<25} {r['accuracy']:>5.0%} {r['detected']:>4}/{r['total']:<4} "
              f"{r['fp_rate']:>5.0%} {r['avg_lead']:>5.1f}d {r['score']:>6.1f}")

    # Sort by score
    markup_results.sort(key=lambda x: x['score'], reverse=True)
    print(f"\n  Top 5 individual MARKUP signals:")
    for r in markup_results[:5]:
        print(f"    {r['combo']:<25} Score={r['score']:.1f} Acc={r['accuracy']:.0%} FP={r['fp_rate']:.0%} Lead={r['avg_lead']:.0f}d")

    # ── Test individual MARKDOWN signals ────────────────────────────────────
    print(f"\n{'='*80}")
    print(f"  MARKDOWN ENTRY — Individual Signals (5 coins)")
    print(f"{'='*80}")
    print(f"  {'Signal':<25} {'Acc':>5} {'Det':>4}/{'':<4} {'FP%':>5} {'Lead':>5} {'Score':>6}")
    print(f"  {'─'*60}")

    markdown_results = []
    for name in sorted(MARKDOWN_RULES.keys()):
        r = test_signal_combo(computers, [name], MARKDOWN_RULES, GROUND_TRUTH, 'MARKDOWN')
        markdown_results.append(r)
        print(f"  {name:<25} {r['accuracy']:>5.0%} {r['detected']:>4}/{r['total']:<4} "
              f"{r['fp_rate']:>5.0%} {r['avg_lead']:>5.1f}d {r['score']:>6.1f}")

    markdown_results.sort(key=lambda x: x['score'], reverse=True)
    print(f"\n  Top 5 individual MARKDOWN signals:")
    for r in markdown_results[:5]:
        print(f"    {r['combo']:<25} Score={r['score']:.1f} Acc={r['accuracy']:.0%} FP={r['fp_rate']:.0%} Lead={r['avg_lead']:.0f}d")

    # ── Test 2-signal combinations ──────────────────────────────────────────
    # Pick top individual signals + key structural ones
    markup_candidates = ['HVF>0.5', 'HVF>0.4', 'CH_any_bull', 'CH_retest_bull',
                         '2W_OS_exit', 'BMSB_above', 'SMA50_pos', 'HH_HL',
                         'CFGI>40', 'CFGI_rising_7d', 'CFGI_rising_14d', 'CFGI_surge_7d', 'CFGI_recovering',
                         'ADX>20', 'Harmonic_bull', '1W_K>30',
                         'Fib_support', 'Fib_golden', 'Fib_bounce']
    
    print(f"\n{'='*80}")
    print(f"  MARKUP ENTRY — 2-Signal Combinations")
    print(f"{'='*80}")
    print(f"  {'Combo':<45} {'Acc':>5} {'Det':>4}/{'':<4} {'FP%':>5} {'Lead':>5} {'Score':>6}")
    print(f"  {'─'*75}")

    combo2_markup = []
    for c in combinations(markup_candidates, 2):
        r = test_signal_combo(computers, list(c), MARKUP_RULES, GROUND_TRUTH, 'MARKUP')
        combo2_markup.append(r)

    combo2_markup.sort(key=lambda x: x['score'], reverse=True)
    for r in combo2_markup[:15]:
        print(f"  {r['combo']:<45} {r['accuracy']:>5.0%} {r['detected']:>4}/{r['total']:<4} "
              f"{r['fp_rate']:>5.0%} {r['avg_lead']:>5.1f}d {r['score']:>6.1f}")

    # MARKDOWN 2-signal combos
    markdown_candidates = ['HVF>0.5', 'HVF>0.4', 'CH_any_bear', 'CH_retest_bear',
                           'BMSB_below', 'SMA50_neg', 'LH_LL',
                           'CFGI<40', 'CFGI<30', 'CFGI_falling_7d', 'CFGI_falling_14d', 'CFGI_crash_7d', 'CFGI_deteriorating',
                           'ADX>20', 'Harmonic_bear', '1W_K<50', '1W_K<30',
                           'Fib_resist', 'Fib_break']

    print(f"\n{'='*80}")
    print(f"  MARKDOWN ENTRY — 2-Signal Combinations")
    print(f"{'='*80}")
    print(f"  {'Combo':<45} {'Acc':>5} {'Det':>4}/{'':<4} {'FP%':>5} {'Lead':>5} {'Score':>6}")
    print(f"  {'─'*75}")

    combo2_markdown = []
    for c in combinations(markdown_candidates, 2):
        r = test_signal_combo(computers, list(c), MARKDOWN_RULES, GROUND_TRUTH, 'MARKDOWN')
        combo2_markdown.append(r)

    combo2_markdown.sort(key=lambda x: x['score'], reverse=True)
    for r in combo2_markdown[:15]:
        print(f"  {r['combo']:<45} {r['accuracy']:>5.0%} {r['detected']:>4}/{r['total']:<4} "
              f"{r['fp_rate']:>5.0%} {r['avg_lead']:>5.1f}d {r['score']:>6.1f}")

    # ── Test 3-signal combinations (top candidates only) ────────────────────
    markup_top3 = ['HVF>0.4', 'BMSB_above', 'SMA50_pos', 'HH_HL', 'CFGI>40',
                   'CFGI_rising_7d', 'CFGI_recovering', 'ADX>20', '1W_K>30',
                   'Fib_support', 'Fib_bounce']

    print(f"\n{'='*80}")
    print(f"  MARKUP ENTRY — 3-Signal Combinations (top candidates)")
    print(f"{'='*80}")
    print(f"  {'Combo':<55} {'Acc':>5} {'Det':>4}/{'':<4} {'FP%':>5} {'Lead':>5} {'Score':>6}")
    print(f"  {'─'*85}")

    combo3_markup = []
    for c in combinations(markup_top3, 3):
        r = test_signal_combo(computers, list(c), MARKUP_RULES, GROUND_TRUTH, 'MARKUP')
        combo3_markup.append(r)

    combo3_markup.sort(key=lambda x: x['score'], reverse=True)
    for r in combo3_markup[:10]:
        print(f"  {r['combo']:<55} {r['accuracy']:>5.0%} {r['detected']:>4}/{r['total']:<4} "
              f"{r['fp_rate']:>5.0%} {r['avg_lead']:>5.1f}d {r['score']:>6.1f}")

    markdown_top3 = ['HVF>0.4', 'BMSB_below', 'SMA50_neg', 'LH_LL', 'CFGI<40',
                     'CFGI_falling_7d', 'CFGI_deteriorating', 'ADX>20', '1W_K<50',
                     'Fib_resist', 'Fib_break']

    print(f"\n{'='*80}")
    print(f"  MARKDOWN ENTRY — 3-Signal Combinations (top candidates)")
    print(f"{'='*80}")
    print(f"  {'Combo':<55} {'Acc':>5} {'Det':>4}/{'':<4} {'FP%':>5} {'Lead':>5} {'Score':>6}")
    print(f"  {'─'*85}")

    combo3_markdown = []
    for c in combinations(markdown_top3, 3):
        r = test_signal_combo(computers, list(c), MARKDOWN_RULES, GROUND_TRUTH, 'MARKDOWN')
        combo3_markdown.append(r)

    combo3_markdown.sort(key=lambda x: x['score'], reverse=True)
    for r in combo3_markdown[:10]:
        print(f"  {r['combo']:<55} {r['accuracy']:>5.0%} {r['detected']:>4}/{r['total']:<4} "
              f"{r['fp_rate']:>5.0%} {r['avg_lead']:>5.1f}d {r['score']:>6.1f}")

    # ── Final summary ───────────────────────────────────────────────────────
    print(f"\n{'='*80}")
    print(f"  WINNERS")
    print(f"{'='*80}")
    
    best_markup_1 = markup_results[0]
    best_markup_2 = combo2_markup[0]
    best_markup_3 = combo3_markup[0]
    best_md_1 = markdown_results[0]
    best_md_2 = combo2_markdown[0]
    best_md_3 = combo3_markdown[0]

    print(f"\n  DCA → MARKUP:")
    print(f"    Best 1-signal: {best_markup_1['combo']:<30} Score={best_markup_1['score']:.1f}")
    print(f"    Best 2-signal: {best_markup_2['combo']:<30} Score={best_markup_2['score']:.1f}")
    print(f"    Best 3-signal: {best_markup_3['combo']:<30} Score={best_markup_3['score']:.1f}")

    print(f"\n  DCA → MARKDOWN:")
    print(f"    Best 1-signal: {best_md_1['combo']:<30} Score={best_md_1['score']:.1f}")
    print(f"    Best 2-signal: {best_md_2['combo']:<30} Score={best_md_2['score']:.1f}")
    print(f"    Best 3-signal: {best_md_3['combo']:<30} Score={best_md_3['score']:.1f}")


if __name__ == '__main__':
    main()
