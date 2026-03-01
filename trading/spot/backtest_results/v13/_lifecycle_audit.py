"""Full lifecycle audit — show all markup/markdown trades and phase transitions.
Compare against paper bot to find discrepancies."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'

COINS = ['ETH/USDC', 'BTC/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']

for coin in COINS:
    cfg = V13Config()
    cfg.CAPITAL = 2500
    cfg.START_DATE = '2023-01-01'
    cfg.END_DATE = '2026-02-27'
    cfg.TIER1_PCT = 0.60
    cfg.TIER2_PCT = 0.20
    cfg.TIER3_PCT = 0.10
    cfg.SHORT_TIER1_PCT = 0.60
    cfg.SHORT_TIER2_PCT = 0.20
    cfg.SHORT_TIER3_PCT = 0.10
    cfg.SHORTS_ENABLED = True

    pack = V13SignalPack(coin, db_path=DB)
    e = V13BacktestV8(pack, cfg)
    r = e.run()
    if not r:
        print(f"{coin}: NO RESULT")
        continue

    short = coin.split('/')[0]
    print(f"\n{'='*110}")
    print(f"  {coin}  |  ROI: {r['roi']:+.1f}%  |  Closed ROI: {r['closed_roi']:+.1f}%  |  Cycles: {r['markup_cycles']}")
    print(f"{'='*110}")

    # Markup entry/exit pairs with P&L
    print(f"\n  MARKUP ENTRIES & EXITS:")
    markup_entry = None
    markup_entry_eq = None
    for p in e.phase_log:
        to = p.get('to', None)
        fr = p.get('from', None)
        if to == Phase.MARKUP:
            markup_entry = p
            markup_entry_eq = p.get('equity', 0)
        elif fr == Phase.MARKUP and markup_entry:
            exit_eq = p.get('equity', 0)
            pnl = exit_eq - markup_entry_eq
            pnl_pct = pnl / markup_entry_eq * 100 if markup_entry_eq > 0 else 0
            reason = p.get('reason', '')
            entry_date = str(markup_entry['date'])[:10]
            exit_date = str(p['date'])[:10]
            days = (p['date'] - markup_entry['date']).days
            to_name = p['to'].name if hasattr(p['to'], 'name') else str(p['to'])
            status = "FAIL" if pnl < 0 else "OK"
            print(f"    {entry_date} -> {exit_date} ({days:>3}d)  eq: ${markup_entry_eq:>7.0f} -> ${exit_eq:>7.0f}  "
                  f"P&L: ${pnl:>+7.0f} ({pnl_pct:>+5.1f}%)  -> {to_name:<12} [{status}]  {reason}")
            markup_entry = None

    # Markdown/short entries
    print(f"\n  MARKDOWN SHORTS:")
    short_entry = None
    for p in e.phase_log:
        to = p.get('to', None)
        fr = p.get('from', None)
        if to == Phase.MARKDOWN:
            short_entry = p
        elif fr == Phase.MARKDOWN and short_entry:
            entry_eq = short_entry.get('equity', 0)
            exit_eq = p.get('equity', 0)
            pnl = exit_eq - entry_eq
            entry_date = str(short_entry['date'])[:10]
            exit_date = str(p['date'])[:10]
            days = (p['date'] - short_entry['date']).days
            to_name = p['to'].name if hasattr(p['to'], 'name') else str(p['to'])
            reason = p.get('reason', '')
            status = "FAIL" if 'FAIL' in reason.upper() else "OK"
            print(f"    {entry_date} -> {exit_date} ({days:>3}d)  eq: ${entry_eq:>7.0f} -> ${exit_eq:>7.0f}  "
                  f"P&L: ${pnl:>+7.0f}  -> {to_name:<12} [{status}]  {reason}")
            short_entry = None
    if short_entry:
        print(f"    {str(short_entry['date'])[:10]} -> OPEN  eq: ${short_entry.get('equity',0):>7.0f}")

    # DCA summary
    print(f"\n  DCA: {e.dca_trades} trades, ${e.dca_pnl:+.1f} P&L, "
          f"{e.dca_wins}/{e.dca_trades} wins ({e.dca_wins/max(e.dca_trades,1)*100:.0f}%)")

    # Full phase log
    print(f"\n  FULL PHASE LOG ({len(e.phase_log)} transitions):")
    for p in e.phase_log:
        fr = p.get('from', '-')
        to = p.get('to', '-')
        if hasattr(fr, 'name'): fr = fr.name
        if hasattr(to, 'name'): to = to.name
        eq = p.get('equity', 0)
        reason = p.get('reason', '')
        dt = str(p['date'])[:10]
        print(f"    {dt}  {str(fr):>12} -> {str(to):<12} eq=${eq:>8.0f}  {reason}")

# Also check: what config values does V13Config default to?
print(f"\n{'='*110}")
print("V13Config DEFAULTS (for comparison with paper bot):")
print(f"{'='*110}")
d = V13Config()
for attr in sorted(dir(d)):
    if attr.startswith('_'):
        continue
    val = getattr(d, attr)
    if callable(val):
        continue
    print(f"  {attr}: {val}")
