"""
Apples-to-apples: v2_full vs paper bot.
Exact same params: Oct 1 2024 start, $10K, 4 coins, high profile.
Compare to dashboard equity ($28,717).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from v13_router_engine_v2 import V13RouterV2, V13Config, Phase, V13SignalPack
from _backtest_full_v2_final import V13RouterV2Final, compute_2d_divergence_dates

coins = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
capital = 10000
per_coin = capital / len(coins)
start = '2024-10-01'

# Pre-compute divergence dates
all_div = {}
for coin in coins:
    base = coin.split('/')[0]
    all_div[base] = compute_2d_divergence_dates(coin)

configs = {
    'v1_baseline (=paper bot)': {'conviction': False, 'top_timing': False},
    'v2_full (conviction+top)': {'conviction': True, 'top_timing': True},
}

print(f"Start: {start}, Capital: ${capital:,}, Coins: {', '.join(c.split('/')[0] for c in coins)}")
print(f"Paper bot dashboard equity: ~$28,717 (+187%)")
print()

for label, cfg in configs.items():
    total = 0
    print(f"--- {label} ---")
    for coin in coins:
        base = coin.split('/')[0]
        pack = V13SignalPack(base)
        
        if not cfg['top_timing']:
            eng = V13RouterV2(pack, V13Config(), conviction_enabled=cfg['conviction'],
                            min_score=3, exhaustion_tf='2W', exhaustion_mode='k_lift')
        else:
            eng = V13RouterV2Final(pack, V13Config(), conviction_enabled=cfg['conviction'],
                                  min_score=3, exhaustion_tf='2W', exhaustion_mode='k_lift',
                                  div_dates=all_div[base], top_timing_enabled=True, max_wait_days=35)
        
        eng.cfg.CAPITAL = per_coin
        eng.cfg.START_DATE = start
        r = eng.run()
        eq = r['final_equity']
        total += eq
        
        # Final state
        phase = eng.phase.name if hasattr(eng.phase, 'name') else str(eng.phase)
        short_coins = eng.short_coins
        spot_coins = eng.coins if hasattr(eng, 'coins') else 0
        
        open_pos = ""
        if short_coins > 0:
            open_pos = f"SHORT {short_coins:.2f} coins"
        elif spot_coins > 0:
            open_pos = f"LONG {spot_coins:.2f} coins"
        else:
            open_pos = "flat"
        
        # Key exits
        key_exits = [t for t in eng.trades if any(x in str(t.get('action','')) 
                     for x in ['OB93', 'FALLBACK', 'FAILSAFE', 'RANGING', 'FAIL', 'CONVICTION', 'DIVERGENCE', 'TIMEOUT', 'OPEN_END'])]
        
        print(f"  {base}: ${eq:,.0f} ({r['roi']:+.1f}%) | {phase} | {open_pos}")
        for t in key_exits:
            a = str(t.get('action',''))
            print(f"    {t['date']} - {a} @ ${t['price']:.2f}")
    
    roi = (total - capital) / capital * 100
    print(f"  TOTAL: ${total:,.0f} ({roi:+.1f}%)")
    print()

# Delta
print("COMPARISON:")
# Rerun to get totals
totals = {}
for label, cfg in configs.items():
    t = 0
    for coin in coins:
        base = coin.split('/')[0]
        pack = V13SignalPack(base)
        if not cfg['top_timing']:
            eng = V13RouterV2(pack, V13Config(), conviction_enabled=cfg['conviction'],
                            min_score=3, exhaustion_tf='2W', exhaustion_mode='k_lift')
        else:
            eng = V13RouterV2Final(pack, V13Config(), conviction_enabled=cfg['conviction'],
                                  min_score=3, exhaustion_tf='2W', exhaustion_mode='k_lift',
                                  div_dates=all_div[base], top_timing_enabled=True, max_wait_days=35)
        eng.cfg.CAPITAL = per_coin
        eng.cfg.START_DATE = start
        t += eng.run()['final_equity']
    totals[label] = t

base_t = totals['v1_baseline (=paper bot)']
full_t = totals['v2_full (conviction+top)']
print(f"  Paper bot baseline: ${base_t:,.0f} ({(base_t-capital)/capital*100:+.1f}%)")
print(f"  V2 full:            ${full_t:,.0f} ({(full_t-capital)/capital*100:+.1f}%)")
print(f"  Delta:              ${full_t-base_t:+,.0f}")
