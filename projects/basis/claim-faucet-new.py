"""Claim USDB from faucet on new deployment."""
from web3 import Web3

RPC = "https://bsc-dataseed.binance.org/"
USDB = "0x217B82e4bAc4E4647B1F189F33554229Ce27c51A"
WALLET = "0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2"
PRIVATE_KEY = "062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"

FAUCET_ABI = [
    {
        "inputs": [],
        "name": "faucet",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

ERC20_ABI = [
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

w3 = Web3(Web3.HTTPProvider(RPC))
print(f"Connected: {w3.is_connected()}, Chain: {w3.eth.chain_id}")

usdb = w3.eth.contract(address=Web3.to_checksum_address(USDB), abi=FAUCET_ABI + ERC20_ABI)

# Check balance before
balance_before = usdb.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
print(f"USDB balance before: {balance_before / 10**18:.2f}")

# Build faucet tx
nonce = w3.eth.get_transaction_count(Web3.to_checksum_address(WALLET))
tx = usdb.functions.faucet().build_transaction({
    "from": Web3.to_checksum_address(WALLET),
    "nonce": nonce,
    "gas": 100000,
    "gasPrice": w3.eth.gas_price,
    "chainId": 56,
})

# Sign and send
signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f"Tx sent: {tx_hash.hex()}")

# Wait for receipt
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
print(f"Status: {'SUCCESS' if receipt.status == 1 else 'FAILED'}")
print(f"Gas used: {receipt.gasUsed}")

# Check balance after
balance_after = usdb.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
print(f"USDB balance after: {balance_after / 10**18:.2f}")
print(f"Claimed: {(balance_after - balance_before) / 10**18:.2f} USDB")
