"""Test proxy-routed coins: start in SHORT_DCA instead of LONG_DCA."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
from v14_dca_engine import V14DCAEngine, V14Config

TIER_B = [
    'SUI/USDT', 'ALGO/USDT', 'ARB/USDT', 'FIL/USDT', 'INJ/USDT',
    'GRT/USDT', 'MANA/USDT', 'RUNE/USDT', 'CRV/USDT', 'FET/USDT',
    'GALA/USDT', 'TAO/USDT', 'TON/USDT', 'DOGE/USDT',
]

CAPITAL = 2500

print("PROXY ROUTER TEST — Start SHORT_DCA vs LONG_DCA", flush=True)
print("=" * 80, flush=True)

print(f"\n{'Coin':<14} {'LONG start':>12} {'SHORT start':>13} {'Delta':>8}", flush=True)
print("-" * 55, flush=True)

for coin in TIER_B:
    try:
        # LONG_DCA start (default — what failed)
        pack = V13SignalPack(coin)
        cfg = V14Config()
        cfg.CAPITAL = CAPITAL; cfg.OB_FALLBACK_1W = 99; cfg.DCA_ACCUMULATE = False
        cfg.DCA_TP_PCT = 0.015; cfg.DCA_BO_PCT = 0.40; cfg.DCA_SO_DEVIATION = 0.02; cfg.DCA_MAX_LAYERS = 10
        eng_long = V14DCAEngine(pack, cfg, initial_phase='LONG_DCA')
        r_long = eng_long.run()

        # SHORT_DCA start (proxy-routed)
        pack2 = V13SignalPack(coin)
        cfg2 = V14Config()
        cfg2.CAPITAL = CAPITAL; cfg2.OB_FALLBACK_1W = 99; cfg2.DCA_ACCUMULATE = False
        cfg2.DCA_TP_PCT = 0.015; cfg2.DCA_BO_PCT = 0.40; cfg2.DCA_SO_DEVIATION = 0.02; cfg2.DCA_MAX_LAYERS = 10
        eng_short = V14DCAEngine(pack2, cfg2, initial_phase='SHORT_DCA')
        r_short = eng_short.run()

        if r_long and r_short:
            delta = r_short['roi'] - r_long['roi']
            print(f"  {coin:<12} {r_long['roi']:>+7.1f}% ({r_long['phase_changes']}p)"
                  f"  {r_short['roi']:>+7.1f}% ({r_short['phase_changes']}p)"
                  f"  {delta:>+7.1f}%", flush=True)
            # Show short-start details
            if r_short['phase_changes'] > 0:
                for p in r_short['phases']:
                    print(f"    {p['date'].date()}: {p['from']}->{p['to']} ({p['reason'][:40]})", flush=True)
    except Exception as e:
        print(f"  {coin:<12} ERROR: {str(e)[:50]}", flush=True)

# Also test Tier A coins starting SHORT to see if it matters
print(f"\n{'='*80}", flush=True)
print("TIER A REFERENCE — Does start phase matter for coins with full history?", flush=True)
print("-" * 55, flush=True)
TIER_A = ['HBAR/USDT', 'ATOM/USDT', 'LINK/USDC', 'NEAR/USDT']
for coin in TIER_A:
    try:
        pack = V13SignalPack(coin)
        cfg = V14Config()
        cfg.CAPITAL = CAPITAL; cfg.OB_FALLBACK_1W = 99; cfg.DCA_ACCUMULATE = False
        cfg.DCA_TP_PCT = 0.015; cfg.DCA_BO_PCT = 0.40; cfg.DCA_SO_DEVIATION = 0.02; cfg.DCA_MAX_LAYERS = 10
        eng_long = V14DCAEngine(pack, cfg, initial_phase='LONG_DCA')
        r_long = eng_long.run()

        pack2 = V13SignalPack(coin)
        cfg2 = V14Config()
        cfg2.CAPITAL = CAPITAL; cfg2.OB_FALLBACK_1W = 99; cfg2.DCA_ACCUMULATE = False
        cfg2.DCA_TP_PCT = 0.015; cfg2.DCA_BO_PCT = 0.40; cfg2.DCA_SO_DEVIATION = 0.02; cfg2.DCA_MAX_LAYERS = 10
        eng_short = V14DCAEngine(pack2, cfg2, initial_phase='SHORT_DCA')
        r_short = eng_short.run()

        if r_long and r_short:
            delta = r_short['roi'] - r_long['roi']
            print(f"  {coin:<12} LONG:{r_long['roi']:>+7.1f}%  SHORT:{r_short['roi']:>+7.1f}%  delta:{delta:>+7.1f}%", flush=True)
    except Exception as e:
        print(f"  {coin:<12} ERROR: {str(e)[:50]}", flush=True)
