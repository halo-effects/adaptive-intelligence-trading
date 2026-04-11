"""Create token and market on-chain (no metadata), then stack."""
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

print("--- CURRENT STATE ---")
usdb_bal = get_balance(USDB, "USDB")

# ============================================================
# STEP 0a: Create Floor+ Token (on-chain only)
# ============================================================
print("\n=== Creating DSTACK Floor+ Token (on-chain) ===")
try:
    result = client.factory.create_token(
        symbol="DSTACK",
        name="DeepStack",
        hybrid_multiplier=50,
        frozen=False,
        usdb_for_bonding=0,
        start_lp=2000,
        auto_vest=False,
        auto_vest_duration=0,
        gradual_autovest=False,
    )
    tx_hash = result["hash"]
    receipt = result["receipt"]
    print(f"  TX: {tx_hash[:20]}...")
    print(f"  Gas used: {receipt.gasUsed}")
    
    # Extract token address from logs
    token_address = None
    for log_entry in receipt.logs:
        # The factory emits an event with the new token address
        if len(log_entry.topics) > 0:
            # Try to find the token address in log data
            pass
    
    # Alternative: check getTokensByCreator
    tokens = client.factory.get_tokens_by_creator(WALLET)
    print(f"  Tokens by creator: {tokens}")
    if tokens:
        token_address = tokens[-1]  # Latest created
        print(f"  New token address: {token_address}")
    
    log.append({"step": "0a", "tx": tx_hash, "desc": "Create DSTACK Floor+ token", "addr": token_address})
    time.sleep(5)
except Exception as e:
    print(f"  ERROR: {e}")
    token_address = None

# ============================================================
# STEP 0b: Create Prediction Market (on-chain)
# ============================================================
print("\n=== Creating AIDFI Prediction Market ===")
end_time = int(time.time()) + (86400 * 90)  # 90 days
try:
    # Need to approve USDB for seed amount first
    erc20_abi = [{"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"}]
    
    # Use the prediction market module's create method
    market_trading = "0xCb64910a19B3641eb600b904741a074578Dda3F7"
    
    result = client.prediction_markets.create_market(
        market_name="Will AI agents manage over $1B DeFi TVL by 2027?",
        symbol="AIDFI",
        end_time=end_time,
        option_names=["Yes", "No"],
        maintoken=MAINTOKEN,
        frozen=False,
        bonding=0,
        seed_amount=50 * 10**18,
    )
    market_tx = result["hash"]
    receipt = result["receipt"]
    print(f"  TX: {market_tx[:20]}...")
    print(f"  Gas used: {receipt.gasUsed}")
    
    # Get market address from tokens by creator
    time.sleep(3)
    tokens_after = client.factory.get_tokens_by_creator(WALLET)
    print(f"  All tokens by creator: {tokens_after}")
    # Market address should be the newest one (after the DSTACK token)
    if token_address and len(tokens_after) > 1:
        market_address = tokens_after[-1]
    elif tokens_after:
        market_address = tokens_after[-1]
    else:
        market_address = None
    print(f"  Market address: {market_address}")
    
    log.append({"step": "0b", "tx": market_tx, "desc": "Create AIDFI prediction market", "addr": market_address})
    time.sleep(3)
except Exception as e:
    print(f"  ERROR: {e}")
    market_address = None

# ============================================================
# STACK 2: Buy own Floor+ token -> Borrow
# ============================================================
print("\n=== STACK 2: Buy DSTACK + Borrow ===")

if token_address:
    # Verify it's in ecosystem
    is_eco = client.factory.is_ecosystem_token(token_address)
    print(f"  DSTACK isEcosystemToken: {is_eco}")
    
    buy_amount = 50 * 10**18
    print(f"\n  Buying DSTACK with 50 USDB...")
    try:
        result = client.trading.buy(token_address, buy_amount, 0)
        print(f"  TX: {result['hash'][:20]}...")
        log.append({"step": "2a", "tx": result["hash"], "desc": "Buy DSTACK with 50 USDB"})
        time.sleep(3)
    except Exception as e:
        print(f"  Buy ERROR: {e}")
    
    dstack_bal = get_balance(token_address, "DSTACK balance")
    
    if dstack_bal > 0:
        print(f"\n  Borrowing against {dstack_bal/10**18:.4f} DSTACK (30 days)...")
        try:
            result = client.loans.take_loan(MAINTOKEN, token_address, dstack_bal, 30)
            print(f"  TX: {result['hash'][:20]}...")
            log.append({"step": "2b", "tx": result["hash"], "desc": f"Borrow against DSTACK"})
            time.sleep(3)
        except Exception as e:
            print(f"  Borrow ERROR: {e}")

    get_balance(USDB, "USDB after Stack 2")

# ============================================================
# STACK 3: Bet on own market
# ============================================================
print("\n=== STACK 3: Bet on AIDFI ===")

if market_address:
    bet_amount = 10 * 10**18
    print(f"\n  Betting 10 USDB on Yes (outcome 0)...")
    try:
        result = client.prediction_markets.buy(market_address, 0, USDB, bet_amount, 0, 0)
        print(f"  TX: {result['hash'][:20]}...")
        log.append({"step": "3", "tx": result["hash"], "desc": "Bet 10 USDB on AIDFI Yes"})
        time.sleep(3)
    except Exception as e:
        print(f"  Bet ERROR: {e}")
    
    try:
        shares = client.prediction_markets.get_user_shares(market_address, WALLET, 0)
        print(f"  AIDFI Yes shares: {shares/10**18:.4f}")
    except Exception as e:
        print(f"  Shares check: {e}")

# ============================================================
# FINAL SUMMARY
# ============================================================
print("\n" + "=" * 60)
print("FINAL STATE")
print("=" * 60)
usdb_final = get_balance(USDB, "USDB")
stake_final = client.staking.get_user_stake_details(WALLET)
print(f"  wSTASIS: liquid={stake_final[0]/10**18:.4f}, locked={stake_final[1]/10**18:.4f}")
if token_address:
    get_balance(token_address, "DSTACK")
bnb_final = client.web3.eth.get_balance(Web3.to_checksum_address(WALLET))
print(f"  BNB: {Web3.from_wei(bnb_final, 'ether')}")
loan_count = client.loans.get_user_loan_count(WALLET)
print(f"  Hub loans: {loan_count}")

# Full log
full_log = [
    {"step": "1a", "tx": "82750cee33ee8e08", "desc": "Buy+Wrap 100 USDB -> wSTASIS"},
    {"step": "1b", "tx": "2a16b85ab1ca3aae", "desc": "Lock 45.24 wSTASIS"},
    {"step": "1c", "tx": "7f2f815c87995004", "desc": "Borrow 97.68 USDB against wSTASIS (30d)"},
] + log

print("\n--- TX LOG ---")
for entry in full_log:
    tx = str(entry.get("tx", ""))[:20]
    addr = entry.get("addr", "")
    extra = f" -> {addr}" if addr else ""
    print(f"  Step {entry['step']}: {entry['desc']}{extra} | tx={tx}...")

with open("stack-execution-log.json", "w") as f:
    json.dump({"strategy": "Creator's Edge Stack", "token": token_address, "market": market_address, "log": full_log}, f, indent=2, default=str)
print("\nDone!")
