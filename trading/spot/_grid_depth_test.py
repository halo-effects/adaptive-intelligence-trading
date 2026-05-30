"""
Grid depth optimization + trapped capital analysis.

Tests: deviation %, max layers, and volume multiplier combinations.
Measures: PnL, trapped capital %, max time in position, avg layers used.
"""
import sqlite3, statistics
from datetime import datetime, timedelta
from collections import defaultdict

DB = "trading/spot/data/candles.db"
conn = sqlite3.connect(DB)
cutoff_ms = int((datetime.now() - timedelta(days=90)).timestamp() * 1000)

COINS = ["GRASS/USDT", "TAO/USDT", "FET/USDT", "ZEC/USDT", "HYPE/USDT",
         "PENDLE/USDT", "JTO/USDT", "INJ/USDT", "TON/USDT", "ONDO/USDT"]

CAPITAL = 5000
TAKER_FEE = 0.00025
MAKER_FEE = 0.0002
TP_PCT = 2.5  # Use the optimal TP from prior analysis

def run_grid_sim(candles, dev_pct, max_layers, vol_mult, bo_pct=0.40):
    """Full DCA grid sim. Returns detailed stats."""
    deals = []
    cash = CAPITAL
    layers = 0
    total_coins = 0
    total_cost = 0
    avg_entry = 0
    tp_price = 0
    entry_candle = 0
    max_layers_used = 0
    trapped_candles = 0  # candles where position is open
    total_candles = len(candles)
    max_drawdown_pct = 0
    peak_cost = 0
    
    # Pre-calculate layer sizes
    layer_sizes = []
    base = CAPITAL * bo_pct * 0.9
    for i in range(max_layers):
        if i == 0:
            layer_sizes.append(base)
        else:
            layer_sizes.append(layer_sizes[-1] * vol_mult)
    
    for idx, (ts, o, h, l, c) in enumerate(candles):
        if layers > 0:
            trapped_candles += 1
            # Track drawdown
            current_value = total_coins * c
            dd = (current_value - total_cost) / total_cost * 100 if total_cost > 0 else 0
            if dd < max_drawdown_pct:
                max_drawdown_pct = dd
        
        if layers > 0 and tp_price > 0 and h >= tp_price:
            proceeds = total_coins * tp_price
            fee = proceeds * MAKER_FEE
            pnl = proceeds - total_cost - fee
            ret_pct = pnl / total_cost * 100
            duration = idx - entry_candle
            deals.append({
                "pnl": pnl, "return_pct": ret_pct, "layers": layers,
                "invested": total_cost, "duration_h": duration
            })
            max_layers_used = max(max_layers_used, layers)
            cash = CAPITAL
            layers = 0
            total_coins = 0
            total_cost = 0
            avg_entry = 0
            tp_price = 0
            continue
        
        if layers == 0:
            size = min(layer_sizes[0], cash)
            if size < 1:
                continue
            coins = size / c
            fee = size * TAKER_FEE
            total_coins = coins
            total_cost = size + fee
            avg_entry = c
            tp_price = avg_entry * (1 + TP_PCT / 100)
            layers = 1
            cash -= size
            entry_candle = idx
        elif layers < max_layers:
            so_trigger = avg_entry * (1 - dev_pct * layers)
            if l <= so_trigger:
                size = min(layer_sizes[layers], cash)
                if size < 1:
                    continue
                fill_price = so_trigger
                coins = size / fill_price
                fee = size * TAKER_FEE
                total_cost += size + fee
                total_coins += coins
                avg_entry = total_cost / total_coins
                tp_price = avg_entry * (1 + TP_PCT / 100)
                layers += 1
                cash -= size
    
    if not deals:
        return None
    
    # Calculate trapped capital metrics
    capital_trapped_pct = trapped_candles / total_candles * 100
    avg_duration = statistics.mean([d["duration_h"] for d in deals])
    max_duration = max(d["duration_h"] for d in deals)
    avg_layers = statistics.mean([d["layers"] for d in deals])
    total_pnl = sum(d["pnl"] for d in deals)
    
    # Still trapped at end?
    still_open = layers > 0
    open_cost = total_cost if still_open else 0
    
    return {
        "deals": len(deals), "total_pnl": total_pnl,
        "avg_ret": statistics.mean([d["return_pct"] for d in deals]),
        "avg_duration": avg_duration, "max_duration": max_duration,
        "avg_layers": avg_layers, "max_layers_used": max_layers_used,
        "capital_trapped_pct": capital_trapped_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "still_open": still_open, "open_cost": open_cost
    }


# Load all candles
all_candles = {}
for sym in COINS:
    rows = conn.execute(
        "SELECT timestamp, open, high, low, close FROM candles "
        "WHERE symbol=? AND timeframe='1h' AND timestamp>=? ORDER BY timestamp",
        (sym, cutoff_ms)
    ).fetchall()
    if rows and len(rows) >= 200:
        all_candles[sym] = rows

print("=" * 85)
print(f"  GRID DEPTH OPTIMIZATION (TP={TP_PCT}%, 90 days, {len(all_candles)} coins)")
print("=" * 85)

# Test grid configurations
configs = [
    # (dev%, layers, vol_mult, label)
    (0.015, 12, 1.5, "CURRENT: 1.5% dev, 12L, 1.5x mult"),
    (0.015,  8, 1.5, "Shallow: 1.5% dev,  8L, 1.5x mult"),
    (0.015,  6, 1.5, "Minimal: 1.5% dev,  6L, 1.5x mult"),
    (0.020, 12, 1.5, "Wide:    2.0% dev, 12L, 1.5x mult"),
    (0.020,  8, 1.5, "Wide-sh: 2.0% dev,  8L, 1.5x mult"),
    (0.025, 10, 1.5, "Wider:   2.5% dev, 10L, 1.5x mult"),
    (0.015, 12, 2.0, "Aggr:    1.5% dev, 12L, 2.0x mult"),
    (0.020, 10, 2.0, "Aggr-w:  2.0% dev, 10L, 2.0x mult"),
]

print(f"\n  {'Config':<40} | {'Deals':>5} | {'PnL':>8} | {'AvgRet':>7} | {'AvgDur':>7} | {'AvgLyr':>6} | {'Trap%':>6} | {'MaxDD':>7} | {'Open':>4}")

for dev, layers, mult, label in configs:
    agg_deals = 0
    agg_pnl = 0
    agg_rets = []
    agg_durs = []
    agg_lyrs = []
    agg_trap = []
    agg_dd = []
    agg_open = 0
    
    for sym, candles in all_candles.items():
        r = run_grid_sim(candles, dev, layers, mult)
        if r:
            agg_deals += r["deals"]
            agg_pnl += r["total_pnl"]
            agg_rets.append(r["avg_ret"])
            agg_durs.append(r["avg_duration"])
            agg_lyrs.append(r["avg_layers"])
            agg_trap.append(r["capital_trapped_pct"])
            agg_dd.append(r["max_drawdown_pct"])
            if r["still_open"]:
                agg_open += 1
    
    avg_ret = statistics.mean(agg_rets) if agg_rets else 0
    avg_dur = statistics.mean(agg_durs) if agg_durs else 0
    avg_lyr = statistics.mean(agg_lyrs) if agg_lyrs else 0
    avg_trap = statistics.mean(agg_trap) if agg_trap else 0
    worst_dd = min(agg_dd) if agg_dd else 0
    
    print(f"  {label:<40} | {agg_deals:>5} | ${agg_pnl:>6.0f} | {avg_ret:>6.2f}% | {avg_dur:>6.1f}h | {avg_lyr:>5.1f} | {avg_trap:>5.1f}% | {worst_dd:>6.1f}% | {agg_open:>4}")

# Per-coin breakdown for current vs best
print(f"\n{'='*85}")
print(f"  PER-COIN: CURRENT (1.5% dev, 12L) vs WIDE (2.0% dev, 8L)")
print(f"{'='*85}")
print(f"  {'Coin':<15} | {'Curr PnL':>9} | {'Wide PnL':>9} | {'Delta':>7} | {'Curr Trap':>9} | {'Wide Trap':>9} | {'Curr DD':>8} | {'Wide DD':>8}")

for sym, candles in all_candles.items():
    curr = run_grid_sim(candles, 0.015, 12, 1.5)
    wide = run_grid_sim(candles, 0.020, 8, 1.5)
    if curr and wide:
        delta = wide["total_pnl"] - curr["total_pnl"]
        print(f"  {sym:<15} | ${curr['total_pnl']:>8.0f} | ${wide['total_pnl']:>8.0f} | ${delta:>+6.0f} | {curr['capital_trapped_pct']:>8.1f}% | {wide['capital_trapped_pct']:>8.1f}% | {curr['max_drawdown_pct']:>7.1f}% | {wide['max_drawdown_pct']:>7.1f}%")

conn.close()
