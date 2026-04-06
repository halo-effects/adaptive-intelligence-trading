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

# Wrap and lock STASIS first
stasis_c = client.web3.eth.contract(address=Web3.to_checksum_address(client.main_token_address), abi=client.trading.erc20_abi)
stasis_bal = stasis_c.functions.balanceOf(wallet).call()
print('STASIS:', stasis_bal / 1e18)

staking_addr = client.staking.contract.address
wstasis = client.web3.eth.contract(address=Web3.to_checksum_address(staking_addr), abi=client.trading.erc20_abi)
wstasis_bal = wstasis.functions.balanceOf(wallet).call()
print('wSTASIS:', wstasis_bal / 1e18)

# Wrap remaining STASIS
if stasis_bal > 0:
    print('Wrapping STASIS...')
    result = client.staking.buy(stasis_bal)
    print('wrap tx:', result.get('hash', '?'))

wstasis_bal = wstasis.functions.balanceOf(wallet).call()
print('wSTASIS after wrap:', wstasis_bal / 1e18)

# Lock
if wstasis_bal > 0:
    print('Locking wSTASIS...')
    result = client.staking.lock(wstasis_bal)
    print('lock tx:', result.get('hash', '?'))

details = client.staking.get_user_stake_details(wallet)
print('stake details:', json.dumps(details, default=str))

# Borrow 5 USDB for 10 days
print()
print('Borrowing 5 USDB for 10 days...')
try:
    result = client.staking.borrow(5 * 10**18, 10)
    print('borrow tx:', result.get('hash', '?'))
    
    count = client.loans.get_user_loan_count(wallet)
    print('loan count:', count)
    if count > 0:
        loan = client.loans.get_user_loan_details(wallet, count - 1)
        print('loan details:', json.dumps(loan, default=str)[:400])
except Exception as e:
    print('borrow ERROR:', e)

print()
print('DONE')
