"""Test create_token_with_metadata — Sebastian the lobster."""
import sys, os, json, traceback
sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient

PRIVATE_KEY = "0x062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"

print("Creating Sebastian token with metadata...")

client = BasisClient.create(private_key=PRIVATE_KEY)
print(f"Wallet: {client.account.address}")

try:
    result = client.factory.create_token_with_metadata(
        symbol="SEBASTIAN",
        name="Under Da Sea",
        hybrid_multiplier=50,
        start_lp=1000,
        description="The crab who should have been a lobster. SDK test token #2, now with proper metadata and a face. 🦀🦞",
        image_url="https://miro.medium.com/1*nY2ZBYr56BjQ0242GnVH-Q.jpeg",
        website="https://launchonbasis.com",
        telegram="https://t.me/basis_production",
        twitterx="https://x.com/LaunchOnBasis",
    )
    print(f"PASS!")
    print(f"TX: {result.get('hash', 'unknown')}")
    print(f"Token: {result.get('token_address', 'unknown')}")
    print(f"Image: {result.get('image_url', 'unknown')}")
    print(f"Metadata: {json.dumps(result.get('metadata', {}), indent=2)}")
except Exception as e:
    print(f"FAIL: {e}")
    traceback.print_exc()
