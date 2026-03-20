import csv
from collections import defaultdict

# The key question: when were these trades actually OPENED vs when were they RECORDED?
# If recorded_at is today but open_time is March 12, these trades were backfilled.

today_trades = []
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\trades.csv") as f:
    for row in csv.DictReader(f):
        rt = row["recorded_at"][:10]
        if rt in ("2026-03-19", "2026-03-20"):
            today_trades.append(row)

# How many are backdated (open_time much earlier than recorded_at)?
backdated = 0
legit = 0
for t in today_trades:
    open_date = t["open_time"][:10]
    record_date = t["recorded_at"][:10]
    if open_date < "2026-03-19":
        backdated += 1
    else:
        legit += 1

print(f"Today's 'recorded' trades: {len(today_trades)}")
print(f"  Legitimately opened today: {legit}")
print(f"  Backdated (opened before today): {backdated}")
print()

# Show all GRASS trades open dates
print("=== All GRASS trades recorded today, sorted by open_time ===")
grass = [t for t in today_trades if t["symbol"] == "GRASS/USDT"]
for t in sorted(grass, key=lambda x: x["open_time"]):
    print(f"  open={t['open_time'][:16]}, close={t['close_time'][:16]}, dur={t['duration_h']}h, L{t['layers']}, pnl=${float(t['pnl']):.2f}, recorded={t['recorded_at'][:16]}")

# What this means: the engine was created fresh today for GRASS (new coin in scanner),
# and it replayed the entire backfilled candle history, generating trades retroactively.
print()
print("=== Earliest open_time per symbol (for today's recorded trades) ===")
by_sym = defaultdict(list)
for t in today_trades:
    by_sym[t["symbol"]].append(t)
for sym in sorted(by_sym.keys()):
    earliest = min(t["open_time"] for t in by_sym[sym])
    latest = max(t["close_time"] for t in by_sym[sym])
    print(f"  {sym}: earliest_open={earliest[:16]}, latest_close={latest[:16]}, count={len(by_sym[sym])}")
