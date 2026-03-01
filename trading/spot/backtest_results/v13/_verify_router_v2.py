"""
Verify ROUTER v2:
  Step 1: Conviction OFF must match v1 exactly ($0.00 delta)
  Step 2: Run conviction ON comparison
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_router_engine_v1 import V13RouterV1, V13Config
from v13_router_engine_v2 import V13RouterV2, run_comparison
from v13_signals import V13SignalPack

COINS = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
START = '2024-10-01'
PER_COIN = 2500.0

def step1_verify_baseline():
    """Conviction OFF must match v1 exactly."""
    print("=" * 70)
    print("STEP 1: Verify v2 (conviction OFF) == v1")
    print("=" * 70)

    all_pass = True
    for coin in COINS:
        try:
            pack = V13SignalPack(coin)
        except Exception as e:
            print(f"  {coin}: SKIP (pack error: {e})")
            continue

        # v1
        cfg1 = V13Config()
        cfg1.CAPITAL = PER_COIN
        cfg1.START_DATE = START
        eng1 = V13RouterV1(pack, cfg1)
        r1 = eng1.run()

        # v2 conviction OFF
        cfg2 = V13Config()
        cfg2.CAPITAL = PER_COIN
        cfg2.START_DATE = START
        eng2 = V13RouterV2(pack, cfg2, conviction_enabled=False)
        r2 = eng2.run()

        if r1 is None or r2 is None:
            print(f"  {coin}: SKIP (no results)")
            continue

        delta = abs(r1['final_equity'] - r2['final_equity'])
        phases_match = len(r1['phases']) == len(r2['phases'])
        trades_match = len(r1['trades']) == len(r2['trades'])

        status = "PASS" if delta < 0.01 and phases_match and trades_match else "FAIL"
        if status == "FAIL":
            all_pass = False

        print(f"  {coin}: {status} -- v1=${r1['final_equity']:,.2f} v2=${r2['final_equity']:,.2f}"
              f" delta=${delta:.2f} phases={len(r1['phases'])}/{len(r2['phases'])}"
              f" trades={len(r1['trades'])}/{len(r2['trades'])}")

    print(f"\n  STEP 1: {'ALL PASS' if all_pass else 'FAILED'}")
    return all_pass


def step2_conviction_comparison():
    """Run side-by-side with conviction enabled, sweep K thresholds."""
    from v13_router_engine_v2 import V13RouterV2, V13Config
    from v13_signals import V13SignalPack

    for k_min in [5.0, 10.0]:
        print(f"\n{'='*70}")
        print(f"STEP 2: 3D DX + 2W StochRSI Exhaustion (K >= {k_min})")
        print("=" * 70)

        per_coin = 10000 / len(COINS)
        results = {}
        for coin in COINS + ['HBAR/USDC']:
            cap = per_coin if coin != 'HBAR/USDC' else 2500
            try:
                pack = V13SignalPack(coin)
            except Exception as e:
                print(f"  {coin}: SKIP ({e})")
                continue

            cfg_off = V13Config(); cfg_off.CAPITAL = cap; cfg_off.START_DATE = START
            eng_off = V13RouterV2(pack, cfg_off, conviction_enabled=False)
            r_off = eng_off.run()

            cfg_on = V13Config(); cfg_on.CAPITAL = cap; cfg_on.START_DATE = START
            eng_on = V13RouterV2(pack, cfg_on, conviction_enabled=True, min_score=3, exhaustion_k_min=k_min)
            r_on = eng_on.run()

            if r_off and r_on:
                delta = r_on['final_equity'] - r_off['final_equity']
                triggers = r_on.get('conviction_triggers', [])
                tdate = triggers[0]['date'].strftime('%Y-%m-%d') if triggers else 'N/A'
                tscore = triggers[0]['score'] if triggers else '-'
                print(f"  {coin:<12} base=${r_off['final_equity']:>10,.2f}  conv=${r_on['final_equity']:>10,.2f}  delta=${delta:>+10,.2f}  trigger={tdate} ({tscore})")

        print()


if __name__ == '__main__':
    ok = step1_verify_baseline()
    if ok:
        step2_conviction_comparison()
    else:
        print("\nSTEP 1 FAILED -- fix before proceeding to Step 2")
