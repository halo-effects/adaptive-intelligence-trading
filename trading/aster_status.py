"""Status checker — reads live/status.json and prints a formatted report."""
import json
import sys
from pathlib import Path
from datetime import datetime

STATUS_PATH = Path(__file__).parent / "live" / "status.json"


def main():
    if not STATUS_PATH.exists():
        print("No status file found. Is the bot running?")
        sys.exit(1)

    with open(STATUS_PATH) as f:
        s = json.load(f)

    mode = "DRY RUN" if s.get("dry_run") else "LIVE"
    halted = "🛑 HALTED" if s.get("halted") else "🟢 Running" if s.get("running") else "⏸️ Stopped"

    print(f"\n{'='*60}")
    print(f"  Aster Trader Status [{mode}]")
    print(f"{'='*60}")
    print(f"  Status:     {halted}")
    if s.get("halted"):
        print(f"  Reason:     {s.get('halt_reason', '?')}")
    print(f"  Symbol:     {s.get('symbol')} | {s.get('timeframe')}")
    print(f"  Price:      ${s.get('price', 0):.3f}")
    print(f"  Regime:     {s.get('regime')}")
    print(f"  Leverage:   {s.get('leverage')}x")
    print(f"  Equity:     ${s.get('equity', 0):.2f}")
    print(f"  Start:      ${s.get('start_equity', 0):.2f}")
    print(f"  Peak:       ${s.get('peak_equity', 0):.2f}")
    pnl = s.get("pnl", 0)
    pnl_pct = s.get("pnl_pct", 0)
    print(f"  PnL:        ${pnl:+.2f} ({pnl_pct:+.1f}%)")
    print(f"  Drawdown:   {s.get('drawdown_pct', 0):.1f}% / {s.get('max_drawdown_threshold', 25)}%")
    print(f"  Cycles:     {s.get('cycle_count', 0)}")
    print(f"  Deals:      {s.get('deal_counter', 0)} total")

    deal = s.get("deal")
    if deal:
        print(f"\n  --- Active Deal #{deal['deal_id']} ---")
        print(f"  Entry:      ${deal['entry_price']:.3f}")
        print(f"  Avg Entry:  ${deal['avg_entry']:.3f}")
        print(f"  Qty:        {deal['total_qty']:.2f}")
        print(f"  Cost:       ${deal['total_cost']:.2f}")
        print(f"  SOs Filled: {deal['safety_orders_filled']}/{s.get('config', {}).get('max_sos', 8)}")
        tp_pct = s.get("config", {}).get("tp_pct", 4.0)
        tp_price = deal["avg_entry"] * (1 + tp_pct / 100)
        print(f"  TP Target:  ${tp_price:.3f}")
        if s.get("price"):
            upnl = deal["total_qty"] * s["price"] - deal["total_cost"]
            print(f"  uPnL:       ${upnl:+.2f}")
    else:
        print(f"\n  No active deal")

    print(f"\n  Updated:    {s.get('timestamp', '?')}")
    print(f"  Started:    {s.get('start_time', '?')}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
