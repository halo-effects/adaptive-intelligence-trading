import json, sys
sys.stdout.reconfigure(encoding='utf-8')

data = json.load(open('trading/spot/backtest_results/v12_lifecycle/eth_1h.json'))
d = data[0]

print("=== V12 Lifecycle Summary ===")
for k in ['pnl_pct','exit_phases','spring_phases','markup_phases','short_pnl','spring_pnl','markup_pnl']:
    print("  %s: %s" % (k, d.get(k, 'N/A')))

print("\n=== Chunk Timeline ===")
for c in d.get('chunks', []):
    phase = c.get('lifecycle_phase', '?')
    eq = c.get('final_equity', 0)
    cash = c.get('cash', 0)
    deals = c.get('completed_deals', 0)
    print("  Chunk %s: %s | eq=$%.0f cash=$%.0f deals=%d phase=%s" % (
        c['chunk'], c['period'], eq, cash, deals, phase))
