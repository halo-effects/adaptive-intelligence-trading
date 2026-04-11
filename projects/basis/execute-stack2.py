"""Fix and continue the Conservative Stack.
Step 1a done (wSTASIS acquired). Need to: lock -> borrow -> buy Floor+ -> borrow -> bet.
"""
import sys, time, json
sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient
from web3 import Web3

PRIVATE_KEY = "062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"
WALLET = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"
USDB = "0x78dD776204aA7e06BaF488959a90142f0B3027CE"
MAINTOKEN = "0x76ACb5F98A422995a801008c8b7b28dBC23946Ff"
STAKING_ADDR = "0xb4D72acEa5E26B8438e3604b49A153eB58A7C578"

client = BasisClient.create(private_key=PRIVATE_KEY)
print(f"Authenticated. API key: {client.api_key[:12]}...")

def get_balance(token_addr, label):
    erc20_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
    contract = client.web3.eth.contract(address=Web3.to_checksum_address(token_addr), abi=erc20_abi)
    bal = contract.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
    print(f"  {label}: {bal / 10**18:.4f}")
    return bal

log = []

# Current state
print("--- CURRENT STATE ---")
usdb_bal = get_balance(USDB, "USDB")
stake = client.staking.get_user_stake_details(WALLET)
print(f"  wSTASIS: liquid={stake[0]/10**18:.4f}, locked={stake[1]/10**18:.4f}, total_shares={stake[2]/10**18:.4f}, total_assets={stake[3]/10**18:.4f}")
avail = client.staking.get_available_stasis(WALLET)
print(f"  Available STASIS for borrow: {avail/10**18:.4f}")

# ============================================================
# STACK 1 continued: Lock wSTASIS -> Borrow
# ============================================================
print("\n=== STACK 1: Lock wSTASIS + Borrow ===")

# Lock all liquid wSTASIS
liquid_wstasis = stake[0]
if liquid_wstasis > 0:
    print(f"\nStep 1b: Locking {liquid_wstasis/10**18:.4f} wSTASIS...")
    try:
        result = client.staking.lock(liquid_wstasis)
        print(f"  TX: {result['hash'][:20]}...")
        log.append({"step": "1b-lock", "tx": result["hash"], "desc": f"Lock {liquid_wstasis/10**18:.2f} wSTASIS"})
        time.sleep(3)
    except Exception as e:
        print(f"  ERROR: {e}")

# Check available stasis after lock
avail = client.staking.get_available_stasis(WALLET)
print(f"  Available STASIS after lock: {avail/10**18:.4f}")

# Borrow against locked wSTASIS
if avail > 0:
    print(f"\nStep 1c: Borrowing against {avail/10**18:.4f} STASIS (30 days)...")
    try:
        result = client.staking.borrow(avail, 30)
        print(f"  TX: {result['hash'][:20]}...")
        log.append({"step": "1c-borrow", "tx": result["hash"], "desc": f"Borrow against {avail/10**18:.2f} STASIS"})
        time.sleep(3)
    except Exception as e:
        print(f"  ERROR: {e}")

usdb_after_s1 = get_balance(USDB, "USDB after Stack 1 borrow")

# ============================================================
# Check which tokens are actually in this ecosystem
# ============================================================
print("\n=== CHECKING ECOSYSTEM TOKENS ===")
tokens_to_check = [
    ("TMPST-1", "0xC43DF80EFc3B29925BAbd744CD8AF28A0BE9AE3a"),
    ("TMPST-2", "0x550E46ffE3030451b97BDCfE2CDE76d6c96D9718"),
    ("TMPST-3", "0x0d5057868ca14771A3085d65Ef17D06A0Dbb9717"),
    ("LVTHN-1", "0xFf84209eBCCAc7328070E0011e973451c4a045F9"),
    ("LVTHN-2", "0x696b9807f9DbFE45B04c42B8b2C9C3c8a9288021"),
    ("LVTHN-3", "0x19432d15b87b7F411F9d31E50D2773fbbD32F44a"),
    ("AGNT", "0x43e256d9A65bFcFCFe65154d9eDC058dcaE7B515"),
    ("PRINT", "0x0068bb0090906ce85e9510388696e8447455cf91"),
]

valid_floor = []
for name, addr in tokens_to_check:
    try:
        is_eco = client.factory.is_ecosystem_token(addr)
        if is_eco:
            HM_ABI = [{"inputs":[],"name":"hybridMultiplier","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]
            c = client.web3.eth.contract(address=Web3.to_checksum_address(addr), abi=HM_ABI)
            hm = c.functions.hybridMultiplier().call()
            usd = int(client.trading.get_usd_price(addr)) / 10**18
            ttype = "Floor+" if hm < 100 else "Stable+"
            print(f"  {name}: ECO=YES | {ttype} (hm={hm}) | ${usd:.4f}")
            if hm < 100:
                valid_floor.append((name, addr, hm, usd))
        else:
            print(f"  {name}: ECO=NO (different deployment)")
    except Exception as e:
        print(f"  {name}: ERROR - {str(e)[:60]}")

# ============================================================
# STACK 2: Buy best Floor+ token -> borrow
# ============================================================
print("\n=== STACK 2: Floor+ Path ===")

if valid_floor:
    # Pick the one closest to floor (lowest price)
    best = sorted(valid_floor, key=lambda x: x[3])[0]
    floor_name, floor_addr, floor_hm, floor_price = best
    print(f"\nSelected: {floor_name} (hm={floor_hm}, ${floor_price:.4f})")
    
    # Use 50 USDB for Floor+ buy
    floor_buy = 50 * 10**18
    print(f"\nStep 2a: Buying {floor_name} with 50 USDB...")
    try:
        result = client.trading.buy(floor_addr, floor_buy, 0)
        print(f"  TX: {result['hash'][:20]}...")
        log.append({"step": "2a", "tx": result["hash"], "desc": f"Buy {floor_name} with 50 USDB"})
        time.sleep(3)
    except Exception as e:
        print(f"  ERROR: {e}")
    
    floor_bal = get_balance(floor_addr, f"{floor_name} balance")
    
    if floor_bal > 0:
        print(f"\nStep 2b: Borrowing against {floor_bal/10**18:.4f} {floor_name} (30 days)...")
        try:
            result = client.loans.take_loan(MAINTOKEN, floor_addr, floor_bal, 30)
            print(f"  TX: {result['hash'][:20]}...")
            log.append({"step": "2b", "tx": result["hash"], "desc": f"Borrow against {floor_name}"})
            time.sleep(3)
        except Exception as e:
            print(f"  ERROR: {e}")
    
    usdb_after_s2 = get_balance(USDB, "USDB after Stack 2")
else:
    print("  No valid Floor+ tokens found in this ecosystem!")

# ============================================================
# STACK 3: Prediction bet
# ============================================================
print("\n=== STACK 3: Prediction Bet ===")

# Check which prediction markets are in this ecosystem
pred_markets = [
    ("FEDCUT", "0xe13a8f12b5c1df2bfdaee169add44587dd7e2c06"),
    ("BAS1K", "0x5E36ac438650d9548E72Ce41d3225913a7EaEFb8"),
    ("TGEQ2", "0x22acB59faEBDEf1133016D96752Ab3366aB3bFC1"),
    ("CLAUDE5", "0x30151243fb21BDda761F628e09F6783aE51107D2"),
]

valid_pred = None
for name, addr in pred_markets:
    try:
        is_eco = client.factory.is_ecosystem_token(addr)
        if is_eco:
            market_data = client.prediction_markets.get_market_data(addr)
            resolved = market_data[8] if isinstance(market_data, (list, tuple)) else False
            print(f"  {name}: ECO=YES, resolved={resolved}")
            if not resolved and valid_pred is None:
                valid_pred = (name, addr)
        else:
            print(f"  {name}: ECO=NO")
    except Exception as e:
        print(f"  {name}: ERROR - {str(e)[:60]}")

if valid_pred:
    pred_name, pred_addr = valid_pred
    bet_wei = 10 * 10**18
    print(f"\nStep 3: Betting 10 USDB on {pred_name} outcome 0 (Yes)...")
    try:
        result = client.prediction_markets.buy(pred_addr, 0, USDB, bet_wei, 0, 0)
        print(f"  TX: {result['hash'][:20]}...")
        log.append({"step": "3", "tx": result["hash"], "desc": f"Bet 10 USDB on {pred_name}"})
        time.sleep(3)
    except Exception as e:
        print(f"  ERROR: {e}")
else:
    print("  No valid prediction markets found!")

# ============================================================
# FINAL STATE
# ============================================================
print("\n" + "=" * 60)
print("FINAL STATE")
print("=" * 60)
usdb_final = get_balance(USDB, "USDB")
get_balance(MAINTOKEN, "STASIS")
stake_final = client.staking.get_user_stake_details(WALLET)
print(f"  wSTASIS: liquid={stake_final[0]/10**18:.4f}, locked={stake_final[1]/10**18:.4f}")
bnb_final = client.web3.eth.get_balance(Web3.to_checksum_address(WALLET))
print(f"  BNB: {Web3.from_wei(bnb_final, 'ether')}")

loan_count = client.loans.get_user_loan_count(WALLET)
print(f"  Hub loans: {loan_count}")

print("\n--- TX LOG ---")
for entry in log:
    print(f"  Step {entry['step']}: {entry['desc']} | tx={entry['tx'][:20]}...")

with open("stack-execution-log.json", "w") as f:
    json.dump(log, f, indent=2, default=str)
print("\nDone!")
