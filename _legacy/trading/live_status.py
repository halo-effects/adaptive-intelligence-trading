"""Status checker for the live trader. Reads status.json and prints a report."""
import json
import sys
import os
from pathlib import Path
from datetime import datetime

LIVE_DIR = Path(__file__).parent / "live"


def main():
    status_path = LIVE_DIR / "status.json"
    if not status_path.exists():
        print("❌ No status.json found. Is the live trader running?")
        sys.exit(1)

    with open(status_path) as f:
        s = json.load(f)

    mode = "DRY-RUN" if s.get("dry_run") else "LIVE"
    running = "🟢 Running" if s.get("running") else "⏹ Stopped"
    cb = "🔴 TRIGGERED" if s.get("circuit_breaker") else "🟢 OK"

    pnl = s.get("pnl", 0)
    pnl_color = "+" if pnl >= 0 else ""

    print(f"\n{'='*60}")
    print(f"  🤖 Martingale Live Trader — Status Report")
    print(f"{'='*60}")
    print(f"  Mode:           {mode} | {running}")
    print(f"  Symbol:         {s.get('symbol', '?')}")
    print(f"  Price:          ${s.get('current_price', 0):.4f}")
    print(f"  Regime:         {s.get('regime', '?')}")
    print(f"  Timeframe:      {s.get('timeframe', '?')}")
    print(f"{'─'*60}")
    print(f"  Equity:         ${s.get('equity', 0):,.2f}")
    print(f"  Cash:           ${s.get('cash', 0):,.2f}")
    print(f"  PnL:            {pnl_color}${pnl:,.2f} ({pnl_color}{s.get('pnl_pct', 0):.1f}%)")
    print(f"  Peak Equity:    ${s.get('peak_equity', 0):,.2f}")
    print(f"  Drawdown:       {s.get('drawdown_pct', 0):.1f}% / {s.get('max_drawdown_threshold', 25)}%")
    print(f"  Circuit Breaker: {cb}")
    print(f"{'─'*60}")

    deals = s.get("open_deals", [])
    print(f"  Open Deals:     {len(deals)}")
    for d in deals:
        upnl = d.get("unrealized_pnl", 0)
        sign = "+" if upnl >= 0 else ""
        print(f"    Deal #{d['deal_id']}: entry=${d['avg_entry']:.4f} | SOs={d['so_count']} | "
              f"uPnL={sign}${upnl:.2f} | pending={d.get('pending_sos', 0)}")

    closed = s.get("closed_deals_recent", [])
    print(f"\n  Closed Deals:   {s.get('closed_deals_count', 0)} total")
    if closed:
        print(f"  Last 5:")
        for d in closed[-5:]:
            rpnl = d.get("pnl", 0)
            sign = "+" if rpnl >= 0 else ""
            print(f"    #{d['deal_id']}: {sign}${rpnl:.2f} | SOs={d['so_count']} | {d.get('close_time', '?')[:19]}")

    cfg = s.get("config", {})
    print(f"\n{'─'*60}")
    print(f"  Config: BO=${cfg.get('base_order_size',0):.0f} SO=${cfg.get('safety_order_size',0):.0f} "
          f"TP={cfg.get('take_profit_pct',0)}% MaxSO={cfg.get('max_safety_orders',0)}")
    print(f"  Started:        {(s.get('start_time') or '?')[:19]}")
    print(f"  Last Update:    {(s.get('timestamp') or '?')[:19]}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
