import sqlite3, datetime
db = sqlite3.connect(r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db")

# The last candle we have is 13:00 UTC. L5 was at 16:00 UTC.
# The deal closed at 18:00 UTC. Let's check if there are later candles
latest = db.execute("""
    SELECT timestamp, close FROM candles 
    WHERE symbol = 'TAO/USDT' AND timeframe = '1h'
    ORDER BY timestamp DESC LIMIT 5
""").fetchall()
for ts, c in latest:
    dt = datetime.datetime.fromtimestamp(ts/1000, tz=datetime.timezone.utc)
    print(f"Latest: {dt.strftime('%Y-%m-%d %H:%M')} close={c}")

# The deal had 5 layers, total invested $16,939.49
# We have L1-L4 = $15,473.17, so L5 = $16,939.49 - $15,473.17 = $1,466.32
# L5 amount confirmed: $1,466.31

# L5 was at 16:00 UTC Apr 10. Price was somewhere around $256-262 range
# (13:00 was $262.70, and current_price in status is $256.70)
# Let's estimate with $258 (midpoint of likely range)

# Actually, the deal PnL is $250.65 at 1.48% return
# invested = $16,939.49, PnL = $250.65
# return = 250.65 / 16939.49 = 1.479% ≈ 1.48% ✓
# exit_value = invested + pnl = $17,190.14
# But fees reduce this: returned $17,193.58 to pool

# Work backwards from the 1.48% return:
# TP is at avg_entry * 1.015 (the engine sells at TP price)
# So: pnl = total_coins * (tp_price - avg_entry) - fees
# Or more precisely: pnl = invested * 0.015 - fees (since TP = avg * 1.015)
# But return is 1.48%, and TP is 1.5%, so ~0.02% went to fees

# Let me work out L5 price from total deal math
# total_invested = 16939.49
# pnl = 250.6536
# return = 1.48%
# L1-L4 coins: 47.2262 coins, cost $15,473.17
# L5 cost: $1,466.31
# Total coins = 47.2262 + (1466.31 / L5_price)
# avg_entry = 16939.49 / total_coins
# tp = avg_entry * 1.015
# The 18:00 candle high must have >= tp

# Since the last candle we see is 13:00 at $262.70, and status shows current $256.70...
# Let's try a few L5 prices to see what TP would be

for l5_price in [255, 257, 258, 260, 262]:
    l5_coins = 1466.31 / l5_price
    total_coins = 47.2262 + l5_coins
    total_inv = 16939.49
    avg = total_inv / total_coins
    tp = avg * 1.015
    # Check if TP is achievable given the price dropped to ~$249-265 range
    print(f"  L5@${l5_price}: coins={l5_coins:.2f}, total={total_coins:.2f}, avg=${avg:.2f}, TP=${tp:.2f}")

db.close()
