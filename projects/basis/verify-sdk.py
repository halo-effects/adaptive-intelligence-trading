"""Verify the new official SDK against the live site."""
from basis import BasisClient

PK = "062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"
c = BasisClient.create(private_key=PK)

print("=== NEW SDK ADDRESSES ===")
print(f"USDB: {c.usdb_address}")
print(f"STASIS: {c.main_token_address}")
print(f"Factory: {c.factory.factory_address}")

# Can we read TMPST from API?
print("\n=== API: TMPST ===")
result = c.api.get_token("0xC43DF80EFc3B29925BAbd744CD8AF28A0BE9AE3a")
d = result.get("data", result)
print(f"Name: {d.get('name')} | Symbol: {d.get('symbol')} | Multiplier: {d.get('multiplier')}")

# Can we read TMPST on-chain with the new factory?
print("\n=== On-chain: TMPST ===")
try:
    state = c.factory.get_token_state("0xC43DF80EFc3B29925BAbd744CD8AF28A0BE9AE3a")
    print(f"State: {state}")
except Exception as e:
    print(f"Error: {e}")

# Can we read FEDCUT prediction market?
print("\n=== On-chain: FEDCUT market ===")
try:
    md = c.prediction_markets.get_market_data("0xe13a8f12b5c1df2bfdaee169add44587dd7e2c06")
    print(f"Market name: {md[4]}")
    print(f"EndTime: {md[6]}")
    print(f"Resolved: {md[8]}")
    print(f"GeneralPot: {int(md[10])/10**18:.2f} USDB")
except Exception as e:
    print(f"Error: {e}")

# Check wallet balance with new USDB
print("\n=== Wallet Balances (new USDB) ===")
from web3 import Web3
WALLET = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"
erc20_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]

usdb_contract = c.web3.eth.contract(address=Web3.to_checksum_address(c.usdb_address), abi=erc20_abi)
usdb_bal = usdb_contract.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
print(f"USDB (new): {usdb_bal / 10**18:.4f}")

stasis_contract = c.web3.eth.contract(address=Web3.to_checksum_address(c.main_token_address), abi=erc20_abi)
stasis_bal = stasis_contract.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
print(f"STASIS (new): {stasis_bal / 10**18:.4f}")

bnb = c.web3.eth.get_balance(Web3.to_checksum_address(WALLET))
print(f"BNB: {Web3.from_wei(bnb, 'ether')}")
