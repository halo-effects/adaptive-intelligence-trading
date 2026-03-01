"""
Test: HVF + Channel Dwell + Breakout as bear-bottom / markup entry signal.

Hypothesis:
- Long channel dwell (60-90+ days) = bear bottom likely in (energy stored)
- HVF fires = energy building, breakout imminent
- Channel breakout = confirmation
- Retest NOT required when dwell is long + HVF confirms

Dwell tiers:
- 14-30 days: standard channel, require retest
- 30-60 days: moderate dwell, HVF can substitute for retest
- 90+ days: extended dwell, HVF + breakout = high conviction entry

Brett: "HVF is very reliable, especially when the coin has been in a channel
for that long. Totally suppressed."
"""
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from channel_breakout import ChannelBreakout
from test_hvf_daily import composite_hvf_score, detect_swing_points, hvf_harmonic_pattern
from v13_dca_transition_matrix import (
    SignalComputer, GROUND_TRUTH, fibonacci_levels,
    MARKUP_RULES, MARKDOWN_RULES, test_signal_combo
)

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "candles.db"


class DwellAwareBreakout(ChannelBreakout):
    """Extended ChannelBreakout that exposes dwell duration and HVF-aware confirmation."""

    def dwell_breakouts(self):
        """Return breakouts enriched with dwell tier classification."""
        results = []
        for bo in self.breakouts:
            days = bo['channel_days']
            if days < 30:
                tier = 'short'
            elif days < 60:
                tier = 'moderate'
            elif days < 90:
                tier = 'long'
            else:
                tier = 'extended'
            
            results.append({
                **bo,
                'dwell_tier': tier,
                'dwell_days': days,
            })
        return results


def analyze_coin(symbol):
    """Analyze HVF + dwell + breakout alignment for a coin."""
    db = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql(
        'SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp',
        db, params=(symbol,))
    db.close()

    if len(df) == 0:
        print(f"  No data for {symbol}")
        return None

    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('date', inplace=True)

    # Detect channels + breakouts with dwell awareness
    dab = DwellAwareBreakout(df)
    dwell_bos = dab.dwell_breakouts()

    # Compute HVF
    hvf_composite, hvf_vuvu, hvf_vol, hvf_price = composite_hvf_score(df, lookback=30)

    print(f"\n{'='*70}")
    print(f"  {symbol}")
    print(f"{'='*70}")
    print(f"  Channels: {len(dab.channels)}, Breakouts: {len(dwell_bos)}")

    # For each breakout, check HVF score in the window leading up to it
    for bo in dwell_bos:
        bo_date = bo['breakout_date']
        direction = bo['direction']
        dwell = bo['dwell_days']
        tier = bo['dwell_tier']
        confirmed = bo['confirmed']
        retest = bo['retest_found']
        run = bo['no_retest_run']
        invalidated = bo['invalidated']

        # Get HVF scores in 30-day window before breakout
        window_start = bo_date - pd.Timedelta(days=30)
        hvf_window = {d: v for d, v in hvf_composite.items() 
                      if window_start <= d <= bo_date}
        
        max_hvf = max(hvf_window.values()) if hvf_window else 0
        avg_hvf = np.mean(list(hvf_window.values())) if hvf_window else 0
        
        # Also check HVF at breakout date specifically
        hvf_at_bo = hvf_composite.get(bo_date, 0)

        # Classification
        if invalidated:
            status = "❌ INVALIDATED"
        elif confirmed and retest:
            status = f"✅ RETEST-CONFIRMED (retests: {bo.get('retest_count', 1)})"
        elif confirmed and run:
            status = "✅ RUN (no retest, >10% move)"
        else:
            status = "⏳ UNCONFIRMED"

        # Would HVF + dwell have confirmed this without retest?
        hvf_confirms = max_hvf > 0.3  # HVF fired in pre-breakout window
        hvf_strong = max_hvf > 0.5
        dwell_long = dwell >= 60
        dwell_extended = dwell >= 90

        # New signal: HVF + dwell substitutes for retest
        hvf_dwell_signal = False
        if not invalidated and direction == 'BULLISH':
            if dwell_extended and hvf_confirms:
                hvf_dwell_signal = True  # Extended dwell + any HVF = enter
            elif dwell_long and hvf_strong:
                hvf_dwell_signal = True  # Long dwell + strong HVF = enter
            elif dwell >= 30 and hvf_strong:
                hvf_dwell_signal = True  # Moderate dwell + strong HVF = enter
        elif not invalidated and direction == 'BEARISH':
            if dwell_extended and hvf_confirms:
                hvf_dwell_signal = True
            elif dwell_long and hvf_strong:
                hvf_dwell_signal = True

        gained = ""
        if hvf_dwell_signal and not confirmed:
            gained = " 🆕 NEW SIGNAL (would have entered!)"
        elif hvf_dwell_signal and confirmed:
            gained = " ✓ (redundant — already confirmed)"

        print(f"\n  [BO] Breakout: {bo_date.date()} {direction}")
        print(f"     Channel: {bo['channel_start'].date()} → {bo['channel_end'].date()} "
              f"({dwell}d, tier={tier})")
        print(f"     Range: ${bo['channel_low']:.4f} — ${bo['channel_high']:.4f}")
        print(f"     Status: {status}")
        print(f"     HVF: max={max_hvf:.3f}, avg={avg_hvf:.3f}, at_breakout={hvf_at_bo:.3f}")
        print(f"     HVF+Dwell signal: {'YES' if hvf_dwell_signal else 'NO'}{gained}")

    return dab, hvf_composite, dwell_bos


def matrix_test():
    """Add HVF+Dwell signals to the transition matrix and test combos."""
    print(f"\n{'='*70}")
    print(f"  TRANSITION MATRIX — HVF + Dwell Signals")
    print(f"{'='*70}")

    # Load SignalComputers (reuse existing infrastructure)
    computers = {}
    for symbol in ['BTC/USDC', 'ETH/USDC', 'SOL/USDC', 'BNB/USDT', 'XRP/USDT']:
        print(f"  Loading {symbol}...", flush=True)
        try:
            computers[symbol] = SignalComputer(symbol)
            print(f"    OK", flush=True)
        except Exception as e:
            print(f"    ERROR: {e}", flush=True)

    # Enrich each computer with dwell-aware breakout data
    dwell_data = {}
    for symbol, comp in computers.items():
        dab = DwellAwareBreakout(comp.daily)
        dwell_data[symbol] = dab.dwell_breakouts()

    # Add new signal rules for dwell-aware breakouts
    def make_hvf_dwell_rule(min_dwell, min_hvf, direction):
        """Create a rule that checks HVF + channel dwell at a given date."""
        def rule(s):
            # HVF must be active
            if s['S1_hvf'] < min_hvf:
                return False
            # Channel breakout must exist (either retest or run)
            if direction == 'BULLISH':
                has_bo = s['S2_ch_retest'] or s['S3_ch_run']
                right_dir = s.get('ch_direction') == 'BULLISH'
            else:
                has_bo = s['S2_ch_retest'] or s['S3_ch_run']
                right_dir = s.get('ch_direction') == 'BEARISH'
            return has_bo and right_dir
        return rule

    # We need to actually check dwell days — but the existing signal infrastructure
    # doesn't pass channel dwell through. Let's add it.
    
    # Extend signals_at to include dwell info
    for symbol, comp in computers.items():
        dab = DwellAwareBreakout(comp.daily)
        # Store on the computer for signal access
        comp._dwell_breakouts = dab.dwell_breakouts()
    
    # Monkey-patch signals_at to add dwell info
    original_signals_at = SignalComputer.signals_at

    def extended_signals_at(self, date):
        sigs = original_signals_at(self, date)
        if sigs is None:
            return sigs
        
        d = pd.Timestamp(date)
        if d not in self.daily.index:
            mask = self.daily.index <= d
            if not mask.any():
                return sigs
            d = self.daily.index[mask][-1]

        # Add dwell info from breakouts
        sigs['dwell_days'] = 0
        sigs['dwell_tier'] = 'none'
        sigs['has_dwell_bo'] = False
        
        if hasattr(self, '_dwell_breakouts'):
            for bo in self._dwell_breakouts:
                if bo['invalidated']:
                    continue
                cd = bo['retest_date'] or bo['breakout_date']
                if cd and cd <= d and (d - cd).days <= 30:
                    sigs['dwell_days'] = bo['dwell_days']
                    sigs['dwell_tier'] = bo['dwell_tier']
                    sigs['has_dwell_bo'] = True
                    break
                # Also fire on breakout date itself for run-without-retest
                if bo['breakout_date'] and bo['breakout_date'] <= d and (d - bo['breakout_date']).days <= 30:
                    sigs['dwell_days'] = bo['dwell_days']
                    sigs['dwell_tier'] = bo['dwell_tier']
                    sigs['has_dwell_bo'] = True
                    break
        
        # Composite HVF + dwell signals
        hvf = sigs['S1_hvf']
        dwell = sigs['dwell_days']
        
        # HVF + Dwell tiers (bullish — direction checked separately)
        sigs['HVF_dwell_30'] = hvf > 0.3 and dwell >= 30   # Any HVF + moderate dwell
        sigs['HVF_dwell_60'] = hvf > 0.3 and dwell >= 60   # Any HVF + long dwell
        sigs['HVF_dwell_90'] = hvf > 0.3 and dwell >= 90   # Any HVF + extended dwell
        sigs['HVF_strong_dwell_30'] = hvf > 0.5 and dwell >= 30
        sigs['HVF_strong_dwell_60'] = hvf > 0.5 and dwell >= 60
        sigs['HVF_strong_dwell_90'] = hvf > 0.5 and dwell >= 90
        
        # Channel breakout without retest but WITH dwell+HVF
        sigs['dwell_bo_no_retest'] = (
            sigs['has_dwell_bo'] and 
            not sigs.get('S2_ch_retest', False) and 
            dwell >= 30
        )
        
        return sigs

    SignalComputer.signals_at = extended_signals_at

    # Define new rules
    new_markup_rules = {
        **MARKUP_RULES,
        # HVF + Dwell combos (direction checked via ch_direction)
        'HVF_dwell30': lambda s: s.get('HVF_dwell_30', False) and s.get('ch_direction') == 'BULLISH',
        'HVF_dwell60': lambda s: s.get('HVF_dwell_60', False) and s.get('ch_direction') == 'BULLISH',
        'HVF_dwell90': lambda s: s.get('HVF_dwell_90', False) and s.get('ch_direction') == 'BULLISH',
        'HVF_strong_dwell30': lambda s: s.get('HVF_strong_dwell_30', False) and s.get('ch_direction') == 'BULLISH',
        'HVF_strong_dwell60': lambda s: s.get('HVF_strong_dwell_60', False) and s.get('ch_direction') == 'BULLISH',
        'HVF_strong_dwell90': lambda s: s.get('HVF_strong_dwell_90', False) and s.get('ch_direction') == 'BULLISH',
        # Dwell-only (no HVF requirement, just long suppression)
        'Dwell60_bo': lambda s: s.get('dwell_days', 0) >= 60 and s.get('ch_direction') == 'BULLISH' and (s.get('S2_ch_retest') or s.get('S3_ch_run')),
        'Dwell90_bo': lambda s: s.get('dwell_days', 0) >= 90 and s.get('ch_direction') == 'BULLISH' and (s.get('S2_ch_retest') or s.get('S3_ch_run')),
        # The key test: HVF + dwell replaces retest requirement
        'HVF_dwell_no_retest': lambda s: s.get('HVF_dwell_30', False) and s.get('dwell_bo_no_retest', False) and s.get('ch_direction') == 'BULLISH',
    }

    new_markdown_rules = {
        **MARKDOWN_RULES,
        'HVF_dwell30': lambda s: s.get('HVF_dwell_30', False) and s.get('ch_direction') == 'BEARISH',
        'HVF_dwell60': lambda s: s.get('HVF_dwell_60', False) and s.get('ch_direction') == 'BEARISH',
        'HVF_dwell90': lambda s: s.get('HVF_dwell_90', False) and s.get('ch_direction') == 'BEARISH',
        'HVF_strong_dwell30': lambda s: s.get('HVF_strong_dwell_30', False) and s.get('ch_direction') == 'BEARISH',
        'Dwell60_bo': lambda s: s.get('dwell_days', 0) >= 60 and s.get('ch_direction') == 'BEARISH' and (s.get('S2_ch_retest') or s.get('S3_ch_run')),
        'Dwell90_bo': lambda s: s.get('dwell_days', 0) >= 90 and s.get('ch_direction') == 'BEARISH' and (s.get('S2_ch_retest') or s.get('S3_ch_run')),
    }

    # ── Test individual new signals ─────────────────────────────────────────
    new_signal_names = [
        'HVF_dwell30', 'HVF_dwell60', 'HVF_dwell90',
        'HVF_strong_dwell30', 'HVF_strong_dwell60', 'HVF_strong_dwell90',
        'Dwell60_bo', 'Dwell90_bo', 'HVF_dwell_no_retest',
    ]

    print(f"\n{'='*70}")
    print(f"  NEW MARKUP SIGNALS — HVF + Dwell (all 5 coins)")
    print(f"{'='*70}")
    print(f"  {'Signal':<30} {'Acc':>5} {'Det':>4}/{'':<4} {'FP%':>5} {'Lead':>5} {'Score':>6}")
    print(f"  {'─'*65}")

    for name in new_signal_names:
        if name not in new_markup_rules:
            continue
        r = test_signal_combo(computers, [name], new_markup_rules, GROUND_TRUTH, 'MARKUP')
        print(f"  {name:<30} {r['accuracy']:>5.0%} {r['detected']:>4}/{r['total']:<4} "
              f"{r['fp_rate']:>5.0%} {r['avg_lead']:>5.1f}d {r['score']:>6.1f}")

    # Compare with existing winners
    print(f"\n  --- Existing winners for comparison ---")
    for name in ['HH_HL', 'Fib_support', 'Fib_golden', 'CH_retest_bull', 'CH_any_bull', 'HVF>0.4']:
        r = test_signal_combo(computers, [name], new_markup_rules, GROUND_TRUTH, 'MARKUP')
        print(f"  {name:<30} {r['accuracy']:>5.0%} {r['detected']:>4}/{r['total']:<4} "
              f"{r['fp_rate']:>5.0%} {r['avg_lead']:>5.1f}d {r['score']:>6.1f}")

    # ── Test key 2-signal combos with dwell ─────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  KEY 2-SIGNAL COMBOS — HVF+Dwell + existing signals")
    print(f"{'='*70}")
    print(f"  {'Combo':<50} {'Acc':>5} {'Det':>4}/{'':<4} {'FP%':>5} {'Lead':>5} {'Score':>6}")
    print(f"  {'─'*80}")

    dwell_combos_markup = [
        # HVF+dwell with structure signals
        ['HVF_dwell60', 'HH_HL'],
        ['HVF_dwell60', 'Fib_support'],
        ['HVF_dwell60', 'Fib_bounce'],
        ['HVF_dwell60', 'SMA50_pos'],
        ['HVF_dwell60', 'BMSB_above'],
        ['HVF_dwell60', 'ADX>20'],
        ['HVF_dwell90', 'HH_HL'],
        ['HVF_dwell90', 'Fib_support'],
        ['HVF_strong_dwell30', 'HH_HL'],
        ['HVF_strong_dwell30', 'Fib_support'],
        # Dwell-only with structure
        ['Dwell60_bo', 'HH_HL'],
        ['Dwell60_bo', 'Fib_support'],
        ['Dwell90_bo', 'HH_HL'],
        # Existing best combo for comparison
        ['HH_HL', 'Fib_support'],
        # HVF+dwell replacing retest
        ['HVF_dwell_no_retest', 'HH_HL'],
        ['HVF_dwell_no_retest', 'Fib_support'],
    ]

    for combo in dwell_combos_markup:
        r = test_signal_combo(computers, combo, new_markup_rules, GROUND_TRUTH, 'MARKUP')
        print(f"  {r['combo']:<50} {r['accuracy']:>5.0%} {r['detected']:>4}/{r['total']:<4} "
              f"{r['fp_rate']:>5.0%} {r['avg_lead']:>5.1f}d {r['score']:>6.1f}")

    # ── Per-coin breakdown for BNB and XRP ──────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  PER-COIN FOCUS: BNB & XRP (the cold-start problem coins)")
    print(f"{'='*70}")

    for symbol in ['BNB/USDT', 'XRP/USDT']:
        print(f"\n  {symbol}:")
        single_gt = {symbol: GROUND_TRUTH[symbol]}
        single_comp = {symbol: computers[symbol]}

        key_signals = [
            'HVF_dwell30', 'HVF_dwell60', 'HVF_dwell90',
            'HVF_strong_dwell30', 'Dwell60_bo', 'Dwell90_bo',
            'HVF_dwell_no_retest',
            'HH_HL', 'Fib_support', 'CH_retest_bull', 'CH_any_bull',
        ]
        
        print(f"    {'Signal':<30} {'Acc':>5} {'Det':>4}/{'':<4} {'FP%':>5} {'Lead':>5} {'Score':>6}")
        print(f"    {'─'*65}")
        
        for name in key_signals:
            if name not in new_markup_rules:
                continue
            r = test_signal_combo(single_comp, [name], new_markup_rules, single_gt, 'MARKUP')
            flag = " ⭐" if r['accuracy'] > 0 and r['fps'] == 0 else ""
            print(f"    {name:<30} {r['accuracy']:>5.0%} {r['detected']:>4}/{r['total']:<4} "
                  f"{r['fp_rate']:>5.0%} {r['avg_lead']:>5.1f}d {r['score']:>6.1f}{flag}")

    # Restore original
    SignalComputer.signals_at = original_signals_at


def main():
    print("HVF + Channel Dwell + Breakout — Bear Bottom Signal Test")
    print("=" * 70)

    # Part 1: Qualitative analysis per coin
    for symbol in ['BNB/USDT', 'XRP/USDT', 'BTC/USDC', 'ETH/USDC', 'SOL/USDC']:
        analyze_coin(symbol)

    # Part 2: Matrix testing
    matrix_test()

    print(f"\n{'='*70}")
    print(f"  DONE")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
