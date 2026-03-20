"""Parse actual loan struct to get interest rate"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'basis-sdk-python'))
from basis import BasisClient

PK = '0x062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4'
WALLET = '0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2'
c = BasisClient.create(private_key=PK)

# Get raw loan data and print ALL fields with indices
for hub_id in range(1, 4):
    try:
        details = c.loans.get_user_loan_details(WALLET, hub_id)
        print(f"\n=== Loan Hub ID {hub_id} ===")
        # The struct from contract: 
        # getUserLoanDetails returns FullLoanDetails which is:
        # hubId, ecosystem, coreLoanId, collateralToken, token,
        # collateralAmount, liquidatedAmount, fullAmount, borrowedAmount,
        # liquidationTime, liquidationClaim, isLiquidated, active, creationTime
        fields = ['hubId', 'ecosystem', 'coreLoanId', 'collateralToken', 'token',
                  'collateralAmount', 'liquidatedAmount', 'fullAmount', 'borrowedAmount',
                  'liquidationTime', 'liquidationClaim', 'isLiquidated', 'active', 'creationTime']
        for i, val in enumerate(details):
            name = fields[i] if i < len(fields) else f'field_{i}'
            if isinstance(val, int) and val > 10**15:
                print(f"  [{i}] {name}: {val} ({val / 1e18:.6f} tokens)")
            else:
                print(f"  [{i}] {name}: {val}")
        
        # Interest calc
        borrowed = details[8]  # borrowedAmount
        full = details[7]      # fullAmount 
        if borrowed > 0 and full > 0:
            interest_abs = (full - borrowed) / 1e18
            interest_pct = ((full / borrowed) - 1) * 100
            
            creation = details[13]  # creationTime
            liquidation = details[9]  # liquidationTime
            if isinstance(creation, int) and isinstance(liquidation, int) and creation > 0:
                duration_days = (liquidation - creation) / 86400
                annualized = interest_pct * (365 / duration_days)
                print(f"\n  >> Interest: {interest_abs:.6f} tokens ({interest_pct:.4f}%)")
                print(f"  >> Duration: {duration_days:.1f} days")
                print(f"  >> Annualized: ~{annualized:.2f}%")
    except Exception as e:
        print(f"Loan {hub_id}: {e}")
