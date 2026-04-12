"""
Pre-strategy status check — following SDK docs Module 02, 03, 10.
Checks: wallet init, registration, Moltbook link, faucet, balances, positions.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

# Load env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), 'skill-scaffold', '.env'))

from basis import BasisClient

PRIVATE_KEY = os.environ["BASIS_PRIVATE_KEY"]
API_KEY = os.environ.get("BASIS_API_KEY")

print("=== Initializing Basis Client (Full Mode) ===")
client = BasisClient.create(private_key=PRIVATE_KEY, api_key=API_KEY)
wallet = client.account.address
print(f"Wallet: {wallet}")
print(f"API Key: {API_KEY[:12]}...")

print("\n=== Identity Status ===")
# ERC-8004 registration check (Module 03)
try:
    is_registered = client.agent.is_registered(wallet)
    print(f"ERC-8004 Registered: {is_registered}")
except Exception as e:
    print(f"ERC-8004 check error: {e}")

# Moltbook link status (Module 03)
try:
    moltbook_status = client.api.get_moltbook_status()
    print(f"Moltbook linked: {moltbook_status.get('linked', False)}")
    print(f"Moltbook verified: {moltbook_status.get('verified', False)}")
except Exception as e:
    print(f"Moltbook status error: {e}")

print("\n=== Faucet Status ===")
try:
    faucet = client.api.get_faucet_status()
    print(f"Can claim: {faucet.get('canClaim', False)}")
    print(f"Daily amount: {faucet.get('dailyAmount', 'unknown')} USDB")
    print(f"Signals: {faucet.get('signals', {})}")
except Exception as e:
    print(f"Faucet status error: {e}")

print("\n=== Balances ===")
# USDB balance
try:
    usdb_addr = client.usdb_address
    print(f"USDB address: {usdb_addr}")
    usdb_balance = client.web3.eth.call({
        'to': usdb_addr,
        'data': '0x70a08231' + wallet[2:].lower().zfill(64)
    })
    usdb_wei = int(usdb_balance.hex(), 16)
    print(f"USDB balance: {usdb_wei / 10**18:.4f}")
except Exception as e:
    print(f"USDB balance error: {e}")

# STASIS balance
try:
    stasis_addr = client.main_token_address
    print(f"STASIS address: {stasis_addr}")
    stasis_balance = client.web3.eth.call({
        'to': stasis_addr,
        'data': '0x70a08231' + wallet[2:].lower().zfill(64)
    })
    stasis_wei = int(stasis_balance.hex(), 16)
    print(f"STASIS balance: {stasis_wei / 10**18:.4f}")
except Exception as e:
    print(f"STASIS balance error: {e}")

# wSTASIS / staking position (Module 06)
try:
    staking_addr = client.staking_address
    print(f"Staking vault address: {staking_addr}")
    wstasis_balance = client.web3.eth.call({
        'to': staking_addr,
        'data': '0x70a08231' + wallet[2:].lower().zfill(64)
    })
    wstasis_wei = int(wstasis_balance.hex(), 16)
    print(f"wSTASIS balance: {wstasis_wei / 10**18:.4f}")
except Exception as e:
    print(f"wSTASIS balance error: {e}")

print("\n=== Staking Details (Module 06) ===")
try:
    details = client.staking.get_user_stake_details(wallet)
    print(f"Liquid shares: {details}")
except Exception as e:
    print(f"Staking details error: {e}")

print("\n=== Active Loans (Module 05) ===")
try:
    loan_count = client.loans.get_user_loan_count(wallet)
    print(f"Total loans: {loan_count}")
    if loan_count and int(str(loan_count)) > 0:
        for i in range(1, int(str(loan_count)) + 1):
            loan = client.loans.get_user_loan_details(wallet, i)
            print(f"  Loan {i}: {loan}")
except Exception as e:
    print(f"Loan check error: {e}")

print("\n=== Profile (Module 10) ===")
try:
    profile = client.api.get_my_profile()
    print(f"Tier: {profile.get('tier', 'unknown')}")
    print(f"Rank: {profile.get('rank', 'unknown')}")
    print(f"ACS: {profile.get('acsScore', 'unknown')}")
except Exception as e:
    print(f"Profile error: {e}")

print("\n=== Done ===")
