"""Deep dive into Stasis Vault mechanics — live state query"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'basis-sdk-python'))
from basis import BasisClient

PK = '0x062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4'
WALLET = '0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2'

c = BasisClient.create(private_key=PK)
vault = c.staking.contract

print("=== VAULT CONTRACT STATE ===")
print(f"Vault address: {c.staking.staking_address}")
print(f"STASIS token: {vault.functions.stasisToken().call()}")
print(f"Loan Hub: {vault.functions.loanHub().call()}")
print(f"SWAP: {vault.functions.SWAP().call()}")
print(f"TAXES: {vault.functions.TAXES().call()}")

print(f"\n--- Global State ---")
total_supply = vault.functions.totalSupply().call()
total_assets = vault.functions.totalAssets().call()
total_pledged = vault.functions.totalStasisPledged().call()
total_available = vault.functions.totalStasisAvailable().call()
min_buy = vault.functions.minBuyAmount().call()
print(f"wSTASIS Total Supply: {total_supply / 1e18:.4f}")
print(f"Total Assets (STASIS): {total_assets / 1e18:.4f}")
print(f"Total STASIS Pledged: {total_pledged / 1e18:.4f}")
print(f"Total STASIS Available: {total_available / 1e18:.4f}")
print(f"Min Buy Amount: {min_buy / 1e18:.4f} STASIS")

# Exchange rate
if total_supply > 0:
    rate = total_assets / total_supply
    print(f"\nExchange Rate: 1 wSTASIS = {rate:.6f} STASIS")
    print(f"Exchange Rate: 1 STASIS = {1/rate:.6f} wSTASIS")

# Conversion checks
shares_for_1 = c.staking.convert_to_shares(10**18)
assets_for_1 = c.staking.convert_to_assets(10**18)
print(f"\nconvertToShares(1 STASIS) = {shares_for_1 / 1e18:.6f} wSTASIS")
print(f"convertToAssets(1 wSTASIS) = {assets_for_1 / 1e18:.6f} STASIS")

print(f"\n--- Our Wallet State ---")
details = c.staking.get_user_stake_details(WALLET)
print(f"getUserStakeDetails: liquidShares={details[0]/1e18:.4f}, lockedShares={details[1]/1e18:.4f}, totalShares={details[2]/1e18:.4f}, totalAssetValue={details[3]/1e18:.4f}")

available = c.staking.get_available_stasis(WALLET)
print(f"getAvailableStasis: {available / 1e18:.4f} STASIS")

# Check userVaults mapping directly
user_vault = vault.functions.userVaults(WALLET).call()
print(f"userVaults: lockedWStasis={user_vault[0]/1e18:.4f}, pledgedStasis={user_vault[1]/1e18:.4f}, hubId={user_vault[2]}, hasActiveLoan={user_vault[3]}")

# Check our wSTASIS balance
wstasis_bal = vault.functions.balanceOf(WALLET).call()
print(f"wSTASIS balance: {wstasis_bal / 1e18:.6f}")

# Check STASIS balance
from web3 import Web3
stasis = c.web3.eth.contract(address=Web3.to_checksum_address(c.main_token_address), abi=c.staking.erc20_abi)
stasis_bal = stasis.functions.balanceOf(WALLET).call()
print(f"STASIS balance: {stasis_bal / 1e18:.4f}")

# Yield analysis
print(f"\n--- Yield Analysis ---")
print(f"If rate > 1.0, vault is accruing yield")
print(f"Current rate: {assets_for_1 / 1e18:.6f} STASIS per wSTASIS")
if assets_for_1 > 10**18:
    yield_pct = ((assets_for_1 / 10**18) - 1) * 100
    print(f"Accumulated yield: {yield_pct:.4f}%")
else:
    print(f"No yield accumulated yet (rate <= 1.0)")

# Check what the sell function does with claimUSDC
print(f"\n--- Sell Modes ---")
print(f"sell(shares, claimUSDC=False, minUSDC=0): Returns STASIS tokens")
print(f"sell(shares, claimUSDC=True, minUSDC=X): Sells STASIS -> USDB in one tx")
print(f"  This combines unstake + sell in one atomic operation")

# Loan parameters — check hub for vault-specific loan terms
loan_hub = vault.functions.loanHub().call()
print(f"\n--- Loan Hub Integration ---")
print(f"Vault uses LoanHub at: {loan_hub}")
print(f"When you borrow(), the vault:")
print(f"  1. Pledges your locked wSTASIS as collateral")
print(f"  2. Creates a loan on LoanHub (gets hubId)")  
print(f"  3. Borrows STASIS against the collateral")
print(f"  4. You receive liquid STASIS")
print(f"Current userVault.hubId: {user_vault[2]} (0 = no loan)")
print(f"Current userVault.hasActiveLoan: {user_vault[3]}")
