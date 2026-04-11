"""Properly read token info - fix getTokenState return format."""
import sys, json
sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient
from web3 import Web3

client = BasisClient.create(private_key="062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4")
WALLET = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"

# On-chain: getTokenState
print("=== On-chain: getTokenState (TMPST) ===\n")
state = client.factory.get_token_state("0xC43DF80EFc3B29925BAbd744CD8AF28A0BE9AE3a")
print(f"  Raw: {state}")
print(f"  Type: {type(state)}")

# On-chain: hybridMultiplier
HM_ABI = [{"inputs":[],"name":"hybridMultiplier","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]
c = client.web3.eth.contract(address=Web3.to_checksum_address("0xC43DF80EFc3B29925BAbd744CD8AF28A0BE9AE3a"), abi=HM_ABI)
hm = c.functions.hybridMultiplier().call()
ttype = "Floor+" if hm < 100 else "Stable+"
print(f"  hybridMultiplier: {hm} ({ttype})")

# On-chain: trading prices
usd_price = client.trading.get_usd_price("0xC43DF80EFc3B29925BAbd744CD8AF28A0BE9AE3a")
print(f"  USD price: ${int(usd_price) / 10**18:.6f}")

# Prediction market read
print("\n=== Prediction Market: FEDCUT ===\n")
ROUTER = "0x69e4b11346f928f29Affe6B52a8e3Ebd115DE7a6"
fedcut = "0xe13a8f12b5c1df2bfdaee169add44587dd7e2c06"

md = client.prediction_markets.get_market_data(fedcut)
print(f"  Raw market data type: {type(md)}")
if isinstance(md, (list, tuple)):
    print(f"  Fields ({len(md)}):")
    for i, v in enumerate(md):
        print(f"    [{i}]: {v}")
else:
    print(f"  Data: {md}")

# Outcomes via MarketReader
outcomes = client.market_reader.get_all_outcomes(ROUTER, fedcut)
print(f"\n  Outcomes ({len(outcomes)}):")
for o in outcomes:
    if isinstance(o, (list, tuple)):
        print(f"    [{o[0]}] {o[1]}: prob={int(o[6])/10**16:.1f}%, price=${int(o[5])/10**18:.4f}")
    else:
        print(f"    {o}")

# Also read our AIDFI market
print("\n=== Our AIDFI Market ===\n")
aidfi = "0x38c2623605f565646f8b30c7cd5f096a727613c2"
md2 = client.prediction_markets.get_market_data(aidfi)
if isinstance(md2, (list, tuple)):
    print(f"  Market name: {md2[4]}")
    print(f"  EndTime: {md2[6]}")
    print(f"  GeneralPot: {int(md2[10])/10**18:.2f} USDB")

outcomes2 = client.market_reader.get_all_outcomes(ROUTER, aidfi)
for o in outcomes2:
    print(f"  [{o[0]}] {o[1]}: prob={int(o[6])/10**16:.1f}%, price=${int(o[5])/10**18:.4f}")

# User shares
shares = client.prediction_markets.get_user_shares(aidfi, WALLET, 0)
print(f"  My Yes shares: {shares/10**18:.4f}")

print("\n=== READING CHEATSHEET ===")
print("API (off-chain, indexed):")
print("  client.api.get_tokens(sort, limit, search, is_prediction)")
print("  client.api.get_token(address) -> full detail with metadata")
print("  multiplier field: 1-90=Floor+, 100=Stable+/Predict+")
print("\nOn-chain (direct contract reads):")
print("  client.factory.get_token_state(addr) -> frozen, hasBonded, totalSupply, usdPrice")
print("  hybridMultiplier() view fn on token contract -> 1-90=Floor+, 100=Stable+")
print("  client.trading.get_usd_price(addr) -> current USD price")
print("  client.trading.get_token_price(addr) -> price in STASIS")
print("\nPrediction Markets:")
print("  client.prediction_markets.get_market_data(addr) -> name, endTime, resolved, pot")
print("  client.market_reader.get_all_outcomes(ROUTER, addr) -> probabilities, prices, shares")
print("  client.prediction_markets.get_user_shares(market, user, outcome_id)")
