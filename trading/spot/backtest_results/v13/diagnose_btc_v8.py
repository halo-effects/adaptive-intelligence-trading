"""Deep dive into BTC v8 — why only +7.8%?"""
import sys, os, importlib.util
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

spec = importlib.util.spec_from_file_location('v8', os.path.join(os.path.dirname(__file__), 'v13_phase_backtest_v8.py'))
v8 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v8)

import pandas as pd, numpy as np

cfg = v8.V13Config()
pack = v8.V13SignalPack('BTC')
engine = v8.V13BacktestV8(pack, cfg)
result = engine.run()

if result:
    print("BTC DETAILED PHASE ANALYSIS")
    print("=" * 80)
    
    for i, p in enumerate(engine.phase_log):
        end_date = engine.phase_log[i+1]['date'] if i+1 < len(engine.phase_log) else pd.Timestamp(cfg.END_DATE)
        days = (end_date - p['date']).days
        print(f"\n{p['date'].strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')} ({days}d): {p['to']}")
        print(f"  Reason: {p['reason']}")
        print(f"  Equity at start: ${p['equity']:,.0f}")
        
        # Get price range during phase
        mask = (engine.daily.index >= p['date']) & (engine.daily.index <= end_date)
        phase_data = engine.daily[mask]
        if len(phase_data) > 0:
            print(f"  Price: ${phase_data['close'].iloc[0]:,.0f} -> ${phase_data['close'].iloc[-1]:,.0f} (range ${phase_data['close'].min():,.0f}-${phase_data['close'].max():,.0f})")
    
    print("\n" + "=" * 80)
    print("ALL TRADES:")
    print("=" * 80)
    for t in engine.trades:
        extra = f" pnl={t['pnl_pct']:+.1f}%" if 'pnl_pct' in t else ""
        print(f"  {t['date'].strftime('%Y-%m-%d')}: {t['action']:<35} @ ${t['price']:>10,.0f}  amt=${t['amount']:>8,.0f}{extra}")
    
    print(f"\nFinal: ${result.get('equity', 0):,.0f}, ROI={result['roi']:+.1f}%, Closed={result['closed_roi']:+.1f}%")
    print(f"B&H: {result['buy_hold_return']:+.1f}%")
    
    # Key question: how much time was BTC in cash vs invested?
    total_days = (pd.Timestamp(cfg.END_DATE) - pd.Timestamp(cfg.START_DATE)).days
    phase_days = {}
    for i in range(len(engine.phase_log)):
        end_d = engine.phase_log[i+1]['date'] if i+1 < len(engine.phase_log) else pd.Timestamp(cfg.END_DATE)
        days = (end_d - engine.phase_log[i]['date']).days
        ph = str(engine.phase_log[i]['to'])
        phase_days[ph] = phase_days.get(ph, 0) + days
    
    print(f"\nTime allocation ({total_days} total days):")
    for ph, d in sorted(phase_days.items()):
        print(f"  {ph}: {d}d ({d/total_days*100:.0f}%)")
