"""
Reconstruct how the LIVE bot would have handled the TAO crash.
Live bot: polls every 65s, processes CLOSED hourly candles only.
One _long_dca_tick per candle = at most ONE layer per candle.
"""
import sqlite3, datetime

db = sqlite3.connect(r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db")

# Get TAO 1h candles around the crash
# From chart: TAO peaked ~$350 then crashed to ~$250
# Let's get Apr 8-11
candles = db.execute("""
    SELECT timestamp, open, high, low, close 
    FROM candles WHERE symbol='TAO/USDT' AND timeframe='1h'
    AND timestamp >= 1775606400000  
    ORDER BY timestamp
""").fetchall()

print("=" * 80)
print("TAO 1H CANDLES (Apr 8-11 UTC)")
print("=" * 80)
print(f"{'Time UTC':>16} {'Open':>8} {'High':>8} {'Low':>8} {'Close':>8} {'Range%':>7}")
print("-" * 80)

candle_data = []
for ts, o, h, l, c in candles:
    dt = datetime.datetime.fromtimestamp(ts/1000, tz=datetime.timezone.utc)
    range_pct = (h - l) / o * 100
    candle_data.append({"ts": dt, "ts_ms": ts, "open": o, "high": h, "low": l, "close": c})
    marker = ""
    if range_pct > 5:
        marker = " <<<< BIG MOVE"
    elif range_pct > 2:
        marker = " << notable"
    print(f"{dt.strftime('%m-%d %H:%M'):>16} {o:>8.2f} {h:>8.2f} {l:>8.2f} {c:>8.2f} {range_pct:>6.1f}%{marker}")

# Now simulate the live bot's DCA grid
print("\n" + "=" * 80)
print("LIVE BOT DCA SIMULATION")
print("=" * 80)
print("Mechanics:")
print("  - Polls exchange every 65s, fetches CLOSED hourly candles")
print("  - Runs _long_dca_tick(price=close, high=candle_high) per candle")  
print("  - ONE layer decision per candle (not real-time within candle)")
print("  - TP via exchange limit order (resting on book)")
print("  - Capital reset after each BUY (GAP-13 fix)")
print()

# DCA params (High profile, live)
DCA_BO_PCT = 0.30
DCA_SO_MULT = 1.5
DCA_SO_DEV = 0.02  # 2% deviation per layer (was 0.015 in scanner)
DCA_MAX_LAYERS = 12
DCA_TP_PCT = 0.015
TAKER_FEE = 0.00035  # Aster

# Assume TAO allocation from PM router
# With $340 capital, 3 coins, 90/10 split: active pool = $306, ~$102/coin
# With $20K capital, 5 coins, 75/25 split: active pool = $15K, ~$3K/coin
# Let's show both

for scenario_name, alloc in [("Live ($340 cap, 3 coins)", 102), 
                               ("Production ($20K cap, 5 coins)", 3000),
                               ("Paper ($50K cap, 10 coins, ~$20K alloc)", 20000)]:
    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario_name} — allocation=${alloc}")
    print(f"{'='*80}")
    
    capital = alloc  # Engine sees full alloc each time (GAP-13 reset)
    coins = 0.0
    cost = 0.0
    layers = 0
    avg_entry = 0.0
    tp_price = 0.0
    in_deal = False
    tp_hit = False
    
    # Find the candle where TAO was first bought (assume deal opens when
    # price starts dropping from peak — let's start from where close < prev close
    # after the peak). Actually, let's just start from the first candle and 
    # let the DCA logic decide.
    
    # The PM bot would have entered TAO when scanner selected it.
    # For this sim, assume entry happens on first candle we see.
    # But more realistically, TAO was already in position before the crash.
    # Let's find the peak and simulate from the first buy near the top.
    
    # From the chart, TAO peaked around $350 on Apr 9.
    # Let's assume L1 entry was around $337 (the paper bot's actual L1)
    # and simulate from there.
    
    entry_candle_idx = None
    for i, c in enumerate(candle_data):
        if c["close"] <= 340 and c["close"] >= 330 and entry_candle_idx is None:
            entry_candle_idx = i
            break
    
    if entry_candle_idx is None:
        # Fallback: find first candle with close near $337
        for i, c in enumerate(candle_data):
            if abs(c["close"] - 337) < 10:
                entry_candle_idx = i
                break
    
    if entry_candle_idx is None:
        entry_candle_idx = 0
    
    print(f"Starting from candle: {candle_data[entry_candle_idx]['ts'].strftime('%m-%d %H:%M')} "
          f"(close=${candle_data[entry_candle_idx]['close']:.2f})")
    print()
    
    for candle in candle_data[entry_candle_idx:]:
        price = candle["close"]
        high = candle["high"]
        
        # Check TP (via hourly high — simulating exchange limit order fill)
        if in_deal and coins > 0 and tp_price > 0 and high >= tp_price:
            proceeds = coins * tp_price
            fee = proceeds * TAKER_FEE
            pnl = proceeds - fee - cost
            print(f"  {'TP HIT':>8} @ {candle['ts'].strftime('%m-%d %H:%M')} | "
                  f"high=${high:.2f} >= TP=${tp_price:.2f} | "
                  f"PnL=${pnl:.2f} ({pnl/cost*100:.2f}%)")
            tp_hit = True
            break
        
        # DCA layer check — one per candle
        should_buy = False
        if not in_deal:
            should_buy = True
        elif layers < DCA_MAX_LAYERS and avg_entry > 0:
            target_drop = DCA_SO_DEV * layers
            current_drop = (avg_entry - price) / avg_entry
            if current_drop >= target_drop:
                should_buy = True
        
        if should_buy:
            # Calculate order size (live: capital resets to alloc after each buy)
            if layers == 0:
                order = alloc * DCA_BO_PCT
            else:
                order = alloc * DCA_BO_PCT * (DCA_SO_MULT ** min(layers, 4))
            
            order = min(order, alloc)  # Can't exceed allocation
            
            if order >= 5:  # $5 minimum
                new_coins = order / price
                fee = order * TAKER_FEE
                coins += new_coins
                cost += order
                layers += 1
                avg_entry = cost / coins
                tp_price = avg_entry * (1 + DCA_TP_PCT)
                in_deal = True
                
                # Grid depth: how far below L1 entry?
                if layers == 1:
                    l1_price = price
                    depth_pct = 0.0
                else:
                    depth_pct = (l1_price - price) / l1_price * 100
                
                # What's the next SO trigger?
                next_so_target = avg_entry * (1 - DCA_SO_DEV * layers) if layers < DCA_MAX_LAYERS else 0
                
                print(f"  L{layers:>2} BUY @ {candle['ts'].strftime('%m-%d %H:%M')} | "
                      f"${order:>9.2f} @ ${price:>7.2f} | "
                      f"avg=${avg_entry:>7.2f} | TP=${tp_price:>7.2f} | "
                      f"depth={depth_pct:>5.1f}% | next_SO=${next_so_target:>7.2f}")
    
    if not tp_hit and in_deal:
        last_price = candle_data[-1]["close"]
        unrealized = coins * (last_price - avg_entry)
        pct_to_tp = (tp_price - last_price) / last_price * 100
        total_grid_depth = (l1_price - candle_data[-1]["close"]) / l1_price * 100 if layers > 1 else 0
        print(f"\n  POSITION STILL OPEN:")
        print(f"  {layers} layers | ${cost:.0f} invested of ${alloc} allocation ({cost/alloc*100:.0f}%)")
        print(f"  {coins:.4f} coins @ avg ${avg_entry:.2f}")
        print(f"  TP target: ${tp_price:.2f}")
        print(f"  Current: ${last_price:.2f} | Unrealized: ${unrealized:.0f} ({unrealized/cost*100:.1f}%)")
        print(f"  Recovery needed: {pct_to_tp:.1f}%")
        print(f"  Grid depth from L1: {total_grid_depth:.1f}%")

db.close()
