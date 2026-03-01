"""Test V14 on HBAR and AAVE, plus V13 baseline comparison."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v14_dca_engine import V14DCAEngine, V14Config, Phase
from v13_phase_backtest_v8 import V13BacktestV8, V13Config as V8Config
from v13_signals import V13SignalPack

test_coins = ['HBAR/USDT', 'AAVE/USDT', 'ETH/USDC', 'LINK/USDC']
capital = 10000
per_coin = capital / len(test_coins)

# V13 baseline
print("V13 BASELINE")
print("=" * 60)
v13_total = 0
for coin in test_coins:
    try:
        pack = V13SignalPack(coin)
        cfg = V8Config()
        cfg.CAPITAL = per_coin
        cfg.START_DATE = '2024-10-01'
        eng = V13BacktestV8(pack, cfg)
        r = eng.run()
        v13_total += r['final_equity']
        print(f"  {coin:<12} ${r['final_equity']:>10,.2f} ({r['roi']:>+8.1f}%)")
    except Exception as e:
        print(f"  {coin:<12} ERROR: {e}")
print(f"  {'TOTAL':<12} ${v13_total:>10,.2f} ({(v13_total-capital)/capital*100:>+8.1f}%)")

# V14 accumulate
print(f"\nV14 DCA ACCUMULATE (BO=30%, Dev=2.5%, Mult=1.5x)")
print("=" * 60)
v14_total = 0
for coin in test_coins:
    try:
        pack = V13SignalPack(coin)
        cfg = V14Config()
        cfg.CAPITAL = per_coin
        cfg.START_DATE = '2024-10-01'
        eng = V14DCAEngine(pack, cfg)
        r = eng.run()
        v14_total += r['final_equity']
        print(f"  {coin:<12} ${r['final_equity']:>10,.2f} ({r['roi']:>+8.1f}%)")
        print(f"    L:{r['total_long_trades']}({r['long_wins']}W ${r['long_pnl']:>+,.0f})"
              f"  S:{r['total_short_trades']}({r['short_wins']}W ${r['short_pnl']:>+,.0f})"
              f"  DD:{r['max_drawdown']:.1f}%")
        for p in r['phases']:
            print(f"    {p['date'].strftime('%Y-%m-%d')} {p['from']:>10} -> {p['to']:<10} {p['reason']}")
        for t in r.get('conviction_triggers', []):
            print(f"    BOTTOM: {t['date'].strftime('%Y-%m-%d')} score={t['score']}/4 short_pnl={t['short_pnl_pct']:+.1f}%")
        for t in r.get('top_triggers', []):
            print(f"    TOP: {t['date'].strftime('%Y-%m-%d')} {t['reason']} @ ${t['price']:.2f}")
    except Exception as e:
        print(f"  {coin:<12} ERROR: {e}")
        import traceback; traceback.print_exc()

print(f"  {'TOTAL':<12} ${v14_total:>10,.2f} ({(v14_total-capital)/capital*100:>+8.1f}%)")
print(f"\n  V13: ${v13_total:,.0f} ({(v13_total-capital)/capital*100:+.1f}%)")
print(f"  V14: ${v14_total:,.0f} ({(v14_total-capital)/capital*100:+.1f}%)")
