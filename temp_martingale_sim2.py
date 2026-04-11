"""Simulate TAO from the actual L1 entry point with proper Martingale"""
import sqlite3, datetime

db = sqlite3.connect(r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db")

# Start from the actual L1 candle: Apr 9 19:00 UTC (close=$337.30)
# ts_ms for Apr 9 19:00 = 1775775600000
start_ms = 1775775600000

candles = db.execute("""
    SELECT timestamp, open, high, low, close 
    FROM candles WHERE symbol='TAO/USDT' AND timeframe='1h'
    AND timestamp >= ?
    ORDER BY timestamp
""", (start_ms,)).fetchall()

candle_list = []
for ts, o, h, l, c in candles:
    dt = datetime.datetime.fromtimestamp(ts/1000, tz=datetime.timezone.utc)
    candle_list.append({"ts": dt, "open": o, "high": h, "low": l, "close": c})

ALLOCATION = 20167.35
DCA_BO_PCT = 0.30
DCA_SO_MULT = 1.5
DCA_SO_DEV = 0.02
DCA_MAX_LAYERS = 12
DCA_TP_PCT = 0.015

def simulate(name, use_cap):
    print(f"\n{'='*70}")
    print(f"{name}")
    print(f"{'='*70}")
    
    capital = ALLOCATION
    coins = 0.0
    cost = 0.0
    layers = 0
    avg_entry = 0.0
    tp_hit = False
    
    for candle in candle_list:
        price = candle["close"]
        high = candle["high"]
        
        # Check TP with hourly high
        if coins > 0 and avg_entry > 0:
            tp = avg_entry * (1 + DCA_TP_PCT)
            if high >= tp:
                proceeds = coins * tp
                fee = proceeds * 0.0001  # maker fee
                pnl = proceeds - cost - fee
                print(f"\n  >> TP HIT @ {candle['ts'].strftime('%m-%d %H:%M')} | "
                      f"high=${high:.2f} >= TP=${tp:.2f}")
                print(f"  >> Sold {coins:.2f} coins @ ${tp:.2f}")
                print(f"  >> PnL: ${pnl:.2f} ({pnl/cost*100:.2f}%)")
                tp_hit = True
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
            
            if use_cap:
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
                pct_used = cost / ALLOCATION * 100
                print(f"  L{layers:2d}: ${order:>8.0f} @ ${price:>7.2f} | "
                      f"total_coins={coins:>7.2f} | avg=${avg_entry:>7.2f} | "
                      f"TP=${tp:>7.2f} | used={pct_used:.0f}%")
    
    if not tp_hit and coins > 0:
        tp = avg_entry * (1 + DCA_TP_PCT)
        last_price = candle_list[-1]["close"]
        unrealized = coins * (last_price - avg_entry)
        pct_to_tp = (tp - last_price) / last_price * 100
        print(f"\n  POSITION OPEN:")
        print(f"  {layers} layers | ${cost:.0f} invested ({cost/ALLOCATION*100:.0f}% of allocation)")
        print(f"  {coins:.2f} coins | avg entry: ${avg_entry:.2f}")
        print(f"  TP target: ${tp:.2f}")
        print(f"  Current price: ${last_price:.2f}")
        print(f"  Unrealized: ${unrealized:.0f} ({unrealized/cost*100:.1f}%)")
        print(f"  Distance to TP: {pct_to_tp:.1f}% recovery needed")
    
    return layers, cost, avg_entry, avg_entry * (1 + DCA_TP_PCT) if avg_entry > 0 else 0

print(f"TAO/USDT Martingale Comparison")
print(f"Allocation: ${ALLOCATION:.2f} | Entry: Apr 9 19:00 UTC")
print(f"Candles available: {len(candle_list)} (through {candle_list[-1]['ts'].strftime('%m-%d %H:%M')})")

l_cap, c_cap, avg_cap, tp_cap = simulate("SCENARIO A: With 30% cap (old paper bot)", True)
l_no, c_no, avg_no, tp_no = simulate("SCENARIO B: Proper Martingale (fixed)", False)

print(f"\n{'='*70}")
print(f"COMPARISON")
print(f"{'='*70}")
print(f"                    30% Cap     Martingale")
print(f"  Layers:           {l_cap:<12d}{l_no}")
print(f"  Invested:         ${c_cap:<11.0f}${c_no:.0f}")
print(f"  Avg Entry:        ${avg_cap:<11.2f}${avg_no:.2f}")
print(f"  TP Target:        ${tp_cap:<11.2f}${tp_no:.2f}")
print(f"  TP Difference:    ${tp_cap - tp_no:.2f} (Martingale TP is ${tp_cap - tp_no:.2f} lower)")

db.close()
