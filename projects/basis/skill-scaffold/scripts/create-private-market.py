"""Create a private prediction market."""
import os, time
from dotenv import load_dotenv
load_dotenv()
from basis import BasisClient

client = BasisClient.create(
    private_key=os.environ['BASIS_PRIVATE_KEY'],
    api_key=os.environ['BASIS_API_KEY']
)

stasis = client.main_token_address
end_time = int(time.time()) + (60 * 24 * 60 * 60)

print(f"Creating PRIVATE market with 1 STASIS seed...")
priv = client.private_markets.create_market_with_metadata(
    market_name='Will BASIS token launch before June 2026?',
    symbol='TGEQ2',
    end_time=end_time,
    option_names=['Yes', 'No'],
    maintoken=stasis,
    image_url='https://cdn-icons-png.flaticon.com/512/2991/2991148.png',
    description='Resolves Yes if the BASIS token TGE (Token Generation Event) occurs on or before June 30, 2026.',
    private_event=True,
    seed_amount=20 * 10**18
)
priv_addr = priv.get('token_address', priv.get('market_token_address', 'N/A'))
print(f"PRIVATE market created!")
print(f"  Token: {priv_addr}")
print(f"  Tx: {priv['hash']}")
print(f"  URL: https://launchonbasis.com/predictions/{priv_addr}")
