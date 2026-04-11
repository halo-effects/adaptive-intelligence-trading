"""Properly read token info using the API + on-chain methods from the docs."""
import sys, json
sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient
from web3 import Web3

client = BasisClient.create(private_key="062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4")
WALLET = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"

# 1. List tokens via API (newest non-prediction)
print("=== API: Newest Tokens ===\n")
result = client.api.get_tokens(sort="newest", limit=10)
tokens = result.get("data", result.get("tokens", []))
for t in tokens:
    print(f"  [{t.get('symbol')}] {t.get('name')}")
    print(f"    addr: {t.get('address')}")
    print(f"    multiplier: {t.get('multiplier')} | isPred: {t.get('isPrediction')}")
    print(f"    description: {str(t.get('description', ''))[:60]}")
    print(f"    image: {t.get('image', 'none')}")
    print(f"    dev: {t.get('dev', '?')}")
    print()

# 2. Get full details for one specific token
print("=== API: Single Token Detail (TMPST) ===\n")
tmpst = client.api.get_token("0xC43DF80EFc3B29925BAbd744CD8AF28A0BE9AE3a")
tmpst_data = tmpst.get("data", tmpst)
print(json.dumps(tmpst_data, indent=2, default=str)[:800])

# 3. On-chain: getTokenState for TMPST
print("\n\n=== On-chain: getTokenState (TMPST) ===\n")
state = client.factory.get_token_state("0xC43DF80EFc3B29925BAbd744CD8AF28A0BE9AE3a")
print(f"  frozen: {state[0]}")
print(f"  hasBonded: {state[1]}")
print(f"  totalSupply: {state[2] / 10**18:.4f}")
print(f"  usdPrice: {state[3] / 10**18:.6f}")

# 4. On-chain: hybridMultiplier
HM_ABI = [{"inputs":[],"name":"hybridMultiplier","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]
c = client.web3.eth.contract(address=Web3.to_checksum_address("0xC43DF80EFc3B29925BAbd744CD8AF28A0BE9AE3a"), abi=HM_ABI)
hm = c.functions.hybridMultiplier().call()
print(f"  hybridMultiplier: {hm} ({'Floor+' if hm < 100 else 'Stable+'})")

# 5. On-chain: trading price methods
usd_price = client.trading.get_usd_price("0xC43DF80EFc3B29925BAbd744CD8AF28A0BE9AE3a")
token_price = client.trading.get_token_price("0xC43DF80EFc3B29925BAbd744CD8AF28A0BE9AE3a")
print(f"  trading.getUSDPrice: {int(usd_price) / 10**18:.6f}")
print(f"  trading.getTokenPrice: {int(token_price) / 10**18:.6f}")

# 6. Prediction market: full read
print("\n=== Prediction Market: FEDCUT ===\n")
ROUTER = "0x69e4b11346f928f29Affe6B52a8e3Ebd115DE7a6"
fedcut = "0xe13a8f12b5c1df2bfdaee169add44587dd7e2c06"

# API detail
fedcut_api = client.api.get_token(fedcut)
fedcut_data = fedcut_api.get("data", fedcut_api)
print(f"  Name: {fedcut_data.get('name')}")
print(f"  predictionStatus: {fedcut_data.get('predictionStatus')}")
print(f"  predictionOptions: {fedcut_data.get('predictionOptions')}")

# On-chain market data
md = client.prediction_markets.get_market_data(fedcut)
print(f"  marketName: {md[4]}")
print(f"  endTime: {md[6]}")
print(f"  resolved: {md[8]}")
print(f"  generalPot: {int(md[10])/10**18:.2f} USDB")

# On-chain outcomes via MarketReader
outcomes = client.market_reader.get_all_outcomes(ROUTER, fedcut)
for o in outcomes:
    oid = o[0]
    name = o[1]
    prob = int(o[6]) / 10**16
    price = int(o[5]) / 10**18
    shares = int(o[4]) / 10**18
    print(f"  [{oid}] {name}: prob={prob:.1f}%, price=${price:.4f}, shares={shares:.2f}")

print("\n=== Summary: How to read token info ===")
print("API: client.api.get_tokens() for list, client.api.get_token(addr) for details")
print("On-chain: client.factory.get_token_state(addr) for state")
print("On-chain: hybridMultiplier() view function for type (1-90=Floor+, 100=Stable+)")
print("On-chain: client.trading.get_usd_price(addr) for price")
print("Markets: client.prediction_markets.get_market_data(addr) for market state")
print("Markets: client.market_reader.get_all_outcomes(ROUTER, addr) for outcome odds")
