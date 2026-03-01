"""Quick test for CFGI client — pulls current scores for ETH, SOL, BTC."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cfgi_client import CFGIClient

def main():
    api_key = os.environ.get("CFGI_API_KEY")
    if not api_key:
        print("ERROR: Set CFGI_API_KEY environment variable")
        sys.exit(1)

    client = CFGIClient(api_key)
    tokens = ["BTC", "ETH", "SOL"]

    # Pull with ALL fields for full picture
    print("Fetching current CFGI scores (all fields)...")
    print(f"Estimated credits: {client.estimate_credits(tokens=3, fields=1, rows=1)}")

    result = client.get_current(tokens, period=4, fields="cfgi")

    for token, data in result.items():
        print(f"\n{'='*40}")
        print(f"  {token}")
        print(f"{'='*40}")
        if isinstance(data, dict):
            for k, v in data.items():
                print(f"  {k:>12}: {v}")
        else:
            print(f"  {data}")

    print(f"\n--- Credits remaining: {client.credits_remaining()} ---")

if __name__ == "__main__":
    main()
