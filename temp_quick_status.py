import json
from datetime import datetime, timezone

bots = {
    "V14PM Live": r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json",
    "V14PM Paper": r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json",
    "V14 Paper": r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14\status.json",
}
now = datetime.now(timezone.utc)
for name, path in bots.items():
    with open(path) as f:
        d = json.load(f)
    ts = datetime.fromisoformat(d["last_update"])
    age = int((now - ts).total_seconds() / 60)
    eq = d.get("equity", 0)
    pnl = d.get("pnl_pct", 0)
    deals = d.get("deals_completed", 0)
    wr = d.get("win_rate", 0)
    coins = sum(1 for c in d.get("coins", {}).values() if c.get("layers", 0) > 0)
    print(f"{name}: ${eq:,.2f} ({pnl:+.1f}%) | {coins} positions | {deals} deals ({wr:.0f}% WR) | {age}m ago")
