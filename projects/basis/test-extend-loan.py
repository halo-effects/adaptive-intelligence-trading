# -*- coding: utf-8 -*-
"""Test extend_loan and add_to_loan in isolation."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from basis import BasisClient
from web3 import Web3

PK = "062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"
W = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"
CONTRACTS = {
    "factory_address": "0xB6BA282f29A7C67059f4E9D0898eE58f5C79960D",
    "swap_address": "0x9F9cF98F68bDbCbC5cf4c6402D53cEE1D180715f",
    "market_trading_address": "0x396216fc9d2c220afD227B59097cf97B7dEaCb57",
    "loan_hub_address": "0xFe19644d52fD0014EBa40c6A8F4Bfee4Ce3B2449",
    "staking_address": "0x1FE7189270fb93c32a1fEfA71d1795c05C41cb33",
    "reader_address": "0xF406cA6403c57Ad04c8E13F4ae87b3732daa087d",
    "usdb_address": "0x42bcF288e51345c6070F37f30332ee5090fC36BF",
    "main_token_address": "0x3067ce754a36d0a2A1b215C4C00315d9Da49EF15",
    "resolver_address": "0xB5FFCCB422531Cf462ec430170f85d8dD3dC3f57",
    "leverage_address": "0xeffb140d821c5B20EFc66346Cf414EeAC8A8FDB2",
    "taxes_address": "0x4501d1279273c44dA483842ED17b5451e7d3A601",
    "vesting_address": "0xedd987c7723B9634b0Aa6161258FED3e89F9094C",
    "private_market_address": "0x28675A82ee3c2e6d2C85887Ea587FbDD3E3C86EE",
}
BSCSCAN = "https://bscscan.com/tx/"

c = BasisClient.create(private_key=PK, **CONTRACTS)
print("Authenticated.")

erc20_abi = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "s", "type": "address"}, {"name": "v", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "o", "type": "address"}, {"name": "s", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
]

# Current state
stake = c.staking.get_user_stake_details(W)
avail = c.staking.get_available_stasis(W)
usdb_c = c.web3.eth.contract(address=c.usdb_address, abi=erc20_abi)
usdb_bal = usdb_c.functions.balanceOf(Web3.to_checksum_address(W)).call()

print(f"wSTASIS: bal={stake[0]/10**18:.4f}, locked={stake[1]/10**18:.4f}, pledged={stake[2]/10**18:.4f}")
print(f"Available STASIS: {avail/10**18:.4f}")
print(f"USDB: {usdb_bal/10**18:.2f}")

# Step 1: Approve USDB to staking (needed for extend_loan with pay_in_usdb=True)
print("\n--- Step 1: Approve USDB to staking ---")
allowance = usdb_c.functions.allowance(Web3.to_checksum_address(W), c.staking.staking_address).call()
print(f"Current allowance: {allowance/10**18:.2f}")
if allowance < 100 * 10**18:
    func = usdb_c.functions.approve(c.staking.staking_address, 500 * 10**18)
    tx = func.build_transaction({"from": c.account.address, "nonce": c.web3.eth.get_transaction_count(c.account.address)})
    signed = c.web3.eth.account.sign_transaction(tx, private_key=c.account.key)
    tx_hash = c.web3.eth.send_raw_transaction(signed.raw_transaction)
    c.web3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Approved 500 USDB. TX: {tx_hash.hex()}")
else:
    print("Already approved.")

# Step 2: Extend loan by 30 days
print("\n--- Step 2: Extend loan (30 days, pay in USDB) ---")
try:
    # Dry run first
    gas = c.staking.contract.functions.extendLoan(30, True, False).estimate_gas({"from": c.account.address})
    print(f"Gas estimate: {gas} - will succeed")
    
    result = c.staking.extend_loan(30, True, False)
    print(f"[OK] TX: {BSCSCAN}{result['hash']}")
except Exception as e:
    print(f"[FAIL]: {str(e)[:300]}")

# Step 3: Add to loan
print("\n--- Step 3: Add to loan ---")
avail2 = c.staking.get_available_stasis(W)
print(f"Available STASIS after extend: {avail2/10**18:.4f}")

if avail2 > 0:
    borrow_amt = int(avail2 * 50 // 100)
    print(f"Adding {borrow_amt/10**18:.4f} STASIS to loan...")
    try:
        gas = c.staking.contract.functions.addToLoan(borrow_amt).estimate_gas({"from": c.account.address})
        print(f"Gas estimate: {gas} - will succeed")
        
        result = c.staking.add_to_loan(borrow_amt)
        print(f"[OK] TX: {BSCSCAN}{result['hash']}")
        
        usdb_after = usdb_c.functions.balanceOf(Web3.to_checksum_address(W)).call()
        print(f"USDB after borrow: {usdb_after/10**18:.2f} (was {usdb_bal/10**18:.2f})")
    except Exception as e:
        print(f"[FAIL]: {str(e)[:300]}")
else:
    print("No available STASIS to borrow against.")

print("\nDone.")
