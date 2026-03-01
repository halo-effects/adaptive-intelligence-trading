"""
Compare Router v2 against paper bot from Oct 1, 2024.
Every trade should match until conviction triggers diverge.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from v13_router_engine_v2 import V13RouterV2
from v13_router_engine_v1 import V13RouterV1, V13Config
from v13_signals import V13SignalPack

COINS = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']
CAP = 2500
START = '2024-10-01'

def run_comparison():
    print("ROUTER V2 vs V1 — Paper Bot Period (Oct 1, 2024+)")
    print("="*90)

    for coin in COINS:
        print(f"\n{'='*60}")
        print(f"  {coin}")
        print(f"{'='*60}")

        pack = V13SignalPack(coin)
        
        # V1 baseline
        cfg1 = V13Config()
        cfg1.CAPITAL = CAP
        cfg1.TIER1_PCT = 0.60
        cfg1.TIER2_PCT = 0.20
        cfg1.TIER3_PCT = 0.10
        cfg1.START_DATE = START
        v1 = V13RouterV1(pack, cfg1)
        r1 = v1.run()

        # V2 with conviction
        cfg2 = V13Config()
        cfg2.CAPITAL = CAP
        cfg2.TIER1_PCT = 0.60
        cfg2.TIER2_PCT = 0.20
        cfg2.TIER3_PCT = 0.10
        cfg2.START_DATE = START
        v2 = V13RouterV2(pack, cfg2)
        r2 = v2.run()

        if not r1 or not r2:
            print("  ERROR: no results")
            continue

        eq1 = r1['final_equity']
        eq2 = r2['final_equity']
        delta = eq2 - eq1
        print(f"  V1 equity: ${eq1:,.2f}")
        print(f"  V2 equity: ${eq2:,.2f}")
        print(f"  Delta:     ${delta:+,.2f}")

        # Compare trades
        t1 = v1.trades
        t2 = v2.trades

        print(f"  V1 trades: {len(t1)}")
        print(f"  V2 trades: {len(t2)}")

        # Find first divergence
        min_len = min(len(t1), len(t2))
        diverge_idx = None
        for i in range(min_len):
            if (str(t1[i]['date'])[:10] != str(t2[i]['date'])[:10] or
                t1[i]['action'] != t2[i]['action']):
                diverge_idx = i
                break

        if diverge_idx is not None:
            print(f"\n  First divergence at trade #{diverge_idx}:")
            print(f"    V1: {str(t1[diverge_idx]['date'])[:10]} {t1[diverge_idx]['action']} ${t1[diverge_idx].get('price',0):.2f}")
            print(f"    V2: {str(t2[diverge_idx]['date'])[:10]} {t2[diverge_idx]['action']} ${t2[diverge_idx].get('price',0):.2f}")
            print(f"  Trades matching before divergence: {diverge_idx}/{min_len}")
        elif len(t1) == len(t2):
            print(f"  ALL {len(t1)} trades IDENTICAL")
        else:
            print(f"  First {min_len} trades match, then V2 has {len(t2)-len(t1)} extra trades")

        # Show conviction triggers
        if hasattr(v2, 'conviction_triggers') and v2.conviction_triggers:
            print(f"\n  CONVICTION TRIGGERS:")
            for ct in v2.conviction_triggers:
                d = ct.get('details', {})
                print(f"    {str(ct['date'])[:10]} score={ct['score']}/5 "
                      f"sma={'Y' if d.get('below_sma200') else '-'} "
                      f"rsi={'Y' if d.get('rsi_ok') else '-'} "
                      f"stoch={'Y' if d.get('stoch_ok') else '-'} "
                      f"cfgi={'Y' if d.get('cfgi_ok') else '-'} "
                      f"pi={'Y' if d.get('pi_bottom') else '-'} "
                      f"${ct.get('price', d.get('price', 0)):.2f}")
        else:
            print(f"\n  No conviction triggers (identical to V1)")

        # Show phase timeline comparison
        print(f"\n  V1 phases: {len(r1.get('phases', []))}")
        print(f"  V2 phases: {len(r2.get('phases', []))}")

    print(f"\n\n{'='*90}")
    print("SUMMARY")
    print("="*90)

if __name__ == '__main__':
    run_comparison()
