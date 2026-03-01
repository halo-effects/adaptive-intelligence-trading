import csv
losses = []
wins = []
total_pnl = 0
with open(r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v13\trades.csv') as f:
    for r in csv.DictReader(f):
        pnl = float(r['pnl'])
        total_pnl += pnl
        entry = (r['deal_id'], r['symbol'], r['regime'], r['open_time'][:10], r['close_time'][:10], r['layers'], pnl, r['return_pct'])
        if pnl < 0:
            losses.append(entry)
        else:
            wins.append(entry)

print(f"WINS: {len(wins)}, LOSSES: {len(losses)}")
print(f"Total realized PnL: ${total_pnl:,.1f}")
print(f"\nALL LOSSES:")
loss_total = 0
for d, sym, reg, o, c, lay, pnl, pct in losses:
    print(f"  #{d:>3} {sym:<12} {reg:<12} {o}->{c}  L={lay}  pnl=${pnl:>+10.1f} ({pct}%)")
    loss_total += pnl
print(f"  Total loss: ${loss_total:,.1f}")

print(f"\nBIG WINS (>$100):")
for d, sym, reg, o, c, lay, pnl, pct in wins:
    if pnl > 100:
        print(f"  #{d:>3} {sym:<12} {reg:<12} {o}->{c}  L={lay}  pnl=${pnl:>+10.1f} ({pct}%)")
