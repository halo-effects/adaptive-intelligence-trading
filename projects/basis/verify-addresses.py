"""Verify which contract addresses the SDK is actually using."""
from basis import BasisClient
from web3 import Web3

PK = "062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"
WALLET = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"

# Create with full auth
c = BasisClient.create(private_key=PK)

print("=== SDK Addresses After create() ===")
print(f"USDB:           {c.usdb_address}")
print(f"STASIS:         {c.main_token_address}")
print(f"Factory:        {c.factory.factory_address}")
print(f"MarketTrading:  {c.prediction_markets.market_trading_address}")
print(f"LoanHub:        {c.loans.loan_hub_address}")
print(f"Staking:        {c.staking.staking_address}")
print(f"Swap:           {c.trading.swap_address}")

# Compare with contracts.json
import requests
contracts = requests.get("https://launchonbasis.com/contracts.json").json()
print(f"\n=== contracts.json ===")
for k, v in contracts.items():
    if k not in ("chain", "chainId"):
        print(f"{k:20s}: {v}")

# Check balances on BOTH USDB addresses
erc20_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]

print(f"\n=== Balances ===")
# SDK USDB
sdk_usdb = c.web3.eth.contract(address=Web3.to_checksum_address(c.usdb_address), abi=erc20_abi)
bal1 = sdk_usdb.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
print(f"SDK USDB ({c.usdb_address[:10]}...): {bal1/10**18:.4f}")

# contracts.json USDB
cj_usdb = c.web3.eth.contract(address=Web3.to_checksum_address(contracts["usdb"]), abi=erc20_abi)
bal2 = cj_usdb.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
print(f"CJ  USDB ({contracts['usdb'][:10]}...): {bal2/10**18:.4f}")

# Test: can we read FEDCUT on the contracts.json MarketTrading?
print(f"\n=== FEDCUT on contracts.json MarketTrading ===")
from basis.modules.prediction_markets import PredictionMarketsModule
pm2 = PredictionMarketsModule(c, contracts["marketTrading"])
try:
    md = pm2.get_market_data("0xe13a8f12b5c1df2bfdaee169add44587dd7e2c06")
    print(f"Name: {md[4]}")
    print(f"EndTime: {md[6]}")
    print(f"GeneralPot: {int(md[10])/10**18:.2f}")
except Exception as e:
    print(f"Error: {e}")
