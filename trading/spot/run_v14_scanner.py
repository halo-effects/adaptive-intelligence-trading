"""
Runner for V13 Coin Scanner.
Usage: python -u -m trading.spot.run_v14_scanner
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path

# Ensure workspace root is on path
workspace = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(workspace))

from trading.spot.coin_scanner import run_scanner, print_summary, ALL_TOKENS


def main():
    # Parse args: optionally pass coin names to test subset
    coins = None
    if len(sys.argv) > 1:
        subset = [c.upper() for c in sys.argv[1:]]
        coins = {c: ALL_TOKENS[c] for c in subset if c in ALL_TOKENS}
        if not coins:
            print(f"No valid coins in: {sys.argv[1:]}")
            print(f"Valid: {', '.join(sorted(ALL_TOKENS.keys()))}")
            sys.exit(1)
        print(f"Running scanner on subset: {list(coins.keys())}")

    result = run_scanner(tokens=coins)
    print_summary(result)


if __name__ == '__main__':
    main()
