"""Test HVF-based FLAT routing to shorten FLAT phase and correctly route to DCA vs MARKDOWN.

Current FLAT behavior:
  - Post-top: waits up to 42 days for LH_LL+ADX+Fib_break, else defaults to DCA
  - Post-markdown/ranging: waits for ADX<20 sustained 14 days, then DCA
  
Problem: 42-day timeout too long. BTC enters DCA when it should enter MARKDOWN.
HVF is computed but only logged — never used for routing.

Test: Use HVF composite to accelerate FLAT decisions:
  - High HVF (>threshold) = energy compressed, breakout imminent → use direction signals
  - Low HVF = still trending, not compressed → stay flat or route to markdown
  
Direction signals to combine with HVF:
  1. Price vs SMA50 (above = bullish lean, below = bearish lean)
  2. LH_LL / HH_HL structure streaks
  3. CFGI level (fear = accumulation, greed = distribution)
  4. Price change since FLAT entry (trending down = bearish)
"""
import sqlite3
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack
from run_new_coins_profiles import make_config
from test_hvf_daily import composite_hvf_score

DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'candles.db'

COINS = ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']


def load_daily(coin: str) -> pd.DataFrame:
    """Load daily candles from DB."""
    conn = sqlite3.connect(DB_PATH)
    sym = coin
    df = pd.read_sql_query(
        "SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp",
        conn, params=(sym,))
    if df.empty:
        sym = coin.replace('/USDC', '/USDT')
        df = pd.read_sql_query(
            "SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp",
            conn, params=(sym,))
    conn.close()
    if df.empty:
        return df
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('date', inplace=True)
    return df


def analyze_flat_windows(coin: str, profile: str = 'high'):
    """Run V13, extract FLAT windows, compute HVF and direction signals during each."""
    pack = V13SignalPack(coin)
    cfg = make_config(profile)
    bt = V13BacktestV8(pack, cfg)
    bt.run()
    
    daily = load_daily(coin)
    if daily.empty:
        return []
    
    # Compute HVF for entire series
    hvf_composite, hvf_vuvu, hvf_vol, hvf_price = composite_hvf_score(daily, lookback=30)
    
    # Compute SMA50
    sma50 = daily['close'].rolling(50).mean()
    
    # Extract FLAT windows
    flat_windows = []
    for i, t in enumerate(bt.phase_log):
        if str(t.get('to', '')) != 'FLAT':
            continue
        
        flat_start = t.get('date')
        from_phase = str(t.get('from', ''))
        reason = t.get('reason', '')
        
        # Find exit
        exit_to = 'END'
        exit_date = None
        exit_days = 0
        for j in range(i+1, len(bt.phase_log)):
            nxt = bt.phase_log[j]
            if str(nxt.get('to', '')) != 'FLAT':
                exit_to = str(nxt.get('to', ''))
                exit_date = nxt.get('date')
                exit_days = (exit_date - flat_start).days if exit_date else 0
                break
        
        if exit_date is None:
            continue
        
        # Get daily data during FLAT window
        mask = (daily.index >= flat_start) & (daily.index <= exit_date)
        window_daily = daily[mask]
        
        if len(window_daily) < 3:
            continue
        
        # Price change during FLAT
        start_price = window_daily.iloc[0]['close']
        end_price = window_daily.iloc[-1]['close']
        price_chg = (end_price - start_price) / start_price * 100
        
        # HVF at various points during FLAT
        hvf_values = []
        for d in window_daily.index:
            idx = daily.index.get_indexer([d], method='pad')[0]
            if idx >= 0 and idx < len(hvf_composite):
                val = hvf_composite.iloc[idx]
                hvf_values.append({'date': d, 'hvf': float(val) if not hasattr(val, '__len__') else float(val)})
        
        # Find when HVF first exceeds thresholds
        hvf_cross_dates = {}
        for thresh in [0.2, 0.3, 0.4, 0.5]:
            for hv in hvf_values:
                if hv['hvf'] >= thresh and thresh not in hvf_cross_dates:
                    days_in = (hv['date'] - flat_start).days
                    hvf_cross_dates[thresh] = days_in
        
        # Direction signals at various points
        # Price vs SMA50
        sma50_signals = []
        for d in window_daily.index:
            idx = sma50.index.get_indexer([d], method='pad')[0]
            if idx >= 0:
                s = sma50.iloc[idx]
                p = daily.iloc[idx]['close']
                if not np.isnan(s):
                    sma50_signals.append('ABOVE' if p > s else 'BELOW')
        
        # Midpoint HVF
        mid_idx = len(hvf_values) // 2
        mid_hvf = hvf_values[mid_idx]['hvf'] if hvf_values and mid_idx < len(hvf_values) else 0
        
        # Peak HVF
        peak_hvf = max(hv['hvf'] for hv in hvf_values) if hvf_values else 0
        
        # Entry HVF (first day)
        entry_hvf = hvf_values[0]['hvf'] if hvf_values else 0
        
        # SMA50 at entry vs exit
        entry_sma = sma50_signals[0] if sma50_signals else '?'
        exit_sma = sma50_signals[-1] if sma50_signals else '?'
        
        # Determine if post-top
        post_top = from_phase == 'MARKUP'
        
        flat_windows.append({
            'coin': coin,
            'start': str(flat_start)[:10],
            'end': str(exit_date)[:10],
            'days': exit_days,
            'from': from_phase,
            'exit_to': exit_to,
            'reason': reason[:50],
            'price_chg': price_chg,
            'post_top': post_top,
            'entry_hvf': entry_hvf,
            'mid_hvf': mid_hvf,
            'peak_hvf': peak_hvf,
            'hvf_crosses': hvf_cross_dates,
            'entry_sma50': entry_sma,
            'exit_sma50': exit_sma,
        })
    
    return flat_windows


def test_routing_rules(all_windows: List[dict]):
    """Test various routing rules on all FLAT windows."""
    
    rules = [
        # (name, function(window) -> predicted_exit or None for "stay flat")
        ('CURRENT (42d timeout)', lambda w: None),  # baseline — just measure
        ('HVF>0.3 + SMA50_BELOW -> MD', lambda w: 
            'MARKDOWN' if w['peak_hvf'] > 0.3 and w['exit_sma50'] == 'BELOW' else None),
        ('HVF>0.3 + SMA50_ABOVE -> DCA', lambda w:
            'DCA' if w['peak_hvf'] > 0.3 and w['exit_sma50'] == 'ABOVE' else None),
        ('HVF>0.4 + price_drop>5% -> MD', lambda w:
            'MARKDOWN' if w['peak_hvf'] > 0.4 and w['price_chg'] < -5 else None),
        ('price_drop>5% + SMA50_BELOW -> MD (no HVF)', lambda w:
            'MARKDOWN' if w['price_chg'] < -5 and w['exit_sma50'] == 'BELOW' else None),
        ('SMA50_BELOW at entry -> MD lean', lambda w:
            'MARKDOWN' if w['entry_sma50'] == 'BELOW' else 'DCA'),
        ('HVF>0.3 within 14d -> early DCA/MD', lambda w:
            'MARKDOWN' if w['hvf_crosses'].get(0.3, 999) <= 14 and w['entry_sma50'] == 'BELOW'
            else ('DCA' if w['hvf_crosses'].get(0.3, 999) <= 14 else None)),
    ]
    
    print(f"\n{'='*110}")
    print(f"FLAT ROUTING RULE EVALUATION")
    print(f"{'='*110}")
    
    for rule_name, rule_fn in rules:
        correct = 0
        incorrect = 0
        no_signal = 0
        time_saved_days = 0
        details = []
        
        for w in all_windows:
            actual = w['exit_to']
            if actual not in ('DCA', 'MARKDOWN'):
                continue  # Skip END or other
            
            predicted = rule_fn(w)
            if predicted is None:
                no_signal += 1
                details.append(f"    {w['coin'][:3]} {w['start']} -> {actual:>10} | NO SIGNAL (stayed {w['days']}d)")
            elif predicted == actual:
                correct += 1
                # Time saved = days in FLAT minus 14 (min eval)
                saved = max(0, w['days'] - 14)
                time_saved_days += saved
                details.append(f"    {w['coin'][:3]} {w['start']} -> {actual:>10} | CORRECT ({predicted}) saved ~{saved}d")
            else:
                incorrect += 1
                details.append(f"    {w['coin'][:3]} {w['start']} -> {actual:>10} | WRONG (predicted {predicted}) ***")
        
        total = correct + incorrect + no_signal
        accuracy = correct / (correct + incorrect) * 100 if (correct + incorrect) > 0 else 0
        coverage = (correct + incorrect) / total * 100 if total > 0 else 0
        
        print(f"\n  Rule: {rule_name}")
        print(f"  Accuracy: {accuracy:.0f}% ({correct}/{correct+incorrect}) | Coverage: {coverage:.0f}% | "
              f"No-signal: {no_signal} | Time saved: ~{time_saved_days}d")
        if incorrect > 0:
            print(f"  *** WRONG predictions: {incorrect} ***")
        for d in details:
            print(d)


def main():
    print("FLAT PHASE ROUTING ANALYSIS")
    print("Testing HVF + direction signals for faster/better FLAT routing\n")
    
    all_windows = []
    
    for coin in COINS:
        print(f"\n{'='*110}")
        print(f"  {coin}")
        print(f"{'='*110}")
        
        windows = analyze_flat_windows(coin)
        all_windows.extend(windows)
        
        print(f"  {'Start':>12} {'End':>12} {'Days':>5} {'From':>10} {'Exit':>10} {'Price%':>8} "
              f"{'HVF_entry':>9} {'HVF_mid':>8} {'HVF_peak':>9} {'SMA50_in':>9} {'SMA50_out':>9}")
        print(f"  {'-'*12} {'-'*12} {'-'*5} {'-'*10} {'-'*10} {'-'*8} "
              f"{'-'*9} {'-'*8} {'-'*9} {'-'*9} {'-'*9}")
        
        for w in windows:
            hvf_cross_str = ','.join(f"{t}:{d}d" for t, d in sorted(w['hvf_crosses'].items()))
            print(f"  {w['start']:>12} {w['end']:>12} {w['days']:>5} {w['from']:>10} {w['exit_to']:>10} "
                  f"{w['price_chg']:>+7.1f}% {w['entry_hvf']:>9.3f} {w['mid_hvf']:>8.3f} {w['peak_hvf']:>9.3f} "
                  f"{w['entry_sma50']:>9} {w['exit_sma50']:>9}")
    
    # Test routing rules
    test_routing_rules(all_windows)
    
    # HVF timeline summary
    print(f"\n{'='*110}")
    print("HVF THRESHOLD CROSS TIMING (days into FLAT when HVF first exceeds threshold)")
    print(f"{'='*110}")
    print(f"  {'Coin':>5} {'Start':>12} {'Exit':>10} {'Days':>5} | {'HVF>0.2':>8} {'HVF>0.3':>8} {'HVF>0.4':>8} {'HVF>0.5':>8}")
    for w in all_windows:
        crosses = w['hvf_crosses']
        print(f"  {w['coin'][:3]:>5} {w['start']:>12} {w['exit_to']:>10} {w['days']:>5} | "
              f"{str(crosses.get(0.2,'--'))+'d':>8} {str(crosses.get(0.3,'--'))+'d':>8} "
              f"{str(crosses.get(0.4,'--'))+'d':>8} {str(crosses.get(0.5,'--'))+'d':>8}")


if __name__ == '__main__':
    main()
