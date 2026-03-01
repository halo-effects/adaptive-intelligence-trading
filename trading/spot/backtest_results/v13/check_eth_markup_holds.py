"""Check ETH markup behavior - did we hold through pullbacks or sell early?"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import importlib.util
spec = importlib.util.spec_from_file_location('v8', os.path.join(os.path.dirname(__file__), 'v13_phase_backtest_v8.py'))
v8 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v8)

import pandas as pd
import numpy as np

cfg = v8.V13Config()
pack = v8.V13SignalPack('ETH')
engine = v8.V13BacktestV8(pack, cfg)
result = engine.run()

if result:
    print("ETH MARKUP PHASE ANALYSIS")
    print("=" * 80)
    
    # Find all markup phases
    for i in range(len(engine.phase_log)):
        p = engine.phase_log[i]
        if p['to'] != v8.Phase.MARKUP:
            continue
        
        # Find end of this markup
        end_p = engine.phase_log[i+1] if i+1 < len(engine.phase_log) else None
        start_date = p['date']
        end_date = end_p['date'] if end_p else pd.Timestamp(cfg.END_DATE)
        days = (end_date - start_date).days
        
        entry_price = p['price']
        exit_price = end_p['price'] if end_p else engine.daily.loc[engine.daily.index <= end_date, 'close'].iloc[-1]
        exit_reason = end_p['reason'] if end_p else 'STILL OPEN'
        
        print(f"\nMARKUP #{i}: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')} ({days}d)")
        print(f"  Entry: ${entry_price:,.0f} -> Exit: ${exit_price:,.0f} ({(exit_price/entry_price-1)*100:+.1f}%)")
        print(f"  Exit reason: {exit_reason}")
        
        # Check for pullbacks during this markup
        mask = (engine.daily.index >= start_date) & (engine.daily.index <= end_date)
        markup_data = engine.daily[mask]
        
        if len(markup_data) > 0:
            peak = markup_data['high'].cummax()
            drawdown = (markup_data['close'] - peak) / peak * 100
            
            # Find significant pullbacks (> 10%)
            in_pullback = False
            pullback_start = None
            pullback_peak = 0
            
            print(f"  Price range: ${markup_data['close'].min():,.0f} - ${markup_data['close'].max():,.0f}")
            print(f"  Max intra-phase drawdown: {drawdown.min():.1f}%")
            
            # Weekly price + check for pullbacks
            print(f"\n  Weekly prices during markup:")
            for date, row in markup_data.iterrows():
                if date.weekday() == 0:  # Monday
                    dd = drawdown.loc[date]
                    note = ""
                    if dd < -10:
                        note = " ** PULLBACK"
                    elif dd < -5:
                        note = " * dip"
                    print(f"    {date.strftime('%Y-%m-%d')}: ${row['close']:>7,.0f}  dd={dd:+.1f}%{note}")
        
        # Check trades during this markup
        markup_trades = [t for t in engine.trades 
                        if t['date'] >= start_date and t['date'] <= end_date]
        if markup_trades:
            print(f"\n  Trades during markup:")
            for t in markup_trades:
                extra = f" pnl={t['pnl_pct']:+.1f}%" if 'pnl_pct' in t else ""
                print(f"    {t['date'].strftime('%Y-%m-%d')}: {t['action']} @ ${t['price']:,.0f} (${t['amount']:,.0f}){extra}")
