#!/usr/bin/env python3
"""
V14 Incident Viewer — CLI tool for reviewing losing trade incidents.

Usage:
    python -m trading.spot.incident_viewer [--dir PATH] [--coin HBAR] [--type GRID_EXHAUSTION] [--severity HIGH]
"""

import argparse
import json
import sys
from pathlib import Path
from collections import Counter


DEFAULT_DIR = Path(__file__).resolve().parent / "paper" / "v14" / "incidents"


def load_incidents(directory: Path, coin: str = None, classification: str = None, severity: str = None):
    """Load and optionally filter incident JSON files."""
    if not directory.exists():
        print(f"No incidents directory: {directory}")
        return []

    incidents = []
    for f in sorted(directory.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            # Apply filters
            if coin and coin.upper() not in data.get("trade", {}).get("symbol", "").upper():
                continue
            if classification and data.get("classification", "").upper() != classification.upper():
                continue
            if severity and data.get("severity", "").upper() != severity.upper():
                continue
            incidents.append(data)
        except Exception as e:
            print(f"Warning: failed to read {f.name}: {e}", file=sys.stderr)

    return incidents


def print_summary(incidents: list):
    """Print a summary table of incidents."""
    if not incidents:
        print("No incidents found.")
        return

    # Header
    print(f"\n{'Date':<20} {'Coin':<12} {'Type':<20} {'Loss':>10} {'Sev':>6} {'Layers':>7} {'Hours':>7}")
    print("-" * 85)

    total_loss = 0.0
    for inc in incidents:
        trade = inc.get("trade", {})
        ts = inc.get("timestamp", "")[:16]
        symbol = trade.get("symbol", "?")
        coin = symbol.split("/")[0] if "/" in symbol else symbol
        classification = inc.get("classification", "?")
        pnl = trade.get("pnl", 0)
        severity = inc.get("severity", "?")
        layers = trade.get("layers", 0)
        hours = trade.get("duration_h", 0)
        total_loss += pnl

        print(f"{ts:<20} {coin:<12} {classification:<20} ${pnl:>9.2f} {severity:>6} {layers:>5}L {hours:>6.1f}h")

    print("-" * 85)
    print(f"{'TOTAL':<20} {len(incidents)} incidents{' ' * 21} ${total_loss:>9.2f}")

    # Aggregates
    print(f"\n--- Aggregate Stats ---")
    type_counts = Counter(inc.get("classification", "?") for inc in incidents)
    print(f"By type:     {dict(type_counts)}")

    coin_losses = {}
    for inc in incidents:
        sym = inc.get("trade", {}).get("symbol", "?")
        coin = sym.split("/")[0] if "/" in sym else sym
        coin_losses[coin] = coin_losses.get(coin, 0) + inc.get("trade", {}).get("pnl", 0)
    worst_coin = min(coin_losses, key=coin_losses.get) if coin_losses else "N/A"
    print(f"By coin:     {', '.join(f'{c}: ${v:.2f}' for c, v in sorted(coin_losses.items(), key=lambda x: x[1]))}")
    print(f"Worst coin:  {worst_coin} (${coin_losses.get(worst_coin, 0):.2f})")

    sev_counts = Counter(inc.get("severity", "?") for inc in incidents)
    print(f"By severity: {dict(sev_counts)}")
    print(f"Total loss:  ${total_loss:.2f}")


def main():
    parser = argparse.ArgumentParser(description="V14 Incident Report Viewer")
    parser.add_argument("--dir", type=str, default=str(DEFAULT_DIR), help="Incidents directory")
    parser.add_argument("--coin", type=str, default=None, help="Filter by coin (e.g. HBAR)")
    parser.add_argument("--type", type=str, default=None, help="Filter by classification")
    parser.add_argument("--severity", type=str, default=None, help="Filter by severity (LOW/MEDIUM/HIGH)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    incidents = load_incidents(Path(args.dir), args.coin, args.type, args.severity)

    if args.json:
        print(json.dumps(incidents, indent=2))
    else:
        print_summary(incidents)


if __name__ == "__main__":
    main()
