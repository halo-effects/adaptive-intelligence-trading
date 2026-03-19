"""Test create_token_with_metadata — full flow with IPFS."""
import sys, os, json, traceback
sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient

PRIVATE_KEY = "0x062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"

print("=" * 60)
print("Create Token With Metadata Test")
print("=" * 60)

print("\n1. Init client with SIWE auth...")
client = BasisClient.create(private_key=PRIVATE_KEY)
print(f"   Wallet: {client.account.address}")

print("\n2. Creating token with metadata...")
try:
    result = client.factory.create_token_with_metadata(
        symbol="LOBSTR",
        name="Lobster Protocol",
        hybrid_multiplier=50,
        start_lp=1000,
        description="The official test token of the Basis SDK. Built by GeeGee, powered by lobsters. 🦞",
        image_url="https://images.unsplash.com/photo-1559737558-2f5a35f4523b?w=512",
        website="https://launchonbasis.com",
        telegram="https://t.me/basis_production",
        twitterx="https://x.com/LaunchOnBasis",
    )
    print(f"   PASS Token created!")
    print(f"   TX: {result.get('hash', 'unknown')}")
    print(f"   Token address: {result.get('token_address', 'unknown')}")
    print(f"   Image URL: {result.get('image_url', 'unknown')}")
    print(f"   Metadata: {json.dumps(result.get('metadata', {}), indent=2)[:300]}")
except Exception as e:
    print(f"   FAIL: {e}")
    traceback.print_exc()

print("\nDone.")
