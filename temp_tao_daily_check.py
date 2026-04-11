"""Check what daily OHLC the engine used for TAO's TP fills"""
import sqlite3, datetime, csv
from pathlib import Path

db = sqlite3.connect(r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db")

# Get TAO daily candles
print("=== TAO/USDT daily candles ===")
candles = db.execute("""
    SELECT timestamp, open, high, low, close 
    FROM candles_daily 
    WHERE symbol = 'TAO/USDT'
    ORDER BY timestamp DESC LIMIT 10
""").fetchall()
candles.reverse()
for ts, o, h, l, c in candles:
    dt = datetime.datetime.fromtimestamp(ts/1000, tz=datetime.timezone.utc) if ts > 1e9 else ts
    print(f"  {dt} | O={o:.2f} H={h:.2f} L={l:.2f} C={c:.2f}")

# Now check ALL TAO deals - are they all 1.48%?
print("\n=== ALL TAO trades from CSV ===")
csv_path = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\trades.csv")
with open(csv_path) as f:
    reader = list(csv.DictReader(f))

tao_trades = [t for t in reader if "TAO" in t.get("symbol", "")]
print(f"Total TAO deals: {len(tao_trades)}")

# Check return distribution
returns = [float(t["return_pct"]) for t in tao_trades]
from collections import Counter
ret_counts = Counter(returns)
print(f"Return distribution: {dict(ret_counts)}")

# Check if any had more than 1-2 layers
layer_counts = Counter([int(t["layers"]) for t in tao_trades])
print(f"Layer distribution: {dict(sorted(layer_counts.items()))}")

# Show the deals with 3+ layers specifically
print("\nDeals with 3+ layers:")
for t in tao_trades:
    layers = int(t["layers"])
    if layers >= 3:
        print(f"  {t['open_time'][:10]} -> {t['close_time'][:10]} | L{layers} | inv=${float(t['invested']):.0f} | ret={t['return_pct']}% | pnl=${float(t['pnl']):.2f} | dur={t['duration_h']}h")

# Now check ALL coins - is the 1.48% pattern universal?
print("\n=== Return distribution across ALL coins ===")
all_returns = [float(t["return_pct"]) for t in reader]
all_ret_counts = Counter(all_returns)
print(f"All returns: {dict(sorted(all_ret_counts.items()))}")

# Check if any deal has a non-1.48% return
non_tp = [t for t in reader if abs(float(t["return_pct"]) - 1.48) > 0.1]
print(f"\nDeals with return != 1.48%: {len(non_tp)}")
for t in non_tp[:10]:
    print(f"  {t['symbol']} {t['open_time'][:10]}->{t['close_time'][:10]} L{t['layers']} ret={t['return_pct']}% pnl=${float(t['pnl']):.2f}")

db.close()
