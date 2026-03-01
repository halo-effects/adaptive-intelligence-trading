"""Apples-to-apples: Paper bot timeframe (Sep 2024 -> today).
4 coins: ETH, SOL, LINK, XRP. $2,500/coin. High profile.
Baseline V13 vs Baseline + isolated 1h DCA grinder."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'

# Paper bot exact config
COINS = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
CAPITAL = 2500
START = '2024-10-01'
END = '2026-02-27'

# DCA grinder configs (1h winners)
DCA_OVERRIDES = {
    'ETH/USDC': {'tp': 0.015, 'dev': 0.025, 'so_mult': 2.0, 'layers': 8, 'bo_pct': 0.05},
    'SOL/USDC': {'tp': 0.020, 'dev': 0.030, 'so_mult': 2.0, 'layers': 8, 'bo_pct': 0.05},
    'LINK/USDC': {'tp': 0.010, 'dev': 0.020, 'so_mult': 2.0, 'layers': 8, 'bo_pct': 0.05},
    'XRP/USDC': {'tp': 0.015, 'dev': 0.025, 'so_mult': 2.0, 'layers': 8, 'bo_pct': 0.05},
}

# Import enhanced engine
from v13_enhanced_dca_test import V13Enhanced, load_1h_candles

print("=" * 110)
print(f"PAPER BOT COMPARISON: {START} -> {END}")
print(f"Coins: {', '.join(c.split('/')[0] for c in COINS)} | Capital: ${CAPITAL}/coin | Profile: high")
print("=" * 110)

total_base_eq = 0
total_grinder_pnl = 0
results = []

for coin in COINS:
    short = coin.split('/')[0]
    print(f"\n{'='*110}")
    print(f"  {coin}")
    print(f"{'='*110}")

    cfg = V13Config()
    cfg.CAPITAL = CAPITAL
    cfg.START_DATE = START
    cfg.END_DATE = END
    cfg.TIER1_PCT = 0.60; cfg.TIER2_PCT = 0.20; cfg.TIER3_PCT = 0.10
    cfg.SHORT_TIER1_PCT = 0.60; cfg.SHORT_TIER2_PCT = 0.20; cfg.SHORT_TIER3_PCT = 0.10
    cfg.SHORTS_ENABLED = True

    # Baseline
    pack = V13SignalPack(coin, db_path=DB)
    baseline = V13BacktestV8(pack, cfg)
    br = baseline.run()
    if not br:
        print(f"  FAILED")
        continue

    # Enhanced (isolated grinder)
    candles_1h = load_1h_candles(coin)
    pack2 = V13SignalPack(coin, db_path=DB)
    enhanced = V13Enhanced(pack2, cfg, DCA_OVERRIDES.get(coin), candles_1h)
    er = enhanced.run()

    grinder_pnl = er.get('grinder_pnl', 0) if er else 0
    grinder_trades = er.get('grinder_trades', 0) if er else 0
    grinder_wins = er.get('grinder_wins', 0) if er else 0
    grinder_lots = er.get('grinder_lots', 0) if er else 0
    grinder_cap = er.get('grinder_capital', 0) if er else 0

    combined_equity = br['final_equity'] + grinder_pnl
    combined_roi = (combined_equity - CAPITAL) / CAPITAL * 100

    # Phase log
    print(f"\n  PHASE LOG:")
    for p in baseline.phase_log:
        fr = p.get('from', '-')
        to = p.get('to', '-')
        if hasattr(fr, 'name'): fr = fr.name
        if hasattr(to, 'name'): to = to.name
        eq = p.get('equity', 0)
        reason = p.get('reason', '')
        dt = str(p['date'])[:10]
        print(f"    {dt}  {str(fr):>12} -> {str(to):<12} eq=${eq:>8.0f}  {reason}")

    # Markup trades
    print(f"\n  MARKUP ENTRIES & EXITS:")
    markup_entry = None
    for p in baseline.phase_log:
        to_p = p.get('to', None)
        fr_p = p.get('from', None)
        if to_p == Phase.MARKUP:
            markup_entry = p
        elif fr_p == Phase.MARKUP and markup_entry:
            entry_eq = markup_entry.get('equity', 0)
            exit_eq = p.get('equity', 0)
            pnl = exit_eq - entry_eq
            pnl_pct = pnl / entry_eq * 100 if entry_eq > 0 else 0
            entry_dt = str(markup_entry['date'])[:10]
            exit_dt = str(p['date'])[:10]
            days = (p['date'] - markup_entry['date']).days
            reason = p.get('reason', '')
            to_name = p['to'].name if hasattr(p['to'], 'name') else str(p['to'])
            status = "FAIL" if pnl < 0 else "OK"
            print(f"    {entry_dt} -> {exit_dt} ({days:>3}d)  ${entry_eq:>7.0f} -> ${exit_eq:>7.0f}  "
                  f"P&L: ${pnl:>+7.0f} ({pnl_pct:>+5.1f}%)  [{status}]  {reason}")
            markup_entry = None

    # All trades
    print(f"\n  ALL TRADES:")
    for t in baseline.trades:
        action = t.get('action', '')
        pnl = t.get('pnl_pct', None)
        price = t.get('price', 0)
        amt = t.get('amount', 0)
        phase = t.get('phase', '')
        if hasattr(phase, 'name'): phase = phase.name
        dt = str(t['date'])[:10]
        pnl_s = f"pnl={pnl:+.1f}%" if pnl is not None else ""
        print(f"    {dt}  {action:<45} ${amt:>8.1f}  @{price:.4f}  {phase:<12} {pnl_s}")

    # Summary
    print(f"\n  --- BASELINE ---")
    print(f"    ROI:        {br['roi']:>+8.1f}%  (${br['final_equity'] - CAPITAL:>+,.0f})")
    print(f"    Closed ROI: {br['closed_roi']:>+8.1f}%")
    print(f"    DCA P&L:    ${baseline.dca_pnl:>+8.1f}  ({baseline.dca_trades} trades)")
    print(f"    Max DD:     {br['max_drawdown']:>8.1f}%")

    print(f"\n  --- 1h DCA GRINDER (additive) ---")
    print(f"    Grinder P&L: ${grinder_pnl:>+8.1f}  ({grinder_trades} trades, "
          f"{grinder_wins/max(grinder_trades,1)*100:.0f}% WR, {grinder_lots} lots)")

    print(f"\n  --- COMBINED ---")
    print(f"    ROI:        {combined_roi:>+8.1f}%  (${combined_equity - CAPITAL:>+,.0f})")
    print(f"    Lift:       {combined_roi - br['roi']:>+8.1f}%  (${grinder_pnl:>+,.0f})")

    total_base_eq += br['final_equity']
    total_grinder_pnl += grinder_pnl
    results.append({
        'coin': short, 'base_roi': br['roi'], 'combined_roi': combined_roi,
        'base_eq': br['final_equity'], 'grinder_pnl': grinder_pnl,
        'dca_pnl': baseline.dca_pnl, 'grinder_trades': grinder_trades,
    })

# Portfolio
total_cap = len(results) * CAPITAL
base_port = (total_base_eq - total_cap) / total_cap * 100
comb_port = (total_base_eq + total_grinder_pnl - total_cap) / total_cap * 100

print(f"\n{'='*110}")
print(f"PORTFOLIO SUMMARY (Sep 2024 -> today, 4 coins, ${total_cap:,})")
print(f"{'='*110}")
print(f"\n  {'Coin':<6} {'Base ROI':>10} {'Combined':>10} {'Grinder$':>10} {'Base DCA$':>10}")
print(f"  {'_'*6} {'_'*10} {'_'*10} {'_'*10} {'_'*10}")
for r in results:
    print(f"  {r['coin']:<6} {r['base_roi']:>+9.1f}% {r['combined_roi']:>+9.1f}% "
          f"${r['grinder_pnl']:>+9.1f} ${r['dca_pnl']:>+9.1f}")

print(f"\n  PORTFOLIO:")
print(f"    Baseline:  {base_port:>+8.1f}%  (${total_base_eq - total_cap:>+,.0f})")
print(f"    Combined:  {comb_port:>+8.1f}%  (${total_base_eq + total_grinder_pnl - total_cap:>+,.0f})")
print(f"    Grinder:   +${total_grinder_pnl:>,.0f} additive")

# Compare to live paper bot
print(f"\n  LIVE PAPER BOT (for reference):")
print(f"    Equity: $30,011 (+200.1%) as of Feb 27 2026")
print(f"    Started: Feb 25 2026 with backfill from historical data")

print(f"\n{'='*110}")
print("Done.")
