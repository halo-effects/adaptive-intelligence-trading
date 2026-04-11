"""Reconstruct live bot TAO layers with actual crash candle prices and $20,167 allocation."""

alloc = 20167.35
BO_PCT = 0.30
SO_MULT = 1.5
SO_DEV = 0.02
TP_PCT = 0.015

# Actual candle close prices from the crash (from bot log + candle data)
# L1: Apr 9 19:00 close=$337.30
# L2: Apr 9 21:00 close=$335.20 — wait, need to check when 2% drop triggers

# Live bot: engine capital resets to $20,167 after each buy
# Layer trigger: current_drop >= SO_DEV * layers (from avg_entry)

capital = alloc
total_cost = 0
total_coins = 0
layers = 0

# Candle closes during the crash (from our candle data)
crash_candles = [
    ("Apr 9 19:00", 337.30),  # L1 entry
    ("Apr 9 20:00", 337.80),
    ("Apr 9 21:00", 335.20),
    ("Apr 9 22:00", 332.40),
    ("Apr 9 23:00", 305.10),
    ("Apr 10 00:00", 284.90),
    ("Apr 10 01:00", 290.80),
    ("Apr 10 02:00", 291.90),
    ("Apr 10 03:00", 276.20),
    ("Apr 10 04:00", 264.50),
    ("Apr 10 05:00", 270.00),
    ("Apr 10 06:00", 264.60),
    ("Apr 10 07:00", 262.90),
    ("Apr 10 08:00", 263.00),
    ("Apr 10 09:00", 268.40),
    ("Apr 10 10:00", 267.30),
    ("Apr 10 11:00", 263.70),
    ("Apr 10 12:00", 261.60),
    ("Apr 10 13:00", 262.70),
]

print(f"TAO Live Bot Simulation (alloc=${alloc:.2f})")
print(f"Martingale: BO=30%, Mult=1.5x, Dev=2%/layer, TP=1.5%")
print(f"GAP-13: engine capital resets to ${alloc:.2f} after each buy")
print(f"Guard: order > engine capital = BLOCKED")
print()

for time_str, price in crash_candles:
    # Check if should buy
    should_buy = False
    if layers == 0:
        should_buy = True
    else:
        avg_entry = total_cost / total_coins
        target_drop = SO_DEV * layers
        current_drop = (avg_entry - price) / avg_entry
        if current_drop >= target_drop:
            should_buy = True
    
    if should_buy:
        # Calculate order (engine capital = alloc due to GAP-13 reset)
        if layers == 0:
            order = alloc * BO_PCT
        else:
            order = alloc * BO_PCT * (SO_MULT ** min(layers, 4))
        
        # Live bot guard
        if order > alloc:
            avg_entry = total_cost / total_coins
            tp = avg_entry * (1 + TP_PCT)
            print(f"  {time_str}: L{layers+1} BLOCKED — order ${order:.0f} > capital ${alloc:.0f}")
            print(f"  (Would need ${order:.0f} but allocation is ${alloc:.0f})")
            continue
        
        new_coins = order / price
        total_cost += order
        total_coins += new_coins
        layers += 1
        avg_entry = total_cost / total_coins
        tp = avg_entry * (1 + TP_PCT)
        depth = (crash_candles[0][1] - price) / crash_candles[0][1] * 100
        
        print(f"  {time_str}: L{layers} BUY ${order:>10,.2f} @ ${price:.2f} | "
              f"avg=${avg_entry:.2f} | TP=${tp:.2f} | grid depth={depth:.1f}%")

print()
avg_entry = total_cost / total_coins
tp = avg_entry * (1 + TP_PCT)
last_price = 262.70
unrealized = total_coins * (last_price - avg_entry)
recovery = (tp - last_price) / last_price * 100

print(f"RESULT:")
print(f"  Layers: {layers}")
print(f"  Total invested: ${total_cost:,.2f} of ${alloc:,.2f} allocation")
print(f"  Coins: {total_coins:.4f} TAO")
print(f"  Avg entry: ${avg_entry:.2f}")
print(f"  TP target: ${tp:.2f}")
print(f"  Current price: ${last_price:.2f}")
print(f"  Unrealized: ${unrealized:,.2f} ({unrealized/total_cost*100:.1f}%)")
print(f"  Recovery needed: {recovery:.1f}%")
