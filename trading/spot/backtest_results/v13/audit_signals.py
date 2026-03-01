"""
Full signal pipeline audit — traces from raw DB data through indicators to phase decisions.
Focuses on known problem periods:
  - ETH Oct 2020 → May 2021: HH_HL + Fib_support never fires (should enter MARKUP)
  - BTC May 2021 + Jun 2024: Bad MARKDOWN entries (MARKDOWN_FAIL shorts)
"""
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
from v13_signals import V13SignalPack, load_daily, _stoch_rsi, resample_nweek
from v13_phase_backtest_v8 import compute_fib_levels, price_near_fib_support, price_broke_fib_support, FIB_TOLERANCE

DB = Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'


def audit_data_quality(coin_symbol):
    """Audit 1: Raw data quality check."""
    print(f"\n{'='*70}")
    print(f"  AUDIT 1: Data Quality — {coin_symbol}")
    print(f"{'='*70}")
    
    conn = sqlite3.connect(str(DB))
    
    # 1h candle coverage
    h1 = pd.read_sql(
        "SELECT MIN(timestamp) as min_ts, MAX(timestamp) as max_ts, COUNT(*) as cnt "
        "FROM candles WHERE symbol=?", conn, params=[coin_symbol])
    if h1['cnt'].iloc[0] == 0:
        print(f"  ❌ NO 1h candles for {coin_symbol}")
        conn.close()
        return
    min_dt = pd.to_datetime(h1['min_ts'].iloc[0], unit='ms')
    max_dt = pd.to_datetime(h1['max_ts'].iloc[0], unit='ms')
    print(f"  1h candles: {h1['cnt'].iloc[0]:,} rows, {min_dt.date()} → {max_dt.date()}")
    
    # Check for gaps in 1h data
    candles = pd.read_sql(
        "SELECT timestamp FROM candles WHERE symbol=? ORDER BY timestamp",
        conn, params=[coin_symbol])
    ts = candles['timestamp'].values
    diffs = np.diff(ts) / 3600000  # hours
    gaps = np.where(diffs > 2)[0]  # More than 2h gap
    if len(gaps) > 0:
        print(f"  ⚠️  {len(gaps)} gaps > 2h in 1h data:")
        for g in gaps[:10]:
            gap_start = pd.to_datetime(ts[g], unit='ms')
            gap_end = pd.to_datetime(ts[g+1], unit='ms')
            print(f"    {gap_start} → {gap_end} ({diffs[g]:.0f}h gap)")
        if len(gaps) > 10:
            print(f"    ... and {len(gaps)-10} more gaps")
    else:
        print(f"  ✅ No gaps > 2h in 1h data")
    
    # Daily candle coverage
    daily = pd.read_sql(
        "SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp",
        conn, params=[coin_symbol])
    print(f"\n  Daily candles: {len(daily)} rows")
    if len(daily) > 0:
        daily['dt'] = pd.to_datetime(daily['timestamp'], unit='ms')
        print(f"  Range: {daily['dt'].iloc[0].date()} → {daily['dt'].iloc[-1].date()}")
        
        # Check indicator coverage
        for col in ['sma50', 'sma200', 'adx', 'consec_hh_hl', 'price_vs_sma200']:
            non_null = daily[col].notna().sum()
            first_valid = daily[daily[col].notna()]['dt'].iloc[0].date() if non_null > 0 else 'NONE'
            print(f"  {col}: {non_null}/{len(daily)} non-null, first valid: {first_valid}")
    
    conn.close()
    return daily


def audit_hh_hl_computation(coin_symbol, start='2020-10-01', end='2021-06-01'):
    """Audit 2: Trace HH/HL computation day-by-day."""
    print(f"\n{'='*70}")
    print(f"  AUDIT 2: HH/HL Streak Computation — {coin_symbol} ({start} → {end})")
    print(f"{'='*70}")
    
    conn = sqlite3.connect(str(DB))
    daily = pd.read_sql(
        "SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp",
        conn, params=[coin_symbol])
    conn.close()
    
    if len(daily) == 0:
        print("  ❌ No daily data")
        return
    
    daily['dt'] = pd.to_datetime(daily['timestamp'], unit='ms')
    daily.set_index('dt', inplace=True)
    
    mask = (daily.index >= start) & (daily.index <= end)
    window = daily[mask]
    
    print(f"  Days in window: {len(window)}")
    if len(window) == 0:
        print("  ❌ No data in window")
        return
    
    # Manually recompute HH/HL to verify DB values
    print(f"\n  {'Date':<12} {'High':>10} {'Low':>10} {'Close':>10} {'HH':>4} {'HL':>4} {'DB_streak':>10} {'Calc_streak':>11}")
    print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*4} {'-'*4} {'-'*10} {'-'*11}")
    
    calc_streak = 0
    prev_high = None
    prev_low = None
    
    # Include one day before window for context
    start_idx = max(0, daily.index.get_loc(window.index[0]) - 1)
    
    streaks_with_2_plus = []
    
    for i in range(len(window)):
        row = window.iloc[i]
        date = window.index[i]
        
        hh = row['high'] > daily.loc[:date, 'high'].iloc[-2] if i > 0 or start_idx > 0 else False
        hl = row['low'] > daily.loc[:date, 'low'].iloc[-2] if i > 0 or start_idx > 0 else False
        
        if hh and hl:
            calc_streak += 1
        else:
            calc_streak = 0
        
        db_streak = row.get('consec_hh_hl', 'N/A')
        
        # Only print days with streaks or every 7th day for context
        if calc_streak >= 1 or (i % 7 == 0):
            flag = " ⬅️ ENTRY SIGNAL" if calc_streak >= 2 else ""
            mismatch = " ❌ MISMATCH" if db_streak != calc_streak and not np.isnan(float(db_streak)) else ""
            print(f"  {date.date()!s:<12} {row['high']:>10,.2f} {row['low']:>10,.2f} {row['close']:>10,.2f} "
                  f"{'Y' if hh else 'N':>4} {'Y' if hl else 'N':>4} {db_streak:>10} {calc_streak:>11}{flag}{mismatch}")
        
        if calc_streak >= 2:
            streaks_with_2_plus.append(date)
    
    print(f"\n  Total days with consec_hh_hl >= 2: {len(streaks_with_2_plus)}")
    if streaks_with_2_plus:
        print(f"  Dates: {', '.join(str(d.date()) for d in streaks_with_2_plus[:20])}")


def audit_fib_levels(coin_symbol, dates_to_check):
    """Audit 3: Trace Fibonacci level computation at key dates."""
    print(f"\n{'='*70}")
    print(f"  AUDIT 3: Fibonacci Levels — {coin_symbol}")
    print(f"{'='*70}")
    
    daily = load_daily(coin_symbol.split('/')[0])
    if daily is None:
        print("  ❌ No daily data")
        return
    
    for date_str in dates_to_check:
        date = pd.Timestamp(date_str)
        price = daily.loc[daily.index <= date, 'close'].iloc[-1]
        fib = compute_fib_levels(daily, date)
        near = price_near_fib_support(price, fib)
        broke = price_broke_fib_support(price, fib)
        
        print(f"\n  {date.date()}: Close=${price:,.2f}")
        if fib:
            print(f"    Swing High: ${fib['swing_high']:,.2f}")
            print(f"    Swing Low:  ${fib['swing_low']:,.2f}")
            for ratio in [0.236, 0.382, 0.5, 0.618, 0.786]:
                level = fib.get(ratio, 0)
                dist = abs(price - level) / level * 100 if level > 0 else 999
                within = "✅ NEAR" if dist < FIB_TOLERANCE * 100 else ""
                print(f"    Fib {ratio}: ${level:,.2f} (dist={dist:.1f}%) {within}")
            print(f"    → near_fib_support={near}, broke_fib_support={broke}")
        else:
            print(f"    ⚠️  No Fib levels computed (no valid swing)")


def audit_markup_gate(coin_symbol, start='2020-10-01', end='2021-06-01'):
    """Audit 4: Full markup entry gate check — HH_HL + Fib_support + SMA200."""
    print(f"\n{'='*70}")
    print(f"  AUDIT 4: Full MARKUP Entry Gate — {coin_symbol} ({start} → {end})")
    print(f"{'='*70}")
    
    pack = V13SignalPack(coin_symbol.split('/')[0])
    daily = pack.daily
    
    mask = (daily.index >= start) & (daily.index <= end)
    window = daily[mask]
    
    print(f"  Days in window: {len(window)}")
    
    blocked_days = []
    passed_days = []
    
    for i, (date, row) in enumerate(window.iterrows()):
        # Check HH_HL
        hh_hl = pack.structure.hh_hl_streak(date, min_streak=2)
        if not hh_hl:
            continue
        
        # HH_HL fires — now check Fib
        price = row['close']
        fib = compute_fib_levels(daily, date)
        near_fib = price_near_fib_support(price, fib)
        
        # Check SMA200 overextension
        overext = pack.sma200.overextension_at(date)
        sma200_blocked = not np.isnan(overext) and overext > 20
        
        # Check ADX
        adx = pack.structure.adx_at(date)
        
        status = "PASS ✅" if (near_fib and not sma200_blocked) else "BLOCKED"
        reasons = []
        if not near_fib:
            reasons.append(f"Fib_support=False")
            if fib:
                # Show nearest fib level
                min_dist = 999
                nearest_ratio = None
                for ratio in [0.236, 0.382, 0.5, 0.618, 0.786]:
                    level = fib.get(ratio, 0)
                    if level > 0:
                        dist = abs(price - level) / level
                        if dist < min_dist:
                            min_dist = dist
                            nearest_ratio = ratio
                reasons.append(f"nearest_fib={nearest_ratio}@{min_dist*100:.1f}%")
            else:
                reasons.append("no_fibs")
        if sma200_blocked:
            reasons.append(f"SMA200_overext={overext:.1f}%")
        
        if near_fib and not sma200_blocked:
            passed_days.append(date)
        else:
            blocked_days.append((date, reasons))
        
        print(f"  {date.date()}: HH_HL=True, price=${price:,.2f}, fib_near={near_fib}, "
              f"SMA200={overext:.1f}%, ADX={adx:.1f} → {status} {' | '.join(reasons)}")
    
    print(f"\n  Summary: {len(passed_days)} PASS, {len(blocked_days)} BLOCKED")
    if passed_days:
        print(f"  First PASS: {passed_days[0].date()}")
    if blocked_days and not passed_days:
        print(f"  ❌ NO MARKUP ENTRY possible in entire window!")
        # Group blocked reasons
        fib_blocked = sum(1 for _, r in blocked_days if any('Fib_support=False' in x for x in r))
        sma_blocked = sum(1 for _, r in blocked_days if any('SMA200_overext' in x for x in r))
        print(f"     Fib_support blocked: {fib_blocked}")
        print(f"     SMA200 blocked: {sma_blocked}")


def audit_markdown_entries(coin_symbol, shorts_to_check):
    """Audit 5: Check MARKDOWN entry signals for known bad shorts."""
    print(f"\n{'='*70}")
    print(f"  AUDIT 5: MARKDOWN Entry Audit — {coin_symbol}")
    print(f"{'='*70}")
    
    pack = V13SignalPack(coin_symbol.split('/')[0])
    daily = pack.daily
    
    for entry_date_str, context in shorts_to_check:
        date = pd.Timestamp(entry_date_str)
        
        # Find the actual MARKDOWN entry conditions
        nearby = daily[(daily.index >= date - pd.Timedelta(days=3)) & (daily.index <= date + pd.Timedelta(days=3))]
        
        print(f"\n  MARKDOWN entry near {date.date()} ({context})")
        for d, row in nearby.iterrows():
            price = row['close']
            adx = row.get('adx', np.nan)
            fib = compute_fib_levels(daily, d)
            broke = price_broke_fib_support(price, fib)
            overext = row.get('price_vs_sma200', np.nan)
            lh_ll = row.get('consec_lh_ll', 0)
            
            # What was the actual price direction next 30/60/90 days?
            future = daily[daily.index > d].head(90)
            if len(future) > 0:
                max_up = (future['high'].max() - price) / price * 100
                min_down = (future['low'].min() - price) / price * 100
            else:
                max_up = min_down = 0
            
            trigger = "🔴 TRIGGER" if (not np.isnan(adx) and adx > 20 and broke) else ""
            print(f"    {d.date()}: close=${price:,.2f}, ADX={adx:.1f}, LH/LL={lh_ll}, "
                  f"fib_broke={broke}, SMA200%={overext:.1f}% {trigger}")
            if trigger:
                print(f"      → Next 90d: max_up={max_up:+.1f}%, max_down={min_down:+.1f}%")
                if fib:
                    golden = fib.get(0.618, 0)
                    deep = fib.get(0.786, 0)
                    print(f"      → Fib 0.618=${golden:,.2f}, 0.786=${deep:,.2f}, swing_low=${fib['swing_low']:,.2f}")


def audit_compute_fib_internals(coin_symbol, date_str):
    """Audit 6: Deep dive into Fib computation internals."""
    print(f"\n{'='*70}")
    print(f"  AUDIT 6: Fib Computation Internals — {coin_symbol} @ {date_str}")
    print(f"{'='*70}")
    
    daily = load_daily(coin_symbol.split('/')[0])
    date = pd.Timestamp(date_str)
    
    # Reproduce compute_fib_levels logic
    lookback = 44
    idx = daily.index.get_indexer([date], method='pad')[0]
    window = daily.iloc[max(0, idx - lookback):idx + 1]
    
    swing_high_idx = window['high'].idxmax()
    swing_low_idx = window['low'].idxmin()
    
    swing_high = {'date': swing_high_idx, 'price': window.loc[swing_high_idx, 'high']}
    swing_low = {'date': swing_low_idx, 'price': window.loc[swing_low_idx, 'low']}
    
    print(f"  Lookback window: {window.index[0].date()} → {window.index[-1].date()} ({len(window)} days)")
    print(f"  Swing High: ${swing_high['price']:,.2f} on {swing_high_idx.date()}")
    print(f"  Swing Low:  ${swing_low['price']:,.2f} on {swing_low_idx.date()}")
    print(f"  Range: ${swing_high['price'] - swing_low['price']:,.2f}")
    
    if swing_high['price'] <= swing_low['price']:
        print(f"  ❌ Invalid swing (high <= low), no Fib levels!")
        return
    
    price = daily.loc[daily.index <= date, 'close'].iloc[-1]
    rng = swing_high['price'] - swing_low['price']
    print(f"  Current price: ${price:,.2f}")
    print(f"\n  Fib Levels (retracement from high):")
    for ratio in [0.236, 0.382, 0.5, 0.618, 0.786]:
        level = swing_high['price'] - rng * ratio
        dist = abs(price - level) / level * 100
        within = f"  ✅ WITHIN TOLERANCE ({FIB_TOLERANCE*100}%)" if dist < FIB_TOLERANCE * 100 else ""
        print(f"    {ratio}: ${level:,.2f} (price dist: {dist:.2f}%){within}")


if __name__ == '__main__':
    print("=" * 70)
    print("  V13 SIGNAL PIPELINE AUDIT")
    print("=" * 70)
    
    # ── ETH AUDIT (missed 2020-2021 bull run) ──
    
    print("\n\n" + "█" * 70)
    print("  ETH/USDC — Why no MARKUP Oct 2020 → May 2021?")
    print("█" * 70)
    
    eth_daily = audit_data_quality('ETH/USDC')
    audit_hh_hl_computation('ETH/USDC', '2020-10-01', '2021-06-01')
    
    # Check Fib levels at key dates during ETH bull run
    audit_fib_levels('ETH/USDC', [
        '2020-11-01', '2020-12-01', '2021-01-01', '2021-02-01',
        '2021-03-01', '2021-04-01', '2021-05-01'
    ])
    
    audit_markup_gate('ETH/USDC', '2020-10-01', '2021-06-01')
    
    # Deep Fib internals for a specific date where HH_HL fires
    # (will know which dates after seeing HH_HL audit)
    
    # ── BTC AUDIT (reference — works correctly) ──
    
    print("\n\n" + "█" * 70)
    print("  BTC/USDC — Reference (enters MARKUP Oct 5, 2020)")
    print("█" * 70)
    
    btc_daily = audit_data_quality('BTC/USDC')
    audit_hh_hl_computation('BTC/USDC', '2020-10-01', '2020-10-10')
    audit_markup_gate('BTC/USDC', '2020-10-01', '2020-10-10')
    
    # ── BTC Bad Shorts ──
    
    print("\n\n" + "█" * 70)
    print("  BTC/USDC — Bad MARKDOWN entries")
    print("█" * 70)
    
    audit_markdown_entries('BTC/USDC', [
        ('2021-05-15', 'Short at $46.7K → lost 32% as BTC went to $61.7K'),
        ('2024-06-24', 'Short at $60.3K → lost 27% as BTC went to $76.5K'),
    ])
    
    # ── SOL Bad Shorts ──
    
    print("\n\n" + "█" * 70)
    print("  SOL/USDC — MARKDOWN_FAIL entry")  
    print("█" * 70)
    
    audit_markdown_entries('SOL/USDC', [
        ('2024-06-15', 'Short at $145.5 → lost 26% as SOL went to $183'),
    ])
