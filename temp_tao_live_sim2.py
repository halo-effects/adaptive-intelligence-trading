"""
Reconstruct live bot TAO behavior with deal cycling.
Shows all deals through the crash.
"""
import sqlite3, datetime

db = sqlite3.connect(r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db")

candles = db.execute("""
    SELECT timestamp, open, high, low, close 
    FROM candles WHERE symbol='TAO/USDT' AND timeframe='1h'
    AND timestamp >= 1775606400000  
    ORDER BY timestamp
""").fetchall()

candle_data = []
for ts, o, h, l, c in candles:
    dt = datetime.datetime.fromtimestamp(ts/1000, tz=datetime.timezone.utc)
    candle_data.append({"ts": dt, "ts_ms": ts, "open": o, "high": h, "low": l, "close": c})

DCA_BO_PCT = 0.30
DCA_SO_MULT = 1.5
DCA_SO_DEV = 0.02  # 2% per layer
DCA_MAX_LAYERS = 12
DCA_TP_PCT = 0.015

def sim(name, alloc):
    print(f"\n{'='*90}")
    print(f"SCENARIO: {name} — allocation=${alloc}")
    print(f"Grid depth: 2% × layer (L2=2%, L3=4%, L4=6%... L12=22%)")
    print(f"{'='*90}")
    
    deal_num = 0
    coins = 0.0
    cost = 0.0
    layers = 0
    avg_entry = 0.0
    tp_price = 0.0
    in_deal = False
    l1_price = 0.0
    total_pnl = 0.0
    
    for candle in candle_data:
        price = candle["close"]
        high = candle["high"]
        
        # Check TP via hourly high (exchange limit order would fill)
        if in_deal and coins > 0 and tp_price > 0 and high >= tp_price:
            proceeds = coins * tp_price
            fee = proceeds * 0.00035
            pnl = proceeds - fee - cost
            total_pnl += pnl
            deal_num_str = f"Deal {deal_num}"
            print(f"  {'>> TP':>8} @ {candle['ts'].strftime('%m-%d %H:%M')} | "
                  f"high=${high:.2f} >= TP=${tp_price:.2f} | "
                  f"PnL=${pnl:>7.2f} | L{layers} deal, total PnL=${total_pnl:.2f}")
            in_deal = False
            coins = 0.0
            cost = 0.0
            layers = 0
            avg_entry = 0.0
            tp_price = 0.0
            # Don't enter new deal this candle — next candle
            continue
        
        # DCA layer check
        should_buy = False
        if not in_deal:
            should_buy = True  # Start new deal
        elif layers < DCA_MAX_LAYERS and avg_entry > 0:
            target_drop = DCA_SO_DEV * layers
            current_drop = (avg_entry - price) / avg_entry
            if current_drop >= target_drop:
                should_buy = True
        
        if should_buy:
            # Live bot: capital resets to alloc after each buy (GAP-13)
            if layers == 0:
                order = alloc * DCA_BO_PCT
            else:
                order = alloc * DCA_BO_PCT * (DCA_SO_MULT ** min(layers, 4))
            
            order = min(order, alloc)
            
            if order >= 5:
                if not in_deal:
                    deal_num += 1
                    in_deal = True
                    
                new_coins = order / price
                coins += new_coins
                cost += order
                layers += 1
                avg_entry = cost / coins
                tp_price = avg_entry * (1 + DCA_TP_PCT)
                
                if layers == 1:
                    l1_price = price
                    depth_pct = 0.0
                else:
                    depth_pct = (l1_price - price) / l1_price * 100
                
                next_so = avg_entry * (1 - DCA_SO_DEV * layers) if layers < DCA_MAX_LAYERS else 0
                
                marker = ""
                if layers >= 3:
                    marker = " << DEEP"
                if layers >= 6:
                    marker = " << VERY DEEP"
                    
                print(f"  L{layers:>2} BUY @ {candle['ts'].strftime('%m-%d %H:%M')} | "
                      f"${order:>9.2f} @ ${price:>7.2f} | "
                      f"avg=${avg_entry:>7.2f} TP=${tp_price:>7.2f} | "
                      f"depth={depth_pct:>5.1f}% next_SO=${next_so:>7.2f}{marker}")
    
    if in_deal:
        last_price = candle_data[-1]["close"]
        unrealized = coins * (last_price - avg_entry)
        pct_to_tp = (tp_price - last_price) / last_price * 100
        grid_depth = (l1_price - last_price) / l1_price * 100
        print(f"\n  ┌─ OPEN POSITION (Deal {deal_num}) ─────────────────────────")
        print(f"  │ {layers} layers | ${cost:.0f} invested of ${alloc} ({cost/alloc*100:.0f}%)")
        print(f"  │ {coins:.4f} coins @ avg ${avg_entry:.2f}")
        print(f"  │ TP target: ${tp_price:.2f}")
        print(f"  │ Current: ${last_price:.2f} | Unrealized: ${unrealized:.0f} ({unrealized/cost*100:.1f}%)")
        print(f"  │ Recovery needed: {pct_to_tp:.1f}%")
        print(f"  │ Grid depth from L1: {grid_depth:.1f}%")
        print(f"  │ Total realized PnL from prior deals: ${total_pnl:.2f}")
        print(f"  └──────────────────────────────────────────────────")
    else:
        print(f"\n  All deals closed. Total PnL: ${total_pnl:.2f} across {deal_num} deals")

print("KEY MECHANIC: Live bot processes ONE closed hourly candle per tick.")
print("It does NOT see real-time price within a candle.")
print("DCA decision uses candle CLOSE price. TP checks candle HIGH.")
print("At most ONE new layer per candle.")

sim("Current Live ($340, 3 coins)", 102)
sim("Production Clone ($20K, 5 coins)", 3000)
sim("Paper ($50K, ~$20K/coin alloc)", 20000)

db.close()
