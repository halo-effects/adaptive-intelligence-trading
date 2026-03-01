"""Check SMA50 slope and price vs SMA200 at ALL markup entries for all 3 coins."""
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from v13_signals import V13SignalPack
from v13_phase_backtest_v8 import V13BacktestV8, V13Config
import pandas as pd
import numpy as np

COINS = ['ETH', 'SOL', 'BTC']
STARTS = {'ETH': '2020-10-01', 'BTC': '2020-10-01', 'SOL': '2021-07-01'}

for coin in COINS:
    pack = V13SignalPack(coin)
    cfg = V13Config()
    cfg.START_DATE = STARTS[coin]
    cfg.END_DATE = '2026-02-17'
    bt = V13BacktestV8(pack, cfg)
    bt.run()
    daily = bt.daily
    
    print(f"\n{'='*120}")
    print(f"  {coin} — All MARKUP Entries")
    print(f"{'='*120}")
    print(f"  {'Date':<12} {'Entry$':>10} {'Exit$':>10} {'P&L':>8} {'Days':>5} {'HH_HL':>6} {'ADX':>6} {'vsSMA200':>9} {'SMA50slp':>9} {'ExitReason':<35} {'SMA50<0?'}")
    print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*8} {'-'*5} {'-'*6} {'-'*6} {'-'*9} {'-'*9} {'-'*35} {'-'*10}")
    
    # Find MARKUP entries from phase_log
    for i, p in enumerate(bt.phase_log):
        if p['to'] == 'MARKUP':
            entry_date = p['date']
            entry_price = p['price']
            
            # Find matching exit (next non-MARKUP transition)
            exit_info = None
            for j in range(i+1, len(bt.phase_log)):
                if bt.phase_log[j]['from'] == 'MARKUP':
                    exit_info = bt.phase_log[j]
                    break
            
            if exit_info:
                exit_date = exit_info['date']
                exit_price = exit_info['price']
                exit_reason = exit_info['reason'][:35]
                pnl = (exit_price / entry_price - 1) * 100
                days = (exit_date - entry_date).days
            else:
                exit_price = 0
                exit_reason = 'STILL_IN_MARKUP'
                pnl = 0
                days = 0
            
            # Get indicators at entry
            row = daily[daily.index <= entry_date].iloc[-1]
            hh_hl = row.get('consec_hh_hl', 0)
            adx = row.get('adx', np.nan)
            vs_sma200 = row.get('price_vs_sma200', np.nan)
            sma50_slope = row.get('sma50_slope', np.nan)
            
            is_fail = 'FAIL' in str(exit_reason) or 'fail' in str(exit_reason)
            neg_slope = sma50_slope < 0 if not np.isnan(sma50_slope) else False
            
            if is_fail and neg_slope:
                tag = " <-- SAVED"
            elif not is_fail and neg_slope:
                tag = " <-- FALSE BLOCK"
            else:
                tag = ""
            
            print(f"  {entry_date.strftime('%Y-%m-%d'):<12} ${entry_price:>9.2f} ${exit_price:>9.2f} {pnl:>+7.1f}% {days:>5} {hh_hl:>6} {adx:>6.1f} {vs_sma200:>+8.1f}% {sma50_slope:>+8.2f}% {exit_reason:<35} {str(neg_slope):>5}{tag}")

# Summary
print(f"\n{'='*120}")
print(f"  SUMMARY: Would 'SMA50 slope > 0' gate block bad entries without blocking good ones?")
print(f"{'='*120}")
