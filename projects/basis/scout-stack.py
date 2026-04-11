"""Scout available tokens and markets for the Conservative Stack strategy."""
import sys, json
sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient
from web3 import Web3

# Read env for API key
import os
from dotenv import load_dotenv
load_dotenv("skill-scaffold/.env")

PRIVATE_KEY = "062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"
API_KEY = os.getenv("MOLTBOOK_API_KEY")  # might not be the right key

# Try with the basis API key from bsc_wallet.env
load_dotenv("bsc_wallet.env")
API_KEY = os.getenv("BASIS_API_KEY") or os.getenv("API_KEY")

client = BasisClient(private_key=PRIVATE_KEY, api_key=API_KEY)

# If no API key, try to authenticate and get one
if not client.api_key:
    print("No API key found, attempting SIWE auth...")
    try:
        client.authenticate()
        client.ensure_api_key()
        print(f"Got API key: {client.api_key[:12]}...")
    except Exception as e:
        print(f"Auth failed: {e}")

print("=== SCOUTING TOKENS ===\n")

# Get newest tokens (likely closest to floor)
try:
    tokens = client.api.get_tokens(sort="newest", limit=20)
    print(f"Found {len(tokens.get('tokens', []))} tokens\n")
    
    for t in tokens.get('tokens', []):
        name = t.get('name', '?')
        symbol = t.get('symbol', '?')
        addr = t.get('address', '?')
        token_type = t.get('tokenType', t.get('type', '?'))
        mcap = t.get('marketCap', t.get('mcap', '?'))
        price = t.get('price', '?')
        floor_price = t.get('floorPrice', t.get('floor', ''))
        created = t.get('createdAt', t.get('created', '?'))
        
        print(f"  {symbol} ({name})")
        print(f"    Type: {token_type} | Addr: {addr[:10]}...")
        print(f"    Price: {price} | Floor: {floor_price} | MCap: {mcap}")
        print(f"    Created: {created}")
        print()
except Exception as e:
    print(f"Token fetch error: {e}")

print("\n=== SCOUTING PREDICTION MARKETS ===\n")

try:
    markets = client.api.get_tokens(is_prediction=True, sort="newest", limit=10)
    print(f"Found {len(markets.get('tokens', []))} prediction markets\n")
    
    for m in markets.get('tokens', []):
        name = m.get('name', '?')
        symbol = m.get('symbol', '?')
        addr = m.get('address', '?')
        token_type = m.get('tokenType', m.get('type', '?'))
        volume = m.get('volume', m.get('totalVolume', '?'))
        created = m.get('createdAt', m.get('created', '?'))
        
        print(f"  {symbol} ({name})")
        print(f"    Type: {token_type} | Addr: {addr[:10]}...")
        print(f"    Volume: {volume}")
        print(f"    Created: {created}")
        print()
except Exception as e:
    print(f"Market fetch error: {e}")

# Also check STASIS price and wSTASIS details
print("\n=== STASIS / wSTASIS STATUS ===\n")
try:
    stasis_price = client.trading.get_usd_price(client.main_token_address)
    print(f"STASIS USD price: {int(stasis_price) / 10**18:.6f}")
except Exception as e:
    print(f"Price check error: {e}")

try:
    w = Web3.to_checksum_address("0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2")
    details = client.staking.get_user_stake_details(w)
    print(f"Stake details: wSTASIS={details[0]/10**18:.4f}, locked={details[1]/10**18:.4f}, pledged={details[2]/10**18:.4f}, available={details[3]/10**18:.4f}")
except Exception as e:
    print(f"Stake details error: {e}")
