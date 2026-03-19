import sys
sys.path.insert(0, "sdk-python-v3")
from web3 import Web3

USDB = "0x78dD776204aA7e06BaF488959a90142f0B3027CE"
WALLET = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"

w3 = Web3(Web3.HTTPProvider("https://bsc-dataseed.binance.org/"))

abi = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "NORMAL_FAUCET_AMOUNT", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
]

usdb = w3.eth.contract(address=Web3.to_checksum_address(USDB), abi=abi)

print(f"Name: {usdb.functions.name().call()}")
print(f"Symbol: {usdb.functions.symbol().call()}")
print(f"Decimals: {usdb.functions.decimals().call()}")

raw_bal = usdb.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
print(f"Raw balance: {raw_bal}")

try:
    faucet_amt = usdb.functions.NORMAL_FAUCET_AMOUNT().call()
    print(f"Faucet amount: {faucet_amt}")
except:
    print("No NORMAL_FAUCET_AMOUNT function")

# Check tx receipt logs
tx_hash = "0x64c4515e67961e8c59be62f62f25ed749492a08f13aecc2b1c53056316fd9610"
receipt = w3.eth.get_transaction_receipt(tx_hash)
print(f"\nTX logs count: {len(receipt['logs'])}")
for log in receipt['logs']:
    print(f"  Log: address={log['address']}, topics={[t.hex() for t in log['topics']]}, data={log['data'].hex()[:100]}")
