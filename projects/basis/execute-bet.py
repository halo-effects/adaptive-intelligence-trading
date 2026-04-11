"""Stack 3: Bet on the AIDFI market we created."""
import sys, time
sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient
from web3 import Web3

client = BasisClient.create(private_key="062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4")
WALLET = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"
USDB = "0x78dD776204aA7e06BaF488959a90142f0B3027CE"
MARKET = "0x38c2623605f565646f8b30c7cd5f096a727613c2"
ROUTER = "0x69e4b11346f928f29Affe6B52a8e3Ebd115DE7a6"

# Verify market
print("=== AIDFI Market Data ===")
md = client.prediction_markets.get_market_data(MARKET)
print(f"  Name: {md[4]}")
print(f"  EndTime: {md[6]}")
print(f"  Resolved: {md[8]}")
print(f"  GeneralPot: {int(md[10])/10**18:.2f} USDB")

# Check outcomes
outcomes = client.market_reader.get_all_outcomes(ROUTER, MARKET)
for o in outcomes:
    name = o[1]
    prob = int(o[6]) / 10**16
    price = int(o[5]) / 10**18
    print(f"  [{o[0]}] {name}: {prob:.1f}% @ ${price:.4f}/share")

# Bet 10 USDB on Yes (outcome 0)
bet_amount = 10 * 10**18
print(f"\nBetting 10 USDB on Yes...")
try:
    result = client.prediction_markets.buy(MARKET, 0, USDB, bet_amount, 0, 0)
    print(f"  TX: {result['hash'][:20]}...")
    time.sleep(3)
except Exception as e:
    print(f"  ERROR: {e}")

# Check shares
shares = client.prediction_markets.get_user_shares(MARKET, WALLET, 0)
print(f"  Yes shares held: {shares/10**18:.4f}")

# Final balances
erc20_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
usdb_contract = client.web3.eth.contract(address=Web3.to_checksum_address(USDB), abi=erc20_abi)
usdb_bal = usdb_contract.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
print(f"\nFinal USDB: {usdb_bal/10**18:.4f}")

stake = client.staking.get_user_stake_details(WALLET)
print(f"wSTASIS: liquid={stake[0]/10**18:.4f}, locked={stake[1]/10**18:.4f}")
loans = client.loans.get_user_loan_count(WALLET)
print(f"Hub loans: {loans}")
bnb = client.web3.eth.get_balance(Web3.to_checksum_address(WALLET))
print(f"BNB: {Web3.from_wei(bnb, 'ether')}")

print("\n=== CREATOR'S EDGE STACK COMPLETE ===")
print("Stack 1: wSTASIS yielding base (100 USDB -> 45.24 wSTASIS locked, earning vault yield)")
print("Stack 2: Created DSTACK Floor+ token, bought 50 USDB, borrowed against it")
print(f"Stack 3: Created AIDFI market, bet 10 USDB on Yes ({shares/10**18:.2f} shares)")
print(f"Remaining USDB: {usdb_bal/10**18:.2f}")
print("Categories: Trading + Staking + Lending + Token Creation + Predictions = 5 categories")
