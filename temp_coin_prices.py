"""Check current prices vs entry for all open positions."""
import json

# Paper PM bot
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json") as f:
    paper = json.load(f)

# Live bot
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json") as f:
    live = json.load(f)

print("=" * 70)
print("PAPER PM — Open Positions")
print("=" * 70)
print(f"{'Coin':<12} {'Price':>10} {'Avg Entry':>10} {'Layers':>6} {'Invested':>10} {'Unreal PnL':>12} {'Dist to TP':>10}")
print("-" * 70)
for sym, c in paper.get("coins", {}).items():
    if c.get("layers", 0) > 0:
        price = c.get("current_price", 0)
        entry = c.get("avg_entry", 0)
        tp = c.get("next_tp_price", 0)
        layers = c.get("layers", 0)
        invested = c.get("invested", 0)
        upnl = c.get("unrealized_pnl", 0)
        dist = ((tp - price) / price * 100) if price > 0 and tp > 0 else 0
        coin = sym.split("/")[0]
        print(f"{coin:<12} ${price:>9.4f} ${entry:>9.4f} {layers:>6} ${invested:>9.2f} ${upnl:>10.2f} {dist:>9.1f}%")

print(f"\n{'=' * 70}")
print("LIVE PM — Open Positions")
print("=" * 70)
print(f"{'Coin':<12} {'Price':>10} {'Avg Entry':>10} {'Layers':>6} {'Invested':>10} {'Unreal PnL':>12} {'Dist to TP':>10}")
print("-" * 70)
for sym, c in live.get("coins", {}).items():
    if c.get("layers", 0) > 0:
        price = c.get("current_price", 0)
        entry = c.get("avg_entry", 0)
        tp = c.get("next_tp_price", 0)
        layers = c.get("layers", 0)
        invested = c.get("invested", 0)
        upnl = c.get("unrealized_pnl", 0)
        dist = ((tp - price) / price * 100) if price > 0 and tp > 0 else 0
        coin = sym.split("/")[0]
        print(f"{coin:<12} ${price:>9.4f} ${entry:>9.4f} {layers:>6} ${invested:>9.2f} ${upnl:>10.2f} {dist:>9.1f}%")

print(f"\nLive equity: ${live.get('equity', 0):,.2f} | Paper equity: ${paper.get('equity', 0):,.2f}")
print(f"Live update: {live.get('last_update', '?')}")
print(f"Paper update: {paper.get('last_update', '?')}")
