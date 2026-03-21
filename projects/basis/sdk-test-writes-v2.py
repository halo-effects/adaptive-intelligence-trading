"""
Basis SDK Write Tests — New Deployment (2026-03-21)
Tests: buy, sell, sell_percentage on STASIS (MAINTOKEN)
Wallet: 0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2
"""
import sys, os, time, json

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "basis-sdk-python"))

from basis.client import BasisClient

PRIVATE_KEY = "062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"

results = []

def log_test(name, status, details=""):
    emoji = "PASS" if status == "PASS" else "FAIL"
    print(f"[{emoji}] {name}: {status} {details}")
    results.append({"test": name, "status": status, "details": details})

def check_balance(client, token_addr, label=""):
    """Check ERC20 balance with retry for node lag."""
    from web3 import Web3
    erc20_abi = [{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]
    contract = client.web3.eth.contract(address=Web3.to_checksum_address(token_addr), abi=erc20_abi)
    time.sleep(3)  # Node lag
    bal = contract.functions.balanceOf(client.account.address).call()
    if label:
        print(f"  {label}: {bal / 10**18:.6f}")
    return bal

def main():
    print("=" * 60)
    print("BASIS SDK WRITE TESTS — New Deployment")
    print("=" * 60)

    # Init client
    client = BasisClient(private_key=PRIVATE_KEY)
    wallet = client.account.address
    print(f"Wallet: {wallet}")
    print(f"USDB: {client.usdb_address}")
    print(f"STASIS: {client.main_token_address}")
    print()

    # Pre-flight: check balances
    usdb_before = check_balance(client, client.usdb_address, "USDB balance")
    stasis_before = check_balance(client, client.main_token_address, "STASIS balance")
    bnb_balance = client.web3.eth.get_balance(wallet)
    print(f"  BNB balance: {bnb_balance / 10**18:.6f}")
    print()

    if usdb_before == 0:
        print("❌ No USDB! Claim from faucet first.")
        return

    # ============================================================
    # TEST 1: Buy STASIS with 5 USDB
    # ============================================================
    print("-" * 40)
    print("TEST 1: Buy STASIS with 5 USDB")
    try:
        buy_amount = 5 * 10**18  # 5 USDB

        # Preview
        expected = client.trading.get_amounts_out(buy_amount, [client.usdb_address, client.main_token_address])
        print(f"  Expected output: {expected}")

        result = client.trading.buy(client.main_token_address, buy_amount)
        print(f"  Tx: {result['hash']}")
        print(f"  Status: {'SUCCESS' if result['receipt'].status == 1 else 'FAILED'}")
        print(f"  Gas: {result['receipt'].gasUsed}")

        # Verify
        stasis_after = check_balance(client, client.main_token_address, "STASIS after buy")
        usdb_after = check_balance(client, client.usdb_address, "USDB after buy")

        if stasis_after > stasis_before:
            log_test("Buy STASIS", "PASS", f"Got {(stasis_after - stasis_before) / 10**18:.6f} STASIS for 5 USDB")
        else:
            log_test("Buy STASIS", "FAIL", "Balance didn't increase")
    except Exception as e:
        log_test("Buy STASIS", "FAIL", str(e))

    # ============================================================
    # TEST 2: Sell half of STASIS back to USDB
    # ============================================================
    print("-" * 40)
    print("TEST 2: Sell 50% STASIS to USDB")
    try:
        stasis_bal = check_balance(client, client.main_token_address)
        if stasis_bal == 0:
            log_test("Sell 50% STASIS", "SKIP", "No STASIS to sell")
        else:
            result = client.trading.sell_percentage(client.main_token_address, 50, to_usdb=True)
            print(f"  Tx: {result['hash']}")
            print(f"  Status: {'SUCCESS' if result['receipt'].status == 1 else 'FAILED'}")
            print(f"  Gas: {result['receipt'].gasUsed}")

            stasis_after_sell = check_balance(client, client.main_token_address, "STASIS after sell")
            usdb_after_sell = check_balance(client, client.usdb_address, "USDB after sell")

            if stasis_after_sell < stasis_bal:
                log_test("Sell 50% STASIS", "PASS", f"Sold {(stasis_bal - stasis_after_sell) / 10**18:.6f} STASIS")
            else:
                log_test("Sell 50% STASIS", "FAIL", "Balance didn't decrease")
    except Exception as e:
        log_test("Sell 50% STASIS", "FAIL", str(e))

    # ============================================================
    # TEST 3: Sell remaining STASIS (explicit amount, to USDB)
    # ============================================================
    print("-" * 40)
    print("TEST 3: Sell remaining STASIS to USDB")
    try:
        stasis_bal = check_balance(client, client.main_token_address)
        if stasis_bal == 0:
            log_test("Sell remaining STASIS", "SKIP", "No STASIS to sell")
        else:
            result = client.trading.sell(client.main_token_address, stasis_bal, to_usdb=True)
            print(f"  Tx: {result['hash']}")
            print(f"  Status: {'SUCCESS' if result['receipt'].status == 1 else 'FAILED'}")
            print(f"  Gas: {result['receipt'].gasUsed}")

            stasis_final = check_balance(client, client.main_token_address, "STASIS final")
            usdb_final = check_balance(client, client.usdb_address, "USDB final")

            if stasis_final == 0:
                log_test("Sell remaining STASIS", "PASS", f"USDB recovered: {usdb_final / 10**18:.2f}")
            else:
                log_test("Sell remaining STASIS", "FAIL", f"Still have {stasis_final / 10**18:.6f} STASIS")
    except Exception as e:
        log_test("Sell remaining STASIS", "FAIL", str(e))

    # ============================================================
    # TEST 4: Read — getAmountsOut preview
    # ============================================================
    print("-" * 40)
    print("TEST 4: Read — getAmountsOut")
    try:
        preview = client.trading.get_amounts_out(
            10 * 10**18,
            [client.usdb_address, client.main_token_address]
        )
        print(f"  10 USDB → {preview} STASIS raw")
        if preview and int(preview[-1] if isinstance(preview, (list, tuple)) else preview) > 0:
            log_test("getAmountsOut", "PASS", f"Output: {preview}")
        else:
            log_test("getAmountsOut", "FAIL", f"Zero or invalid output: {preview}")
    except Exception as e:
        log_test("getAmountsOut", "FAIL", str(e))

    # ============================================================
    # TEST 5: Read — getUSDPrice
    # ============================================================
    print("-" * 40)
    print("TEST 5: Read — getUSDPrice STASIS")
    try:
        price = client.trading.get_usd_price(client.main_token_address)
        print(f"  STASIS USD price: {price}")
        if int(price) > 0:
            log_test("getUSDPrice", "PASS", f"Price: {int(price) / 10**18:.6f} USD")
        else:
            log_test("getUSDPrice", "FAIL", "Price is zero")
    except Exception as e:
        log_test("getUSDPrice", "FAIL", str(e))

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
        emoji = "PASS" if r["status"] == "PASS" else ("FAIL" if r["status"] == "FAIL" else "SKIP")
        print(f"  {emoji} {r['test']}: {r['status']} — {r['details']}")

    # Save results
    with open("sdk-test-writes-v2-results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to sdk-test-writes-v2-results.json")

if __name__ == "__main__":
    main()
