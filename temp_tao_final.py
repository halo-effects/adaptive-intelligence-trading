import sqlite3
db = sqlite3.connect(r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db")

# Get TAO trades from DB
rows = db.execute("""
    SELECT deal_id, open_time, close_time, layers, invested, pnl, return_pct, 
           entry_price, exit_price, duration_hours
    FROM trades 
    WHERE symbol LIKE '%TAO%' 
    ORDER BY close_time DESC 
    LIMIT 5
""").fetchall()
print("Recent TAO trades from DB:")
for r in rows:
    print(f"  Deal {r[0]}: open={r[1]}, close={r[2]}, layers={r[3]}, inv=${r[4]:.2f}, pnl=${r[5]:.2f}, ret={r[6]:.2f}%, entry=${r[7]}, exit=${r[8]}, dur={r[9]:.1f}h")

# Get TAO candles around the TP time
# Latest candle timestamp: 1775826000000 (ms)
# Convert buy times to ms timestamps
import datetime
# 2026-04-09 19:00 UTC
buy_times_utc = [
    datetime.datetime(2026, 4, 9, 19, 0, tzinfo=datetime.timezone.utc),
    datetime.datetime(2026, 4, 9, 21, 0, tzinfo=datetime.timezone.utc),
    datetime.datetime(2026, 4, 9, 22, 0, tzinfo=datetime.timezone.utc),
    datetime.datetime(2026, 4, 10, 0, 0, tzinfo=datetime.timezone.utc),
    datetime.datetime(2026, 4, 10, 16, 0, tzinfo=datetime.timezone.utc),
]
tp_time = datetime.datetime(2026, 4, 10, 18, 0, tzinfo=datetime.timezone.utc)

start_ms = int(buy_times_utc[0].timestamp() * 1000) - 3600000
end_ms = int(tp_time.timestamp() * 1000) + 3600000

candles = db.execute("""
    SELECT timestamp, open, high, low, close 
    FROM candles 
    WHERE symbol = 'TAO/USDT' AND timeframe = '1h'
    AND timestamp >= ? AND timestamp <= ?
    ORDER BY timestamp
""", (start_ms, end_ms)).fetchall()

print(f"\nTAO/USDT 1h candles ({len(candles)} candles):")
candle_dict = {}
for ts, o, h, l, c in candles:
    dt = datetime.datetime.fromtimestamp(ts/1000, tz=datetime.timezone.utc)
    candle_dict[ts] = (o, h, l, c)
    print(f"  {dt.strftime('%Y-%m-%d %H:%M')} | O={o:.2f} H={h:.2f} L={l:.2f} C={c:.2f}")

# Reconstruct DCA grid
buy_amounts = [6109.19, 4276.07, 2992.99, 2094.92, 1466.31]
total_coins = 0.0
total_cost = 0.0

print(f"\n=== DCA RECONSTRUCTION ===")
for i, (bt, amt) in enumerate(zip(buy_times_utc, buy_amounts)):
    ts_ms = int(bt.timestamp() * 1000)
    if ts_ms in candle_dict:
        o, h, l, c = candle_dict[ts_ms]
        coins = amt / c
        total_coins += coins
        total_cost += amt
        avg = total_cost / total_coins
        tp = avg * 1.015
        print(f"  L{i+1}: ${amt:.2f} @ ${c:.2f} = {coins:.4f} TAO | avg=${avg:.2f} | TP=${tp:.2f}")
    else:
        # Try previous candle close
        prev_ms = ts_ms - 3600000
        if prev_ms in candle_dict:
            o, h, l, c = candle_dict[prev_ms]
            coins = amt / c
            total_coins += coins
            total_cost += amt
            avg = total_cost / total_coins
            tp = avg * 1.015
            print(f"  L{i+1}: ${amt:.2f} @ ${c:.2f} (prev candle) = {coins:.4f} TAO | avg=${avg:.2f} | TP=${tp:.2f}")
        else:
            print(f"  L{i+1}: ${amt:.2f} @ {bt.strftime('%H:%M')} - NO CANDLE (ts={ts_ms})")

if total_coins > 0:
    final_avg = total_cost / total_coins
    final_tp = final_avg * 1.015
    print(f"\n  FINAL: invested=${total_cost:.2f}, coins={total_coins:.4f}")
    print(f"  Weighted avg entry: ${final_avg:.2f}")
    print(f"  TP target (1.5%): ${final_tp:.2f}")
    
    # Check TP candle
    tp_ms = int(tp_time.timestamp() * 1000)
    if tp_ms in candle_dict:
        o, h, l, c = candle_dict[tp_ms]
        print(f"\n  TP candle (18:00 UTC): O={o:.2f} H={h:.2f} L={l:.2f} C={c:.2f}")
        print(f"  High ${h:.2f} >= TP ${final_tp:.2f}? {h >= final_tp}")

db.close()
