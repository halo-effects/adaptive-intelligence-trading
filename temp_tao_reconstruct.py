"""Reconstruct TAO's last deal from the buy log entries and DCA math."""
# From bot log:
# L1: $6,109.19  @ 2026-04-09 19:00 UTC
# L2: $4,276.07  @ 2026-04-09 21:00 UTC
# L3: $2,992.99  @ 2026-04-09 22:00 UTC
# L4: $2,094.92  @ 2026-04-10 00:00 UTC
# L5: $1,466.31  @ 2026-04-10 16:00 UTC
# Total: $16,939.48
# Deal closed: 2026-04-10 18:00 UTC
# PnL: $250.65, return: 1.48%
# Returned to pool: $17,193.58 ($16,939 + $250.65 = ~$17,190 + fees)

# To find TP price, I need the entry prices at each layer.
# Let's check Hyperliquid candle data for TAO around those times
import json
from pathlib import Path

# Try to get candle data from the DB
import sqlite3
db = sqlite3.connect(r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db")

# Get TAO 1h candles around the buy times
cur = db.execute("""
    SELECT timestamp, open, high, low, close 
    FROM candles_1h 
    WHERE symbol = 'TAO/USDT' 
    AND timestamp >= '2026-04-09 18:00' 
    AND timestamp <= '2026-04-11 00:00'
    ORDER BY timestamp
""")
candles = cur.fetchall()
print("TAO/USDT 1h candles during the deal:")
for ts, o, h, l, c in candles:
    print(f"  {ts} | O={o:.2f} H={h:.2f} L={l:.2f} C={c:.2f}")

# DCA grid math: BO=30%, Dev=1.5% (actually 2% for high profile), Mult=1.5x
# High profile: DCA_BO_PCT=0.30, DCA_SO_DEV=0.02, DCA_SO_MULT=1.5, TP=1.5%

# L1 (base order): 30% of allocation at entry price
# L2: BO * 1.5 at entry * (1 - 0.02)
# etc.

# The entry prices come from the candle close at each buy time
# L1 @ 19:00 UTC, L2 @ 21:00, L3 @ 22:00, L4 @ 00:00 Apr 10, L5 @ 16:00 Apr 10

buy_times = [
    "2026-04-09 19:00",
    "2026-04-09 21:00",
    "2026-04-09 22:00",
    "2026-04-10 00:00",
    "2026-04-10 16:00",
]
buy_amounts = [6109.19, 4276.07, 2992.99, 2094.92, 1466.31]

# Get the close price at each buy candle
candle_dict = {ts[:16]: (o, h, l, c) for ts, o, h, l, c in candles}

total_coins = 0.0
total_cost = 0.0
for i, (t, amt) in enumerate(zip(buy_times, buy_amounts)):
    if t in candle_dict:
        o, h, l, c = candle_dict[t]
        # Engine buys at close of the candle that triggered the signal
        coins = amt / c
        total_coins += coins
        total_cost += amt
        avg = total_cost / total_coins
        tp = avg * 1.015  # 1.5% TP
        print(f"\n  Layer {i+1}: ${amt:.2f} @ ${c:.2f} = {coins:.4f} TAO")
        print(f"    Running avg_entry: ${avg:.2f}, TP target: ${tp:.2f}")
    else:
        print(f"\n  Layer {i+1}: ${amt:.2f} @ {t} - NO CANDLE DATA")

if total_coins > 0:
    final_avg = total_cost / total_coins
    final_tp = final_avg * 1.015
    print(f"\n=== FINAL ===")
    print(f"  Total invested: ${total_cost:.2f}")
    print(f"  Total coins: {total_coins:.4f}")
    print(f"  Weighted avg entry: ${final_avg:.2f}")
    print(f"  TP price (1.5% above avg): ${final_tp:.2f}")
    
    # What was the close price when TP hit?
    tp_time = "2026-04-10 18:00"
    if tp_time in candle_dict:
        o, h, l, c = candle_dict[tp_time]
        print(f"\n  TP candle ({tp_time}): O={o:.2f} H={h:.2f} L={l:.2f} C={c:.2f}")
        print(f"  High >= TP? {h >= final_tp} (high ${h:.2f} vs TP ${final_tp:.2f})")

db.close()
