"""Claim 1000 USDB from the faucet."""
import sys, os
sys.path.insert(0, "sdk-python-v3")
from web3 import Web3

USDB = "0x78dD776204aA7e06BaF488959a90142f0B3027CE"
WALLET = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"
PRIVATE_KEY = "062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"

w3 = Web3(Web3.HTTPProvider("https://bsc-dataseed.binance.org/"))
account = w3.eth.account.from_key(PRIVATE_KEY)

# Faucet ABI - just the faucet() function
faucet_abi = [
    {"inputs": [], "name": "faucet", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"}
]

usdb = w3.eth.contract(address=Web3.to_checksum_address(USDB), abi=faucet_abi)

# Check balance before
bal_before = usdb.functions.balanceOf(account.address).call()
print(f"USDB balance before: {bal_before / 10**18}")

# Call faucet
print("Calling faucet()...")
tx = usdb.functions.faucet().build_transaction({
    "from": account.address,
    "nonce": w3.eth.get_transaction_count(account.address),
    "gas": 100000,
    "gasPrice": w3.eth.gas_price,
})
signed = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f"TX sent: {tx_hash.hex()}")

receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
print(f"Status: {'SUCCESS' if receipt['status'] == 1 else 'FAILED'}")
print(f"Gas used: {receipt['gasUsed']}")

# Check balance after
bal_after = usdb.functions.balanceOf(account.address).call()
print(f"USDB balance after: {bal_after / 10**18}")
