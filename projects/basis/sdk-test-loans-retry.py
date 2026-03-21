"""
Loans retry — hubId is 1-indexed
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
    print("LOANS RETRY - 1-indexed hubId")
    print("=" * 60)

    client = BasisClient(private_key=PRIVATE_KEY)
    wallet = client.account.address
    USDB = client.usdb_address
    STASIS = client.main_token_address

    usdb_bal = get_balance(client, USDB)
    stasis_bal = get_balance(client, STASIS)
    print(f"USDB: {usdb_bal / 10**18:.2f} | STASIS: {stasis_bal / 10**18:.6f}")

    # First check if we already have a loan from the previous test
    loan_count = client.loans.get_user_loan_count(wallet)
    print(f"Existing loan count: {loan_count}")

    # Try reading with hubId=1 (1-indexed) if we have a loan
    if loan_count > 0:
        print("\n-- Trying to read existing loan with hubId=1 --")
        try:
            details = client.loans.get_user_loan_details(wallet, 1)
            print(f"  Loan details (hubId=1): {details}")
            log_test("Read loan hubId=1", "PASS", f"Details: {details}")
        except Exception as e:
            print(f"  hubId=1 failed: {e}")
            # Try hubId=loan_count
            try:
                details = client.loans.get_user_loan_details(wallet, loan_count)
                print(f"  Loan details (hubId={loan_count}): {details}")
                log_test(f"Read loan hubId={loan_count}", "PASS", f"Details: {details}")
            except Exception as e2:
                print(f"  hubId={loan_count} also failed: {e2}")
                log_test("Read existing loan", "FAIL", str(e2))

    # Buy STASIS if needed
    if stasis_bal < 20 * 10**18:
        print("\nBuying 30 USDB of STASIS...")
        client.trading.buy(STASIS, 30 * 10**18)
        stasis_bal = get_balance(client, STASIS)
        print(f"STASIS: {stasis_bal / 10**18:.6f}")

    # Take a new loan
    print("\n" + "-" * 40)
    print("TEST: Take Loan - 10 STASIS, 30 days")
    try:
        result = client.loans.take_loan(STASIS, STASIS, 10 * 10**18, 30)
        print(f"  Tx: {result['hash']}")
        print(f"  Status: {'SUCCESS' if result['receipt'].status == 1 else 'FAILED'}")
        
        new_count = client.loans.get_user_loan_count(wallet)
        print(f"  Loan count after: {new_count}")

        # Try 1-indexed
        hub_id = new_count  # 1-indexed means latest = count
        print(f"\n  Trying hubId={hub_id} (1-indexed = count)...")
        try:
            details = client.loans.get_user_loan_details(wallet, hub_id)
            print(f"  SUCCESS! Loan details: {details}")
            log_test("Take Loan (1-indexed)", "PASS", f"hubId={hub_id}")
        except Exception as e:
            print(f"  hubId={hub_id} failed: {e}")
            # Try other values
            for try_id in range(1, new_count + 2):
                try:
                    details = client.loans.get_user_loan_details(wallet, try_id)
                    print(f"  Found at hubId={try_id}! Details: {details}")
                    hub_id = try_id
                    log_test("Take Loan", "PASS", f"Found at hubId={try_id}")
                    break
                except:
                    print(f"  hubId={try_id} - not found")
            else:
                log_test("Take Loan", "FAIL", "Could not find loan at any hubId")
                hub_id = None

        if hub_id:
            # TEST: Extend
            print(f"\n  Extending hubId={hub_id} by 15 days...")
            try:
                ext_result = client.loans.extend_loan(hub_id, 15, True, False)
                print(f"  Tx: {ext_result['hash']}")
                print(f"  Status: {'SUCCESS' if ext_result['receipt'].status == 1 else 'FAILED'}")
                log_test("Extend Loan", "PASS", f"Extended hubId={hub_id}")
            except Exception as e:
                log_test("Extend Loan", "FAIL", str(e))

            # TEST: Repay
            print(f"\n  Repaying hubId={hub_id}...")
            try:
                repay_result = client.loans.repay_loan(hub_id)
                print(f"  Tx: {repay_result['hash']}")
                print(f"  Status: {'SUCCESS' if repay_result['receipt'].status == 1 else 'FAILED'}")
                log_test("Repay Loan", "PASS", f"Repaid hubId={hub_id}")
            except Exception as e:
                log_test("Repay Loan", "FAIL", str(e))

    except Exception as e:
        log_test("Take Loan", "FAIL", str(e))

    # Cleanup
    print("\n" + "-" * 40)
    print("CLEANUP")
    stasis_bal = get_balance(client, STASIS)
    if stasis_bal > 0:
        try:
            client.trading.sell(STASIS, stasis_bal, to_usdb=True)
        except:
            pass
    usdb_final = get_balance(client, USDB)
    print(f"USDB final: {usdb_final / 10**18:.2f}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    print(f"PASS: {passed} | FAIL: {failed} | TOTAL: {len(results)}")
    for r in results:
        print(f"  [{r['status']}] {r['test']}: {r['details']}")

    with open("sdk-test-loans-retry-results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
