"""V12f Production Coin Scanner — scans all CFGI coins directly.

No T1 pre-filter. All 44 CFGI coins go through V12f backtest.
Candle data read from SQLite DB, CFGI from cached history.

Standalone: python -m trading.run_scanner [--current ASTER/USDT]
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from trading.coin_scanner_t2_v12f import run_full_scan

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="V12f Production Coin Scanner")
    parser.add_argument("--current", default="ASTER/USDT", help="Current trading coin")
    parser.add_argument("--threshold", type=float, default=0.20, help="Rotation threshold")
    args = parser.parse_args()
    run_full_scan(current_coin=args.current, rotation_threshold=args.threshold)
