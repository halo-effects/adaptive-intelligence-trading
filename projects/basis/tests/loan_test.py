"""Buy $50 STASIS then take a $25 loan — Python SDK"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'C:\Users\Never\.openclaw\workspace\projects\basis\basis-sdk-python')
from basis import BasisClient

PK = '0x062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4'
WALLET = '0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2'

c = BasisClient.create(private_key=PK)
MAIN = c.main_token_address
USDB = c.usdb_address

# Step 1: Buy $50 of STASIS
print("=== Step 1: Buy $50 STASIS ===")
result = c.trading.buy(MAIN, 50 * 10**18)
print(f"✅ Buy tx: {result['hash'][:20]}...")
time.sleep(5)

# Check STASIS balance
bal = c.web3.eth.call({'to': MAIN, 'data': '0x70a08231000000000000000000000000' + WALLET[2:].lower()})
stasis = int.from_bytes(bal, byteorder='big') / 10**18
print(f"STASIS balance: {stasis:.4f}")

# Step 2: Take a loan — $25 worth of STASIS as collateral
# STASIS price ~$1, so 25 tokens ≈ $25 collateral
print("\n=== Step 2: Take loan (25 STASIS collateral, 10 days) ===")
collateral = 25 * 10**18
try:
    result = c.loans.take_loan(MAIN, MAIN, collateral, 10)
    print(f"✅ Loan tx: {result['hash'][:20]}...")
except Exception as e:
    print(f"❌ Loan failed: {e}")
    # Try with a factory token as the token param
    print("\nRetrying with USDB as loan token...")
    try:
        result = c.loans.take_loan(MAIN, USDB, collateral, 10)
        print(f"✅ Loan tx: {result['hash'][:20]}...")
    except Exception as e2:
        print(f"❌ Also failed: {e2}")

time.sleep(3)

# Check loan count
print("\n=== Loan Status ===")
try:
    count = c.loans.get_user_loan_count(WALLET)
    print(f"Loan count: {count}")
    if count and count > 0:
        for i in range(count):
            try:
                details = c.loans.get_user_loan_details(WALLET, i)
                print(f"Loan {i}: {details}")
            except Exception as e:
                print(f"Loan {i}: error — {e}")
except Exception as e:
    print(f"Error getting loan count: {e}")

# Check remaining balances
bal_usdb = c.web3.eth.call({'to': USDB, 'data': '0x70a08231000000000000000000000000' + WALLET[2:].lower()})
bal_stasis = c.web3.eth.call({'to': MAIN, 'data': '0x70a08231000000000000000000000000' + WALLET[2:].lower()})
print(f"\nUSDB:   {int.from_bytes(bal_usdb, byteorder='big') / 10**18:.4f}")
print(f"STASIS: {int.from_bytes(bal_stasis, byteorder='big') / 10**18:.4f}")
