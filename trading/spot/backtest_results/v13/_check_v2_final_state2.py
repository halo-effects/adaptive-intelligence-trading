"""Check final state of v2_full."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from v13_router_engine_v2 import V13RouterV2, V13Config, Phase, V13SignalPack
from _backtest_full_v2_final import V13RouterV2Final, compute_2d_divergence_dates

coins = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
capital = 10000
per_coin = capital / len(coins)
total_eq = 0

for coin in coins:
    base = coin.split('/')[0]
    div_dates = compute_2d_divergence_dates(coin)
    pack = V13SignalPack(base)
    eng = V13RouterV2Final(pack, V13Config(), conviction_enabled=True,
                          min_score=3, exhaustion_tf='2W', exhaustion_mode='k_lift',
                          div_dates=div_dates, top_timing_enabled=True, max_wait_days=35)
    eng.cfg.CAPITAL = per_coin
    r = eng.run()
    
    # Check result keys
    print(f"\n{coin}: ${r['final_equity']:,.0f} ({r['roi']:+.1f}%)")
    print(f"  Phase: {r.get('final_phase', 'unknown')}")
    print(f"  Trades: {r['total_trades']}")
    
    # Check for open positions from result dict
    for k in sorted(r.keys()):
        if any(x in k.lower() for x in ['short', 'coin', 'cash', 'open', 'position', 'invested', 'unrealized']):
            print(f"  {k}: {r[k]}")
    
    # Check engine state directly
    for attr in ['coins', 'short_coins', 'short_entry_price', 'invested', 
                 'phase', 'entry_price', '_capital', 'capital']:
        if hasattr(eng, attr):
            val = getattr(eng, attr)
            print(f"  eng.{attr} = {val}")
    
    total_eq += r['final_equity']
    
    # Last 3 trades with amounts
    print(f"  Last trades:")
    for t in eng.trades[-5:]:
        a = t.get('action', '')
        amt = t.get('amount', 0)
        c = t.get('coins', 0)
        print(f"    {t['date']} {a} @ ${t['price']:.2f} amt=${amt:.2f} coins={c:.6f}")

print(f"\nTotal: ${total_eq:,.0f} (PnL: ${total_eq-capital:+,.0f}, ROI: {(total_eq-capital)/capital*100:+.1f}%)")
