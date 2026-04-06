import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from dotenv import load_dotenv
import os, json
load_dotenv()
from basis import BasisClient
from web3 import Web3

pk = os.getenv('BASIS_PRIVATE_KEY')
api_key = os.getenv('BASIS_API_KEY')
client = BasisClient.create(private_key=pk, api_key=api_key)
wallet = client.account.address

# Check wSTASIS balance
staking_addr = client.staking.contract.address
wstasis = client.web3.eth.contract(address=Web3.to_checksum_address(staking_addr), abi=client.trading.erc20_abi)
wstasis_bal = wstasis.functions.balanceOf(wallet).call()
print('wSTASIS balance:', wstasis_bal / 1e18)

stasis_c = client.web3.eth.contract(address=Web3.to_checksum_address(client.main_token_address), abi=client.trading.erc20_abi)
stasis_bal = stasis_c.functions.balanceOf(wallet).call()
print('STASIS balance:', stasis_bal / 1e18)

# Lock wSTASIS
print('Locking wSTASIS...')
try:
    result = client.staking.lock(wstasis_bal)
    h = result.get('hash', 'no hash')
    print('lock tx:', h)
    details = client.staking.get_user_stake_details(wallet)
    print('stake details:', json.dumps(details, default=str))
except Exception as e:
    print('lock ERROR:', e)

# Borrow
print()
print('Borrowing 5 USDB for 7 days...')
try:
    result = client.staking.borrow(5 * 10**18, 7)
    h = result.get('hash', 'no hash')
    print('borrow tx:', h)
    count = client.loans.get_user_loan_count(wallet)
    print('loan count:', count)
    if count > 0:
        loan = client.loans.get_user_loan_details(wallet, count - 1)
        print('loan:', json.dumps(loan, default=str)[:400])
except Exception as e:
    print('borrow ERROR:', e)

# Repay
print()
print('Repaying loan...')
try:
    count = client.loans.get_user_loan_count(wallet)
    if count > 0:
        result = client.staking.repay(count - 1)
        h = result.get('hash', 'no hash')
        print('repay tx:', h)
except Exception as e:
    print('repay ERROR:', e)

# Unlock
print()
print('Unlocking...')
try:
    result = client.staking.unlock(wstasis_bal)
    h = result.get('hash', 'no hash')
    print('unlock tx:', h)
except Exception as e:
    print('unlock ERROR:', e)

print()
print('DONE')
