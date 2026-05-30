"""
TP target optimization analysis using actual candle data for PM scanner coins.
"""
import csv, json, statistics, sqlite3, time
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

DB_PATH = Path("trading/spot/data/candles.db")
cutoff_ms = int((datetime.now() - timedelta(days=90)).timestamp() * 1000)

# Load paper PM trades
with open("trading/spot/paper/v14_portfolio/trades.csv") as f:
    trades = list(csv.DictReader(f))

# Get top coins by trade count
coin_counts = defaultdict(int)
for t in trades:
    coin_counts[t.get("symbol", "")] += 1
top_coins = sorted(coin_counts.items(), key=lambda x: x[1], reverse=True)[:10]
top_syms = [sym for sym, _ in top_coins]

conn = sqlite3.connect(str(DB_PATH))

print("=" * 70)
print("  CANDLE VOLATILITY — TOP PM SCANNER COINS (90 days)")
print("=" * 70)

for sym in top_syms:
    rows = conn.execute(
        "SELECT open, high, low, close FROM candles "
        "WHERE symbol=? AND timeframe='1h' AND timestamp>=? ORDER BY timestamp",
        (sym, cutoff_ms)
    ).fetchall()
    
    if not rows or len(rows) < 100:
        continue
    
    ranges_pct = [(h - l) / o * 100 for o, h, l, c in rows if o > 0]
    
    gt_15 = sum(1 for r in ranges_pct if r > 1.5) / len(ranges_pct) * 100
    gt_20 = sum(1 for r in ranges_pct if r > 2.0) / len(ranges_pct) * 100
    gt_30 = sum(1 for r in ranges_pct if r > 3.0) / len(ranges_pct) * 100
    gt_50 = sum(1 for r in ranges_pct if r > 5.0) / len(ranges_pct) * 100
    
    print(f"\n  {sym} ({len(rows)} 1h candles)")
    print(f"    Avg range:      {statistics.mean(ranges_pct):.2f}%")
    print(f"    Median range:   {statistics.median(ranges_pct):.2f}%")
    print(f"    >1.5% range:    {gt_15:.1f}% of candles")
    print(f"    >2.0% range:    {gt_20:.1f}% of candles")
    print(f"    >3.0% range:    {gt_30:.1f}% of candles")
    print(f"    >5.0% range:    {gt_50:.1f}% of candles")

# TP simulation
print("\n" + "=" * 70)
print("  TP TARGET SIMULATION (actual 1h candle highs)")
print("=" * 70)
print("  For each candle, enter at close, check subsequent candle HIGHS")
print("  for TP hit. Measures cycle speed and weekly return potential.")

for sym in top_syms[:8]:
    rows = conn.execute(
        "SELECT timestamp, open, high, low, close FROM candles "
        "WHERE symbol=? AND timeframe='1h' AND timestamp>=? ORDER BY timestamp",
        (sym, cutoff_ms)
    ).fetchall()
    
    if not rows or len(rows) < 200:
        continue
    
    print(f"\n  {sym} ({len(rows)} candles):")
    print(f"    {'TP':>6} | {'Avg Cycle':>10} | {'Med Cycle':>10} | {'Deals/Wk':>9} | {'Hit Rate':>9} | {'Wkly Ret':>9}")
    
    for tp_pct in [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]:
        cycle_times = []
        attempts = 0
        
        # Sample every 4th candle as entry point (avoid overlap)
        for i in range(0, len(rows) - 168, 4):
            attempts += 1
            entry_price = float(rows[i][4])  # close
            tp_target = entry_price * (1 + tp_pct / 100)
            
            for j in range(i + 1, min(i + 168, len(rows))):  # max 7 days
                if float(rows[j][2]) >= tp_target:  # HIGH >= tp
                    cycle_times.append(j - i)
                    break
        
        if cycle_times and attempts > 0:
            hit_rate = len(cycle_times) / attempts * 100
            avg_h = statistics.mean(cycle_times)
            med_h = statistics.median(cycle_times)
            deals_wk = 168 / avg_h if avg_h > 0 else 0
            wkly_ret = deals_wk * tp_pct
            print(f"    {tp_pct:>5.1f}% | {avg_h:>8.1f}h  | {med_h:>8.1f}h  | {deals_wk:>8.1f} | {hit_rate:>8.1f}% | {wkly_ret:>8.1f}%")
        else:
            print(f"    {tp_pct:>5.1f}% | {'--':>10} | {'--':>10} | {'--':>9} | {0:>8.1f}% | {'--':>9}")

# Summary analysis
print("\n" + "=" * 70)
print("  COMPOUNDING COMPARISON: 1.5% vs 2.5% TP")
print("=" * 70)
print("  (Assumes $5000 per trade, full reinvestment)")

for sym in top_syms[:6]:
    rows = conn.execute(
        "SELECT timestamp, open, high, low, close FROM candles "
        "WHERE symbol=? AND timeframe='1h' AND timestamp>=? ORDER BY timestamp",
        (sym, cutoff_ms)
    ).fetchall()
    
    if not rows or len(rows) < 200:
        continue
    
    results = {}
    for tp_pct in [1.5, 2.5]:
        capital = 5000
        trades_done = 0
        i = 0
        while i < len(rows) - 1:
            entry_price = float(rows[i][4])
            tp_target = entry_price * (1 + tp_pct / 100)
            
            for j in range(i + 1, min(i + 168, len(rows))):
                if float(rows[j][2]) >= tp_target:
                    capital *= (1 + tp_pct / 100)
                    trades_done += 1
                    i = j + 1
                    break
            else:
                i += 168  # skip 7 days if no fill
            
            if i >= len(rows) - 1:
                break
        
        results[tp_pct] = (capital, trades_done)
    
    days = len(rows) / 24
    c15, t15 = results.get(1.5, (5000, 0))
    c25, t25 = results.get(2.5, (5000, 0))
    print(f"\n  {sym} ({days:.0f} days):")
    print(f"    1.5% TP: {t15} trades, ${c15:,.0f} final ({(c15/5000-1)*100:.1f}% total)")
    print(f"    2.5% TP: {t25} trades, ${c25:,.0f} final ({(c25/5000-1)*100:.1f}% total)")
    if c15 > c25:
        print(f"    >> 1.5% wins by ${c15-c25:,.0f} ({(c15/c25-1)*100:.1f}% better)")
    else:
        print(f"    >> 2.5% wins by ${c25-c15:,.0f} ({(c25/c15-1)*100:.1f}% better)")

conn.close()
