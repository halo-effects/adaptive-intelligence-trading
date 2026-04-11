"""Check on-chain token types and floor prices."""
import sys, json
sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient
from web3 import Web3

PRIVATE_KEY = "062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"
client = BasisClient.create(private_key=PRIVATE_KEY)

# ABI for checking token properties
TOKEN_ABI = [
    {"inputs":[],"name":"getTokenPrice","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"getUSDPrice","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"floorPrice","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"getFloorPrice","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"bondingCurveType","outputs":[{"name":"","type":"uint8"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"tokenType","outputs":[{"name":"","type":"uint8"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"getBuyTax","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"buyTax","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"isPredictionMarket","outputs":[{"name":"","type":"bool"}],"stateMutability":"view","type":"function"},
]

tokens = [
    ("LVTHN", "0xFf84209eBCCAc7328070E0011e973451c4a045F9"),
    ("MRINA", "0x3a0C6CE442Ad0F1E89cE38a7e773000903034A86"),
    ("TMPST", "0xC43DF80EFc3B29925BAbd744CD8AF28A0BE9AE3a"),
    ("BRINE", "0xB4916b462a69b9ce7be9e74138683D15208aB12f"),
    ("AGNT", "0x43e256d9A65bFcFCFe65154d9eDC058dcaE7B515"),
    ("PRINT", "0x0068bb0090906ce85e9510388696e8447455cf91"),
    ("GEEGEE", "0xbb8c70bDC0e7cE8a0e1D5a923b7FCB6a1fF2a9e2"),
    ("STASIS", client.main_token_address),
]

for name, addr in tokens:
    print(f"\n--- {name} ({addr[:12]}...) ---")
    contract = client.web3.eth.contract(address=Web3.to_checksum_address(addr), abi=TOKEN_ABI)
    
    for fn_name in ['getTokenPrice', 'getUSDPrice', 'totalSupply', 'floorPrice', 'getFloorPrice', 'bondingCurveType', 'tokenType', 'getBuyTax', 'buyTax', 'isPredictionMarket']:
        try:
            result = getattr(contract.functions, fn_name)().call()
            if fn_name in ['getTokenPrice', 'getUSDPrice', 'floorPrice', 'getFloorPrice', 'totalSupply']:
                print(f"  {fn_name}: {result} ({result/10**18:.6f})")
            elif fn_name in ['getBuyTax', 'buyTax']:
                print(f"  {fn_name}: {result} ({result/100:.1f}%)")
            else:
                print(f"  {fn_name}: {result}")
        except Exception as e:
            err = str(e)[:60]
            print(f"  {fn_name}: N/A ({err})")

# Check BNB balance
w = Web3.to_checksum_address("0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2")
bnb = client.web3.eth.get_balance(w)
print(f"\n\nBNB balance: {Web3.from_wei(bnb, 'ether')} BNB")
