"""Check if JTO price hit TP target in recent candles."""
import json, sys, os
sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")
os.chdir(r"C:\Users\Never\.openclaw\workspace")

from trading.spot.exchange_client import SpotExchangeClient

client = SpotExchangeClient()
client.connect("aster")
client.exchange.load_markets()

# Fetch recent 1h candles for JTO
candles = client.exchange.fetch_ohlcv("JTO/USDT:USDT", "1h", limit=24)

print("JTO/USDT last 24 hourly candles:")
print(f"{'Time UTC':<20} {'Open':>10} {'High':>10} {'Low':>10} {'Close':>10}")
print("-" * 65)

tp_target = 0.342024
hits = []
for c in candles:
    from datetime import datetime, timezone
    ts = datetime.fromtimestamp(c[0] / 1000, tz=timezone.utc)
    o, h, l, cl = c[1], c[2], c[3], c[4]
    hit = "<<< HIT TP" if h >= tp_target else ""
    print(f"{ts.strftime('%Y-%m-%d %H:%M'):<20} ${o:>9.6f} ${h:>9.6f} ${l:>9.6f} ${cl:>9.6f} {hit}")
    if h >= tp_target:
        hits.append(ts)

if hits:
    print(f"\n⚠️ JTO HIGH touched TP (${tp_target}) at: {[str(h)[:16] for h in hits]}")
else:
    print(f"\nJTO never reached TP target ${tp_target} in last 24h")
    print(f"Highest high: ${max(c[2] for c in candles):.6f}")
    print(f"Current price: ${candles[-1][4]:.6f}")
    print(f"Distance to TP: {(tp_target - candles[-1][4]) / candles[-1][4] * 100:.2f}%")

# Also check paper bot status
print("\n--- Paper PM Bot JTO State ---")
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json") as f:
    data = json.load(f)
jto = data.get("coins", {}).get("JTO/USDT", {})
print(f"  Layers: {jto.get('layers')}")
print(f"  Avg entry: ${jto.get('avg_entry', 0):.6f}")
print(f"  Current price: ${jto.get('current_price', 0):.6f}")
print(f"  TP: ${jto.get('next_tp_price', 0):.6f}")
print(f"  Unrealized: ${jto.get('unrealized_pnl', 0):.2f}")
print(f"  Last update: {data.get('last_update', '?')[:19]}")
