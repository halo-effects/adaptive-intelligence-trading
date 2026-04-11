"""Get full token details to find Floor+ types."""
import sys, json
sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient

PRIVATE_KEY = "062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"
client = BasisClient.create(private_key=PRIVATE_KEY)

# Check a few tokens for their type
targets = [
    "0xFf84209eBCCAc7328070E0011e973451c4a045F9",  # LVTHN
    "0x3a0C6CE442Ad0F1E89cE38a7e773000903034A86",  # MRINA
    "0xC43DF80EFc3B29925BAbd744CD8AF28A0BE9AE3a",  # TMPST
    "0xB4916b462a69b9ce7be9e74138683D15208aB12f",  # BRINE
    "0x43e256d9A65bFcFCFe65154d9eDC058dcaE7B515",  # AGNT
    "0x0068bb0090906ce85e9510388696e8447455cf91",  # PRINT
    "0xF758ef7f7e2d4250C7c03e06FE5Acf4F6E3b71dA",  # CLAWBACK
    "0xbb8c70bDC0e7cE8a0e1D5a923b7FCB6a1fF2a9e2",  # GEEGEE
    "0x1679223d140c3E8a4Ae11f82ba84f0c7E5e58d34",  # PELCN
    "0x46F92EFB3C798e5e2D5A1e23aeaDC7e01F02ce0c",  # SIRENE
]

for addr in targets:
    try:
        info = client.api.get_token(addr)
        d = info.get('data', info) if isinstance(info, dict) else info
        if isinstance(d, dict):
            name = d.get('name', '?')
            symbol = d.get('symbol', '?')
            ttype = d.get('tokenType', d.get('type', d.get('bondingCurveType', '?')))
            price = d.get('price', d.get('currentPrice', '?'))
            floor = d.get('floorPrice', d.get('floor', '-'))
            mcap = d.get('marketCap', '?')
            supply = d.get('totalSupply', d.get('supply', '?'))
            is_pred = d.get('isPrediction', d.get('isPredictionMarket', '?'))
            tax = d.get('buyTax', d.get('tax', '?'))
            
            # Look for any type-related keys
            type_keys = {k: v for k, v in d.items() if any(x in k.lower() for x in ['type', 'floor', 'stable', 'predict', 'bonding', 'curve', 'kind', 'category'])}
            
            print(f"[{symbol}] {name}")
            print(f"  type={ttype} | isPred={is_pred} | price={price} | floor={floor}")
            print(f"  mcap={mcap} | tax={tax}")
            print(f"  type-related keys: {type_keys}")
            print()
    except Exception as e:
        print(f"  {addr[:12]}: ERROR - {e}\n")
