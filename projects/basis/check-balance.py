import sys, os
sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient
from web3 import Web3

client = BasisClient()
w = Web3.to_checksum_address("0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2")

# BNB
bnb = client.web3.eth.get_balance(w)
print(f"BNB balance: {Web3.from_wei(bnb, 'ether')} BNB")

# USDB
USDB = "0x78dD776204aA7e06BaF488959a90142f0B3027CE"
erc20_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
usdb_contract = client.web3.eth.contract(address=Web3.to_checksum_address(USDB), abi=erc20_abi)
usdb_bal = usdb_contract.functions.balanceOf(w).call()
print(f"USDB balance: {usdb_bal / 10**18} USDB")

# STASIS
MAIN = "0x76ACb5F98A422995a801008c8b7b28dBC23946Ff"
main_contract = client.web3.eth.contract(address=Web3.to_checksum_address(MAIN), abi=erc20_abi)
main_bal = main_contract.functions.balanceOf(w).call()
print(f"STASIS balance: {main_bal / 10**18} STASIS")
