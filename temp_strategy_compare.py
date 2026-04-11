"""
Compare inverted Martingale (large L1, fast cycling) vs proper Martingale (balanced grid).
Question: Is the inverted approach actually a better strategy for capital velocity?
"""
import sqlite3
import datetime

db = sqlite3.connect(r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db")

# Get ALL 1h candles for a good sample - let's use top coins from the scanner
# for the last 30 days
symbols = ["TAO/USDT", "FET/USDT", "ZRO/USDT", "GRASS/USDT", "RENDER/USDT", 
           "JTO/USDT", "ZEC/USDT", "NEAR/USDT", "DOT/USDT", "HYPE/USDT"]

# 30 days back from Apr 10
start_ms = 1775865600000 - (30 * 86400 * 1000)
end_ms = 1775865600000

BO_PCT_INVERTED = 0.30
BO_MULT = 1.5
SO_DEV = 0.02
TP_PCT = 0.015
MAX_LAYERS = 12
ALLOC = 20000

# Pre-calculated grid
mult_sum = sum(BO_MULT ** min(i, 4) for i in range(MAX_LAYERS))
PRE_BASE = ALLOC / mult_sum

def sim_strategy(candles, name, order_func):
    """Simulate DCA strategy on hourly candles. Returns stats."""
    deals = []
    in_deal = False
    layers = 0
    total_cost = 0
    total_coins = 0
    avg_entry = 0
    tp_price = 0
    deal_start = 0
    max_layers_seen = 0
    capital_deployed = 0  # Track actual capital used
    
    for ts, o, h, l, c, *_ in candles:
        # Check TP
        if in_deal and total_coins > 0 and tp_price > 0 and h >= tp_price:
            proceeds = total_coins * tp_price
            fee = proceeds * 0.00035
            pnl = proceeds - fee - total_cost
            duration_h = max((ts - deal_start) / 3600000, 1)
            deals.append({
                "pnl": pnl,
                "invested": total_cost,
                "layers": layers,
                "duration_h": duration_h,
                "return_pct": pnl / total_cost * 100,
            })
            max_layers_seen = max(max_layers_seen, layers)
            in_deal = False
            layers = 0
            total_cost = 0
            total_coins = 0
            continue
        
        # Check buy
        should_buy = False
        if not in_deal:
            should_buy = True
        elif layers < MAX_LAYERS and avg_entry > 0:
            target_drop = SO_DEV * layers
            current_drop = (avg_entry - c) / avg_entry
            if current_drop >= target_drop:
                should_buy = True
        
        if should_buy:
            order = order_func(layers, ALLOC)
            if order is None or order < 5:
                continue
            
            new_coins = order / c
            total_cost += order
            total_coins += new_coins
            layers += 1
            avg_entry = total_cost / total_coins
            tp_price = avg_entry * (1 + TP_PCT)
            if not in_deal:
                deal_start = ts
                in_deal = True
    
    # Stats
    if not deals:
        return None
    
    total_pnl = sum(d["pnl"] for d in deals)
    total_invested_turnover = sum(d["invested"] for d in deals)
    avg_duration = sum(d["duration_h"] for d in deals) / len(deals)
    l1_deals = sum(1 for d in deals if d["layers"] == 1)
    deep_deals = sum(1 for d in deals if d["layers"] >= 3)
    avg_pnl = total_pnl / len(deals)
    
    # Layer distribution
    layer_dist = {}
    for d in deals:
        l = d["layers"]
        layer_dist[l] = layer_dist.get(l, 0) + 1
    
    return {
        "name": name,
        "deals": len(deals),
        "total_pnl": total_pnl,
        "avg_pnl": avg_pnl,
        "avg_duration_h": avg_duration,
        "l1_pct": l1_deals / len(deals) * 100,
        "deep_pct": deep_deals / len(deals) * 100,
        "capital_turnover": total_invested_turnover,
        "max_layers": max_layers_seen,
        "layer_dist": layer_dist,
        "still_open": in_deal,
        "open_layers": layers if in_deal else 0,
        "open_cost": total_cost if in_deal else 0,
    }

def inverted_order(layer, alloc):
    """Old 30% cap strategy - large L1, shrinking layers."""
    # Simulate depleting capital with 30% cap
    # This is approximate - we track a running capital
    if not hasattr(inverted_order, '_cap'):
        inverted_order._cap = alloc
    if layer == 0:
        inverted_order._cap = alloc
        order = alloc * BO_PCT_INVERTED
    else:
        order = inverted_order._cap * BO_PCT_INVERTED * (BO_MULT ** min(layer, 4))
        order = min(order, inverted_order._cap * 0.3)
    if order > inverted_order._cap or order < 5:
        return None
    inverted_order._cap -= order
    return order

def proper_order(layer, alloc):
    """Pre-calculated grid - balanced across all 12 layers."""
    base = alloc / mult_sum
    order = base * (BO_MULT ** min(layer, 4))
    return order

def live_bot_order(layer, alloc):
    """GAP-13 reset - how the live bot actually works."""
    if layer == 0:
        order = alloc * BO_PCT_INVERTED
    else:
        order = alloc * BO_PCT_INVERTED * (BO_MULT ** min(layer, 4))
    if order > alloc:
        return None
    return order

print("=" * 90)
print("STRATEGY COMPARISON: 30-Day Backtest Across 10 Coins")
print(f"Capital per coin: ${ALLOC:,} | TP: {TP_PCT:.1%} | Dev: {SO_DEV:.0%}/layer | Max: {MAX_LAYERS} layers")
print("=" * 90)

strategies = [
    ("Inverted Martingale (30% cap)", inverted_order),
    ("Pre-Calculated Grid", proper_order),
    ("Live Bot (GAP-13 reset)", live_bot_order),
]

totals = {name: {"deals": 0, "pnl": 0, "turnover": 0, "stuck": 0, "stuck_cost": 0,
                  "durations": [], "layer_counts": []} 
          for name, _ in strategies}

for symbol in symbols:
    rows = db.execute("""
        SELECT timestamp, open, high, low, close 
        FROM candles WHERE symbol=? AND timeframe='1h'
        AND timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp
    """, (symbol, start_ms, end_ms)).fetchall()
    
    if len(rows) < 48:
        continue
    
    print(f"\n--- {symbol} ({len(rows)} candles) ---")
    
    for name, func in strategies:
        # Reset state for inverted
        if hasattr(inverted_order, '_cap'):
            del inverted_order._cap
        
        result = sim_strategy(rows, name, func)
        if result is None:
            print(f"  {name:35s}: No completed deals")
            continue
        
        t = totals[name]
        t["deals"] += result["deals"]
        t["pnl"] += result["total_pnl"]
        t["turnover"] += result["capital_turnover"]
        t["durations"].append(result["avg_duration_h"])
        if result["still_open"]:
            t["stuck"] += 1
            t["stuck_cost"] += result["open_cost"]
        
        stuck = f" [STUCK L{result['open_layers']} ${result['open_cost']:,.0f}]" if result['still_open'] else ""
        print(f"  {name:35s}: {result['deals']:>3} deals | "
              f"PnL ${result['total_pnl']:>8,.2f} | "
              f"avg ${result['avg_pnl']:>6,.2f}/deal | "
              f"L1={result['l1_pct']:.0f}% | "
              f"avg {result['avg_duration_h']:.0f}h{stuck}")

print("\n" + "=" * 90)
print("TOTALS (all 10 coins, 30 days)")
print("=" * 90)

for name, t in totals.items():
    avg_dur = sum(t["durations"]) / len(t["durations"]) if t["durations"] else 0
    pnl_per_deal = t["pnl"] / t["deals"] if t["deals"] else 0
    print(f"\n  {name}:")
    print(f"    Completed deals:     {t['deals']:>5}")
    print(f"    Total realized PnL:  ${t['pnl']:>10,.2f}")
    print(f"    PnL per deal:        ${pnl_per_deal:>10,.2f}")
    print(f"    Capital turnover:    ${t['turnover']:>12,.2f}")
    print(f"    Avg deal duration:   {avg_dur:>6.1f} hours")
    print(f"    Stuck positions:     {t['stuck']} (${t['stuck_cost']:,.0f} locked)")
    if t["turnover"] > 0:
        roi = t["pnl"] / ALLOC * 100
        velocity = t["pnl"] / t["turnover"] * 10000  # bps per dollar deployed
        print(f"    ROI on ${ALLOC:,}:       {roi:>6.1f}%")

db.close()
