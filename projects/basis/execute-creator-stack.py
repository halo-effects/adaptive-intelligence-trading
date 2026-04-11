"""Execute the Creator's Edge Stack strategy on BASIS.
Stack 1: DONE (wSTASIS yielding base - 45.24 wSTASIS locked, borrowing)
Stack 2: CREATE Floor+ token -> buy it -> borrow against it  
Stack 3: CREATE prediction market -> bet on it
"""
import sys, time, json
sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient
from web3 import Web3

PRIVATE_KEY = "062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"
WALLET = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"
USDB = "0x78dD776204aA7e06BaF488959a90142f0B3027CE"
MAINTOKEN = "0x76ACb5F98A422995a801008c8b7b28dBC23946Ff"

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
print("--- CURRENT STATE (Post Stack 1) ---")
usdb_bal = get_balance(USDB, "USDB")
stake = client.staking.get_user_stake_details(WALLET)
print(f"  wSTASIS: liquid={stake[0]/10**18:.4f}, locked={stake[1]/10**18:.4f}")
bnb = client.web3.eth.get_balance(Web3.to_checksum_address(WALLET))
print(f"  BNB: {Web3.from_wei(bnb, 'ether')}")

# ============================================================
# STEP 0: CREATE a Floor+ Token
# ============================================================
print("\n" + "=" * 60)
print("STEP 0a: Creating Floor+ Token")
print("=" * 60)

print("\nCreating DEEPSTACK (Floor+ hm=50, startLP=2000)...")
try:
    result = client.factory.create_token_with_metadata(
        symbol="DSTACK",
        name="DeepStack",
        hybrid_multiplier=50,
        start_lp=2000,
        description="The stacking strategy token. Floor-protected, built by an AI agent to demonstrate capital-efficient DeFi on Basis. Every buy raises the floor.",
        image_url="https://cyan-abundant-swordtail-589.mypinata.cloud/ipfs/bafkreihnfni5yde5y24e7pri4xgb5djnb2xweexrtrcm5f64xbua3vpmym",
    )
    token_address = result.get("token_address", result.get("tokenAddress", "?"))
    print(f"  Token created: {token_address}")
    print(f"  TX: {result['hash'][:20]}...")
    log.append({"step": "0a", "tx": result["hash"], "desc": f"Create DSTACK Floor+ token", "token": token_address})
    time.sleep(5)
except Exception as e:
    print(f"  ERROR: {e}")
    token_address = None

# ============================================================
# STEP 0b: CREATE a Prediction Market
# ============================================================
print("\n" + "=" * 60)
print("STEP 0b: Creating Prediction Market")
print("=" * 60)

end_time = int(time.time()) + (86400 * 90)  # 90 days from now
print(f"\nCreating prediction market: 'Will AI agents manage >$1B in DeFi by 2027?'...")
try:
    market = client.prediction_markets.create_market_with_metadata(
        market_name="Will AI agents manage over $1B in DeFi TVL by end of 2027?",
        symbol="AIDFI",
        end_time=end_time,
        option_names=["Yes", "No"],
        maintoken=MAINTOKEN,
        seed_amount=50 * 10**18,
        description="AI agents are increasingly managing DeFi positions autonomously. Will the total value locked by AI-operated wallets exceed $1 billion by December 31, 2027?",
    )
    market_address = market.get("market_token_address", market.get("marketTokenAddress", "?"))
    print(f"  Market created: {market_address}")
    print(f"  TX: {market['hash'][:20]}...")
    log.append({"step": "0b", "tx": market["hash"], "desc": "Create AIDFI prediction market", "market": market_address})
    time.sleep(5)
except Exception as e:
    print(f"  ERROR: {e}")
    market_address = None

# ============================================================
# STACK 2: Buy own Floor+ token -> Borrow against it
# ============================================================
print("\n" + "=" * 60)
print("STACK 2: Buy DSTACK + Borrow")
print("=" * 60)

if token_address and token_address != "?":
    # Buy 50 USDB worth
    buy_amount = 50 * 10**18
    print(f"\nStep 2a: Buying DSTACK with 50 USDB...")
    try:
        result = client.trading.buy(token_address, buy_amount, 0)
        print(f"  TX: {result['hash'][:20]}...")
        log.append({"step": "2a", "tx": result["hash"], "desc": "Buy DSTACK with 50 USDB"})
        time.sleep(3)
    except Exception as e:
        print(f"  ERROR: {e}")

    dstack_bal = get_balance(token_address, "DSTACK balance")
    
    # Get USD price
    try:
        usd_price = int(client.trading.get_usd_price(token_address)) / 10**18
        print(f"  DSTACK price after buy: ${usd_price:.4f}")
    except:
        pass

    # Borrow against DSTACK
    if dstack_bal > 0:
        print(f"\nStep 2b: Borrowing against {dstack_bal/10**18:.4f} DSTACK (30 days)...")
        try:
            result = client.loans.take_loan(MAINTOKEN, token_address, dstack_bal, 30)
            print(f"  TX: {result['hash'][:20]}...")
            log.append({"step": "2b", "tx": result["hash"], "desc": f"Borrow against {dstack_bal/10**18:.2f} DSTACK"})
            time.sleep(3)
        except Exception as e:
            print(f"  ERROR: {e}")
    
    usdb_after_s2 = get_balance(USDB, "USDB after Stack 2")
else:
    print("  Skipping - no token created")

# ============================================================
# STACK 3: Bet on own prediction market
# ============================================================
print("\n" + "=" * 60)
print("STACK 3: Bet on AIDFI Market")
print("=" * 60)

if market_address and market_address != "?":
    bet_amount = 10 * 10**18
    print(f"\nStep 3: Betting 10 USDB on 'Yes' (outcome 0)...")
    try:
        result = client.prediction_markets.buy(market_address, 0, USDB, bet_amount, 0, 0)
        print(f"  TX: {result['hash'][:20]}...")
        log.append({"step": "3", "tx": result["hash"], "desc": "Bet 10 USDB on AIDFI (Yes)"})
        time.sleep(3)
    except Exception as e:
        print(f"  ERROR: {e}")
    
    # Check shares
    try:
        shares = client.prediction_markets.get_user_shares(market_address, WALLET, 0)
        print(f"  AIDFI Yes shares: {shares/10**18:.4f}")
    except Exception as e:
        print(f"  Shares check error: {e}")
else:
    print("  Skipping - no market created")

# ============================================================
# FINAL SUMMARY
# ============================================================
print("\n" + "=" * 60)
print("FINAL STATE - CREATOR'S EDGE STACK COMPLETE")
print("=" * 60)

usdb_final = get_balance(USDB, "USDB")
get_balance(MAINTOKEN, "STASIS")
stake_final = client.staking.get_user_stake_details(WALLET)
print(f"  wSTASIS: liquid={stake_final[0]/10**18:.4f}, locked={stake_final[1]/10**18:.4f}")
if token_address and token_address != "?":
    get_balance(token_address, "DSTACK (in loan collateral, so likely 0)")
bnb_final = client.web3.eth.get_balance(Web3.to_checksum_address(WALLET))
print(f"  BNB: {Web3.from_wei(bnb_final, 'ether')}")
loan_count = client.loans.get_user_loan_count(WALLET)
print(f"  Hub loans: {loan_count}")

print("\n--- FULL EXECUTION LOG ---")
# Include Stack 1 from earlier
full_log = [
    {"step": "1a", "tx": "82750cee33ee8e08", "desc": "Buy+Wrap 100 USDB -> wSTASIS"},
    {"step": "1b", "tx": "2a16b85ab1ca3aae", "desc": "Lock 45.24 wSTASIS"},
    {"step": "1c", "tx": "7f2f815c87995004", "desc": "Borrow 97.68 USDB against wSTASIS (30d)"},
] + log

for entry in full_log:
    tx = str(entry.get("tx", ""))[:20]
    print(f"  Step {entry['step']}: {entry['desc']} | tx={tx}...")

# Save complete log
with open("stack-execution-log.json", "w") as f:
    json.dump({
        "strategy": "Creator's Edge Stack",
        "start_usdb": 100,
        "token_created": token_address,
        "market_created": market_address,
        "log": full_log,
    }, f, indent=2, default=str)
print("\nLog saved to stack-execution-log.json")
