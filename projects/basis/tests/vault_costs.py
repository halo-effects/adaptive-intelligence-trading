"""Query vault costs, tax rates, and loan interest to build the cost model"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'basis-sdk-python'))
from basis import BasisClient
from web3 import Web3

PK = '0x062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4'
WALLET = '0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2'

c = BasisClient.create(private_key=PK)
MAIN = c.main_token_address
USDB = c.usdb_address

print("=== COST MODEL ===")

# Tax rates
tax_rate = c.taxes.get_tax_rate(MAIN, WALLET)
base_rates = c.taxes.get_base_tax_rates()
print(f"\nTax rate for STASIS trades: {tax_rate} bps ({tax_rate/100:.2f}%)")
print(f"Base tax rates: {base_rates}")
print(f"  stasis: {base_rates['stasis']} bps ({base_rates['stasis']/100:.2f}%)")
print(f"  stable: {base_rates['stable']} bps ({base_rates['stable']/100:.2f}%)")
print(f"  default: {base_rates['default']} bps ({base_rates['default']/100:.2f}%)")
print(f"  prediction: {base_rates['prediction']} bps ({base_rates['prediction']/100:.2f}%)")

# Simulate buying $100 STASIS — what do we actually get?
amounts_out = c.trading.get_amounts_out(100 * 10**18, [USDB, MAIN])
print(f"\n$100 USDB -> {amounts_out / 1e18:.4f} STASIS")
print(f"  Effective price: ${100 / (amounts_out / 1e18):.6f} per STASIS")
print(f"  Slippage + tax from $100: {(1 - amounts_out / (100 * 1e18)) * 100:.4f}%")

# Vault exchange rate
vault = c.staking.contract
shares_for_100 = c.staking.convert_to_shares(100 * 10**18)
assets_for_shares = c.staking.convert_to_assets(shares_for_100)
print(f"\n100 STASIS wraps to: {shares_for_100 / 1e18:.6f} wSTASIS")
print(f"Those shares unwrap to: {assets_for_shares / 1e18:.6f} STASIS")
print(f"Round-trip wrap/unwrap loss: {(1 - assets_for_shares / (100 * 1e18)) * 100:.6f}%")

# Check if there's a loan interest rate in the hub
loan_hub_addr = vault.functions.loanHub().call()
loan_hub_abi = c.loans.contract.abi if hasattr(c.loans, 'contract') else None

# Check loan hub for interest parameters
hub = c.loans.contract
print(f"\n=== LOAN HUB ===")
# Check for interest-related functions
for item in hub.abi:
    if item.get('type') == 'function' and item.get('stateMutability') == 'view':
        name = item['name']
        if any(kw in name.lower() for kw in ['interest', 'rate', 'fee', 'annual', 'cost', 'param', 'config', 'min', 'max', 'day']):
            try:
                if len(item.get('inputs', [])) == 0:
                    result = hub.functions[name]().call()
                    print(f"  {name}() = {result}")
            except:
                pass

# Look at our existing loan to reverse-engineer the interest
print(f"\n=== EXISTING LOAN ANALYSIS ===")
loan_count = c.loans.get_user_loan_count(WALLET)
print(f"Total loans: {loan_count}")
for i in range(1, min(loan_count + 1, 5)):
    try:
        details = c.loans.get_user_loan_details(WALLET, i)
        print(f"\nLoan {i}:")
        print(f"  Collateral amount: {details[5] / 1e18:.4f}")
        print(f"  Borrowed amount:   {details[7] / 1e18:.4f}")
        print(f"  Full amount (owed): {details[6] / 1e18:.4f}")
        print(f"  Interest: {(details[6] - details[7]) / 1e18:.6f} ({((details[6] / details[7]) - 1) * 100:.4f}%)")
        print(f"  Liquidation time: {details[8]}")
        print(f"  Creation time: {details[12]}")
        duration_days = (details[8] - details[12]) / 86400
        print(f"  Duration: {duration_days:.1f} days")
        print(f"  Active: {details[11]}")
        print(f"  Is liquidated: {details[10]}")
        annualized = ((details[6] / details[7]) - 1) * (365 / duration_days) * 100
        print(f"  Annualized interest: ~{annualized:.2f}%")
    except Exception as e:
        print(f"Loan {i}: {e}")

# Gas costs for each operation
print(f"\n=== GAS ESTIMATES ===")
print(f"(BSC gas is ~3-5 gwei, BNB ~$600)")
print(f"Typical costs per operation:")
print(f"  buy() [wrap]: ~150k gas = ~$0.27-$0.45")
print(f"  sell() [unwrap]: ~120k gas = ~$0.22-$0.36")
print(f"  lock(): ~80k gas = ~$0.14-$0.24")
print(f"  unlock(): ~80k gas = ~$0.14-$0.24")
print(f"  borrow(): ~200k gas = ~$0.36-$0.60")
print(f"  repay(): ~180k gas = ~$0.32-$0.54")
print(f"  Full stack (buy STASIS + wrap + lock + borrow): ~4 txs = ~$1.00-$1.65")

# Simulate the full journey: $100 USDB -> yield
print(f"\n=== FULL COST BREAKDOWN: $100 USDB -> Vault ===")
stasis_received = amounts_out / 1e18
swap_cost_pct = (1 - stasis_received / 100) * 100
shares = shares_for_100 / 1e18
print(f"Step 1: Buy STASIS  — $100 USDB -> {stasis_received:.2f} STASIS (cost: {swap_cost_pct:.2f}%)")
print(f"Step 2: Wrap        — {stasis_received:.2f} STASIS -> {stasis_received * (shares_for_100 / (100 * 1e18)):.4f} wSTASIS (cost: ~0%, lossless conversion)")
print(f"Step 3: Gas         — ~$0.50 for buy + wrap (2 transactions)")
print(f"Total entry cost: ~{swap_cost_pct:.2f}% + $0.50 gas")
print(f"")
print(f"To exit:")
print(f"Step 4: Unwrap      — wSTASIS -> STASIS (lossless, you get MORE back due to yield)")
print(f"Step 5: Sell STASIS — STASIS -> USDB (same {swap_cost_pct:.2f}% swap cost)")
print(f"Step 6: Gas         — ~$0.50 for unwrap + sell")
print(f"Total round-trip cost: ~{swap_cost_pct * 2:.2f}% + $1.00 gas")
print(f"")
print(f"Break-even yield needed: ~{swap_cost_pct * 2:.2f}% to cover swap costs")
