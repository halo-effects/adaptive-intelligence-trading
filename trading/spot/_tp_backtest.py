"""
Full DCA grid backtest at different TP levels using actual 1h candle data.

Simulates the real V14 grid: layered entries on dips, TP on avg entry + X%.
Uses High profile: BO=40%, Dev=1.5%, Mult=1.5x, Max 12 layers.
Measures: total PnL, deals, avg return, capital efficiency.
"""
import sqlite3, statistics
from collections import defaultdict
from datetime import datetime, timedelta

DB = "trading/spot/data/candles.db"
conn = sqlite3.connect(DB)

# High profile params
BO_PCT = 0.40       # 40% base order
SO_DEV = 0.015      # 1.5% deviation between layers
SO_MULT = 1.5       # volume multiplier per layer
MAX_LAYERS = 12
CAPITAL = 5000      # per coin
TAKER_FEE = 0.00025 # Hyperliquid taker 0.025%
MAKER_FEE = 0.0002  # Hyperliquid maker 0.02%

# Top PM scanner coins
COINS = ["GRASS/USDT", "TAO/USDT", "FET/USDT", "ZEC/USDT", "JTO/USDT", 
         "HYPE/USDT", "PENDLE/USDT", "INJ/USDT", "TON/USDT", "ONDO/USDT"]

# Use last 90 days
cutoff_ms = int((datetime.now() - timedelta(days=90)).timestamp() * 1000)

def run_dca_sim(candles, tp_pct, capital):
    """Simulate DCA grid on 1h candles. Returns (deals, total_pnl, returns, avg_duration)."""
    deals = []
    cash = capital
    layers = 0
    total_coins = 0
    total_cost = 0
    avg_entry = 0
    tp_price = 0
    entry_candle = 0
    
    # Pre-calculate layer sizes
    layer_sizes = []
    base = capital * BO_PCT * 0.9  # 90% DCA allocation, BO%
    for i in range(MAX_LAYERS):
        if i == 0:
            layer_sizes.append(base)
        else:
            layer_sizes.append(layer_sizes[-1] * SO_MULT)
    
    for idx, (ts, o, h, l, c) in enumerate(candles):
        price = c  # use close for decisions
        
        if layers > 0 and tp_price > 0:
            # Check TP: use HIGH of candle (realistic — limit order fills when price touches)
            if h >= tp_price:
                # Fill at TP price (not candle close — realistic limit fill)
                proceeds = total_coins * tp_price
                fee = proceeds * MAKER_FEE
                pnl = proceeds - total_cost - fee
                ret_pct = pnl / total_cost * 100
                duration = idx - entry_candle
                deals.append({
                    "pnl": pnl, "return_pct": ret_pct, "layers": layers,
                    "invested": total_cost, "duration_h": duration
                })
                cash = capital  # reset (simplified: single position)
                layers = 0
                total_coins = 0
                total_cost = 0
                avg_entry = 0
                tp_price = 0
                continue
        
        # Check for new layer entry
        if layers == 0:
            # First layer: buy at current price
            size = min(layer_sizes[0], cash)
            if size < 1:
                continue
            coins = size / price
            fee = size * TAKER_FEE
            total_coins = coins
            total_cost = size + fee
            avg_entry = price
            tp_price = avg_entry * (1 + tp_pct / 100)
            layers = 1
            cash -= size
            entry_candle = idx
        elif layers < MAX_LAYERS:
            # Check if price dropped enough for next SO
            so_trigger = avg_entry * (1 - SO_DEV * layers)
            if l <= so_trigger:  # LOW touches SO trigger
                size = min(layer_sizes[layers], cash)
                if size < 1:
                    continue
                fill_price = so_trigger  # fill at trigger (realistic)
                coins = size / fill_price
                fee = size * TAKER_FEE
                total_cost += size + fee
                total_coins += coins
                avg_entry = total_cost / total_coins  # true avg including fees
                tp_price = avg_entry * (1 + tp_pct / 100)
                layers += 1
                cash -= size
    
    # Close any open position at end (mark to market)
    if layers > 0 and total_coins > 0:
        last_price = candles[-1][4]
        proceeds = total_coins * last_price
        pnl = proceeds - total_cost
        # Don't count as a deal — it's an open position
    
    if not deals:
        return 0, 0, [], 0
    
    total_pnl = sum(d["pnl"] for d in deals)
    returns = [d["return_pct"] for d in deals]
    durations = [d["duration_h"] for d in deals]
    avg_dur = statistics.mean(durations) if durations else 0
    
    return len(deals), total_pnl, returns, avg_dur


print("=" * 80)
print("  DCA GRID BACKTEST — TP TARGET COMPARISON (90 days, actual candles)")
print("  Profile: High (BO=40%, Dev=1.5%, Mult=1.5x, 12 layers)")
print("  TP fills at limit price (not candle close). Fees: HL taker/maker.")
print("=" * 80)

all_results = defaultdict(lambda: defaultdict(dict))

for sym in COINS:
    candles = conn.execute(
        "SELECT timestamp, open, high, low, close FROM candles "
        "WHERE symbol=? AND timeframe='1h' AND timestamp>=? ORDER BY timestamp",
        (sym, cutoff_ms)
    ).fetchall()
    
    if not candles or len(candles) < 200:
        continue
    
    days = len(candles) / 24
    print(f"\n  {sym} ({len(candles)} candles, {days:.0f} days)")
    print(f"    {'TP':>5} | {'Deals':>5} | {'Total PnL':>10} | {'Avg Ret':>8} | {'Med Ret':>8} | {'Avg Dur':>8} | {'Ann ROI':>8}")
    
    for tp in [1.0, 1.5, 2.0, 2.5, 3.0]:
        n_deals, total_pnl, returns, avg_dur = run_dca_sim(candles, tp, CAPITAL)
        if n_deals == 0:
            print(f"    {tp:>4.1f}% | {'--':>5} | {'--':>10} | {'--':>8} | {'--':>8} | {'--':>8} | {'--':>8}")
            continue
        
        avg_ret = statistics.mean(returns)
        med_ret = statistics.median(returns)
        # Annualized: compound the per-deal return over deals/year
        deals_per_year = n_deals / days * 365
        ann_roi = ((1 + avg_ret/100) ** deals_per_year - 1) * 100
        
        print(f"    {tp:>4.1f}% | {n_deals:>5} | ${total_pnl:>9.0f} | {avg_ret:>7.2f}% | {med_ret:>7.2f}% | {avg_dur:>7.1f}h | {ann_roi:>7.0f}%")
        
        all_results[sym][tp] = {
            "deals": n_deals, "pnl": total_pnl, "avg_ret": avg_ret, 
            "ann_roi": ann_roi, "avg_dur": avg_dur
        }

# Portfolio aggregate
print("\n" + "=" * 80)
print("  PORTFOLIO AGGREGATE (all scanner coins combined)")
print("=" * 80)
print(f"  {'TP':>5} | {'Total Deals':>11} | {'Total PnL':>10} | {'Avg Ret':>8} | {'Avg Dur':>8}")

for tp in [1.0, 1.5, 2.0, 2.5, 3.0]:
    total_deals = sum(all_results[s][tp].get("deals", 0) for s in all_results)
    total_pnl = sum(all_results[s][tp].get("pnl", 0) for s in all_results)
    all_rets = []
    all_durs = []
    for s in all_results:
        if tp in all_results[s]:
            r = all_results[s][tp]
            all_rets.append(r["avg_ret"])
            all_durs.append(r["avg_dur"])
    avg_ret = statistics.mean(all_rets) if all_rets else 0
    avg_dur = statistics.mean(all_durs) if all_durs else 0
    print(f"  {tp:>4.1f}% | {total_deals:>11} | ${total_pnl:>9.0f} | {avg_ret:>7.2f}% | {avg_dur:>7.1f}h")

# Winner
print("\n  VERDICT:")
best_tp = max([1.0, 1.5, 2.0, 2.5, 3.0], 
              key=lambda tp: sum(all_results[s][tp].get("pnl", 0) for s in all_results))
best_pnl = sum(all_results[s][best_tp].get("pnl", 0) for s in all_results)
base_pnl = sum(all_results[s][1.5].get("pnl", 0) for s in all_results)
print(f"  Best TP: {best_tp}% (${best_pnl:,.0f} total PnL)")
print(f"  vs 1.5%: ${base_pnl:,.0f} (delta: ${best_pnl - base_pnl:+,.0f}, {(best_pnl/base_pnl-1)*100:+.1f}%)")

conn.close()
