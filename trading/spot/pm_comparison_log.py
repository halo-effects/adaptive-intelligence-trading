"""
PM Comparison Logger — daily snapshot comparing V14 PM vs V14 Paper.

Appends one entry per day to docs/data/v14/pm_comparison.json.
Run after daily rebalance (~9 AM PST / 17:00 UTC).

Captures:
  - Equity, PnL%, deals, win rate, DD for both bots
  - PM allocation breakdown (coin, allocated $, % of active pool, DCA score)
  - Delta: PM equity minus V14 Paper equity (same $10K starting capital)
"""

import json
from datetime import datetime, timezone, date
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent

V14_STATUS    = WORKSPACE / "trading" / "spot" / "paper" / "v14"    / "status.json"
PM_STATUS     = WORKSPACE / "trading" / "spot" / "paper" / "v14_portfolio" / "status.json"
SCANNER_JSON  = WORKSPACE / "docs" / "data" / "v14" / "cycle_scanner.json"
OUTPUT        = WORKSPACE / "docs" / "data" / "v14" / "pm_comparison.json"


def load(path):
    with open(path) as f:
        return json.load(f)


def bot_snapshot(status):
    capital = status.get("capital", 10000)
    equity  = status.get("equity", capital)
    return {
        "equity":       round(equity, 2),
        "pnl_pct":      round(status.get("pnl_pct", 0), 2),
        "pnl_usd":      round(equity - capital, 2),
        "deals":        status.get("deals_completed", 0),
        "win_rate":     round(status.get("win_rate", 0), 1),
        "max_dd_pct":   round(status.get("max_drawdown_pct", 0), 2),
        "uptime_hours": round(status.get("uptime_hours", 0), 1),
    }


def pm_allocation(status, scanner):
    """Build per-coin allocation breakdown with scanner scores."""
    coins    = status.get("coins", {})
    router   = status.get("router", {})
    active   = router.get("active_cash", 0) or 0

    # Build score lookup from scanner 30d rankings
    scores = {}
    try:
        rankings = scanner.get("windows", {}).get("30d", {}).get("rankings", [])
        if isinstance(rankings, list):
            for r in rankings:
                scores[r.get("symbol", "")] = {
                    "dca_score": round(r.get("dca_score", 0), 2),
                    "rank":      r.get("rank"),
                    "cf":        round(r.get("capital_freedom", 0), 3),
                    "dd":        round(r.get("max_drawdown_pct", 0), 1),
                    "deals_per_week": round(r.get("deals_per_week", 0), 1),
                }
    except Exception:
        pass

    allocation = []
    for sym, coin in coins.items():
        invested = coin.get("invested", 0)
        layers   = coin.get("layers", 0)
        sc       = scores.get(sym, {})
        allocation.append({
            "symbol":         sym,
            "layers":         layers,
            "invested":       round(invested, 2),
            "unrealized_pnl": round(coin.get("unrealized_pnl", 0), 2),
            "realized_pnl":   round(coin.get("realized_pnl", 0), 2),
            "dca_score":      sc.get("dca_score"),
            "rank":           sc.get("rank"),
            "cf":             sc.get("cf"),
            "dd_pct":         sc.get("dd"),
            "deals_per_week": sc.get("deals_per_week"),
        })

    # Sort by rank
    allocation.sort(key=lambda x: (x["rank"] or 99))

    return {
        "active_pool":    round(router.get("active_cash", 0), 2),
        "reserve":        round(router.get("reserve_cash", 0), 2),
        "total_invested": round(sum(c["invested"] for c in allocation), 2),
        "coins":          allocation,
    }


def main():
    today = date.today().isoformat()
    now   = datetime.now(timezone.utc).isoformat()

    # Load existing log
    existing = []
    if OUTPUT.exists():
        try:
            existing = load(OUTPUT)
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []

    # Check if we already have today's entry (update it if so)
    existing = [e for e in existing if e.get("date") != today]

    # Load status files
    try:
        v14_status = load(V14_STATUS)
    except Exception as e:
        print(f"ERROR loading V14 status: {e}")
        return 1

    try:
        pm_status = load(PM_STATUS)
    except Exception as e:
        print(f"ERROR loading PM status: {e}")
        return 1

    scanner = {}
    try:
        scanner = load(SCANNER_JSON)
    except Exception:
        pass

    v14_snap = bot_snapshot(v14_status)
    pm_snap  = bot_snapshot(pm_status)
    alloc    = pm_allocation(pm_status, scanner)

    entry = {
        "date":        today,
        "captured_at": now,
        "v14_paper":   v14_snap,
        "v14_pm":      pm_snap,
        "delta": {
            "equity_usd": round(pm_snap["equity"] - v14_snap["equity"], 2),
            "pnl_pct":    round(pm_snap["pnl_pct"] - v14_snap["pnl_pct"], 2),
            "deals":      pm_snap["deals"] - v14_snap["deals"],
        },
        "pm_allocation": alloc,
    }

    existing.append(entry)
    existing.sort(key=lambda x: x["date"])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(existing, f, indent=2)

    print(f"[{today}] Logged comparison snapshot.")
    print(f"  V14 Paper : ${v14_snap['equity']:,.2f}  ({v14_snap['pnl_pct']:+.2f}%)  {v14_snap['deals']} deals")
    print(f"  V14 PM    : ${pm_snap['equity']:,.2f}  ({pm_snap['pnl_pct']:+.2f}%)  {pm_snap['deals']} deals")
    print(f"  Delta     : ${entry['delta']['equity_usd']:+,.2f}  ({entry['delta']['pnl_pct']:+.2f}%)")
    print(f"  PM Alloc  : {alloc['total_invested']:,.0f} invested / {alloc['active_pool']:,.0f} active pool")
    for c in alloc["coins"]:
        print(f"    #{c['rank']} {c['symbol']:12s}  score={c['dca_score']}  invested=${c['invested']:,.0f}  L{c['layers']}  upnl=${c['unrealized_pnl']:+,.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
