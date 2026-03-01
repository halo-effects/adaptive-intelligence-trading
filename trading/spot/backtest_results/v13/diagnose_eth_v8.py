"""Diagnose ETH whipsawing in v8 — dump all phase transitions with details."""
import sys, os, importlib.util
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

spec = importlib.util.spec_from_file_location("v8", os.path.join(os.path.dirname(__file__), 'v13_phase_backtest_v8.py'))
v8 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v8)

cfg = v8.V13Config()
cfg.CAPITAL = 10000

pack = v8.V13SignalPack('ETH')
engine = v8.V13BacktestV8(pack, cfg)
result = engine.run()

if result:
    print(f"\n{'='*80}")
    print(f"ETH Phase Transitions: {result['phase_changes']} changes")
    print(f"{'='*80}")
    for i, p in enumerate(engine.phase_log):
        days_in = ''
        if i > 0:
            prev = engine.phase_log[i-1]['date']
            days_in = f" ({(p['date'] - prev).days}d in prev phase)"
        print(f"  {p['date'].strftime('%Y-%m-%d')}  {str(p['from']):>12} -> {str(p['to']):<12}  ${p['equity']:>10,.0f}  {p['reason']}{days_in}")
    
    print(f"\n{'='*80}")
    print(f"  Final equity: ${result.get('final_equity', result.get('equity', 0)):,.0f}")
    print(f"  ROI: {result.get('roi', result.get('roi_pct', 0)):+.1f}%")
    print(f"  Closed ROI: {result.get('closed_roi', 0):+.1f}%")
    print(f"  B&H: {result.get('buy_hold_return', 'N/A')}")
    print(f"  Max DD: {result.get('max_drawdown', 'N/A')}")
    print(f"  Phase changes: {result['phase_changes']}")
    
    from collections import defaultdict
    import pandas as pd
    phase_days = defaultdict(int)
    for i in range(1, len(engine.phase_log)):
        days = (engine.phase_log[i]['date'] - engine.phase_log[i-1]['date']).days
        phase_days[str(engine.phase_log[i-1]['to'])] += days
    if engine.phase_log:
        last = engine.phase_log[-1]
        end = pd.Timestamp(cfg.END_DATE)
        phase_days[str(last['to'])] += (end - last['date']).days

    print(f"\n  Days by phase:")
    for phase, days in sorted(phase_days.items()):
        print(f"    {phase}: {days}d")
    
    # Show short phases (< 7 days)
    print(f"\n  Short phases (< 7 days):")
    for i in range(1, len(engine.phase_log)):
        days = (engine.phase_log[i]['date'] - engine.phase_log[i-1]['date']).days if i < len(engine.phase_log) else 0
        if days < 7 and days > 0:
            p = engine.phase_log[i-1]
            print(f"    {p['date'].strftime('%Y-%m-%d')}  {str(p['to']):<12} lasted {days}d  reason: {p['reason']}")
