"""Simulate TAO's 5-layer deal with proper Martingale (no 30% cap)"""
import sqlite3, datetime

db = sqlite3.connect(r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db")

# DCA params (High profile)
DCA_BO_PCT = 0.30
DCA_SO_MULT = 1.5
DCA_SO_DEV = 0.02  # 2% per layer
DCA_MAX_LAYERS = 12
DCA_TP_PCT = 0.015
ALLOCATION = 20167.35  # TAO's allocation from the log

# Get TAO 1h candles from Apr 9 18:00 onward
candles = db.execute("""
    SELECT timestamp, open, high, low, close 
    FROM candles WHERE symbol='TAO/USDT' AND timeframe='1h'
    AND timestamp >= 1775685600000
    ORDER BY timestamp
""").fetchall()

candle_list = []
for ts, o, h, l, c in candles:
    dt = datetime.datetime.fromtimestamp(ts/1000, tz=datetime.timezone.utc)
    candle_list.append({"ts": dt, "open": o, "high": h, "low": l, "close": c})

print("=" * 70)
print("TAO DCA SIMULATION: Proper Martingale vs 30% Cap")
print("=" * 70)
print(f"Allocation: ${ALLOCATION:.2f}")
print(f"Profile: BO=30%, Dev=2%/layer, Mult=1.5x, MaxLayers=12, TP=1.5%")

# Simulate WITH 30% cap (what actually happened)
print(f"\n{'='*70}")
print("SCENARIO A: With 30% cap (what paper bot did)")
print("=" * 70)

capital = ALLOCATION
coins = 0.0
cost = 0.0
layers = 0
avg_entry = 0.0

for candle in candle_list:
    price = candle["close"]
    high = candle["high"]
    
    # Check TP first
    if coins > 0 and avg_entry > 0:
        tp = avg_entry * (1 + DCA_TP_PCT)
        if high >= tp:
            proceeds = coins * tp
            pnl = proceeds - cost
            print(f"  TP HIT @ {candle['ts'].strftime('%m-%d %H:%M')} | price high=${high:.2f} >= TP=${tp:.2f}")
            print(f"  PnL: ${pnl:.2f} ({pnl/cost*100:.2f}%)")
            break
    
    # Check if should buy
    should_buy = False
    if layers == 0:
        should_buy = True
    elif layers < DCA_MAX_LAYERS and avg_entry > 0:
        target_drop = DCA_SO_DEV * layers
        current_drop = (avg_entry - price) / avg_entry
        if current_drop >= target_drop:
            should_buy = True
    
    if should_buy and capital > 10:
        if layers == 0:
            order = capital * DCA_BO_PCT
        else:
            order = capital * DCA_BO_PCT * (DCA_SO_MULT ** min(layers, 4))
        # Apply 30% cap
        order = min(order, capital * 0.3)
        order = min(order, capital)
        if order >= 10:
            new_coins = order / price
            coins += new_coins
            capital -= order
            cost += order
            layers += 1
            avg_entry = cost / coins
            tp = avg_entry * (1 + DCA_TP_PCT)
            print(f"  L{layers}: ${order:.0f} @ ${price:.2f} | coins={new_coins:.2f} | "
                  f"avg=${avg_entry:.2f} | TP=${tp:.2f} | remaining=${capital:.0f}")

if coins > 0 and layers > 0:
    tp = avg_entry * (1 + DCA_TP_PCT)
    last_price = candle_list[-1]["close"]
    unrealized = coins * (last_price - avg_entry)
    print(f"\n  FINAL: {layers} layers, ${cost:.0f} invested, avg=${avg_entry:.2f}, TP=${tp:.2f}")
    print(f"  Current price: ${last_price:.2f}, unrealized: ${unrealized:.2f} ({unrealized/cost*100:.1f}%)")

# Simulate WITHOUT 30% cap (proper Martingale)
print(f"\n{'='*70}")
print("SCENARIO B: Proper Martingale (no 30% cap)")
print("=" * 70)

capital = ALLOCATION
coins = 0.0
cost = 0.0
layers = 0
avg_entry = 0.0

for candle in candle_list:
    price = candle["close"]
    high = candle["high"]
    
    # Check TP first
    if coins > 0 and avg_entry > 0:
        tp = avg_entry * (1 + DCA_TP_PCT)
        if high >= tp:
            proceeds = coins * tp
            pnl = proceeds - cost
            print(f"  TP HIT @ {candle['ts'].strftime('%m-%d %H:%M')} | price high=${high:.2f} >= TP=${tp:.2f}")
            print(f"  PnL: ${pnl:.2f} ({pnl/cost*100:.2f}%)")
            break
    
    # Check if should buy
    should_buy = False
    if layers == 0:
        should_buy = True
    elif layers < DCA_MAX_LAYERS and avg_entry > 0:
        target_drop = DCA_SO_DEV * layers
        current_drop = (avg_entry - price) / avg_entry
        if current_drop >= target_drop:
            should_buy = True
    
    if should_buy and capital > 10:
        if layers == 0:
            order = capital * DCA_BO_PCT
        else:
            order = capital * DCA_BO_PCT * (DCA_SO_MULT ** min(layers, 4))
        # NO 30% cap — proper Martingale
        order = min(order, capital)  # Can't spend more than remaining
        if order >= 10:
            new_coins = order / price
            coins += new_coins
            capital -= order
            cost += order
            layers += 1
            avg_entry = cost / coins
            tp = avg_entry * (1 + DCA_TP_PCT)
            print(f"  L{layers}: ${order:.0f} @ ${price:.2f} | coins={new_coins:.2f} | "
                  f"avg=${avg_entry:.2f} | TP=${tp:.2f} | remaining=${capital:.0f}")

if coins > 0 and layers > 0:
    tp = avg_entry * (1 + DCA_TP_PCT)
    last_price = candle_list[-1]["close"]
    unrealized = coins * (last_price - avg_entry)
    print(f"\n  FINAL: {layers} layers, ${cost:.0f} invested, avg=${avg_entry:.2f}, TP=${tp:.2f}")
    print(f"  Current price: ${last_price:.2f}, unrealized: ${unrealized:.2f} ({unrealized/cost*100:.1f}%)")
    
    # How far from TP?
    pct_to_tp = (tp - last_price) / last_price * 100
    print(f"  Distance to TP: {pct_to_tp:.1f}%")

db.close()
