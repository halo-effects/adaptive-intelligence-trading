"""
Verification: V13BacktestV8 vs V13RouterV1
Must produce 100% identical results (pure architectural refactor).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config as V8Config
from v13_router_engine_v1 import V13RouterV1, V13Config as RouterConfig
from v13_signals import V13SignalPack


def compare(coin, start='2023-01-01', end='2026-02-25', capital=2500):
    pack_v8 = V13SignalPack(coin)
    pack_r1 = V13SignalPack(coin)

    cfg_v8 = V8Config()
    cfg_v8.START_DATE = start
    cfg_v8.END_DATE = end
    cfg_v8.CAPITAL = capital

    cfg_r1 = RouterConfig()
    cfg_r1.START_DATE = start
    cfg_r1.END_DATE = end
    cfg_r1.CAPITAL = capital

    bt_v8 = V13BacktestV8(pack_v8, cfg_v8)
    bt_r1 = V13RouterV1(pack_r1, cfg_r1)

    r8 = bt_v8.run()
    r1 = bt_r1.run()

    if r8 is None and r1 is None:
        print(f"  {coin}: SKIP (no data)")
        return True
    if r8 is None or r1 is None:
        print(f"  {coin}: FAIL - one returned None")
        return False

    ok = True

    # Compare final equity
    eq_delta = abs(r8['final_equity'] - r1['final_equity'])
    if eq_delta > 0.005:
        print(f"  {coin}: FAIL - equity delta ${eq_delta:.2f} (v8=${r8['final_equity']:.2f}, r1=${r1['final_equity']:.2f})")
        ok = False

    # Compare trade count
    if r8['total_trades'] != r1['total_trades']:
        print(f"  {coin}: FAIL - trade count v8={r8['total_trades']}, r1={r1['total_trades']}")
        ok = False

    # Compare phase transition count
    if r8['phase_changes'] != r1['phase_changes']:
        print(f"  {coin}: FAIL - phase changes v8={r8['phase_changes']}, r1={r1['phase_changes']}")
        ok = False

    # Compare phase transition dates
    for i, (p8, p1) in enumerate(zip(r8['phases'], r1['phases'])):
        if p8['date'] != p1['date']:
            print(f"  {coin}: FAIL - phase #{i} date mismatch: v8={p8['date'].date()}, r1={p1['date'].date()}")
            ok = False
            break
        # Compare phase names (FLAT in v8 == ROUTER in r1)
        to_v8 = p8['to']
        to_r1 = p1['to']
        from_v8 = p8['from']
        from_r1 = p1['from']
        # Normalize FLAT<->ROUTER for comparison
        if to_v8 == 'FLAT':
            to_v8 = 'ROUTER'
        if to_r1 == 'FLAT':
            to_r1 = 'ROUTER'
        if from_v8 == 'FLAT':
            from_v8 = 'ROUTER'
        if from_r1 == 'FLAT':
            from_r1 = 'ROUTER'
        if to_v8 != to_r1 or from_v8 != from_r1:
            print(f"  {coin}: FAIL - phase #{i} mismatch: v8={p8['from']}->{p8['to']}, r1={p1['from']}->{p1['to']}")
            ok = False
            break

    if ok:
        print(f"  {coin}: PASS - equity=${r8['final_equity']:.2f}, trades={r8['total_trades']}, phases={r8['phase_changes']}")

    return ok


def main():
    print("=" * 60)
    print("  V13 Router v1 Verification")
    print("  Comparing V13BacktestV8 vs V13RouterV1")
    print("=" * 60)

    coins = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']
    results = {}

    for coin in coins:
        try:
            results[coin] = compare(coin)
        except Exception as e:
            print(f"  {coin}: ERROR - {e}")
            results[coin] = False

    print()
    all_pass = all(results.values())
    if all_pass:
        print("  OVERALL: PASS - All coins match 100%")
    else:
        failed = [c for c, v in results.items() if not v]
        print(f"  OVERALL: FAIL - Failed: {', '.join(failed)}")

    return 0 if all_pass else 1


if __name__ == '__main__':
    sys.exit(main())
