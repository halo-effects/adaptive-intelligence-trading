"""
Long-horizon strategy comparison.
$50K capital, 5 coins, 90/10 pool split.
Tests: 30d, 90d, 180d, 365d
"""
import sqlite3
from datetime import datetime, timezone

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
PER_COIN_ALLOC = (TOTAL_CAPITAL * ACTIVE_PCT) / NUM_COINS

mult_sum = sum(MULT ** min(i, 4) for i in range(MAX_LAYERS))

end_ms = 1775865600000  # Apr 10 2026


def load_candles(days):
    start_ms = end_ms - (days * 86400 * 1000)
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
    return all_candles


def run_sim(all_candles, order_func):
    active_pool = TOTAL_CAPITAL * ACTIVE_PCT
    reserve_pool = TOTAL_CAPITAL * RESERVE_PCT
    
    all_timestamps = sorted(set(ts for sym in all_candles for ts, *_ in all_candles[sym]))
    candle_idx = {}
    for sym, rows in all_candles.items():
        for row in rows:
            candle_idx[(sym, row[0])] = row
    
    coins = {}
    for sym in symbols:
        coins[sym] = {
            "in_deal": False, "layers": 0, "total_cost": 0.0,
            "total_coins": 0.0, "avg_entry": 0.0, "tp_price": 0.0,
            "deal_start": 0,
        }
    
    completed_deals = []
    denied_buys = 0
    max_stuck_capital = 0
    max_pool_drawdown = 0
    
    for ts in all_timestamps:
        # Track pool health
        current_stuck = sum(cs["total_cost"] for cs in coins.values() if cs["in_deal"])
        if current_stuck > max_stuck_capital:
            max_stuck_capital = current_stuck
        pool_used = (TOTAL_CAPITAL * ACTIVE_PCT) - active_pool
        if pool_used > max_pool_drawdown:
            max_pool_drawdown = pool_used
        
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
                    "pnl": pnl, "invested": cs["total_cost"],
                    "layers": cs["layers"], "duration_h": duration_h,
                })
                active_pool += cs["total_cost"] + pnl
                cs["in_deal"] = False
                cs["layers"] = 0
                cs["total_cost"] = 0.0
                cs["total_coins"] = 0.0
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
    
    total_pnl = sum(d["pnl"] for d in completed_deals)
    stuck_cost = sum(cs["total_cost"] for cs in coins.values() if cs["in_deal"])
    stuck_count = sum(1 for cs in coins.values() if cs["in_deal"])
    l1_deals = sum(1 for d in completed_deals if d["layers"] == 1)
    avg_dur = sum(d["duration_h"] for d in completed_deals) / len(completed_deals) if completed_deals else 0
    
    # Layer distribution
    layer_dist = {}
    for d in completed_deals:
        layer_dist[d["layers"]] = layer_dist.get(d["layers"], 0) + 1
    
    # Longest deal
    max_dur = max((d["duration_h"] for d in completed_deals), default=0)
    
    return {
        "deals": len(completed_deals), "total_pnl": total_pnl,
        "avg_pnl": total_pnl / len(completed_deals) if completed_deals else 0,
        "avg_duration": avg_dur, "max_duration": max_dur,
        "l1_pct": l1_deals / len(completed_deals) * 100 if completed_deals else 0,
        "stuck_count": stuck_count, "stuck_cost": stuck_cost,
        "denied_buys": denied_buys,
        "active_remaining": active_pool, "reserve_remaining": reserve_pool,
        "max_stuck": max_stuck_capital, "max_pool_dd": max_pool_drawdown,
        "layer_dist": layer_dist,
    }


def inverted_order(layer, alloc, cs):
    cap = max(0, alloc - cs["total_cost"])
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
    base = alloc / mult_sum
    return base * (MULT ** min(layer, 4))


def fixed_order(layer, alloc, cs):
    remaining = max(0, alloc - cs["total_cost"])
    if remaining < 5:
        return None
    if layer == 0:
        order = remaining * BO_PCT
    else:
        order = remaining * BO_PCT * (MULT ** min(layer, 4))
    order = min(order, remaining)
    return order


strategies = [
    ("Inverted (30% cap)", inverted_order),
    ("Pre-Calc Grid", proper_order),
    ("FIXED (new)", fixed_order),
]

windows = [30, 90, 180, 365]

print("=" * 95)
print("LONG-HORIZON STRATEGY COMPARISON")
print(f"$50K capital | 5 coins | 90/10 split | ${PER_COIN_ALLOC:,.0f}/coin")
print("=" * 95)

for days in windows:
    candles = load_candles(days)
    actual_coins = len(candles)
    
    print(f"\n{'='*95}")
    print(f"  {days}-DAY BACKTEST ({actual_coins} coins with data)")
    print(f"{'='*95}")
    print(f"  {'Strategy':22s} {'Deals':>6s} {'PnL':>11s} {'ROI':>7s} {'Ann.ROI':>8s} "
          f"{'$/Deal':>8s} {'L1%':>4s} {'AvgH':>5s} {'MaxH':>6s} "
          f"{'Deny':>5s} {'Stuck$':>8s} {'MaxStk':>8s}")
    print(f"  {'-'*22} {'-'*6} {'-'*11} {'-'*7} {'-'*8} "
          f"{'-'*8} {'-'*4} {'-'*5} {'-'*6} "
          f"{'-'*5} {'-'*8} {'-'*8}")
    
    for name, func in strategies:
        r = run_sim(candles, func)
        roi = r["total_pnl"] / TOTAL_CAPITAL * 100
        # Annualized: (1 + roi/100) ^ (365/days) - 1
        ann_roi = ((1 + roi/100) ** (365/days) - 1) * 100 if days > 0 else 0
        
        dist_str = " ".join(f"L{l}:{c}" for l, c in sorted(r["layer_dist"].items()))
        
        print(f"  {name:22s} {r['deals']:>6} ${r['total_pnl']:>10,.0f} "
              f"{roi:>6.1f}% {ann_roi:>7.0f}% "
              f"${r['avg_pnl']:>7,.0f} {r['l1_pct']:>3.0f}% "
              f"{r['avg_duration']:>4.0f}h {r['max_duration']:>5.0f}h "
              f"{r['denied_buys']:>5} ${r['stuck_cost']:>7,.0f} ${r['max_stuck']:>7,.0f}")
        print(f"  {'':22s} Layers: {dist_str}")

db.close()
