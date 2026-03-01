"""
P&L Attribution Report -- V13 Backtest
Breaks down ROI by source: Markup sells, DCA scalps, Short (Markdown) trades.
"""
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
from v13_signals import V13SignalPack
from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from run_wyckoff_tables import PROFILES as PROFILE_PARAMS, make_config, COIN_START

DB = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'candles.db'))
COINS = ['ETH', 'SOL', 'BTC']
PROFILES = ['low', 'medium', 'high']
CAPITAL = 10000
END = '2026-02-26'


def classify_trade(t):
    """Classify a trade into markup/dca/short/other."""
    action = t.get('action', '')
    if action.startswith('SELL_ALL'):
        return 'markup'
    if action.startswith('DCA_TP') or action.startswith('DCA_CLOSE'):
        return 'dca'
    if action.startswith('SHORT_CLOSE'):
        return 'short'
    return None  # buys, entries — no realized P&L


def run_attribution(coin, profile):
    symbol = f"{coin}/USDC"
    pack = V13SignalPack(symbol)
    cfg = make_config(profile, coin)
    cfg.END_DATE = END
    bt = V13BacktestV8(pack, cfg)
    r = bt.run()
    if not r:
        return None

    # Classify trades with P&L
    markup_trades = []
    dca_trades = []
    short_trades = []

    for t in r['trades']:
        if 'pnl_pct' not in t:
            continue
        cat = classify_trade(t)
        if cat == 'markup':
            markup_trades.append(t)
        elif cat == 'dca':
            dca_trades.append(t)
        elif cat == 'short':
            short_trades.append(t)

    # Calculate dollar P&L for each trade
    # For markup: pnl = amount - cost_basis (but we need to track cost from BUY_T entries)
    # Simpler: use the equity changes from phase log
    # Actually, let's compute from the trades directly

    # Markup P&L: for SELL_ALL, pnl_pct is relative to entry cost
    # We need dollar amounts. Let's trace BUY→SELL pairs.
    markup_buys = [t for t in r['trades'] if t['action'].startswith('BUY_T')]
    
    # Group markup cycles: buys followed by a sell
    markup_cycles = []
    current_buys = []
    for t in r['trades']:
        if t['action'].startswith('BUY_T'):
            current_buys.append(t)
        elif t['action'].startswith('SELL_ALL') and current_buys:
            cost = sum(b['amount'] for b in current_buys)
            proceeds = t['amount']
            pnl_dollar = proceeds - cost
            markup_cycles.append({
                'entry_date': current_buys[0]['date'].date(),
                'exit_date': t['date'].date(),
                'action': t['action'],
                'tiers': len(current_buys),
                'cost': cost,
                'proceeds': proceeds,
                'pnl_dollar': pnl_dollar,
                'pnl_pct': t['pnl_pct'],
                'entry_price': current_buys[0]['price'],
                'exit_price': t['price'],
            })
            current_buys = []

    # DCA P&L
    dca_details = []
    for t in dca_trades:
        is_open_end = 'OPEN_END' in t.get('action', '')
        if t['action'].startswith('DCA_TP'):
            # TP: proceeds = amount, cost = proceeds / (1 + pnl_pct/100)
            proceeds = t['amount']
            cost = proceeds / (1 + t['pnl_pct'] / 100) if t['pnl_pct'] != -100 else proceeds
            pnl_dollar = proceeds - cost
        else:
            # DCA_CLOSE: hard exit, amount = proceeds
            proceeds = t['amount']
            cost = proceeds / (1 + t['pnl_pct'] / 100) if t['pnl_pct'] != -100 else proceeds
            pnl_dollar = proceeds - cost
        dca_details.append({
            'date': t['date'].date(),
            'action': t['action'],
            'pnl_dollar': pnl_dollar,
            'pnl_pct': t['pnl_pct'],
            'is_open_end': is_open_end,
        })

    # Short P&L
    short_details = []
    short_entries = []
    for t in r['trades']:
        if t['action'].startswith('SHORT_T'):
            short_entries.append(t)
        elif t['action'].startswith('SHORT_CLOSE') and short_entries:
            cost = sum(s['amount'] for s in short_entries)
            # short_close amount = cost + pnl
            pnl_dollar = t['amount'] - cost
            short_details.append({
                'entry_date': short_entries[0]['date'].date(),
                'exit_date': t['date'].date(),
                'action': t['action'],
                'tiers': len(short_entries),
                'cost': cost,
                'pnl_dollar': pnl_dollar,
                'pnl_pct': t['pnl_pct'],
                'entry_price': short_entries[0]['price'],
                'exit_price': t['price'],
                'is_open_end': 'OPEN_END' in t.get('action', ''),
            })
            short_entries = []

    # Summarize
    markup_total = sum(m['pnl_dollar'] for m in markup_cycles)
    dca_total = sum(d['pnl_dollar'] for d in dca_details)
    short_total = sum(s['pnl_dollar'] for s in short_details)
    # Filter out OPEN_END for "closed" view
    dca_closed = sum(d['pnl_dollar'] for d in dca_details if not d['is_open_end'])
    short_closed = sum(s['pnl_dollar'] for s in short_details if not s['is_open_end'])

    return {
        'coin': coin,
        'profile': profile,
        'roi': r['roi'],
        'closed_roi': r['closed_roi'],
        'final_equity': r['final_equity'],
        'closed_equity': r['closed_equity'],
        'buy_hold': r['buy_hold_return'],
        'max_dd': r['max_drawdown'],
        'capital': CAPITAL,
        'markup_total': markup_total,
        'markup_pct': markup_total / CAPITAL * 100,
        'markup_cycles': markup_cycles,
        'dca_total': dca_total,
        'dca_closed': dca_closed,
        'dca_pct': dca_total / CAPITAL * 100,
        'dca_details': dca_details,
        'short_total': short_total,
        'short_closed': short_closed,
        'short_pct': short_total / CAPITAL * 100,
        'short_details': short_details,
        'time_markup': r['time_markup_pct'],
        'time_dca': r['time_dca_pct'],
        'time_flat': r['time_flat_pct'],
        'time_markdown': r['time_markdown_pct'],
        'phase_log': r['phases'],
    }


def print_attribution(a):
    print(f"\n{'='*70}")
    print(f"  {a['coin']} — {a['profile'].upper()} profile — ${a['capital']:,} capital")
    print(f"{'='*70}")
    print(f"  Total ROI:    {a['roi']:+.1f}%  (${a['final_equity']:,.0f})")
    print(f"  Closed ROI:   {a['closed_roi']:+.1f}%  (${a['closed_equity']:,.0f})")
    print(f"  Buy & Hold:   {a['buy_hold']:+.1f}%")
    print(f"  Max DD:       {a['max_dd']:.1f}%")
    print()
    print(f"  ── P&L Attribution (on ${a['capital']:,} capital) ──")
    print(f"  MARKUP sells:   ${a['markup_total']:+,.0f}  ({a['markup_pct']:+.1f}% of capital)")
    print(f"  DCA scalps:     ${a['dca_total']:+,.0f}  ({a['dca_pct']:+.1f}% of capital)")
    print(f"  SHORT trades:   ${a['short_total']:+,.0f}  ({a['short_pct']:+.1f}% of capital)")
    print(f"  Sum:            ${a['markup_total']+a['dca_total']+a['short_total']:+,.0f}")
    print()
    
    print(f"  ── Time in Phase ──")
    print(f"  MARKUP: {a['time_markup']:.0f}%  |  DCA: {a['time_dca']:.0f}%  |  FLAT: {a['time_flat']:.0f}%  |  MARKDOWN: {a['time_markdown']:.0f}%")
    print()

    # Markup detail
    if a['markup_cycles']:
        print(f"  ── Markup Trades ({len(a['markup_cycles'])}) ──")
        for i, m in enumerate(a['markup_cycles'], 1):
            days = (m['exit_date'] - m['entry_date']).days
            print(f"    {i}. {m['entry_date']} → {m['exit_date']} ({days}d) T{m['tiers']}")
            print(f"       Entry ${m['entry_price']:,.2f} → Exit ${m['exit_price']:,.2f}  |  {m['pnl_pct']:+.1f}%  |  ${m['pnl_dollar']:+,.0f}")
            print(f"       Reason: {m['action']}")
        print()

    # Short detail
    if a['short_details']:
        print(f"  ── Short Trades ({len(a['short_details'])}) ──")
        for i, s in enumerate(a['short_details'], 1):
            days = (s['exit_date'] - s['entry_date']).days
            oe = " [OPEN_END]" if s['is_open_end'] else ""
            print(f"    {i}. {s['entry_date']} → {s['exit_date']} ({days}d) T{s['tiers']}{oe}")
            print(f"       Entry ${s['entry_price']:,.2f} → Exit ${s['exit_price']:,.2f}  |  {s['pnl_pct']:+.1f}%  |  ${s['pnl_dollar']:+,.0f}")
            print(f"       Reason: {s['action']}")
        print()

    # DCA summary (can be many trades, just show summary + worst)
    if a['dca_details']:
        wins = [d for d in a['dca_details'] if d['pnl_pct'] > 0 and not d['is_open_end']]
        losses = [d for d in a['dca_details'] if d['pnl_pct'] <= 0 and not d['is_open_end']]
        print(f"  ── DCA Summary ({len(a['dca_details'])} trades) ──")
        print(f"    Wins: {len(wins)}  |  Losses: {len(losses)}")
        if wins:
            print(f"    Avg win:  {np.mean([d['pnl_pct'] for d in wins]):+.1f}%  (${np.mean([d['pnl_dollar'] for d in wins]):+,.0f})")
        if losses:
            print(f"    Avg loss: {np.mean([d['pnl_pct'] for d in losses]):+.1f}%  (${np.mean([d['pnl_dollar'] for d in losses]):+,.0f})")
            worst = min(losses, key=lambda d: d['pnl_pct'])
            print(f"    Worst:    {worst['date']} {worst['action']} {worst['pnl_pct']:+.1f}% (${worst['pnl_dollar']:+,.0f})")
        print()

    # Phase log
    print(f"  ── Phase Transitions ──")
    for p in a['phase_log']:
        print(f"    {p['date'].date()}: {p['from'] or 'START'} → {p['to']}  eq=${p['equity']:,.0f}  | {p['reason']}")


if __name__ == '__main__':
    # Run all 9 combos or specific coin/profile from args
    if len(sys.argv) >= 3:
        coins = [sys.argv[1].upper()]
        profiles = [sys.argv[2].lower()]
    elif len(sys.argv) >= 2:
        coins = [sys.argv[1].upper()]
        profiles = PROFILES
    else:
        coins = COINS
        profiles = PROFILES

    results = []
    for coin in coins:
        for profile in profiles:
            print(f"\nRunning {coin} {profile}...")
            a = run_attribution(coin, profile)
            if a:
                results.append(a)
                print_attribution(a)

    # Summary table
    if len(results) > 1:
        print(f"\n{'='*70}")
        print(f"  SUMMARY TABLE")
        print(f"{'='*70}")
        print(f"  {'Coin':<10} {'Profile':<8} {'ROI':>7} {'Markup$':>10} {'DCA$':>10} {'Short$':>10} {'Total$':>10} {'B&H':>7}")
        print(f"  {'-'*10} {'-'*8} {'-'*7} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*7}")
        for a in results:
            print(f"  {a['coin']:<10} {a['profile']:<8} {a['roi']:+6.1f}% {a['markup_total']:>+10,.0f} {a['dca_total']:>+10,.0f} {a['short_total']:>+10,.0f} {a['markup_total']+a['dca_total']+a['short_total']:>+10,.0f} {a['buy_hold']:+6.1f}%")
