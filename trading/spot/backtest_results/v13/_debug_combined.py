"""Debug: why does ETH bottom conviction not fire in combined test?"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from v13_router_engine_v2 import V13RouterV2, V13Config, V13SignalPack, Phase

coin = 'ETH/USDC'
pack = V13SignalPack(coin)

# Bottom only (should match old v2 test with ETH trigger Jun 2025)
eng = V13RouterV2(pack, V13Config(), conviction_enabled=True, top_detection_enabled=False,
                  exhaustion_mode='k_lift', exhaustion_tf='2W', min_score=3)
eng.cfg.CAPITAL = 2500
eng.cfg.START_DATE = '2024-10-01'
r = eng.run()

print(f"ETH bottom_only: ${r['final_equity']:,.2f}")
print(f"top_detected: {r['top_detected']}")
print(f"conviction_fired: {r['conviction_fired']}")
print(f"conviction_triggers: {r['conviction_triggers']}")

# Print phase changes
phase_trades = [t for t in eng.trades if 'PHASE' in str(t.get('action','')) or 
                'CONVICTION' in str(t.get('action','')) or
                'EARLY_WARNING' in str(t.get('action','')) or
                'PRIMARY' in str(t.get('action','')) or
                'FALLBACK' in str(t.get('action','')) or
                'FAILSAFE' in str(t.get('action','')) or
                'RANGING' in str(t.get('action','')) or
                'FAIL' in str(t.get('action',''))]

print(f"\nKey trades:")
for t in eng.trades:
    a = str(t.get('action',''))
    if any(k in a for k in ['PHASE_', 'CONVICTION', 'EARLY', 'PRIMARY', 'FALLBACK', 
                             'FAILSAFE', 'RANGING', 'MARKUP_FAIL', 'BUY_T', 'SELL_ALL',
                             'SHORT_T', 'CLOSE_SHORT']):
        print(f"  {t['date'].strftime('%Y-%m-%d') if hasattr(t['date'],'strftime') else t['date']} | {a} | ${t['price']:.2f}")

print(f"\n_top_detected = {eng._top_detected}")
print(f"_conviction_fired = {eng._conviction_fired}")
print(f"_no_reshort = {eng._no_reshort}")
