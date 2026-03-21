"""
Basis SDK Write Tests — Loans + Staking
Tests: take loan, extend, repay, staking wrap/lock/borrow/repay/unlock/unwrap
"""
import sys, os, time, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "basis-sdk-python"))
from basis.client import BasisClient
from web3 import Web3

PRIVATE_KEY = "062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"

results = []

def log_test(name, status, details=""):
    print(f"[{status}] {name}: {details}")
    results.append({"test": name, "status": status, "details": details})

def get_balance(client, token_addr):
    time.sleep(3)
    erc20_abi = [{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]
    contract = client.web3.eth.contract(address=Web3.to_checksum_address(token_addr), abi=erc20_abi)
    return contract.functions.balanceOf(client.account.address).call()

def main():
    print("=" * 60)
    print("BASIS SDK WRITE TESTS - LOANS + STAKING")
    print("=" * 60)

    client = BasisClient(private_key=PRIVATE_KEY)
    wallet = client.account.address
    USDB = client.usdb_address
    STASIS = client.main_token_address
    
    usdb_bal = get_balance(client, USDB)
    print(f"Wallet: {wallet}")
    print(f"USDB: {usdb_bal / 10**18:.2f}")
    print()

    # ============================================================
    # First buy some STASIS to use as collateral
    # ============================================================
    print("-" * 40)
    print("SETUP: Buy 50 USDB worth of STASIS for collateral")
    try:
        buy_result = client.trading.buy(STASIS, 50 * 10**18)
        print(f"  Tx: {buy_result['hash']}")
        print(f"  Status: {'SUCCESS' if buy_result['receipt'].status == 1 else 'FAILED'}")
        stasis_bal = get_balance(client, STASIS)
        print(f"  STASIS balance: {stasis_bal / 10**18:.6f}")
    except Exception as e:
        print(f"  SETUP FAILED: {e}")
        return

    # ============================================================
    # TEST 1: Take Loan (STASIS as collateral)
    # ============================================================
    print("-" * 40)
    print("TEST 1: Take Loan - 10 STASIS collateral, 30 days")
    try:
        collateral_amount = 10 * 10**18  # 10 STASIS
        result = client.loans.take_loan(STASIS, STASIS, collateral_amount, 30)
        print(f"  Tx: {result['hash']}")
        print(f"  Status: {'SUCCESS' if result['receipt'].status == 1 else 'FAILED'}")
        
        # Get loan count
        loan_count = client.loans.get_user_loan_count(wallet)
        print(f"  Loan count: {loan_count}")
        
        if loan_count > 0:
            hub_id = loan_count - 1
            details = client.loans.get_user_loan_details(wallet, hub_id)
            print(f"  Loan details: {details}")
            log_test("Take Loan", "PASS", f"hubId={hub_id}, loan_count={loan_count}")
        else:
            log_test("Take Loan", "FAIL", "Loan count is 0 after taking loan")
    except Exception as e:
        log_test("Take Loan", "FAIL", str(e))

    # ============================================================
    # TEST 2: Extend Loan
    # ============================================================
    print("-" * 40)
    print("TEST 2: Extend Loan by 15 days")
    try:
        loan_count = client.loans.get_user_loan_count(wallet)
        if loan_count == 0:
            log_test("Extend Loan", "SKIP", "No loans to extend")
        else:
            hub_id = loan_count - 1
            result = client.loans.extend_loan(hub_id, 15, True, False)
            print(f"  Tx: {result['hash']}")
            print(f"  Status: {'SUCCESS' if result['receipt'].status == 1 else 'FAILED'}")
            log_test("Extend Loan", "PASS", f"Extended hubId={hub_id} by 15 days")
    except Exception as e:
        log_test("Extend Loan", "FAIL", str(e))

    # ============================================================
    # TEST 3: Repay Loan
    # ============================================================
    print("-" * 40)
    print("TEST 3: Repay Loan")
    try:
        loan_count = client.loans.get_user_loan_count(wallet)
        if loan_count == 0:
            log_test("Repay Loan", "SKIP", "No loans to repay")
        else:
            hub_id = loan_count - 1
            result = client.loans.repay_loan(hub_id)
            print(f"  Tx: {result['hash']}")
            print(f"  Status: {'SUCCESS' if result['receipt'].status == 1 else 'FAILED'}")
            log_test("Repay Loan", "PASS", f"Repaid hubId={hub_id}")
    except Exception as e:
        log_test("Repay Loan", "FAIL", str(e))

    # ============================================================
    # STAKING TESTS
    # ============================================================
    stasis_bal = get_balance(client, STASIS)
    print()
    print(f"STASIS before staking: {stasis_bal / 10**18:.6f}")

    # TEST 4: Wrap STASIS -> wSTASIS
    print("-" * 40)
    print("TEST 4: Wrap 10 STASIS into wSTASIS")
    try:
        wrap_amount = 10 * 10**18
        result = client.staking.buy(wrap_amount)
        print(f"  Tx: {result['hash']}")
        print(f"  Status: {'SUCCESS' if result['receipt'].status == 1 else 'FAILED'}")
        log_test("Wrap STASIS", "PASS", "Wrapped 10 STASIS")
    except Exception as e:
        log_test("Wrap STASIS", "FAIL", str(e))

    # TEST 5: Lock wSTASIS
    print("-" * 40)
    print("TEST 5: Lock wSTASIS as collateral")
    try:
        shares = client.staking.convert_to_shares(10 * 10**18)
        print(f"  Shares for 10 STASIS: {shares}")
        shares_int = int(shares)
        if shares_int > 0:
            result = client.staking.lock(shares_int)
            print(f"  Tx: {result['hash']}")
            print(f"  Status: {'SUCCESS' if result['receipt'].status == 1 else 'FAILED'}")
            log_test("Lock wSTASIS", "PASS", f"Locked {shares_int} shares")
        else:
            log_test("Lock wSTASIS", "FAIL", "No shares to lock")
    except Exception as e:
        log_test("Lock wSTASIS", "FAIL", str(e))

    # TEST 6: Borrow against locked wSTASIS
    print("-" * 40)
    print("TEST 6: Borrow against locked staking position")
    try:
        avail = client.staking.get_available_stasis(wallet)
        print(f"  Available STASIS for borrowing: {avail}")
        borrow_amount = 5 * 10**18  # 5 STASIS worth
        result = client.staking.borrow(borrow_amount, 30)
        print(f"  Tx: {result['hash']}")
        print(f"  Status: {'SUCCESS' if result['receipt'].status == 1 else 'FAILED'}")
        usdb_after = get_balance(client, USDB)
        print(f"  USDB after borrow: {usdb_after / 10**18:.2f}")
        log_test("Borrow against stake", "PASS", "Borrowed against locked wSTASIS")
    except Exception as e:
        log_test("Borrow against stake", "FAIL", str(e))

    # TEST 7: Repay staking loan
    print("-" * 40)
    print("TEST 7: Repay staking loan")
    try:
        result = client.staking.repay()
        print(f"  Tx: {result['hash']}")
        print(f"  Status: {'SUCCESS' if result['receipt'].status == 1 else 'FAILED'}")
        log_test("Repay staking loan", "PASS", "Repaid")
    except Exception as e:
        log_test("Repay staking loan", "FAIL", str(e))

    # TEST 8: Unlock wSTASIS
    print("-" * 40)
    print("TEST 8: Unlock wSTASIS")
    try:
        shares = client.staking.convert_to_shares(10 * 10**18)
        shares_int = int(shares)
        result = client.staking.unlock(shares_int)
        print(f"  Tx: {result['hash']}")
        print(f"  Status: {'SUCCESS' if result['receipt'].status == 1 else 'FAILED'}")
        log_test("Unlock wSTASIS", "PASS", f"Unlocked {shares_int} shares")
    except Exception as e:
        log_test("Unlock wSTASIS", "FAIL", str(e))

    # TEST 9: Unwrap wSTASIS -> STASIS
    print("-" * 40)
    print("TEST 9: Unwrap wSTASIS back to STASIS")
    try:
        shares = client.staking.convert_to_shares(10 * 10**18)
        shares_int = int(shares)
        result = client.staking.sell(shares_int)
        print(f"  Tx: {result['hash']}")
        print(f"  Status: {'SUCCESS' if result['receipt'].status == 1 else 'FAILED'}")
        stasis_final = get_balance(client, STASIS)
        print(f"  STASIS after unwrap: {stasis_final / 10**18:.6f}")
        log_test("Unwrap wSTASIS", "PASS", "Unwrapped back to STASIS")
    except Exception as e:
        log_test("Unwrap wSTASIS", "FAIL", str(e))

    # ============================================================
    # CLEANUP: Sell remaining STASIS back to USDB
    # ============================================================
    print("-" * 40)
    print("CLEANUP: Sell all STASIS back to USDB")
    try:
        stasis_bal = get_balance(client, STASIS)
        if stasis_bal > 0:
            client.trading.sell(STASIS, stasis_bal, to_usdb=True)
            usdb_final = get_balance(client, USDB)
            print(f"  USDB final: {usdb_final / 10**18:.2f}")
    except Exception as e:
        print(f"  Cleanup failed: {e}")

    # ============================================================
    # SUMMARY
    # ============================================================
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    skipped = sum(1 for r in results if r["status"] == "SKIP")
    print(f"PASS: {passed} | FAIL: {failed} | SKIP: {skipped} | TOTAL: {len(results)}")
    for r in results:
        print(f"  [{r['status']}] {r['test']}: {r['details']}")

    with open("sdk-test-writes-v3-results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to sdk-test-writes-v3-results.json")

if __name__ == "__main__":
    main()
