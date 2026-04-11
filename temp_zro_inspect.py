import json, sqlite3, datetime
from pathlib import Path

# Get ZRO from paper bot state
state = json.loads(Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\state.json").read_text(encoding="utf-8"))
status = json.loads(Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json").read_text(encoding="utf-8"))

print("=== ZRO in status.json ===")
for sym, c in status.get("coins", {}).items():
    if "ZRO" in sym:
        print(json.dumps(c, indent=2))

print("\n=== ZRO in state.json ===")
for sym, cs in state.get("coins", {}).items():
    if "ZRO" in sym:
        eng = cs.get("engine_state", {})
        print(f"Symbol: {sym}")
        print(f"  allocated_capital: {cs.get('allocated_capital')}")
        print(f"  layer_count: {cs.get('layer_count')}")
        print(f"  tp_limit_price: {cs.get('tp_limit_price')}")
        print(f"  tp_order_id: {cs.get('tp_order_id')}")
        print(f"  paused: {cs.get('paused')}")
        print(f"  regime_flagged: {cs.get('regime_flagged')}")
        print(f"  last_candle_ts: {cs.get('last_candle_ts')}")
        if cs.get('last_candle_ts'):
            dt = datetime.datetime.fromtimestamp(cs['last_candle_ts']/1000, tz=datetime.timezone.utc)
            print(f"    = {dt.isoformat()}")
        print(f"\n  Engine state:")
        print(f"    long_avg_entry: {eng.get('long_avg_entry')}")
        print(f"    long_layers: {eng.get('long_layers')}")
        print(f"    long_cost: {eng.get('long_cost')}")
        print(f"    long_coins: {eng.get('long_coins')}")
        print(f"    long_last_buy: {eng.get('long_last_buy')}")
        print(f"    current_price: {eng.get('current_price')}")
        print(f"    capital: {eng.get('capital')}")
        print(f"    initial_capital: {eng.get('initial_capital')}")
        
        # Calculate TP
        avg = eng.get('long_avg_entry', 0)
        if avg > 0:
            tp = avg * 1.015
            cur = eng.get('current_price', 0)
            pct_to_tp = ((tp - cur) / cur * 100) if cur > 0 else 0
            unrealized = eng.get('long_coins', 0) * (cur - avg)
            print(f"\n  Calculated TP: ${tp:.4f}")
            print(f"  Current price: ${cur:.4f}")
            print(f"  Distance to TP: {pct_to_tp:.2f}%")
            print(f"  Unrealized PnL: ${unrealized:.2f}")
            print(f"  Invested: ${eng.get('long_cost', 0):.2f}")

# Get ZRO buy log entries
print("\n=== ZRO buy log entries ===")
log_path = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\bot.log")
with open(log_path, encoding="utf-8") as f:
    for line in f:
        if "ZRO" in line and ("Router approved BUY" in line or "Granted" in line and "ZRO" in line):
            safe = line.strip().encode("ascii", "replace").decode()[:200]
            print(f"  {safe}")

# Get ZRO candles
print("\n=== Recent ZRO candles ===")
db = sqlite3.connect(r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db")
candles = db.execute("""
    SELECT timestamp, open, high, low, close 
    FROM candles 
    WHERE symbol = 'ZRO/USDT' AND timeframe = '1h'
    ORDER BY timestamp DESC LIMIT 24
""").fetchall()
candles.reverse()
for ts, o, h, l, c in candles:
    dt = datetime.datetime.fromtimestamp(ts/1000, tz=datetime.timezone.utc)
    print(f"  {dt.strftime('%Y-%m-%d %H:%M')} | O={o:.4f} H={h:.4f} L={l:.4f} C={c:.4f}")
db.close()
