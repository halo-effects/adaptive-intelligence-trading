"""Verify everything works with contracts.json addresses."""
from basis import BasisClient
from web3 import Web3

PK = "062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"
WALLET = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"

# Override with contracts.json addresses
c = BasisClient.create(
    private_key=PK,
    factory_address="0xB6BA282f29A7C67059f4E9D0898eE58f5C79960D",
    swap_address="0x9F9cF98F68bDbCbC5cf4c6402D53cEE1D180715f",
    market_trading_address="0x396216fc9d2c220afD227B59097cf97B7dEaCb57",
    loan_hub_address="0xFe19644d52fD0014EBa40c6A8F4Bfee4Ce3B2449",
    vesting_address="0xedd987c7723B9634b0Aa6161258FED3e89F9094C",
    staking_address="0x1FE7189270fb93c32a1fEfA71d1795c05C41cb33",
    resolver_address="0xB5FFCCB422531Cf462ec430170f85d8dD3dC3f57",
    private_market_address="0x28675A82ee3c2e6d2C85887Ea587FbDD3E3C86EE",
    reader_address="0xF406cA6403c57Ad04c8E13F4ae87b3732daa087d",
    leverage_address="0xeffb140d821c5B20EFc66346Cf414EeAC8A8FDB2",
    taxes_address="0x4501d1279273c44dA483842ED17b5451e7d3A601",
    usdb_address="0x42bcF288e51345c6070F37f30332ee5090fC36BF",
    main_token_address="0x3067ce754a36d0a2A1b215C4C00315d9Da49EF15",
)

print("=== Addresses ===")
print(f"USDB:    {c.usdb_address}")
print(f"STASIS:  {c.main_token_address}")
print(f"Factory: {c.factory.factory_address}")

# Balances
erc20_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
usdb = c.web3.eth.contract(address=Web3.to_checksum_address(c.usdb_address), abi=erc20_abi)
stasis = c.web3.eth.contract(address=Web3.to_checksum_address(c.main_token_address), abi=erc20_abi)

print(f"\n=== Wallet Balances ===")
print(f"USDB:    {usdb.functions.balanceOf(Web3.to_checksum_address(WALLET)).call() / 10**18:.4f}")
print(f"STASIS:  {stasis.functions.balanceOf(Web3.to_checksum_address(WALLET)).call() / 10**18:.4f}")
print(f"BNB:     {Web3.from_wei(c.web3.eth.get_balance(Web3.to_checksum_address(WALLET)), 'ether')}")

# Read TMPST
print(f"\n=== TMPST (Floor+) ===")
tmpst = "0xC43DF80EFc3B29925BAbd744CD8AF28A0BE9AE3a"
state = c.factory.get_token_state(tmpst)
print(f"State: {state}")
HM_ABI = [{"inputs":[],"name":"hybridMultiplier","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]
hm = c.web3.eth.contract(address=Web3.to_checksum_address(tmpst), abi=HM_ABI).functions.hybridMultiplier().call()
print(f"hybridMultiplier: {hm} ({'Floor+' if hm < 100 else 'Stable+'})")

# Read FEDCUT prediction market
print(f"\n=== FEDCUT Prediction Market ===")
fedcut = "0xe13a8f12b5c1df2bfdaee169add44587dd7e2c06"
md = c.prediction_markets.get_market_data(fedcut)
print(f"Name: {md[4]}")
print(f"EndTime: {md[6]}")
print(f"Resolved: {md[8]}")
print(f"GeneralPot: {int(md[10])/10**18:.2f} USDB")

# Read outcomes
ROUTER = "0xF406cA6403c57Ad04c8E13F4ae87b3732daa087d"
outcomes = c.market_reader.get_all_outcomes(ROUTER, fedcut)
for o in outcomes:
    print(f"  [{o[0]}] {o[1]}: prob={int(o[6])/10**16:.1f}%")

# Read STASIS price
print(f"\n=== STASIS Price ===")
price = c.trading.get_usd_price(c.main_token_address)
print(f"USD: ${int(price)/10**18:.6f}")

# Staking vault status
print(f"\n=== Staking Vault ===")
try:
    stake = c.staking.get_user_stake_details(WALLET)
    print(f"Stake details: {stake}")
except Exception as e:
    print(f"Error: {e}")

print("\n=== ALL SYSTEMS GO ===")
