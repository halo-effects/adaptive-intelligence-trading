"""Execute the Conservative Stack strategy on BASIS.
Stack 1: Buy STASIS -> wrap to wSTASIS -> borrow USDB
Stack 2: Buy TMPST (Floor+) -> borrow USDB against it
Stack 3: Bet on FEDCUT prediction market
"""
import sys, time, json
sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient
from web3 import Web3

PRIVATE_KEY = "062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"
WALLET = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"
USDB = "0x78dD776204aA7e06BaF488959a90142f0B3027CE"
MAINTOKEN = "0x76ACb5F98A422995a801008c8b7b28dBC23946Ff"  # STASIS
STAKING = "0xb4D72acEa5E26B8438e3604b49A153eB58A7C578"  # wSTASIS vault
TMPST = "0xC43DF80EFc3B29925BAbd744CD8AF28A0BE9AE3a"
FEDCUT = "0xe13a8f12b5c1df2bfdaee169add44587dd7e2c06"

STACK_AMOUNT = 100  # USDB to start with
BET_AMOUNT = 10     # USDB for prediction bet

log = []

def log_step(step, desc, result=None, error=None):
    entry = {"step": step, "desc": desc, "time": time.strftime("%H:%M:%S")}
    if result:
        entry["tx"] = result.get("hash", "?")
        entry["gas"] = result.get("receipt", {}).gasUsed if hasattr(result.get("receipt", {}), "gasUsed") else "?"
    if error:
        entry["error"] = str(error)
    log.append(entry)
    status = "ERROR" if error else "OK"
    tx = entry.get("tx", "")[:16] if entry.get("tx") else ""
    print(f"[{entry['time']}] {status} | Step {step}: {desc} {tx}")

def get_balance(client, token_addr, label):
    erc20_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
    contract = client.web3.eth.contract(address=Web3.to_checksum_address(token_addr), abi=erc20_abi)
    bal = contract.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
    print(f"  {label}: {bal / 10**18:.4f}")
    return bal

print("=" * 60)
print("CONSERVATIVE STACK EXECUTION")
print(f"Starting amount: {STACK_AMOUNT} USDB")
print(f"Prediction bet: {BET_AMOUNT} USDB")
print("=" * 60)

client = BasisClient.create(private_key=PRIVATE_KEY)
print(f"\nAuthenticated. API key: {client.api_key[:12]}...")

# Pre-check balances
print("\n--- PRE-STACK BALANCES ---")
usdb_before = get_balance(client, USDB, "USDB")
stasis_before = get_balance(client, MAINTOKEN, "STASIS")
bnb_before = client.web3.eth.get_balance(Web3.to_checksum_address(WALLET))
print(f"  BNB: {Web3.from_wei(bnb_before, 'ether')}")

stake_details = client.staking.get_user_stake_details(WALLET)
print(f"  wSTASIS: liquid={stake_details[0]/10**18:.4f}, locked={stake_details[1]/10**18:.4f}")

# ============================================================
# STACK 1: Buy STASIS -> wrap to wSTASIS -> borrow USDB
# ============================================================
print("\n" + "=" * 60)
print("STACK 1: Stable+ Path (STASIS -> wSTASIS -> Borrow)")
print("=" * 60)

# Step 1a: Buy STASIS with USDB and wrap to wSTASIS in one tx
amount_wei = STACK_AMOUNT * 10**18
print(f"\nStep 1a: Buying {STACK_AMOUNT} USDB worth of STASIS + wrapping to wSTASIS...")
try:
    result = client.trading.buy(MAINTOKEN, amount_wei, 0, wrap_tokens=True)
    log_step("1a", f"Buy+Wrap {STACK_AMOUNT} USDB -> wSTASIS", result)
    time.sleep(3)
except Exception as e:
    log_step("1a", f"Buy+Wrap FAILED", error=e)
    print(f"FATAL: {e}")
    sys.exit(1)

# Check wSTASIS balance after wrap
stake_details = client.staking.get_user_stake_details(WALLET)
print(f"  wSTASIS after wrap: liquid={stake_details[0]/10**18:.4f}, locked={stake_details[1]/10**18:.4f}")
available_stasis = client.staking.get_available_stasis(WALLET)
print(f"  Available STASIS for borrowing: {available_stasis/10**18:.4f}")

# Step 1b: Borrow USDB against wSTASIS (30 days)
# We borrow the available stasis amount
borrow_amount = available_stasis
print(f"\nStep 1b: Borrowing against {borrow_amount/10**18:.4f} STASIS (30 days)...")
try:
    result = client.staking.borrow(borrow_amount, 30)
    log_step("1b", f"Borrow against wSTASIS ({borrow_amount/10**18:.2f} STASIS, 30d)", result)
    time.sleep(3)
except Exception as e:
    log_step("1b", f"Borrow FAILED", error=e)
    print(f"ERROR: {e}")

# Check USDB recovered
usdb_after_s1 = get_balance(client, USDB, "USDB after Stack 1")
usdb_recovered_s1 = (usdb_after_s1 - (usdb_before - amount_wei)) / 10**18
print(f"  USDB recovered from borrow: ~{usdb_recovered_s1:.2f}")

# ============================================================
# STACK 2: Buy TMPST (Floor+) -> borrow USDB against it
# ============================================================
print("\n" + "=" * 60)
print("STACK 2: Floor+ Path (TMPST -> Borrow)")
print("=" * 60)

# Use 80% of recovered USDB for Floor+ buy (keep some reserve)
usdb_for_floor = int(usdb_after_s1 * 0.7)  # 70% of current USDB
print(f"\nStep 2a: Buying TMPST with {usdb_for_floor/10**18:.2f} USDB...")
try:
    result = client.trading.buy(TMPST, usdb_for_floor, 0)
    log_step("2a", f"Buy TMPST with {usdb_for_floor/10**18:.2f} USDB", result)
    time.sleep(3)
except Exception as e:
    log_step("2a", f"Buy TMPST FAILED", error=e)
    print(f"ERROR: {e}")

# Check TMPST balance
tmpst_balance = get_balance(client, TMPST, "TMPST after buy")

# Step 2b: Borrow against TMPST
if tmpst_balance > 0:
    print(f"\nStep 2b: Borrowing against {tmpst_balance/10**18:.4f} TMPST (30 days)...")
    try:
        result = client.loans.take_loan(MAINTOKEN, TMPST, tmpst_balance, 30)
        log_step("2b", f"Borrow against TMPST ({tmpst_balance/10**18:.2f} tokens, 30d)", result)
        time.sleep(3)
    except Exception as e:
        log_step("2b", f"Borrow against TMPST FAILED", error=e)
        print(f"ERROR: {e}")

usdb_after_s2 = get_balance(client, USDB, "USDB after Stack 2")

# ============================================================
# STACK 3: Bet on FEDCUT prediction market
# ============================================================
print("\n" + "=" * 60)
print("STACK 3: Outcome Bet (FEDCUT - Fed Rate Cut)")
print("=" * 60)

bet_wei = BET_AMOUNT * 10**18
# Bet on outcome 0 (Yes - Fed will cut)
print(f"\nStep 3: Betting {BET_AMOUNT} USDB on FEDCUT outcome 0 (Yes)...")
try:
    result = client.prediction_markets.buy(FEDCUT, 0, USDB, bet_wei, 0, 0)
    log_step("3", f"Bet {BET_AMOUNT} USDB on FEDCUT (Yes)", result)
    time.sleep(3)
except Exception as e:
    log_step("3", f"FEDCUT bet FAILED", error=e)
    print(f"ERROR: {e}")

# ============================================================
# FINAL SUMMARY
# ============================================================
print("\n" + "=" * 60)
print("FINAL STATE")
print("=" * 60)

usdb_final = get_balance(client, USDB, "USDB")
stasis_final = get_balance(client, MAINTOKEN, "STASIS")
tmpst_final = get_balance(client, TMPST, "TMPST")
bnb_final = client.web3.eth.get_balance(Web3.to_checksum_address(WALLET))
print(f"  BNB: {Web3.from_wei(bnb_final, 'ether')}")

stake_final = client.staking.get_user_stake_details(WALLET)
print(f"  wSTASIS: liquid={stake_final[0]/10**18:.4f}, locked={stake_final[1]/10**18:.4f}")

# Check prediction shares
try:
    shares = client.prediction_markets.get_user_shares(FEDCUT, WALLET, 0)
    print(f"  FEDCUT Yes shares: {shares/10**18:.4f}")
except:
    print("  FEDCUT shares: could not read")

# Check loans
try:
    loan_count = client.loans.get_user_loan_count(WALLET)
    print(f"  Active hub loans: {loan_count}")
except:
    pass

print("\n--- EXECUTION LOG ---")
for entry in log:
    status = "❌" if entry.get("error") else "✅"
    tx = entry.get("tx", "")[:20]
    print(f"  {status} [{entry['time']}] {entry['desc']} {tx}")

# Save log
with open("stack-execution-log.json", "w") as f:
    json.dump({"log": log, "strategy": "Conservative Stack", "start_amount": STACK_AMOUNT, "bet_amount": BET_AMOUNT}, f, indent=2, default=str)
print("\nLog saved to stack-execution-log.json")
