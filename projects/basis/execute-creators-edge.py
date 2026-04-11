"""
Creator's Edge Stack â€” Live Execution on Basis Protocol
========================================================
Strategy: Create yield base â†’ Create token â†’ Buy position â†’ Create prediction market â†’ Bet

Steps:
  1. Buy STASIS with USDB (yield foundation)
  2. Wrap STASIS â†’ wSTASIS (staking vault)
  3. Lock wSTASIS as collateral
  4. Borrow USDB against it (capital recycling)
  5. Create Floor+ token with metadata (creator play)
  6. Buy into the token (first buyer advantage)
  7. Create prediction market with metadata
  8. Bet on the prediction market (conviction play)

Uses contracts.json (live deployment) addresses.
"""

import json
import time
import traceback
from web3 import Web3
from basis import BasisClient

# â”€â”€ Config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
PK = "062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"
WALLET = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"

# contracts.json addresses (live deployment)
CONTRACTS = {
    "factory_address": "0xB6BA282f29A7C67059f4E9D0898eE58f5C79960D",
    "swap_address": "0x9F9cF98F68bDbCbC5cf4c6402D53cEE1D180715f",
    "market_trading_address": "0x396216fc9d2c220afD227B59097cf97B7dEaCb57",
    "loan_hub_address": "0xFe19644d52fD0014EBa40c6A8F4Bfee4Ce3B2449",
    "staking_address": "0x1FE7189270fb93c32a1fEfA71d1795c05C41cb33",
    "reader_address": "0xF406cA6403c57Ad04c8E13F4ae87b3732daa087d",
    "usdb_address": "0x42bcF288e51345c6070F37f30332ee5090fC36BF",
    "main_token_address": "0x3067ce754a36d0a2A1b215C4C00315d9Da49EF15",
    "resolver_address": "0xB5FFCCB422531Cf462ec430170f85d8dD3dC3f57",
    "leverage_address": "0xeffb140d821c5B20EFc66346Cf414EeAC8A8FDB2",
    "taxes_address": "0x4501d1279273c44dA483842ED17b5451e7d3A601",
    "vesting_address": "0xedd987c7723B9634b0Aa6161258FED3e89F9094C",
    "private_market_address": "0x28675A82ee3c2e6d2C85887Ea587FbDD3E3C86EE",
}

# Capital allocation (451 USDB available)
STASIS_BUY_USDB = 100  # Step 1: buy STASIS
BORROW_DAYS = 30       # Step 4: loan duration
TOKEN_BUY_USDB = 25    # Step 6: buy into created token
MARKET_SEED = 0        # Step 7: seed liquidity (0 = AMM only)
BET_USDB = 25          # Step 8: prediction bet

# Token config
TOKEN_SYMBOL = "CSTACK"
TOKEN_NAME = "Creator Stack"
TOKEN_HM = 25  # Floor+ (1-90), lower = faster floor rise
TOKEN_START_LP = 0
TOKEN_DESC = "The Creator's Edge Stack â€” a Floor+ token demonstrating how Basis creators build compounding yield positions. Created by GeeGee as a live walkthrough of stacking strategies."
TOKEN_IMAGE = None  # Skip image to avoid 400 error â€” add manually later

# Prediction market config  
MARKET_NAME = "Will an AI agent complete a full Basis stacking strategy by April 2026?"
MARKET_SYMBOL = "AISTACK"
MARKET_END = int(time.time()) + 30 * 24 * 3600  # 30 days from now
MARKET_OPTIONS = ["Yes", "No"]
MARKET_DESC = "Prediction market on whether an AI agent (GeeGee) can successfully execute all layers of the Basis Creator's Edge Stack: yield base, token creation, leveraged position, and prediction bet."
BET_OUTCOME = 0  # 0 = Yes

# â”€â”€ Tracking â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
results = {}
BSCSCAN = "https://bscscan.com/tx/"

def log(step, msg):
    print(f"\n{'='*60}")
    print(f"  STEP {step}: {msg}")
    print(f"{'='*60}")

def record(step, data):
    results[step] = data
    # Save progress after each step
    with open("stack-execution-results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

# â”€â”€ Initialize â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("Initializing BasisClient with contracts.json addresses...")
c = BasisClient.create(private_key=PK, **CONTRACTS)
print(f"Authenticated. Wallet: {c.account.address}")
print(f"API key: {c.api_key[:16]}...")

# Pre-flight checks
erc20_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
usdb = c.web3.eth.contract(address=c.usdb_address, abi=erc20_abi)
usdb_bal = usdb.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
bnb_bal = c.web3.eth.get_balance(Web3.to_checksum_address(WALLET))
print(f"\nPre-flight:")
print(f"  USDB: {usdb_bal/10**18:.2f}")
print(f"  BNB:  {bnb_bal/10**18:.6f}")

fee = c.factory.get_fee_amount()
print(f"  Token creation fee: {fee/10**18:.6f} BNB")

if usdb_bal < STASIS_BUY_USDB * 10**18:
    print("ERROR: Not enough USDB!")
    exit(1)
if bnb_bal < fee * 3:  # Need fee for token + market + some gas
    print(f"WARNING: BNB might be tight ({bnb_bal/10**18:.6f}). Proceeding anyway...")

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# STEP 1: Buy STASIS with USDB
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
log(1, f"Buy {STASIS_BUY_USDB} USDB worth of STASIS")
try:
    amt = STASIS_BUY_USDB * 10**18
    # Estimate output
    path = [c.usdb_address, c.main_token_address]
    est = c.trading.get_amounts_out(amt, path)
    est_val = est[-1] if isinstance(est, (list, tuple)) else est
    print(f"  Estimated STASIS out: {est_val/10**18:.4f}")
    
    result = c.trading.buy(c.main_token_address, amt)
    print(f"  âœ… TX: {BSCSCAN}{result['hash']}")
    
    # Check new STASIS balance
    stasis_contract = c.web3.eth.contract(address=c.main_token_address, abi=erc20_abi)
    stasis_bal = stasis_contract.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
    print(f"  STASIS balance: {stasis_bal/10**18:.4f}")
    
    record("1_buy_stasis", {"tx": result['hash'], "usdb_spent": STASIS_BUY_USDB, "stasis_received": stasis_bal/10**18})
except Exception as e:
    print(f"  âŒ FAILED: {e}")
    traceback.print_exc()
    exit(1)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# STEP 2: Wrap STASIS â†’ wSTASIS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
log(2, "Wrap STASIS â†’ wSTASIS")
try:
    # Wrap all available STASIS
    stasis_contract = c.web3.eth.contract(address=c.main_token_address, abi=erc20_abi)
    stasis_bal = stasis_contract.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
    print(f"  Wrapping {stasis_bal/10**18:.4f} STASIS...")
    
    result = c.staking.buy(stasis_bal)
    print(f"  âœ… TX: {BSCSCAN}{result['hash']}")
    
    # Check wSTASIS
    stake_details = c.staking.get_user_stake_details(WALLET)
    print(f"  wSTASIS balance: {stake_details[0]/10**18:.4f}")
    print(f"  Locked: {stake_details[1]/10**18:.4f}")
    print(f"  Available STASIS: {stake_details[3]/10**18:.4f}")
    
    record("2_wrap_stasis", {"tx": result['hash'], "wstasis_balance": stake_details[0]/10**18})
except Exception as e:
    print(f"  âŒ FAILED: {e}")
    traceback.print_exc()
    exit(1)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# STEP 3: Lock wSTASIS as collateral
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
log(3, "Lock wSTASIS as collateral")
try:
    stake_details = c.staking.get_user_stake_details(WALLET)
    wstasis_bal = stake_details[0]
    locked = stake_details[1]
    free_wstasis = wstasis_bal - locked
    
    if free_wstasis <= 0:
        print("  No free wSTASIS to lock (already locked from before)")
        record("3_lock", {"note": "already locked", "locked": locked/10**18})
    else:
        print(f"  Locking {free_wstasis/10**18:.4f} wSTASIS...")
        result = c.staking.lock(free_wstasis)
        print(f"  âœ… TX: {BSCSCAN}{result['hash']}")
        
        stake_details = c.staking.get_user_stake_details(WALLET)
        print(f"  Now locked: {stake_details[1]/10**18:.4f} wSTASIS")
        record("3_lock", {"tx": result['hash'], "locked": stake_details[1]/10**18})
except Exception as e:
    print(f"  âŒ FAILED: {e}")
    traceback.print_exc()
    exit(1)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# STEP 4: Borrow USDB against locked wSTASIS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
log(4, f"Borrow USDB ({BORROW_DAYS} day loan)")
try:
    # Get available STASIS to borrow against
    available = c.staking.get_available_stasis(WALLET)
    print(f"  Available STASIS for borrowing: {available/10**18:.4f}")
    
    if available <= 0:
        print("  No available STASIS to borrow against. Skipping...")
        record("4_borrow", {"note": "no available collateral"})
    else:
        # Borrow against 80% of available to leave buffer
        borrow_amount = int(available * 80 // 100)
        print(f"  Borrowing against {borrow_amount/10**18:.4f} STASIS...")
        
        result = c.staking.borrow(borrow_amount, BORROW_DAYS)
        print(f"  âœ… TX: {BSCSCAN}{result['hash']}")
        
        # Check USDB balance after borrow
        usdb_after = usdb.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
        print(f"  USDB balance after borrow: {usdb_after/10**18:.2f}")
        record("4_borrow", {"tx": result['hash'], "stasis_pledged": borrow_amount/10**18, "usdb_after": usdb_after/10**18})
except Exception as e:
    print(f"  âŒ FAILED: {e}")
    traceback.print_exc()
    # Don't exit â€” continue with remaining USDB
    record("4_borrow", {"error": str(e)})

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# STEP 5: Create Floor+ token with metadata
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
log(5, f"Create Floor+ token: {TOKEN_SYMBOL}")
try:
    result = c.factory.create_token_with_metadata(
        symbol=TOKEN_SYMBOL,
        name=TOKEN_NAME,
        hybrid_multiplier=TOKEN_HM,
        start_lp=TOKEN_START_LP,
        description=TOKEN_DESC,
        image_url=TOKEN_IMAGE,
        website="https://launchonbasis.com",
        telegram="https://t.me/BasisMarkets",
        twitterx="https://x.com/LaunchOnBasis",
    )
    token_addr = result['token_address']
    print(f"  âœ… Token created: {token_addr}")
    print(f"  TX: {BSCSCAN}{result['hash']}")
    print(f"  Image: {result.get('image_url', 'N/A')}")
    print(f"  Metadata: {result.get('metadata', 'N/A')}")
    
    # Read token state
    state = c.factory.get_token_state(token_addr)
    print(f"  Price: ${int(state['usdPrice'])/10**18:.6f}")
    
    record("5_create_token", {
        "tx": result['hash'],
        "token_address": token_addr,
        "symbol": TOKEN_SYMBOL,
        "name": TOKEN_NAME,
        "hm": TOKEN_HM,
        "image_url": result.get('image_url'),
    })
except Exception as e:
    print(f"  âŒ FAILED: {e}")
    traceback.print_exc()
    # Try without metadata as fallback
    print("  Trying raw create_token as fallback...")
    try:
        result = c.factory._create_token(
            symbol=TOKEN_SYMBOL, name=TOKEN_NAME,
            hybrid_multiplier=TOKEN_HM, frozen=False,
            usdb_for_bonding=0, start_lp=TOKEN_START_LP,
            auto_vest=False, auto_vest_duration=0, gradual_autovest=False,
        )
        print(f"  âœ… Token created (no metadata): TX {BSCSCAN}{result['hash']}")
        # Parse address from logs
        token_created_topic = Web3.keccak(text="TokenCreated(address,string,string,address)").hex()
        for log_entry in result['receipt'].get('logs', []):
            topics = log_entry.get('topics', [])
            if topics:
                t0 = topics[0].hex() if isinstance(topics[0], bytes) else str(topics[0])
                if t0 == token_created_topic and len(topics) > 1:
                    raw = topics[1].hex() if isinstance(topics[1], bytes) else str(topics[1])
                    token_addr = Web3.to_checksum_address("0x" + raw[-40:])
                    print(f"  Token address: {token_addr}")
                    break
        record("5_create_token", {"tx": result['hash'], "token_address": token_addr, "note": "no metadata"})
    except Exception as e2:
        print(f"  âŒ Fallback also failed: {e2}")
        traceback.print_exc()
        exit(1)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# STEP 6: Buy into the created token
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
log(6, f"Buy {TOKEN_BUY_USDB} USDB of {TOKEN_SYMBOL}")
try:
    buy_amt = TOKEN_BUY_USDB * 10**18
    result = c.trading.buy(token_addr, buy_amt)
    print(f"  âœ… TX: {BSCSCAN}{result['hash']}")
    
    # Check token balance
    token_contract = c.web3.eth.contract(address=Web3.to_checksum_address(token_addr), abi=erc20_abi)
    tok_bal = token_contract.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
    print(f"  {TOKEN_SYMBOL} balance: {tok_bal/10**18:.4f}")
    
    state = c.factory.get_token_state(token_addr)
    print(f"  {TOKEN_SYMBOL} price: ${int(state['usdPrice'])/10**18:.6f}")
    
    record("6_buy_token", {"tx": result['hash'], "usdb_spent": TOKEN_BUY_USDB, "tokens_received": tok_bal/10**18})
except Exception as e:
    print(f"  âŒ FAILED: {e}")
    traceback.print_exc()
    record("6_buy_token", {"error": str(e)})

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# STEP 7: Create prediction market
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
log(7, f"Create prediction market: {MARKET_SYMBOL}")
try:
    result = c.prediction_markets.create_market_with_metadata(
        market_name=MARKET_NAME,
        symbol=MARKET_SYMBOL,
        end_time=MARKET_END,
        option_names=MARKET_OPTIONS,
        maintoken=c.main_token_address,
        description=MARKET_DESC,
        image_url=None,  # Skip image for market too
        website="https://launchonbasis.com",
        telegram="https://t.me/BasisMarkets",
        twitterx="https://x.com/LaunchOnBasis",
        seed_amount=MARKET_SEED,
    )
    market_addr = result['market_token_address']
    print(f"  âœ… Market created: {market_addr}")
    print(f"  TX: {BSCSCAN}{result['hash']}")
    
    # Read market data
    md = c.prediction_markets.get_market_data(market_addr)
    print(f"  Name: {md[4]}")
    print(f"  Options: {MARKET_OPTIONS}")
    
    record("7_create_market", {
        "tx": result['hash'],
        "market_address": market_addr,
        "symbol": MARKET_SYMBOL,
        "name": MARKET_NAME,
        "options": MARKET_OPTIONS,
        "end_time": MARKET_END,
    })
except Exception as e:
    print(f"  âŒ FAILED: {e}")
    traceback.print_exc()
    record("7_create_market", {"error": str(e)})
    market_addr = None

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# STEP 8: Bet on the prediction market
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
if market_addr:
    log(8, f"Bet {BET_USDB} USDB on '{MARKET_OPTIONS[BET_OUTCOME]}'")
    try:
        bet_amt = BET_USDB * 10**18
        result = c.prediction_markets.buy(
            market_token=market_addr,
            outcome_id=BET_OUTCOME,
            input_token=c.usdb_address,
            input_amount=bet_amt,
            min_usdb=0,
            min_shares=0,
        )
        print(f"  âœ… TX: {BSCSCAN}{result['hash']}")
        
        # Check shares
        shares = c.prediction_markets.get_user_shares(market_addr, WALLET, BET_OUTCOME)
        print(f"  Shares on '{MARKET_OPTIONS[BET_OUTCOME]}': {shares/10**18:.4f}")
        
        record("8_bet", {"tx": result['hash'], "usdb_bet": BET_USDB, "outcome": MARKET_OPTIONS[BET_OUTCOME], "shares": shares/10**18})
    except Exception as e:
        print(f"  âŒ FAILED: {e}")
        traceback.print_exc()
        record("8_bet", {"error": str(e)})
else:
    print("\n  Skipping bet â€” no market was created.")

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# SUMMARY
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
print("\n" + "="*60)
print("  CREATOR'S EDGE STACK â€” EXECUTION SUMMARY")
print("="*60)

# Final balances
usdb_final = usdb.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
bnb_final = c.web3.eth.get_balance(Web3.to_checksum_address(WALLET))
stake_final = c.staking.get_user_stake_details(WALLET)

print(f"\n  Final USDB:    {usdb_final/10**18:.2f}")
print(f"  Final BNB:     {bnb_final/10**18:.6f}")
print(f"  wSTASIS:       {stake_final[0]/10**18:.4f}")
print(f"  Locked:        {stake_final[1]/10**18:.4f}")

for step, data in results.items():
    tx = data.get('tx', data.get('note', data.get('error', '?')))
    print(f"\n  {step}: {tx[:16]}..." if len(str(tx)) > 16 else f"\n  {step}: {tx}")

print(f"\n  Results saved to: stack-execution-results.json")
print("="*60)

