"""Quick check of ETH short entries — what triggers MARKDOWN?"""
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pnl_attribution import run_attribution

for coin in ['ETH', 'BTC', 'SOL']:
    a = run_attribution(coin, 'medium')
    if not a:
        continue
    
    print(f"\n{'='*60}")
    print(f"  {coin} — MARKDOWN Analysis")
    print(f"{'='*60}")
    
    # Show all MARKDOWN entries and what path they came from
    for p in a['phase_log']:
        if p['to'] == 'MARKDOWN':
            print(f"  {p['date'].date()}: {p['from']} -> MARKDOWN")
            print(f"    Reason: {p['reason']}")
            print(f"    Equity: ${p['equity']:,.0f}")
    
    # Show short results
    print(f"\n  Short trades: {len(a['short_details'])}")
    for i, s in enumerate(a['short_details'], 1):
        days = (s['exit_date'] - s['entry_date']).days
        fail = "MARKDOWN_FAIL" if "FAIL" in s['action'] else "normal_exit"
        oe = " [OPEN_END]" if s['is_open_end'] else ""
        print(f"    {i}. {s['entry_date']} -> {s['exit_date']} ({days}d) "
              f"${s['entry_price']:,.0f} -> ${s['exit_price']:,.0f} "
              f"{s['pnl_pct']:+.1f}% ${s['pnl_dollar']:+,.0f} [{fail}]{oe}")
    
    print(f"  Net short P&L: ${a['short_total']:+,.0f}")
