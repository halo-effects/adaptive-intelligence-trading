"""Find the AIDFI market address from the creation tx."""
import sys
sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient
from web3 import Web3

client = BasisClient.create(private_key="062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4")
WALLET = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"

# Check the market creation tx receipt
market_tx = "0x0a4c4889183302fdf632"  # too short, need full hash

# Let me check the execution log
import json
with open("stack-execution-log.json") as f:
    data = json.load(f)
print("Log:", json.dumps(data, indent=2))

# Let me look at the receipt from the market creation more carefully
# The market address might be extractable from events
# Let's try the API to find markets we created
try:
    tokens = client.api.get_tokens(sort="newest", limit=30)
    token_list = tokens if isinstance(tokens, list) else tokens.get("tokens", tokens.get("data", []))
    print(f"\nAll tokens ({len(token_list)}):")
    for t in token_list:
        if isinstance(t, dict):
            name = t.get("name", "?")
            addr = t.get("address", "?")
            is_pred = t.get("isPrediction", False)
            dev = t.get("dev", "?")
            created = t.get("createdAt", "?")
            ours = "*** OURS ***" if dev and dev.lower() == WALLET.lower() else ""
            print(f"  {'[PRED]' if is_pred else '[TOKEN]'} {name} | {addr[:16]}... | {ours} | {created}")
except Exception as e:
    print(f"API error: {e}")

# Also check factory tokens by creator
tokens_by_creator = client.factory.get_tokens_by_creator(WALLET)
print(f"\nFactory tokens by creator ({len(tokens_by_creator)}):")
for addr in tokens_by_creator:
    try:
        is_eco = client.factory.is_ecosystem_token(addr)
        # Check if prediction market
        try:
            md = client.prediction_markets.get_market_data(addr)
            market_name = md[4] if isinstance(md, (list, tuple)) else md.get("marketName", "?")
            print(f"  {addr} | ECO={is_eco} | PREDICTION: {market_name}")
        except:
            # Not a prediction market, check token type
            HM_ABI = [{"inputs":[],"name":"hybridMultiplier","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]
            c = client.web3.eth.contract(address=Web3.to_checksum_address(addr), abi=HM_ABI)
            try:
                hm = c.functions.hybridMultiplier().call()
                ttype = "Stable+" if hm == 100 else f"Floor+(hm={hm})"
                print(f"  {addr} | ECO={is_eco} | TOKEN: {ttype}")
            except:
                print(f"  {addr} | ECO={is_eco} | UNKNOWN")
    except Exception as e:
        print(f"  {addr} | ERROR: {e}")
