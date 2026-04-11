"""
Strategy comparison with REAL shared pool constraints.
$50K capital, 5 coins, 90/10 pool split.
"""
import sqlite3

db = sqlite3.connect(r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db")

TOTAL_CAPITAL = 50000
ACTIVE_PCT = 0.90
RESERVE_PCT = 0.10
NUM_COINS = 5
BO_PCT = 0.30
MULT = 1.5
SO_DEV = 0.02
TP_PCT = 0.015
MAX_LAYERS = 12
FEE = 0.00035

# Use the top 5 coins from the scanner (same as paper bot at crash time)
symbols = ["TAO/USDT", "FET/USDT", "JTO/USDT", "GRASS/USDT", "ZEC/USDT"]

# Per-coin allocation (equal split for simplicity)
PER_COIN_ALLOC = (TOTAL_CAPITAL * ACTIVE_PCT) / NUM_COINS  # $9,000

# Pre-calculated grid
mult_sum = sum(MULT ** min(i, 4) for i in range(MAX_LAYERS))

# 30 days of candles
start_ms = 1775865600000 - (30 * 86400 * 1000)
end_ms = 1775865600000

# Load all candles
all_candles = {}
for sym in symbols:
    rows = db.execute("""
        SELECT timestamp, open, high, low, close 
        FROM candles WHERE symbol=? AND timeframe='1h'
        AND timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp
    """, (sym, start_ms, end_ms)).fetchall()
    if rows:
        all_candles[sym] = rows

# Build unified timeline
all_timestamps = sorted(set(ts for sym in all_candles for ts, *_ in all_candles[sym]))

# Index candles by (symbol, timestamp) for quick lookup
candle_idx = {}
for sym, rows in all_candles.items():
    for row in rows:
        candle_idx[(sym, row[0])] = row


def run_sim(strategy_name, order_func):
    """Run full portfolio simulation with shared pool."""
    active_pool = TOTAL_CAPITAL * ACTIVE_PCT    # $45,000
    reserve_pool = TOTAL_CAPITAL * RESERVE_PCT  # $5,000
    
    # Per-coin state
    coins = {}
    for sym in symbols:
        coins[sym] = {
            "in_deal": False,
            "layers": 0,
            "total_cost": 0.0,
            "total_coins": 0.0,
            "avg_entry": 0.0,
            "tp_price": 0.0,
            "deal_start": 0,
            "engine_cap": PER_COIN_ALLOC,  # For depleting strategies
        }
    
    completed_deals = []
    denied_buys = 0
    partial_denials = 0
    
    for ts in all_timestamps:
        for sym in symbols:
            if (sym, ts) not in candle_idx:
                continue
            
            row = candle_idx[(sym, ts)]
            _, o, h, l, c = row
            cs = coins[sym]
            
            # Check TP
            if cs["in_deal"] and cs["total_coins"] > 0 and cs["tp_price"] > 0 and h >= cs["tp_price"]:
                proceeds = cs["total_coins"] * cs["tp_price"]
                fee = proceeds * FEE
                pnl = proceeds - fee - cs["total_cost"]
                duration_h = max((ts - cs["deal_start"]) / 3600000, 1)
                
                completed_deals.append({
                    "symbol": sym,
                    "pnl": pnl,
                    "invested": cs["total_cost"],
                    "layers": cs["layers"],
                    "duration_h": duration_h,
                })
                
                # Return capital to active pool
                active_pool += cs["total_cost"] + pnl
                
                # Reset
                cs["in_deal"] = False
                cs["layers"] = 0
                cs["total_cost"] = 0.0
                cs["total_coins"] = 0.0
                cs["avg_entry"] = 0.0
                cs["tp_price"] = 0.0
                cs["engine_cap"] = PER_COIN_ALLOC
                continue
            
            # Check buy
            should_buy = False
            if not cs["in_deal"]:
                should_buy = True
            elif cs["layers"] < MAX_LAYERS and cs["avg_entry"] > 0:
                target_drop = SO_DEV * cs["layers"]
                current_drop = (cs["avg_entry"] - c) / cs["avg_entry"]
                if current_drop >= target_drop:
                    should_buy = True
            
            if should_buy:
                layer = cs["layers"]
                order = order_func(layer, PER_COIN_ALLOC, cs)
                if order is None or order < 5:
                    continue
                
                # Route to correct pool
                pool_name = "reserve" if layer >= 5 else "active"
                pool_cash = reserve_pool if pool_name == "reserve" else active_pool
                
                # Check pool has enough
                if order > pool_cash:
                    if pool_cash >= 5:
                        # Partial - take what's available
                        order = pool_cash
                        partial_denials += 1
                    else:
                        denied_buys += 1
                        continue
                
                # Deduct from pool
                if pool_name == "reserve":
                    reserve_pool -= order
                else:
                    active_pool -= order
                
                new_coins = order / c
                cs["total_cost"] += order
                cs["total_coins"] += new_coins
                cs["layers"] += 1
                cs["avg_entry"] = cs["total_cost"] / cs["total_coins"]
                cs["tp_price"] = cs["avg_entry"] * (1 + TP_PCT)
                if not cs["in_deal"]:
                    cs["deal_start"] = ts
                    cs["in_deal"] = True
                
                # Update engine cap for depleting strategies
                cs["engine_cap"] -= order
    
    # Summary
    total_pnl = sum(d["pnl"] for d in completed_deals)
    total_turnover = sum(d["invested"] for d in completed_deals)
    avg_duration = sum(d["duration_h"] for d in completed_deals) / len(completed_deals) if completed_deals else 0
    
    stuck_cost = sum(cs["total_cost"] for cs in coins.values() if cs["in_deal"])
    stuck_count = sum(1 for cs in coins.values() if cs["in_deal"])
    stuck_layers = {sym: cs["layers"] for sym, cs in coins.items() if cs["in_deal"]}
    
    # Layer distribution
    layer_dist = {}
    for d in completed_deals:
        l = d["layers"]
        layer_dist[l] = layer_dist.get(l, 0) + 1
    
    l1_deals = sum(1 for d in completed_deals if d["layers"] == 1)
    
    return {
        "name": strategy_name,
        "deals": len(completed_deals),
        "total_pnl": total_pnl,
        "avg_pnl": total_pnl / len(completed_deals) if completed_deals else 0,
        "avg_duration": avg_duration,
        "l1_pct": l1_deals / len(completed_deals) * 100 if completed_deals else 0,
        "stuck_count": stuck_count,
        "stuck_cost": stuck_cost,
        "stuck_layers": stuck_layers,
        "denied_buys": denied_buys,
        "partial_denials": partial_denials,
        "active_pool_remaining": active_pool,
        "reserve_pool_remaining": reserve_pool,
        "turnover": total_turnover,
        "layer_dist": layer_dist,
    }


def inverted_order(layer, alloc, cs):
    """30% cap - large L1, shrinking layers."""
    cap = cs["engine_cap"]
    if cap < 5:
        return None
    if layer == 0:
        order = cap * BO_PCT
    else:
        order = cap * BO_PCT * (MULT ** min(layer, 4))
        order = min(order, cap * 0.3)
    if order > cap:
        return None
    return order


def proper_order(layer, alloc, cs):
    """Pre-calculated grid - balanced across 12 layers."""
    base = alloc / mult_sum
    order = base * (MULT ** min(layer, 4))
    return order


def live_order(layer, alloc, cs):
    """GAP-13 reset - live bot behavior, capped at allocation."""
    if layer == 0:
        order = alloc * BO_PCT
    else:
        order = alloc * BO_PCT * (MULT ** min(layer, 4))
    if order > alloc:
        order = alloc  # Cap at allocation instead of blocking
    return order


print("=" * 80)
print("PORTFOLIO SIMULATION: $50K, 5 Coins, 30 Days")
print(f"Active pool: ${TOTAL_CAPITAL * ACTIVE_PCT:,.0f} | "
      f"Reserve pool: ${TOTAL_CAPITAL * RESERVE_PCT:,.0f} | "
      f"Per-coin alloc: ${PER_COIN_ALLOC:,.0f}")
print(f"Coins: {', '.join(s.split('/')[0] for s in symbols)}")
print("=" * 80)

strategies = [
    ("Inverted Martingale (30% cap)", inverted_order),
    ("Pre-Calculated Grid", proper_order),
    ("Live Bot (GAP-13, capped)", live_order),
]

for name, func in strategies:
    r = run_sim(name, func)
    
    print(f"\n{'='*70}")
    print(f"  {r['name']}")
    print(f"{'='*70}")
    print(f"  Completed deals:      {r['deals']:>5}")
    print(f"  Total realized PnL:   ${r['total_pnl']:>10,.2f}")
    print(f"  PnL per deal:         ${r['avg_pnl']:>10,.2f}")
    print(f"  Avg deal duration:    {r['avg_duration']:>6.1f} hours")
    print(f"  L1 deal %:            {r['l1_pct']:>5.0f}%")
    print(f"  Capital turnover:     ${r['turnover']:>12,.2f}")
    print(f"  ROI on $50K:          {r['total_pnl']/TOTAL_CAPITAL*100:>6.1f}%")
    print(f"  Denied buys:          {r['denied_buys']:>5} (pool empty)")
    print(f"  Partial fills:        {r['partial_denials']:>5}")
    print(f"  Active pool left:     ${r['active_pool_remaining']:>10,.2f}")
    print(f"  Reserve pool left:    ${r['reserve_pool_remaining']:>10,.2f}")
    print(f"  Stuck positions:      {r['stuck_count']} coins (${r['stuck_cost']:,.0f} locked)")
    if r['stuck_layers']:
        for sym, layers in sorted(r['stuck_layers'].items()):
            print(f"    {sym}: L{layers}")
    
    # Layer distribution
    if r['layer_dist']:
        print(f"  Layer distribution:")
        for l in sorted(r['layer_dist'].keys()):
            count = r['layer_dist'][l]
            pct = count / r['deals'] * 100
            bar = '#' * int(pct / 2)
            print(f"    L{l:>2}: {count:>4} ({pct:>4.0f}%) {bar}")

db.close()
