"""Scout with full SIWE auth."""
import sys
sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient

PRIVATE_KEY = "062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"

# Use create() for full auth flow
client = BasisClient.create(private_key=PRIVATE_KEY)
print(f"Authenticated. API key: {client.api_key[:12]}...")

print("\n=== ALL TOKENS (newest) ===\n")
tokens = client.api.get_tokens(sort="newest", limit=20)
token_list = tokens if isinstance(tokens, list) else tokens.get('tokens', tokens.get('data', []))
print(f"Got {len(token_list)} tokens")

for t in (token_list if isinstance(token_list, list) else []):
    if isinstance(t, dict):
        name = t.get('name', '?')
        symbol = t.get('symbol', '?')
        addr = t.get('address', t.get('tokenAddress', '?'))
        ttype = t.get('tokenType', t.get('type', '?'))
        price = t.get('price', t.get('currentPrice', '?'))
        floor_p = t.get('floorPrice', t.get('floor', '-'))
        mcap = t.get('marketCap', t.get('mcap', '?'))
        created = t.get('createdAt', t.get('created', '?'))
        print(f"  [{ttype}] {symbol} - {name}")
        print(f"    Addr: {addr}")
        print(f"    Price: {price} | Floor: {floor_p} | MCap: {mcap} | Created: {created}")
        print()
    else:
        print(f"  Raw: {t}")

# If tokens is a dict, dump keys to understand structure
if isinstance(tokens, dict) and not token_list:
    import json
    print("Response structure:", json.dumps({k: type(v).__name__ for k,v in tokens.items()}))
    # Show first 500 chars
    print(json.dumps(tokens, default=str)[:500])

print("\n=== PREDICTION MARKETS ===\n")
markets = client.api.get_tokens(is_prediction=True, sort="newest", limit=10)
market_list = markets if isinstance(markets, list) else markets.get('tokens', markets.get('data', []))
print(f"Got {len(market_list)} markets")

for m in (market_list if isinstance(market_list, list) else []):
    if isinstance(m, dict):
        name = m.get('name', '?')
        addr = m.get('address', m.get('tokenAddress', '?'))
        volume = m.get('volume', m.get('totalVolume', '?'))
        print(f"  {name} | Addr: {addr} | Vol: {volume}")
    else:
        print(f"  Raw: {m}")

if isinstance(markets, dict) and not market_list:
    import json
    print("Response structure:", json.dumps({k: type(v).__name__ for k,v in markets.items()}))
    print(json.dumps(markets, default=str)[:500])
