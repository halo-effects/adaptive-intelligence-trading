"""
Analyze trapped positions: how often, how long, how much capital locked.
"""
import csv, statistics
from collections import defaultdict

with open("trading/spot/paper/v14_portfolio/trades.csv") as f:
    trades = list(csv.DictReader(f))

print("=" * 70)
print("  TRAPPED CAPITAL ANALYSIS — V14PM Paper")
print("=" * 70)

# Look at duration and layers — long duration + high layers = trapped
long_trades = [t for t in trades if float(t.get("duration_h", 0) or 0) > 48]
deep_trades = [t for t in trades if int(t.get("layers", 0) or 0) >= 4]

print(f"\n  Total trades: {len(trades)}")
print(f"  Trades >48h (2+ days stuck): {len(long_trades)} ({len(long_trades)/len(trades)*100:.1f}%)")
print(f"  Trades 4+ layers deep: {len(deep_trades)} ({len(deep_trades)/len(trades)*100:.1f}%)")

# Duration distribution
durs = [float(t.get("duration_h", 0) or 0) for t in trades]
print(f"\n  Duration distribution:")
buckets = [(0, 2, "<2h"), (2, 6, "2-6h"), (6, 24, "6-24h"), (24, 48, "1-2 days"), 
           (48, 168, "2-7 days"), (168, 504, "1-3 weeks"), (504, 9999, "3+ weeks")]
for lo, hi, label in buckets:
    count = sum(1 for d in durs if lo <= d < hi)
    if count > 0:
        avg_ret = statistics.mean([float(t["return_pct"]) for t in trades if lo <= float(t.get("duration_h",0) or 0) < hi])
        avg_pnl = statistics.mean([float(t["pnl"]) for t in trades if lo <= float(t.get("duration_h",0) or 0) < hi])
        avg_layers = statistics.mean([int(t.get("layers",0) or 0) for t in trades if lo <= float(t.get("duration_h",0) or 0) < hi])
        print(f"    {label:<12}: {count:>4} trades ({count/len(trades)*100:>5.1f}%) | avg ret: {avg_ret:>6.2f}% | avg PnL: ${avg_pnl:>7.2f} | avg layers: {avg_layers:.1f}")

# Worst trapped trades
print(f"\n  WORST TRAPPED (>7 days):")
print(f"  {'Coin':<15} {'Duration':>8} {'Layers':>6} {'Invested':>10} {'PnL':>10} {'Return':>8}")
worst = sorted(trades, key=lambda t: float(t.get("duration_h", 0) or 0), reverse=True)[:15]
for t in worst:
    dur = float(t.get("duration_h", 0) or 0)
    if dur < 48:
        break
    sym = t.get("symbol", "")
    layers = int(t.get("layers", 0) or 0)
    inv = float(t.get("invested", 0) or 0)
    pnl = float(t.get("pnl", 0) or 0)
    ret = float(t.get("return_pct", 0) or 0)
    print(f"  {sym:<15} {dur:>7.0f}h {layers:>6} ${inv:>9.2f} ${pnl:>9.2f} {ret:>7.2f}%")

# Capital at risk: what % of capital is locked in positions >48h?
total_invested_long = sum(float(t.get("invested", 0) or 0) for t in trades if float(t.get("duration_h", 0) or 0) > 48)
total_invested_all = sum(float(t.get("invested", 0) or 0) for t in trades)
print(f"\n  Capital locked in >48h trades: ${total_invested_long:,.0f} ({total_invested_long/total_invested_all*100:.1f}% of total deployed)")

# The key question: do deep grid trades (4+ layers) actually recover?
print(f"\n  DEEP GRID RECOVERY (4+ layers):")
deep = [t for t in trades if int(t.get("layers", 0) or 0) >= 4]
if deep:
    deep_wins = sum(1 for t in deep if float(t.get("pnl", 0) or 0) > 0)
    deep_total_pnl = sum(float(t.get("pnl", 0) or 0) for t in deep)
    deep_total_inv = sum(float(t.get("invested", 0) or 0) for t in deep)
    deep_avg_dur = statistics.mean([float(t.get("duration_h", 0) or 0) for t in deep])
    print(f"    {len(deep)} trades, {deep_wins}/{len(deep)} wins ({deep_wins/len(deep)*100:.0f}%)")
    print(f"    Total PnL: ${deep_total_pnl:,.2f} on ${deep_total_inv:,.2f} deployed")
    print(f"    Avg duration: {deep_avg_dur:.0f}h ({deep_avg_dur/24:.1f} days)")
    print(f"    Avg return: {statistics.mean([float(t['return_pct']) for t in deep]):.2f}%")
    
    # Layer breakdown for deep trades
    for layer_n in [4, 5, 6, 7, 8]:
        layer_trades = [t for t in trades if int(t.get("layers", 0) or 0) == layer_n]
        if layer_trades:
            wins = sum(1 for t in layer_trades if float(t.get("pnl", 0) or 0) > 0)
            avg_dur = statistics.mean([float(t.get("duration_h", 0) or 0) for t in layer_trades])
            avg_ret = statistics.mean([float(t.get("return_pct")) for t in layer_trades])
            print(f"    Layer {layer_n}: {len(layer_trades)} trades, {wins} wins, avg {avg_dur:.0f}h, avg ret {avg_ret:.2f}%")

# NEAR specifically — the only loser in the top coins
print(f"\n  NEAR/USDT (known problem coin):")
near = [t for t in trades if "NEAR" in t.get("symbol", "")]
if near:
    near_pnl = sum(float(t.get("pnl", 0) or 0) for t in near)
    near_avg_dur = statistics.mean([float(t.get("duration_h", 0) or 0) for t in near])
    near_losses = [t for t in near if float(t.get("pnl", 0) or 0) < 0]
    print(f"    {len(near)} trades, PnL: ${near_pnl:.2f}, avg duration: {near_avg_dur:.0f}h")
    print(f"    Losses: {len(near_losses)}")
    for t in near_losses:
        print(f"      {t.get('close_time','?')[:10]} | {t.get('layers','?')}L | ${float(t.get('invested',0)):.2f} inv | ${float(t.get('pnl',0)):.2f} | {float(t.get('return_pct',0)):.2f}%")
