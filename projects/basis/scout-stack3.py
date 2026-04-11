"""Deep scout - get token details and identify types."""
import sys, json
sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient
from web3 import Web3

PRIVATE_KEY = "062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"
client = BasisClient.create(private_key=PRIVATE_KEY)

# Get detailed info on interesting tokens
targets = [
    ("PRINT - Fed Printer", "0x0068bb0090906ce85e9510388696e8447455cf91"),
    ("LVTHN - Leviathan DAO", "0xFf84209eBCCAc7328070E0011e973451c4a045F9"),
    ("MRINA - Mariana Token", "0x3a0C6CE442Ad0F1E89cE38a7e773000903034A86"),
    ("TMPST - Tempest Protocol", "0xC43DF80EFc3B29925BAbd744CD8AF28A0BE9AE3a"),
    ("BRINE - Brine Labs", "0xB4916b462a69b9ce7be9e74138683D15208aB12f"),
    ("AGNT - Agent Protocol", "0x43e256d9A65bFcFCFe65154d9eDC058dcaE7B515"),
]

print("=== TOKEN DETAILS ===\n")
for name, addr in targets:
    try:
        info = client.api.get_token(addr)
        print(f"--- {name} ---")
        # Print all keys to understand structure
        if isinstance(info, dict):
            for k, v in info.items():
                if k not in ('abi',):  # skip ABI
                    val_str = str(v)[:100] if len(str(v)) > 100 else str(v)
                    print(f"  {k}: {val_str}")
        print()
    except Exception as e:
        print(f"  {name}: ERROR - {e}\n")

# Also get on-chain prices for the non-prediction tokens
print("\n=== ON-CHAIN PRICES ===\n")
for name, addr in targets:
    try:
        price = client.trading.get_usd_price(addr)
        token_price = client.trading.get_token_price(addr)
        print(f"  {name}: USD={int(price)/10**18:.6f}, TokenPrice={int(token_price)/10**18:.6f}")
    except Exception as e:
        print(f"  {name}: price error - {e}")

# Check all tokens page 2 and 3 for more Floor+ options
print("\n=== MORE TOKENS (page 2-3) ===\n")
for page in [2, 3]:
    tokens = client.api.get_tokens(sort="newest", limit=20, page=page)
    token_list = tokens if isinstance(tokens, list) else tokens.get('tokens', tokens.get('data', []))
    for t in (token_list if isinstance(token_list, list) else []):
        if isinstance(t, dict):
            name = t.get('name', '?')
            symbol = t.get('symbol', '?')
            addr = t.get('address', '?')
            created = t.get('createdAt', '?')
            print(f"  [{symbol}] {name} | {addr[:12]}... | {created}")
