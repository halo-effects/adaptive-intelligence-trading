"""Trace ETH phase transitions in conviction ON backtest."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_router_engine_v2 import V13RouterV2, V13Config, V13SignalPack

pack = V13SignalPack('ETH/USDC')
eng = V13RouterV2(pack, V13Config(), conviction_enabled=True, min_score=3)
eng.cfg.CAPITAL = 2500
eng.cfg.START_DATE = '2024-10-01'

# Monkey-patch _change_phase to log transitions
orig = eng._change_phase
def logged_change(date, new_phase, reason=''):
    pname = eng.phase.name if hasattr(eng.phase, 'name') else str(eng.phase)
    nname = new_phase.name if hasattr(new_phase, 'name') else str(new_phase)
    print(f"  {date.strftime('%Y-%m-%d')} {pname:12} -> {nname:12}  {reason}")
    orig(date, new_phase, reason)
eng._change_phase = logged_change

# Also log short opens/closes
orig_open_short = eng._open_short.__func__
def logged_open_short(self, date, pct, tier):
    print(f"  {date.strftime('%Y-%m-%d')} OPEN SHORT tier={tier} pct={pct:.1%}")
    orig_open_short(self, date, pct, tier)

orig_close_short = eng._close_short
def logged_close_short(date, reason=''):
    result = orig_close_short(date, reason)
    print(f"  {date.strftime('%Y-%m-%d')} CLOSE SHORT reason={reason} pnl={result:+.1f}%")
    return result

eng._open_short = lambda d, p, t: logged_open_short(eng, d, p, t)
eng._close_short = logged_close_short

print("ETH/USDC Phase Trace (conviction ON):")
print("=" * 70)
r = eng.run()
print(f"\nFinal equity: ${r['final_equity']:,.2f} ({r['roi']:+.1f}%)")
