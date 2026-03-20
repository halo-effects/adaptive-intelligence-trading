import csv
from collections import defaultdict

trades_by_date = defaultdict(list)
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\trades.csv") as f:
    for row in csv.DictReader(f):
        rt = row["recorded_at"][:10]  # YYYY-MM-DD
        trades_by_date[rt].append(row)

print("=== Trades per day ===")
for date in sorted(trades_by_date.keys()):
    trades = trades_by_date[date]
    pnl = sum(float(t["pnl"]) for t in trades)
    print(f"  {date}: {len(trades)} trades, PnL=${pnl:.2f}")

print(f"\n=== Today's 68 trades breakdown ===")
today_dates = ["2026-03-19", "2026-03-20"]
today_trades = []
for d in today_dates:
    today_trades.extend(trades_by_date.get(d, []))

by_symbol = defaultdict(list)
for t in today_trades:
    by_symbol[t["symbol"]].append(t)

for sym in sorted(by_symbol.keys()):
    trades = by_symbol[sym]
    pnl = sum(float(t["pnl"]) for t in trades)
    layers = [t["layers"] for t in trades]
    durations = [float(t["duration_h"]) for t in trades]
    avg_dur = sum(durations) / len(durations) if durations else 0
    print(f"  {sym}: {len(trades)} trades, PnL=${pnl:.2f}, avg_duration={avg_dur:.1f}h, layers={','.join(layers[:10])}{'...' if len(layers)>10 else ''}")

print(f"\n=== Sample of today's trades (first 10) ===")
for t in sorted(today_trades, key=lambda x: x["recorded_at"])[:10]:
    print(f"  {t['symbol']} L{t['layers']}: open={t['open_time'][:16]}, close={t['close_time'][:16]}, dur={t['duration_h']}h, pnl=${float(t['pnl']):.2f}")

print(f"\n=== Suspiciously fast trades (< 2h) ===")
fast = [t for t in today_trades if float(t["duration_h"]) <= 2]
print(f"  Count: {len(fast)} of {len(today_trades)}")
for t in fast[:15]:
    print(f"  {t['symbol']} L{t['layers']}: {t['open_time'][:16]} -> {t['close_time'][:16]}, {t['duration_h']}h, pnl=${float(t['pnl']):.2f}")
