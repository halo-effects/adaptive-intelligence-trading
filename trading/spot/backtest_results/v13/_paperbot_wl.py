"""Paper bot W/L comparison. Oct 2024 start, 4 coins."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'
coins = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']

for coin in coins:
    cfg = V13Config()
    cfg.START_DATE = '2024-10-01'
    cfg.END_DATE = '2026-02-27'
    cfg.CAPITAL = 2500
    cfg.TIER1_PCT = 0.60; cfg.TIER2_PCT = 0.20; cfg.TIER3_PCT = 0.10
    cfg.SHORT_TIER1_PCT = 0.60; cfg.SHORT_TIER2_PCT = 0.20; cfg.SHORT_TIER3_PCT = 0.10
    cfg.SHORTS_ENABLED = True

    pack = V13SignalPack(coin, db_path=DB)
    e = V13BacktestV8(pack, cfg)
    r = e.run()
    if not r:
        continue

    short = coin.split('/')[0]
    print(f"\n{'='*90}")
    print(f"  {short}  |  ROI: {r['roi']:+.1f}%  |  Closed: {r['closed_roi']:+.1f}%")
    print(f"{'='*90}")

    # Markup W/L
    print(f"\n  MARKUP ENTRIES:")
    markup_entry = None
    markup_wins = 0
    markup_losses = 0
    for p in e.phase_log:
        if p.get('to') == Phase.MARKUP:
            markup_entry = p
        elif p.get('from') == Phase.MARKUP and markup_entry:
            entry_eq = markup_entry.get('equity', 0)
            exit_eq = p.get('equity', 0)
            pnl = exit_eq - entry_eq
            pnl_pct = pnl / entry_eq * 100 if entry_eq > 0 else 0
            days = (p['date'] - markup_entry['date']).days
            reason = p.get('reason', '')
            win = pnl >= 0
            if win:
                markup_wins += 1
            else:
                markup_losses += 1
            tag = "WIN" if win else "LOSS"
            print(f"    {str(markup_entry['date'])[:10]} -> {str(p['date'])[:10]} "
                  f"({days:>3}d)  ${pnl:>+7.0f} ({pnl_pct:>+5.1f}%)  [{tag}]  {reason}")
            markup_entry = None

    # Markdown W/L
    print(f"\n  MARKDOWN SHORTS:")
    md_entry = None
    md_wins = 0
    md_losses = 0
    for p in e.phase_log:
        if p.get('to') == Phase.MARKDOWN:
            md_entry = p
        elif p.get('from') == Phase.MARKDOWN and md_entry:
            entry_eq = md_entry.get('equity', 0)
            exit_eq = p.get('equity', 0)
            pnl = exit_eq - entry_eq
            days = (p['date'] - md_entry['date']).days
            reason = p.get('reason', '')
            win = pnl >= 0
            if win:
                md_wins += 1
            else:
                md_losses += 1
            tag = "WIN" if win else "LOSS"
            print(f"    {str(md_entry['date'])[:10]} -> {str(p['date'])[:10]} "
                  f"({days:>3}d)  ${pnl:>+7.0f}  [{tag}]  {reason}")
            md_entry = None
    if md_entry:
        print(f"    {str(md_entry['date'])[:10]} -> OPEN (still in markdown)")

    # DCA
    print(f"\n  DCA: {e.dca_trades} trades, {e.dca_wins} wins, "
          f"${e.dca_pnl:+.1f}")

    # Summary
    total_trades = markup_wins + markup_losses + md_wins + md_losses
    total_wins = markup_wins + md_wins
    print(f"\n  W/L SUMMARY:")
    print(f"    Markup:   {markup_wins}W / {markup_losses}L")
    print(f"    Markdown: {md_wins}W / {md_losses}L")
    print(f"    DCA:      {e.dca_wins}W / {e.dca_trades - e.dca_wins}L")
