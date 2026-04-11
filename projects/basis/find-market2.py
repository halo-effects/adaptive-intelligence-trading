"""Find market from TX receipt."""
import sys
sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient
from web3 import Web3

client = BasisClient(private_key="062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4")
WALLET = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"

# Market creation tx
market_tx_hash = "0x0a4c4889183302fdf632e9d17bb7c7a32400e11e19daccfcc85c521372c51955"
receipt = client.web3.eth.get_transaction_receipt(market_tx_hash)

print(f"TX Status: {receipt.status}")
print(f"Gas used: {receipt.gasUsed}")
print(f"Logs: {len(receipt.logs)}")

# Look for MarketCreated event
market_created_sig = Web3.keccak(text="MarketCreated(address,address,address)").hex()
market_trading = "0xCb64910a19B3641eb600b904741a074578Dda3F7".lower()

for i, log in enumerate(receipt.logs):
    addr = log.address.lower() if hasattr(log, 'address') else log.get('address', '').lower()
    topics = log.topics if hasattr(log, 'topics') else log.get('topics', [])
    
    if topics:
        t0 = topics[0].hex() if isinstance(topics[0], bytes) else str(topics[0])
        if t0 == market_created_sig:
            print(f"\n*** MarketCreated event found in log {i}! ***")
            for j, topic in enumerate(topics):
                raw = topic.hex() if isinstance(topic, bytes) else str(topic)
                if j > 0:
                    extracted_addr = "0x" + raw[-40:]
                    print(f"  Topic {j}: {extracted_addr}")
    
    # Also print all non-trivial logs
    if addr == market_trading:
        print(f"\nLog {i} from MarketTrading:")
        for j, topic in enumerate(topics):
            raw = topic.hex() if isinstance(topic, bytes) else str(topic)
            print(f"  Topic {j}: {raw[:66]}")

# Also check: was the previous market creation (which I called create_market) actually creating a token?
# The DSTACK token creation tx
dstack_tx = "0xa82fb839008f2d400b18c8b3ebc10cb7867821e3615b7595aaa6a6c04816b66c"
dstack_receipt = client.web3.eth.get_transaction_receipt(dstack_tx)
print(f"\n\nDSTACK TX Status: {dstack_receipt.status}")

# BNB balance
bnb = client.web3.eth.get_balance(Web3.to_checksum_address(WALLET))
print(f"\nBNB: {Web3.from_wei(bnb, 'ether')}")
