"""Final scout: check hybridMultiplier on-chain for all non-prediction tokens."""
import sys
sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient
from web3 import Web3

client = BasisClient.create(private_key="062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4")

HM_ABI = [{"inputs":[],"name":"hybridMultiplier","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]

tokens = [
    ("LVTHN", "0xFf84209eBCCAc7328070E0011e973451c4a045F9"),
    ("MRINA", "0x3a0C6CE442Ad0F1E89cE38a7e773000903034A86"),
    ("TMPST", "0xC43DF80EFc3B29925BAbd744CD8AF28A0BE9AE3a"),
    ("BRINE", "0xB4916b462a69b9ce7be9e74138683D15208aB12f"),
    ("AGNT", "0x43e256d9A65bFcFCFe65154d9eDC058dcaE7B515"),
    ("PRINT", "0x0068bb0090906ce85e9510388696e8447455cf91"),
]

print("=== TOKEN TYPES (on-chain hybridMultiplier) ===\n")
floor_plus = []
for sym, addr in tokens:
    try:
        c = client.web3.eth.contract(address=Web3.to_checksum_address(addr), abi=HM_ABI)
        hm = c.functions.hybridMultiplier().call()
        usd_price = int(client.trading.get_usd_price(addr)) / 10**18
        token_type = "Stable+" if hm == 100 else f"Floor+ (hm={hm})"
        print(f"  {sym}: {token_type} | USD ${usd_price:.4f}")
        if hm < 100:
            floor_plus.append((sym, addr, hm, usd_price))
    except Exception as e:
        print(f"  {sym}: ERROR - {e}")

print(f"\n=== FLOOR+ TOKENS (best for Stack 2) ===\n")
for sym, addr, hm, price in sorted(floor_plus, key=lambda x: x[3]):
    print(f"  {sym}: hm={hm}, price=${price:.4f}, addr={addr}")

# Check prediction markets for the bet
print(f"\n=== PREDICTION MARKETS ===\n")
ROUTER = "0x69e4b11346f928f29Affe6B52a8e3Ebd115DE7a6"
pred_markets = [
    ("BAS1K - 1000 agents", "0x5E36ac438650d9548E72Ce41d3225913a7EaEFb8"),
    ("FEDCUT - Fed rate cut", "0xe13a8f12b5c1df2bfdaee169add44587dd7e2c06"),
    ("TGEQ2 - BASIS launch", "0x22acB59faEBDEf1133016D96752Ab3366aB3bFC1"),
    ("CLAUDE5 - Claude 5", "0x30151243fb21BDda761F628e09F6783aE51107D2"),
]

for name, addr in pred_markets:
    try:
        outcomes = client.market_reader.get_all_outcomes(ROUTER, addr)
        market_data = client.prediction_markets.get_market_data(addr)
        end_time = market_data[6] if isinstance(market_data, (list, tuple)) else market_data.get("endTime", "?")
        pot = market_data[10] if isinstance(market_data, (list, tuple)) else market_data.get("generalPot", "?")
        pot_usdb = int(pot) / 10**18 if isinstance(pot, int) else "?"
        
        print(f"  {name}")
        print(f"    Pot: ${pot_usdb} USDB | EndTime: {end_time}")
        for o in outcomes:
            oname = o[1] if isinstance(o, (list, tuple)) else o.get("name", "?")
            prob = o[6] if isinstance(o, (list, tuple)) else o.get("probability", "?")
            prob_pct = int(prob) / 10**16 if isinstance(prob, int) else "?"
            print(f"    [{oname}]: {prob_pct:.1f}%")
        print()
    except Exception as e:
        print(f"  {name}: ERROR - {e}")

# Check BNB
w = Web3.to_checksum_address("0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2")
bnb = client.web3.eth.get_balance(w)
print(f"\nBNB balance: {Web3.from_wei(bnb, 'ether')} BNB")
