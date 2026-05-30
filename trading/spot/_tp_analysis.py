"""
Analyze whether higher TP targets would improve cycling profits
on the actual coins the PM scanner selects.

Key question: The scanner picks high-velocity coins. Do these coins
have enough intra-cycle price swings to support 2-3% TPs, or does
the faster 1.5% cycling compound better?
"""
import csv, json, statistics, sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

DB_PATH = Path("trading/spot/data/candles.db")

# Load paper PM trades
with open("trading/spot/paper/v14_portfolio/trades.csv") as f:
    trades = list(csv.DictReader(f))

print("=" * 70)
print("  TP OPTIMIZATION ANALYSIS — V14PM Scanner Coins")
print("=" * 70)

# 1. What coins does the scanner actually pick?
print("\n--- TOP COINS BY TRADE COUNT (scanner selections) ---")
coin_stats = defaultdict(lambda: {"count": 0, "total_pnl": 0, "returns": [], "layers": [], "durations": []})
for t in trades:
    sym = t.get("symbol", "")
    ret = float(t.get("return_pct", 0) or 0)
    pnl = float(t.get("pnl", 0) or 0)
    layers = int(t.get("layers", 0) or 0)
    dur = float(t.get("duration_h", 0) or 0)
    coin_stats[sym]["count"] += 1
    coin_stats[sym]["total_pnl"] += pnl
    coin_stats[sym]["returns"].append(ret)
    coin_stats[sym]["layers"].append(layers)
    coin_stats[sym]["durations"].append(dur)

# Sort by trade count
top_coins = sorted(coin_stats.items(), key=lambda x: x[1]["count"], reverse=True)[:15]
print(f"{'Coin':<15} {'Trades':>6} {'Avg Ret':>8} {'Med Ret':>8} {'Avg Dur':>8} {'PnL':>10}")
for sym, s in top_coins:
    avg_ret = statistics.mean(s["returns"])
    med_ret = statistics.median(s["returns"])
    avg_dur = statistics.mean(s["durations"])
    print(f"{sym:<15} {s['count']:>6} {avg_ret:>7.2f}% {med_ret:>7.2f}% {avg_dur:>7.1f}h ${s['total_pnl']:>9.2f}")

# 2. For the top coins, analyze candle volatility to assess TP potential
print("\n--- CANDLE VOLATILITY FOR TOP PM COINS ---")
print("(How much do these coins move per 1h candle?)")

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# Get recent 90 days of hourly candles for top coins
# Use epoch ms for timestamp comparison (candles table uses epoch ms)
import time as _time
cutoff_dt = datetime.now() - timedelta(days=90)
cutoff = int(cutoff_dt.timestamp() * 1000)  # epoch ms
top_syms = [sym for sym, _ in top_coins[:10]]

for sym in top_syms:
    # Try both USDT and USDC variants
    for quote in ["USDT", "USDC"]:
        full_sym = sym if "/" in sym else f"{sym.split('/')[0]}/{quote}" if "/" not in sym else sym
        cursor.execute("""
            SELECT open, high, low, close FROM candles 
            WHERE symbol = ? AND timeframe = '1h' AND timestamp >= ?
            ORDER BY timestamp
        """, (full_sym, cutoff))
        rows = cursor.fetchall()
        if rows:
            break
    
    if not rows:
        continue
    
    # Calculate per-candle metrics
    ranges = []  # high-low range as % of open
    close_moves = []  # close-to-close moves
    up_moves = []  # only positive close-to-close
    
    for i, (o, h, l, c) in enumerate(rows):
        if o > 0:
            ranges.append((h - l) / o * 100)
        if i > 0:
            prev_c = rows[i-1][3]
            if prev_c > 0:
                move = (c - prev_c) / prev_c * 100
                close_moves.append(move)
                if move > 0:
                    up_moves.append(move)
    
    if not ranges:
        continue
    
    # How often does price move >1.5%, >2%, >3% in a single candle?
    gt_15 = sum(1 for r in ranges if r > 1.5) / len(ranges) * 100
    gt_20 = sum(1 for r in ranges if r > 2.0) / len(ranges) * 100
    gt_30 = sum(1 for r in ranges if r > 3.0) / len(ranges) * 100
    
    print(f"\n  {full_sym} ({len(rows)} candles, 90d)")
    print(f"    Avg 1h range:     {statistics.mean(ranges):.2f}%")
    print(f"    Median 1h range:  {statistics.median(ranges):.2f}%")
    print(f"    Candles >1.5%:    {gt_15:.1f}%")
    print(f"    Candles >2.0%:    {gt_20:.1f}%")
    print(f"    Candles >3.0%:    {gt_30:.1f}%")
    if up_moves:
        print(f"    Avg up move:      {statistics.mean(up_moves):.2f}%")
        print(f"    Median up move:   {statistics.median(up_moves):.2f}%")

# 3. Simulate different TP targets on actual candle data
print("\n" + "=" * 70)
print("  TP TARGET SIMULATION ON ACTUAL CANDLE DATA")
print("=" * 70)
print("  (Simulates simple DCA grid: buy at candle low, TP at entry + X%)")
print("  (Measures: avg cycle time, deals/week, total profit)")

for sym in top_syms[:6]:
    for quote in ["USDT", "USDC"]:
        full_sym = sym if "/" in sym else f"{sym.split('/')[0]}/{quote}"
        cursor.execute("""
            SELECT timestamp, open, high, low, close FROM candles 
            WHERE symbol = ? AND timeframe = '1h' AND timestamp >= ?
            ORDER BY timestamp
        """, (full_sym, cutoff))
        rows = cursor.fetchall()
        if rows:
            break
    
    if not rows or len(rows) < 100:
        continue
    
    print(f"\n  {full_sym}:")
    
    for tp_pct in [1.0, 1.5, 2.0, 2.5, 3.0]:
        # Simple simulation: enter on any candle, check how many candles until
        # price reaches entry * (1 + tp_pct/100)
        cycle_times = []
        
        for i in range(0, len(rows) - 1, 1):
            entry_price = float(rows[i][4])  # close as entry
            tp_target = entry_price * (1 + tp_pct / 100)
            
            # How many candles until high >= tp_target?
            for j in range(i + 1, min(i + 168, len(rows))):  # max 7 days
                if float(rows[j][2]) >= tp_target:  # high >= tp
                    cycle_times.append(j - i)
                    break
        
        if cycle_times:
            hit_rate = len(cycle_times) / (len(rows) - 1) * 100
            avg_hours = statistics.mean(cycle_times)
            deals_per_week = 168 / avg_hours if avg_hours > 0 else 0
            # Profit per week (simplified): deals * tp_pct * capital_fraction
            weekly_return = deals_per_week * tp_pct
            print(f"    TP {tp_pct:.1f}%: avg {avg_hours:>5.1f}h cycle | {deals_per_week:>5.1f} deals/wk | hit rate {hit_rate:>5.1f}% | weekly return ~{weekly_return:.1f}%")
        else:
            print(f"    TP {tp_pct:.1f}%: no cycles completed in window")

conn.close()

print("\n" + "=" * 70)
print("  CONCLUSION")
print("=" * 70)
