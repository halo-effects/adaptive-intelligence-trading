"""Investigate paper PM overspend — what changed and why."""
import json, csv
from datetime import datetime, timezone
from pathlib import Path

# Current state
with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json") as f:
    status = json.load(f)

print("=" * 65)
print("CAPITAL AUDIT")
print("=" * 65)
capital = status.get("capital", 0)
equity = status.get("equity", 0)
realized = status.get("total_realized_pnl", 0)
fees = status.get("total_fees", 0)
router = status.get("router", {})

print(f"Capital: ${capital:,.2f}")
print(f"Equity: ${equity:,.2f}")
print(f"Realized PnL: ${realized:,.2f}")
print(f"Fees: ${fees:,.2f}")
print(f"Available (capital + realized - fees): ${capital + realized - fees:,.2f}")
print(f"\nRouter state:")
print(f"  Active cash: ${router.get('active_cash', 0):,.2f}")
print(f"  Reserve cash: ${router.get('reserve_cash', 0):,.2f}")
print(f"  Total active allocated: ${router.get('total_active_allocated', 0):,.2f}")
print(f"  Total reserve allocated: ${router.get('total_reserve_allocated', 0):,.2f}")

# All positions
print(f"\n{'=' * 65}")
print(f"{'Coin':<12} {'Layers':>6} {'Invested':>10} {'Unrealized':>10} {'Realized':>10}")
print("-" * 65)
total_invested = 0
total_unrealized = 0
for sym, c in status.get("coins", {}).items():
    layers = c.get("layers", 0)
    invested = c.get("invested", 0)
    unrealized = c.get("unrealized_pnl", 0)
    rpnl = c.get("realized_pnl", 0)
    if layers > 0 or invested > 0:
        coin = sym.split("/")[0]
        total_invested += invested
        total_unrealized += unrealized
        print(f"{coin:<12} {layers:>6} ${invested:>9,.2f} ${unrealized:>9,.2f} ${rpnl:>9,.2f}")

print("-" * 65)
print(f"{'TOTAL':<12} {'':>6} ${total_invested:>9,.2f} ${total_unrealized:>9,.2f}")
print(f"\nCash = capital + realized - fees - invested = ${capital + realized - fees - total_invested:,.2f}")
print(f"Utilization: {total_invested / (capital + realized - fees) * 100:.1f}%")

# Count approved symbols and tier
print(f"\nTier coin cap: {status.get('tier_coin_cap')}")
print(f"Approved symbols: {status.get('approved_symbols')}")

# Check how many NEW coins entered since this morning
print(f"\n{'=' * 65}")
print("RECENT TRADES (last 24h)")
print("=" * 65)
csv_path = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\trades.csv")
if csv_path.exists():
    with open(csv_path) as f:
        trades = list(csv.DictReader(f))
    
    # Trades from today
    today_trades = []
    for t in trades:
        ct = t.get("close_time", "")
        if ct and "2026-04-19" in ct:
            today_trades.append(t)
        elif ct and "2026-04-18" in ct:
            today_trades.append(t)
    
    print(f"Trades since yesterday: {len(today_trades)}")
    for t in today_trades:
        print(f"  Deal #{t.get('deal_id')}: {t.get('symbol')} L{t.get('layers')} close={t.get('close_time', '')[:16]} pnl=${float(t.get('pnl', 0)):,.2f}")

# Count unique coins that currently have engines
all_coins = list(status.get("coins", {}).keys())
active_coins = [s for s, c in status.get("coins", {}).items() if c.get("layers", 0) > 0]
print(f"\nTotal engines: {len(all_coins)}")
print(f"Active (layers > 0): {len(active_coins)}")
print(f"Active coins: {[s.split('/')[0] for s in active_coins]}")
