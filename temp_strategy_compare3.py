"""
Strategy comparison with fixed capital accounting.
$50K capital, 5 coins, 90/10 pool split.
4 strategies: old inverted, pre-calc, old GAP-13, FIXED (new behavior).
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

symbols = ["TAO/USDT", "FET/USDT", "JTO/USDT", "GRASS/USDT", "ZEC/USDT"]
PER_COIN_ALLOC = (TOTAL_CAPITAL * ACTIVE_PCT) / NUM_COINS  # $9,000

mult_sum = sum(MULT ** min(i, 4) for i in range(MAX_LAYERS))

start_ms = 1775865600000 - (30 * 86400 * 1000)
end_ms = 1775865600000

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

all_timestamps = sorted(set(ts for sym in all_candles for ts, *_ in all_candles[sym]))
candle_idx = {}
for sym, rows in all_candles.items():
    for row in rows:
        candle_idx[(sym, row[0])] = row


def run_sim(strategy_name, order_func):
    active_pool = TOTAL_CAPITAL * ACTIVE_PCT
    reserve_pool = TOTAL_CAPITAL * RESERVE_PCT
    
    coins = {}
    for sym in symbols:
        coins[sym] = {
            "in_deal": False, "layers": 0, "total_cost": 0.0,
            "total_coins": 0.0, "avg_entry": 0.0, "tp_price": 0.0,
            "deal_start": 0, "engine_cap": PER_COIN_ALLOC,
        }
    
    completed_deals = []
    denied_buys = 0
    
    for ts in all_timestamps:
        for sym in symbols:
            if (sym, ts) not in candle_idx:
                continue
            row = candle_idx[(sym, ts)]
            _, o, h, l, c = row
            cs = coins[sym]
            
            if cs["in_deal"] and cs["total_coins"] > 0 and cs["tp_price"] > 0 and h >= cs["tp_price"]:
                proceeds = cs["total_coins"] * cs["tp_price"]
                fee = proceeds * FEE
                pnl = proceeds - fee - cs["total_cost"]
                duration_h = max((ts - cs["deal_start"]) / 3600000, 1)
                completed_deals.append({
                    "symbol": sym, "pnl": pnl, "invested": cs["total_cost"],
                    "layers": cs["layers"], "duration_h": duration_h,
                })
                active_pool += cs["total_cost"] + pnl
                cs["in_deal"] = False
                cs["layers"] = 0
                cs["total_cost"] = 0.0
                cs["total_coins"] = 0.0
                cs["engine_cap"] = PER_COIN_ALLOC
                continue
            
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
                
                pool_name = "reserve" if layer >= 5 else "active"
                pool_cash = reserve_pool if pool_name == "reserve" else active_pool
                
                if order > pool_cash:
                    if pool_cash >= 5:
                        order = pool_cash
                    else:
                        denied_buys += 1
                        continue
                
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
                
                # Update engine cap (tracks remaining for depleting strategies)
                cs["engine_cap"] = PER_COIN_ALLOC - cs["total_cost"]
    
    total_pnl = sum(d["pnl"] for d in completed_deals)
    stuck_cost = sum(cs["total_cost"] for cs in coins.values() if cs["in_deal"])
    stuck_count = sum(1 for cs in coins.values() if cs["in_deal"])
    stuck_details = {sym: (cs["layers"], cs["total_cost"]) 
                     for sym, cs in coins.items() if cs["in_deal"]}
    l1_deals = sum(1 for d in completed_deals if d["layers"] == 1)
    avg_dur = sum(d["duration_h"] for d in completed_deals) / len(completed_deals) if completed_deals else 0
    turnover = sum(d["invested"] for d in completed_deals)
    
    layer_dist = {}
    for d in completed_deals:
        layer_dist[d["layers"]] = layer_dist.get(d["layers"], 0) + 1
    
    return {
        "name": strategy_name, "deals": len(completed_deals),
        "total_pnl": total_pnl,
        "avg_pnl": total_pnl / len(completed_deals) if completed_deals else 0,
        "avg_duration": avg_dur,
        "l1_pct": l1_deals / len(completed_deals) * 100 if completed_deals else 0,
        "stuck_count": stuck_count, "stuck_cost": stuck_cost,
        "stuck_details": stuck_details,
        "denied_buys": denied_buys,
        "active_remaining": active_pool, "reserve_remaining": reserve_pool,
        "turnover": turnover, "layer_dist": layer_dist,
    }


def inverted_order(layer, alloc, cs):
    """Old 30% cap."""
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
    """Pre-calculated grid."""
    base = alloc / mult_sum
    return base * (MULT ** min(layer, 4))


def old_gap13_order(layer, alloc, cs):
    """Old GAP-13: reset to full alloc (broken)."""
    if layer == 0:
        order = alloc * BO_PCT
    else:
        order = alloc * BO_PCT * (MULT ** min(layer, 4))
    if order > alloc:
        order = alloc
    return order


def fixed_order(layer, alloc, cs):
    """FIXED: capital = alloc - invested. Martingale on remaining."""
    remaining = max(0, alloc - cs["total_cost"])
    if remaining < 5:
        return None
    if layer == 0:
        order = remaining * BO_PCT
    else:
        order = remaining * BO_PCT * (MULT ** min(layer, 4))
    order = min(order, remaining)  # Can't exceed what's left
    return order


print("=" * 80)
print("PORTFOLIO SIMULATION: $50K, 5 Coins, 30 Days")
print(f"Active: ${TOTAL_CAPITAL * ACTIVE_PCT:,.0f} | Reserve: ${TOTAL_CAPITAL * RESERVE_PCT:,.0f} | "
      f"Per-coin: ${PER_COIN_ALLOC:,.0f}")
print(f"Coins: {', '.join(s.split('/')[0] for s in symbols)}")
print("=" * 80)

strategies = [
    ("Old Inverted (30% cap)", inverted_order),
    ("Pre-Calculated Grid", proper_order),
    ("Old GAP-13 (broken)", old_gap13_order),
    ("FIXED (alloc - invested)", fixed_order),
]

for name, func in strategies:
    r = run_sim(name, func)
    
    print(f"\n  {r['name']:35s} | {r['deals']:>3} deals | "
          f"PnL ${r['total_pnl']:>9,.2f} | "
          f"${r['avg_pnl']:>6,.2f}/deal | "
          f"L1={r['l1_pct']:.0f}% | "
          f"denied={r['denied_buys']:>3} | "
          f"stuck={r['stuck_count']}x ${r['stuck_cost']:>7,.0f} | "
          f"pool=${r['active_remaining']:>8,.0f}")
    
    if r['layer_dist']:
        dist_str = " ".join(f"L{l}:{c}" for l, c in sorted(r['layer_dist'].items()))
        print(f"  {'':35s}   Layers: {dist_str}")
    if r['stuck_details']:
        stuck_str = " ".join(f"{s.split('/')[0]}:L{l}/${c:,.0f}" 
                           for s, (l, c) in sorted(r['stuck_details'].items()))
        print(f"  {'':35s}   Stuck: {stuck_str}")

print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}")
print(f"  {'Strategy':35s} {'ROI':>7s} {'PnL':>10s} {'Deals':>6s} {'$/Deal':>8s} {'Denied':>7s} {'Stuck$':>8s}")
print(f"  {'-'*35} {'-'*7} {'-'*10} {'-'*6} {'-'*8} {'-'*7} {'-'*8}")

for name, func in strategies:
    r = run_sim(name, func)
    roi = r['total_pnl'] / TOTAL_CAPITAL * 100
    print(f"  {r['name']:35s} {roi:>6.1f}% ${r['total_pnl']:>9,.0f} {r['deals']:>6} "
          f"${r['avg_pnl']:>7,.0f} {r['denied_buys']:>7} ${r['stuck_cost']:>7,.0f}")

db.close()
