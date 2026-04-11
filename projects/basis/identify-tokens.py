"""Identify all my factory tokens."""
import sys
sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient
from web3 import Web3

client = BasisClient.create(private_key="062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4")
WALLET = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"
USDB = "0x78dD776204aA7e06BaF488959a90142f0B3027CE"

HM_ABI = [{"inputs":[],"name":"hybridMultiplier","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]
NAME_ABI = [{"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"stateMutability":"view","type":"function"},
            {"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"stateMutability":"view","type":"function"}]

tokens = client.factory.get_tokens_by_creator(WALLET)
print(f"Factory tokens by creator: {len(tokens)}\n")

for addr in tokens:
    try:
        c = client.web3.eth.contract(address=Web3.to_checksum_address(addr), abi=NAME_ABI + HM_ABI)
        name = c.functions.name().call()
        symbol = c.functions.symbol().call()
        try:
            hm = c.functions.hybridMultiplier().call()
        except:
            hm = "N/A (prediction market)"
        
        # Check if prediction market
        try:
            md = client.prediction_markets.get_market_data(addr)
            market_name = md[4] if isinstance(md, (list, tuple)) else "?"
            resolved = md[8] if isinstance(md, (list, tuple)) else "?"
            end_time = md[6] if isinstance(md, (list, tuple)) else "?"
            print(f"  {addr}")
            print(f"    Name: {name} ({symbol}) | hm={hm}")
            print(f"    MARKET: {market_name} | resolved={resolved} | endTime={end_time}")
        except:
            usd = int(client.trading.get_usd_price(addr)) / 10**18
            print(f"  {addr}")
            print(f"    Name: {name} ({symbol}) | hm={hm} | price=${usd:.4f}")
        print()
    except Exception as e:
        print(f"  {addr}: ERROR - {e}\n")

# Also check USDB balance and loan count
usdb_bal = client.web3.eth.contract(
    address=Web3.to_checksum_address(USDB),
    abi=[{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
).functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
print(f"USDB: {usdb_bal/10**18:.4f}")
loans = client.loans.get_user_loan_count(WALLET)
print(f"Loans: {loans}")
