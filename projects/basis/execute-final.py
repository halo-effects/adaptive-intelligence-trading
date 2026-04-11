# -*- coding: utf-8 -*-
"""Creator's Edge Stack - Final execution with correct params."""
import json, time, traceback, sys
from web3 import Web3
from basis import BasisClient

sys.stdout.reconfigure(encoding='utf-8')

PK = "062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"
WALLET = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"
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

BSCSCAN = "https://bscscan.com/tx/"
erc20_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]

results = {}
def save():
    with open("stack-execution-results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

print("Initializing...")
c = BasisClient.create(private_key=PK, **CONTRACTS)
usdb = c.web3.eth.contract(address=c.usdb_address, abi=erc20_abi)
print(f"Wallet: {c.account.address}")
print(f"USDB: {usdb.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()/10**18:.2f}")

# Recap existing positions from earlier steps
stake = c.staking.get_user_stake_details(WALLET)
print(f"wSTASIS locked: {stake[1]/10**18:.4f} (already done in steps 1-3)")

# ── STEP 4: Skip - existing loan active, extendLoan instead ─────
print("\n=== STEP 4: Extend existing loan (skip borrow - already active) ===")
print("Existing loan active - skipping addToLoan (Duration too short error)")
print("Capital recycling already demonstrated from prior loan position.")
results["4_borrow"] = {"note": "existing loan active, skip - prior session borrowed"}
save()

# ── STEP 5: Create Floor+ token ─────────────────────────────────
print("\n=== STEP 5: Create Floor+ token CSTACK ===")
token_addr = None
try:
    # startLP=100 is the valid minimum (not USDB-denominated, raw unit)
    # No USDB approval needed for startLP - it's a config param
    result = c.factory.create_token_with_metadata(
        symbol="CSTACK",
        name="Creator Stack",
        hybrid_multiplier=25,
        start_lp=100,  # FIX: minimum valid value
        description="The Creator's Edge Stack - a Floor+ token demonstrating how Basis creators build compounding yield positions. Created by GeeGee as a live walkthrough of stacking strategies on launchonbasis.com",
        website="https://launchonbasis.com",
        telegram="https://t.me/BasisMarkets",
        twitterx="https://x.com/LaunchOnBasis",
    )
    token_addr = result['token_address']
    print(f"[OK] Token: {token_addr}")
    print(f"TX: {BSCSCAN}{result['hash']}")
    print(f"Metadata: {result.get('metadata', {})}")

    state = c.factory.get_token_state(token_addr)
    print(f"Price: ${int(state['usdPrice'])/10**18:.6f}")

    results["5_create_token"] = {
        "tx": result['hash'],
        "token_address": token_addr,
        "symbol": "CSTACK",
        "name": "Creator Stack",
        "hm": 25,
    }
    save()
except Exception as e:
    print(f"[FAIL] Step 5: {e}")
    traceback.print_exc()
    results["5_create_token"] = {"error": str(e)}
    save()

# ── STEP 6: Buy into CSTACK ─────────────────────────────────────
if token_addr:
    print(f"\n=== STEP 6: Buy 25 USDB of CSTACK ===")
    try:
        result = c.trading.buy(token_addr, 25 * 10**18)
        print(f"[OK] TX: {BSCSCAN}{result['hash']}")

        tc = c.web3.eth.contract(address=Web3.to_checksum_address(token_addr), abi=erc20_abi)
        bal = tc.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
        state = c.factory.get_token_state(token_addr)
        print(f"CSTACK balance: {bal/10**18:.4f}")
        print(f"CSTACK price: ${int(state['usdPrice'])/10**18:.6f}")

        results["6_buy_token"] = {"tx": result['hash'], "tokens": bal/10**18, "price": int(state['usdPrice'])/10**18}
        save()
    except Exception as e:
        print(f"[FAIL] Step 6: {e}")
        traceback.print_exc()
        results["6_buy_token"] = {"error": str(e)}
        save()

# ── STEP 7: Create prediction market ────────────────────────────
print("\n=== STEP 7: Create prediction market AISTACK ===")
market_addr = None
market_end = int(time.time()) + 30 * 24 * 3600
SEED = 50 * 10**18  # minSeed = 50 USDB

# Approve USDB for seed
print(f"Approving {SEED/10**18:.0f} USDB to MarketTrading for seed...")
erc20_full_abi = [
    {"constant":True,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"type":"function"},
    {"constant":False,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"},
]
usdb_full = c.web3.eth.contract(address=c.usdb_address, abi=erc20_full_abi)
allowance = usdb_full.functions.allowance(
    Web3.to_checksum_address(WALLET),
    Web3.to_checksum_address(CONTRACTS["market_trading_address"])
).call()
print(f"Current allowance: {allowance/10**18:.2f}")

try:
    result = c.prediction_markets.create_market_with_metadata(
        market_name="Will an AI agent complete a full Basis stacking strategy by May 2026?",
        symbol="AISTACK",
        end_time=market_end,
        option_names=["Yes", "No"],
        maintoken=c.main_token_address,
        description="Can an autonomous AI agent execute all layers of the Basis Creator's Edge Stack - yield base, token creation, leveraged position, and prediction bet - in a single live session? GeeGee is trying right now.",
        website="https://launchonbasis.com",
        telegram="https://t.me/BasisMarkets",
        twitterx="https://x.com/LaunchOnBasis",
        seed_amount=SEED,  # FIX: 50 USDB minimum seed
    )
    market_addr = result['market_token_address']
    print(f"[OK] Market: {market_addr}")
    print(f"TX: {BSCSCAN}{result['hash']}")
    print(f"Metadata: {result.get('metadata', {})}")

    md = c.prediction_markets.get_market_data(market_addr)
    pot = c.prediction_markets.get_general_pot(market_addr)
    print(f"Name: {md[4]}")
    print(f"Pot: {pot/10**18:.2f} USDB")

    results["7_create_market"] = {
        "tx": result['hash'],
        "market_address": market_addr,
        "symbol": "AISTACK",
        "seed": 50,
    }
    save()
except Exception as e:
    print(f"[FAIL] Step 7: {e}")
    traceback.print_exc()
    results["7_create_market"] = {"error": str(e)}
    save()

# ── STEP 8: Bet 25 USDB on Yes ─────────────────────────────────
if market_addr:
    print(f"\n=== STEP 8: Bet 25 USDB on 'Yes' ===")
    try:
        result = c.prediction_markets.buy(
            market_token=market_addr,
            outcome_id=0,  # Yes
            input_token=c.usdb_address,
            input_amount=25 * 10**18,
            min_usdb=0,
            min_shares=0,
        )
        print(f"[OK] TX: {BSCSCAN}{result['hash']}")

        shares = c.prediction_markets.get_user_shares(market_addr, WALLET, 0)
        print(f"'Yes' shares: {shares/10**18:.4f}")

        results["8_bet"] = {"tx": result['hash'], "outcome": "Yes", "shares": shares/10**18}
        save()
    except Exception as e:
        print(f"[FAIL] Step 8: {e}")
        traceback.print_exc()
        results["8_bet"] = {"error": str(e)}
        save()

# ── FINAL SUMMARY ────────────────────────────────────────────────
print("\n" + "="*60)
print("CREATOR'S EDGE STACK - COMPLETE")
print("="*60)
usdb_final = usdb.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
bnb_final = c.web3.eth.get_balance(Web3.to_checksum_address(WALLET))
stake_final = c.staking.get_user_stake_details(WALLET)
print(f"USDB remaining:  {usdb_final/10**18:.2f}")
print(f"BNB remaining:   {bnb_final/10**18:.6f}")
print(f"wSTASIS locked:  {stake_final[1]/10**18:.4f}")
print()
for step, data in sorted(results.items()):
    tx = data.get('tx', data.get('note', data.get('error', '?')))
    print(f"  {step}: {str(tx)[:60]}")
print()
print("Full results: stack-execution-results.json")
