import json, sqlite3, datetime
from pathlib import Path

BASE = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio")
status = json.loads((BASE / "status.json").read_text(encoding="utf-8"))
engine = json.loads((BASE / "engine_state.json").read_text(encoding="utf-8"))

print("=== ZRO in status.json ===")
for sym, c in status.get("coins", {}).items():
    if "ZRO" in sym:
        print(json.dumps(c, indent=2))

print("\n=== ZRO in engine_state.json ===")
for sym, cs in engine.get("coins", {}).items():
    if "ZRO" in sym:
        print(f"Symbol: {sym}")
        # Print all keys
        for k, v in cs.items():
            if k != "engine_state":
                print(f"  {k}: {v}")
        
        eng = cs.get("engine_state", {})
        print(f"\n  Engine state:")
        for k in ["long_avg_entry", "long_layers", "long_cost", "long_coins", 
                   "long_last_buy", "current_price", "capital", "initial_capital",
                   "short_avg_entry", "short_layers", "short_cost", "short_coins"]:
            print(f"    {k}: {eng.get(k)}")
        
        avg = eng.get("long_avg_entry", 0)
        if avg and avg > 0:
            tp = avg * 1.015
            cur = eng.get("current_price", 0)
            coins = eng.get("long_coins", 0)
            cost = eng.get("long_cost", 0)
            layers = eng.get("long_layers", 0)
            unrealized = coins * (cur - avg) if cur else 0
            pct_to_tp = ((tp - cur) / cur * 100) if cur > 0 else 0
            pct_underwater = ((avg - cur) / avg * 100) if avg > 0 and cur < avg else 0
            print(f"\n  === POSITION ANALYSIS ===")
            print(f"  Layers: {layers}")
            print(f"  Invested: ${cost:.2f}")
            print(f"  Coins: {coins:.4f}")
            print(f"  Avg entry: ${avg:.4f}")
            print(f"  Current price: ${cur:.4f}")
            print(f"  TP target (1.5%): ${tp:.4f}")
            print(f"  Distance to TP: {pct_to_tp:+.2f}%")
            print(f"  Underwater: {pct_underwater:.2f}%")
            print(f"  Unrealized PnL: ${unrealized:.2f}")

# Get recent ZRO candles
print("\n=== Recent ZRO/USDT 1h candles ===")
db = sqlite3.connect(r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db")
candles = db.execute("""
    SELECT timestamp, open, high, low, close 
    FROM candles 
    WHERE symbol = 'ZRO/USDT' AND timeframe = '1h'
    ORDER BY timestamp DESC LIMIT 48
""").fetchall()
candles.reverse()
for ts, o, h, l, c in candles:
    dt = datetime.datetime.fromtimestamp(ts/1000, tz=datetime.timezone.utc)
    print(f"  {dt.strftime('%Y-%m-%d %H:%M')} | O={o:.4f} H={h:.4f} L={l:.4f} C={c:.4f}")
db.close()

# Get ZRO buy entries from log
print("\n=== ZRO buy log entries (most recent deal) ===")
log_path = BASE / "bot.log"
zro_buys = []
with open(log_path, encoding="utf-8") as f:
    for line in f:
        if "ZRO" in line and "Router approved BUY" in line:
            zro_buys.append(line.strip()[:200])
# Show last 15
for l in zro_buys[-15:]:
    safe = l.encode("ascii", "replace").decode()
    print(f"  {safe}")
