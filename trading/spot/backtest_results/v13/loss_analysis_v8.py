"""Comprehensive loss analysis across all 5 coins — where is money being lost?"""
import sys, os, importlib.util
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

spec = importlib.util.spec_from_file_location('v8', os.path.join(os.path.dirname(__file__), 'v13_phase_backtest_v8.py'))
v8 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v8)

import pandas as pd, numpy as np

coins = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP']

print("=" * 90)
print("  V13 v8 LOSS ANALYSIS — WHERE IS MONEY BEING LOST?")
print("=" * 90)

all_losses = []

for coin in coins:
    cfg = v8.V13Config()
    try:
        pack = v8.V13SignalPack(coin)
    except Exception as e:
        print(f"\n  SKIP {coin}: {e}")
        continue
    
    engine = v8.V13BacktestV8(pack, cfg)
    result = engine.run()
    if not result:
        continue
    
    print(f"\n{'='*70}")
    print(f"  {coin}: ROI={result['roi']:+.1f}%, B&H={result['buy_hold_return']:+.1f}%, Alpha={result['roi']-result['buy_hold_return']:+.1f}%")
    print(f"{'='*70}")
    
    # Analyze each markup phase — where did we make/lose money?
    for i in range(len(engine.phase_log)):
        p = engine.phase_log[i]
        end_p = engine.phase_log[i+1] if i+1 < len(engine.phase_log) else None
        end_date = end_p['date'] if end_p else pd.Timestamp(cfg.END_DATE)
        end_eq = end_p['equity'] if end_p else result.get('equity', p['equity'])
        
        phase_pnl = end_eq - p['equity']
        phase_pnl_pct = (end_eq / p['equity'] - 1) * 100 if p['equity'] > 0 else 0
        days = (end_date - p['date']).days
        
        if phase_pnl_pct < -1:  # Show losses > 1%
            marker = "*** LOSS ***"
        elif phase_pnl_pct > 5:
            marker = "profit"
        else:
            marker = "flat"
        
        # Get entry/exit prices
        mask = (engine.daily.index >= p['date']) & (engine.daily.index <= end_date)
        phase_data = engine.daily[mask]
        if len(phase_data) > 0:
            p_start = phase_data['close'].iloc[0]
            p_end = phase_data['close'].iloc[-1]
            p_high = phase_data['close'].max()
            p_low = phase_data['close'].min()
        else:
            p_start = p_end = p_high = p_low = 0
        
        if phase_pnl_pct < -1 or abs(phase_pnl) > 200:
            print(f"\n  {p['date'].strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')} ({days}d): {p['to']}")
            print(f"    Equity: ${p['equity']:,.0f} -> ${end_eq:,.0f} ({phase_pnl_pct:+.1f}%) {marker}")
            print(f"    Price: ${p_start:,.0f} -> ${p_end:,.0f} (high=${p_high:,.0f}, low=${p_low:,.0f})")
            if end_p:
                print(f"    Exit reason: {end_p['reason']}")
            
            if phase_pnl_pct < -1:
                all_losses.append({
                    'coin': coin, 'phase': str(p['to']), 
                    'start': p['date'].strftime('%Y-%m-%d'),
                    'days': days, 'pnl_pct': phase_pnl_pct,
                    'pnl_usd': phase_pnl,
                    'reason': end_p['reason'] if end_p else 'OPEN',
                    'entry_price': p_start, 'exit_price': p_end
                })
    
    # Show all trades with P&L
    losing_trades = [t for t in engine.trades if t.get('pnl_pct', 0) < -1]
    if losing_trades:
        print(f"\n  Losing trades:")
        for t in losing_trades:
            print(f"    {t['date'].strftime('%Y-%m-%d')}: {t['action']:<35} @ ${t['price']:>10,.0f}  pnl={t['pnl_pct']:+.1f}%  (${t['amount']:,.0f})")
    
    # Time in cash (FLAT/DCA without position)
    flat_days = 0
    for i in range(len(engine.phase_log)):
        p = engine.phase_log[i]
        if p['to'] in ('FLAT',):
            end_d = engine.phase_log[i+1]['date'] if i+1 < len(engine.phase_log) else pd.Timestamp(cfg.END_DATE)
            flat_days += (end_d - p['date']).days
    total_days = (pd.Timestamp(cfg.END_DATE) - pd.Timestamp(cfg.START_DATE)).days
    print(f"\n  Time in FLAT (cash): {flat_days}d / {total_days}d ({flat_days/total_days*100:.0f}%)")

# Summary
print(f"\n\n{'='*90}")
print(f"  LOSS SUMMARY — ALL COINS")
print(f"{'='*90}")
if all_losses:
    total_loss = sum(l['pnl_usd'] for l in all_losses)
    print(f"\n  {'Coin':<5} {'Phase':<10} {'Start':<12} {'Days':>5} {'PnL%':>8} {'PnL$':>10} {'Reason'}")
    print(f"  {'-'*80}")
    for l in sorted(all_losses, key=lambda x: x['pnl_pct']):
        print(f"  {l['coin']:<5} {l['phase']:<10} {l['start']:<12} {l['days']:>5} {l['pnl_pct']:>+7.1f}% ${l['pnl_usd']:>+9,.0f}  {l['reason'][:50]}")
    print(f"\n  Total losses: ${total_loss:,.0f} across {len(all_losses)} losing phases")
    
    # Categorize losses
    markup_fails = [l for l in all_losses if 'MARKUP' in l['phase'] and 'fail' in l['reason'].lower()]
    bad_entries = [l for l in all_losses if 'MARKUP' in l['phase'] and 'fail' not in l['reason'].lower()]
    short_losses = [l for l in all_losses if 'MARKDOWN' in l['phase']]
    
    if markup_fails:
        print(f"\n  Markup failures (safety net): {len(markup_fails)} events, ${sum(l['pnl_usd'] for l in markup_fails):,.0f}")
    if bad_entries:
        print(f"  Bad markup entries (sold low): {len(bad_entries)} events, ${sum(l['pnl_usd'] for l in bad_entries):,.0f}")
    if short_losses:
        print(f"  Short losses: {len(short_losses)} events, ${sum(l['pnl_usd'] for l in short_losses):,.0f}")
else:
    print("  No significant losses found!")
