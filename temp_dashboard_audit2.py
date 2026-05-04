"""Full audit: paper bot dashboards, trade history, sync status."""
import json, csv, os
from datetime import datetime, timezone
from pathlib import Path

now = datetime.now(timezone.utc)

# ─── V14PM Paper ─────────────────────────────────────────────
print("=" * 65)
print("V14PM PAPER")
print("=" * 65)

pm_status = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json")
pm_csv = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\trades.csv")

with open(pm_status) as f:
    pm = json.load(f)

ts = datetime.fromisoformat(pm["last_update"])
age = int((now - ts).total_seconds() / 60)
print(f"Status: {'RUNNING' if pm.get('running') else 'STOPPED'} | Updated {age}m ago")
print(f"Equity: ${pm.get('equity', 0):,.2f} | Capital: ${pm.get('capital', 0):,.0f} | PnL: {pm.get('pnl_pct', 0):+.1f}%")
print(f"Deals: {pm.get('deals_completed', 0)} | Win rate: {pm.get('win_rate', 0):.0f}%")
print(f"Realized PnL: ${pm.get('total_realized_pnl', 0):,.2f} | Fees: ${pm.get('total_fees', 0):,.2f}")

# CSV check
if pm_csv.exists():
    with open(pm_csv) as f:
        trades = list(csv.DictReader(f))
    print(f"\nTrades CSV: {len(trades)} trades")
    if trades:
        first = trades[0].get("close_time", trades[0].get("open_time", "?"))
        last = trades[-1].get("close_time", trades[-1].get("recorded_at", "?"))
        csv_pnl = sum(float(t.get("pnl", 0)) for t in trades)
        print(f"  First: {first[:19]}")
        print(f"  Last:  {last[:19]}")
        print(f"  CSV total PnL: ${csv_pnl:,.2f}")
        status_pnl = pm.get("total_realized_pnl", 0)
        match = abs(csv_pnl - status_pnl) < 1.0
        print(f"  Status PnL:    ${status_pnl:,.2f} {'✅ MATCH' if match else '❌ MISMATCH'}")
        
        # Check for gaps in deal_id
        ids = [int(t.get("deal_id", 0)) for t in trades if t.get("deal_id")]
        if ids:
            expected = set(range(min(ids), max(ids) + 1))
            missing = expected - set(ids)
            if missing:
                print(f"  ⚠️ Missing deal IDs: {sorted(missing)[:10]}...")
            else:
                print(f"  Deal IDs: {min(ids)}-{max(ids)}, no gaps ✅")
else:
    print("\n❌ trades.csv NOT FOUND")

# Active positions
active = [(sym, c) for sym, c in pm.get("coins", {}).items() if c.get("layers", 0) > 0]
print(f"\nActive positions: {len(active)}")
for sym, c in active:
    coin = sym.split("/")[0]
    print(f"  {coin}: L{c['layers']}, ${c.get('invested', 0):,.0f} invested, {c.get('unrealized_pnl', 0):+,.0f} unrealized")

# ─── V14 Paper ───────────────────────────────────────────────
print(f"\n{'=' * 65}")
print("V14 PAPER")
print("=" * 65)

v14_status = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14\status.json")
v14_csv = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14\trades.csv")

with open(v14_status) as f:
    v14 = json.load(f)

ts2 = datetime.fromisoformat(v14["last_update"])
age2 = int((now - ts2).total_seconds() / 60)
print(f"Status: {'RUNNING' if v14.get('running') else 'STOPPED'} | Updated {age2}m ago")
print(f"Equity: ${v14.get('equity', 0):,.2f} | PnL: {v14.get('pnl_pct', 0):+.1f}%")
print(f"Deals: {v14.get('deals_completed', 0)} | Win rate: {v14.get('win_rate', 0):.0f}%")

if v14_csv.exists():
    with open(v14_csv) as f:
        v14_trades = list(csv.DictReader(f))
    print(f"\nTrades CSV: {len(v14_trades)} trades")
    if v14_trades:
        first = v14_trades[0].get("close_time", "?")
        last = v14_trades[-1].get("close_time", v14_trades[-1].get("recorded_at", "?"))
        csv_pnl = sum(float(t.get("pnl", 0)) for t in v14_trades)
        print(f"  First: {first[:19]}")
        print(f"  Last:  {last[:19]}")
        print(f"  CSV total PnL: ${csv_pnl:,.2f}")
else:
    print("\n❌ trades.csv NOT FOUND")

# ─── V14-ETF Paper ───────────────────────────────────────────
print(f"\n{'=' * 65}")
print("V14-ETF PAPER")
print("=" * 65)

etf_status = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14etf\status.json")
if etf_status.exists():
    with open(etf_status) as f:
        etf = json.load(f)
    ts3 = datetime.fromisoformat(etf["last_update"])
    age3 = int((now - ts3).total_seconds() / 60)
    print(f"Status: {'RUNNING' if etf.get('running') else 'STOPPED'} | Updated {age3}m ago")
    print(f"Equity: ${etf.get('equity', 0):,.2f} | PnL: {etf.get('pnl_pct', 0):+.1f}%")
else:
    print("Status: NOT FOUND")

# ─── Dashboard Sync ──────────────────────────────────────────
print(f"\n{'=' * 65}")
print("DASHBOARD SYNC")
print("=" * 65)

sync_base = Path(os.environ["TEMP"]) / "ait-dashboard-sync" / "docs" / "data"
for label, subdir in [("v14-pm (Paper PM)", "v14-pm"), ("v14-pm-live (Live PM)", "v14-pm-live"), ("v14 (V14 Paper)", "v14")]:
    sp = sync_base / subdir / "status.json"
    if sp.exists():
        mod = datetime.fromtimestamp(sp.stat().st_mtime, tz=timezone.utc)
        sync_age = int((now - mod).total_seconds() / 60)
        print(f"  {label}: synced {sync_age}m ago ✅")
    else:
        print(f"  {label}: NOT IN SYNC REPO ❌")

# Check last git push
import subprocess
result = subprocess.run(
    ["git", "log", "--oneline", "-3"],
    capture_output=True, text=True, timeout=10,
    cwd=str(sync_base.parent.parent)
)
print(f"\nLast 3 sync commits:")
for line in result.stdout.strip().split("\n"):
    print(f"  {line}")
