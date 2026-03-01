"""Read paper trader status without disrupting the running bot."""
import json
import sys
from pathlib import Path
from datetime import datetime

PAPER_DIR = Path(__file__).parent / "paper"


def print_status():
    status_file = PAPER_DIR / "status.json"
    if not status_file.exists():
        print("No paper trader status found. Has it been started?")
        return

    with open(status_file) as f:
        s = json.load(f)

    print("\n" + "=" * 60)
    print("  📊 PAPER TRADER STATUS")
    print("=" * 60)
    print(f"  Running:    {'Yes' if s.get('running') else 'No (last snapshot)'}")
    print(f"  Updated:    {s.get('timestamp', '?')[:19]}")
    print(f"  Started:    {(s.get('start_time') or '?')[:19]}")
    print(f"  Timeframe:  {s.get('timeframe')}")
    print(f"  Symbols:    {', '.join(s.get('symbols', []))}")
    print()
    print(f"  💰 Equity:  ${s.get('equity', 0):,.2f}")
    print(f"  💵 Cash:    ${s.get('cash', 0):,.2f}")
    print(f"  📈 PnL:     ${s.get('pnl', 0):+,.2f} ({s.get('pnl_pct', 0):+.2f}%)")
    print(f"  📉 DD:      {s.get('drawdown_pct', 0):.2f}%")
    print(f"  🏔️  Peak:    ${s.get('peak_equity', 0):,.2f}")

    cb = "🔴 TRIGGERED" if s.get("circuit_breaker") else "🟢 OK"
    print(f"  🛑 Breaker: {cb} (threshold: {s.get('max_drawdown_threshold', 25)}%)")

    # Regimes
    regimes = s.get("regimes", {})
    if regimes:
        print(f"\n  Regimes:")
        for sym, reg in regimes.items():
            print(f"    {sym}: {reg}")

    # Open deals
    open_deals = s.get("open_deals", [])
    if open_deals:
        print(f"\n  Open Deals ({len(open_deals)}):")
        for d in open_deals:
            print(f"    #{d['deal_id']} {d['symbol']}: entry=${d['avg_entry']:.4f} now=${d['current_price']:.4f} SOs={d['so_count']} uPnL=${d['unrealized_pnl']:+.2f}")

    # Recent closed
    recent = s.get("closed_deals_recent", [])
    if recent:
        print(f"\n  Recent Closed ({len(recent)} of {s.get('closed_deals_count', 0)}):")
        for d in recent[-10:]:
            print(f"    #{d['deal_id']} {d['symbol']}: PnL=${d['pnl']:+.2f} SOs={d['so_count']} closed={d.get('close_time', '?')[:16]}")

    print("=" * 60)


if __name__ == "__main__":
    print_status()
