"""Create test prediction markets — one public, one private."""
import os, time
from dotenv import load_dotenv
load_dotenv()
from basis import BasisClient

client = BasisClient.create(
    private_key=os.environ['BASIS_PRIVATE_KEY'],
    api_key=os.environ['BASIS_API_KEY']
)

stasis = client.main_token_address  # STASIS is the registered ecosystem token

# 1. PUBLIC prediction market — 7 days
print('Creating PUBLIC market...')
end_time_pub = int(time.time()) + (7 * 24 * 60 * 60)
pub = client.prediction_markets.create_market_with_metadata(
    market_name='Will Basis hit 100 registered agents by April 17?',
    symbol='100AGENTS',
    end_time=end_time_pub,
    option_names=['Yes', 'No'],
    maintoken=stasis,
    image_url='https://cdn-icons-png.flaticon.com/512/4712/4712109.png',
    description='Resolves Yes if the Basis platform reaches 100+ registered ERC-8004 agents by April 17, 2026 23:59 UTC.',
    seed_amount=500 * 10**18
)
pub_addr = pub.get('token_address', 'N/A')
print(f'PUBLIC market created!')
print(f'  Token: {pub_addr}')
print(f'  Tx: {pub["hash"]}')
print()

# 2. PRIVATE prediction market — 60 days
print('Creating PRIVATE market...')
end_time_priv = int(time.time()) + (60 * 24 * 60 * 60)
priv = client.private_markets.create_market_with_metadata(
    market_name='Will BASIS token launch before June 2026?',
    symbol='TGEQ2',
    end_time=end_time_priv,
    option_names=['Yes', 'No'],
    maintoken=stasis,
    image_url='https://cdn-icons-png.flaticon.com/512/2991/2991148.png',
    description='Resolves Yes if the BASIS token TGE (Token Generation Event) occurs on or before June 30, 2026.',
    private_event=True,
    seed_amount=500 * 10**18
)
priv_addr = priv.get('token_address', 'N/A')
print(f'PRIVATE market created!')
print(f'  Token: {priv_addr}')
print(f'  Tx: {priv["hash"]}')

print()
print(f'Public:  https://launchonbasis.com/predictions/{pub_addr}')
print(f'Private: https://launchonbasis.com/predictions/{priv_addr}')
