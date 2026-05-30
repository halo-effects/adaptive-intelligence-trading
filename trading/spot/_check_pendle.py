import csv
with open("trading/spot/live/v14pm/trades.csv") as f:
    trades = list(csv.DictReader(f))

pendle = [t for t in trades if "PENDLE" in t.get("symbol", "")]
print(f"PENDLE trades: {len(pendle)} total")
for t in pendle[-5:]:
    ct = t.get("close_time", "?")[:19]
    inv = float(t.get("invested", 0))
    pnl = float(t.get("pnl", 0))
    ret = float(t.get("return_pct", 0))
    layers = t.get("layers", "?")
    print(f"  {ct} | layers={layers} | invested=${inv:.2f} | pnl=${pnl:.4f} | {ret:.2f}%")

# Also check the bot log for spread reject details
print()
print("All spread rejects in log:")
import os
log_path = "trading/spot/live/v14pm/bot.log"
if os.path.exists(log_path):
    with open(log_path) as f:
        for line in f:
            if "spread" in line.lower() or "Spread" in line:
                print(f"  {line.strip()}")
