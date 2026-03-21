import json
import os
from pathlib import Path
from web3 import Web3

def load_abi(filename: str):
    abi_path = Path(__file__).parent.parent / 'abis' / filename
    with open(abi_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get('abi', [])

class FactoryModule:
    def __init__(self, client, factory_address: str):
        self.client = client
        self.factory_address = Web3.to_checksum_address(factory_address)
        self.factory_abi = load_abi('ATokenFactory.json')
        self.token_abi = load_abi('FACTORYTOKEN.json')
        self.contract = self.client.web3.eth.contract(address=self.factory_address, abi=self.factory_abi)

    def _build_and_send_tx(self, function_call, value=0):
        if not self.client.account:
            raise ValueError("Stateful initialization (private_key) is required for write methods.")
        
        tx = function_call.build_transaction({
            'from': self.client.account.address,
            'nonce': self.client.web3.eth.get_transaction_count(self.client.account.address),
            'value': value,
            # Let Web3.py estimate gas and gas price automatically
        })

        signed_tx = self.client.web3.eth.account.sign_transaction(tx, private_key=self.client.account.key)
        tx_hash = self.client.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = self.client.web3.eth.wait_for_transaction_receipt(tx_hash)
        
        return {
            'hash': tx_hash.hex(),
            'receipt': receipt
        }

    def _create_token(
        self,
        symbol: str,
        name: str,
        hybrid_multiplier: int,
        frozen: bool,
        usdb_for_bonding: int,
        start_lp: int,
        auto_vest: bool,
        auto_vest_duration: int,
        gradual_autovest: bool
    ):
        fee_amount = self.contract.functions.feeAmount().call()
        func = self.contract.functions.createToken(
            symbol,
            name,
            hybrid_multiplier,
            frozen,
            usdb_for_bonding,
            start_lp,
            auto_vest,
            auto_vest_duration,
            gradual_autovest
        )
        return self._build_and_send_tx(func, value=fee_amount)

    def create_token_with_metadata(
        self,
        symbol: str,
        name: str,
        hybrid_multiplier: int,
        start_lp: int,
        description: str = None,
        image_url: str = None,
        website: str = None,
        telegram: str = None,
        twitterx: str = None,
        frozen: bool = False,
        usdb_for_bonding: int = 0,
        auto_vest: bool = False,
        auto_vest_duration: int = 0,
        gradual_autovest: bool = False,
    ):
        """Creates a token and registers its metadata on IPFS in one call.

        Requires SIWE authentication (call client.authenticate() first).

        1. Creates the token on-chain
        2. Parses the new token address from logs
        3. Downloads, resizes (512x512 WebP), and uploads the image to IPFS
        4. Creates metadata on IPFS

        Returns dict with hash, receipt, token_address, image_url, metadata.
        """
        # 1. Create token on-chain
        create_result = self._create_token(
            symbol=symbol, name=name,
            hybrid_multiplier=hybrid_multiplier, frozen=frozen,
            usdb_for_bonding=usdb_for_bonding, start_lp=start_lp,
            auto_vest=auto_vest, auto_vest_duration=auto_vest_duration,
            gradual_autovest=gradual_autovest,
        )

        receipt = create_result['receipt']
        if receipt.get('status') == 0:
            raise RuntimeError(f"Token creation reverted (tx: {create_result['hash']})")

        # 2. Parse token address from TokenCreated event
        token_created_topic = Web3.keccak(text="TokenCreated(address,string,string,address)").hex()
        factory_lower = self.factory_address.lower()
        token_address = None
        for log_entry in receipt.get('logs', []):
            addr = log_entry.get('address', '')
            if addr.lower() != factory_lower:
                continue
            topics = log_entry.get('topics', [])
            if not topics:
                continue
            t0 = topics[0].hex() if isinstance(topics[0], bytes) else str(topics[0])
            if t0 == token_created_topic and len(topics) > 1:
                raw = topics[1].hex() if isinstance(topics[1], bytes) else str(topics[1])
                token_address = Web3.to_checksum_address("0x" + raw[-40:])
                break

        if not token_address:
            raise RuntimeError("Could not extract token address from creation logs.")

        # 3. Upload image if provided
        uploaded_image_url = None
        if image_url:
            uploaded_image_url = self.client.api.upload_image_from_url(image_url, contract_address=token_address)

        # 4. Create metadata on IPFS
        metadata = self.client.api.update_metadata(
            address=token_address,
            description=description,
            image=uploaded_image_url,
            website=website,
            telegram=telegram,
            twitterx=twitterx,
        )

        return {
            'hash': create_result['hash'],
            'receipt': receipt,
            'token_address': token_address,
            'image_url': uploaded_image_url,
            'metadata': metadata,
        }

    def disable_freeze(self, token_address: str):
        checksum_addr = Web3.to_checksum_address(token_address)
        token_contract = self.client.web3.eth.contract(address=checksum_addr, abi=self.token_abi)
        func = token_contract.functions.DisableFreeze()
        return self._build_and_send_tx(func)

    def set_whitelisted_wallet(self, token_address: str, wallets: list[str], amount: int, tag: str):
        checksum_addr = Web3.to_checksum_address(token_address)
        token_contract = self.client.web3.eth.contract(address=checksum_addr, abi=self.token_abi)
        checksum_wallets = [Web3.to_checksum_address(w) for w in wallets]
        func = token_contract.functions.SetWhitelistedWallet(checksum_wallets, amount, tag)
        return self._build_and_send_tx(func)

    def is_ecosystem_token(self, token_address: str) -> bool:
        """Checks if a token is an ecosystem token."""
        return self.contract.functions.isEcosystemToken(Web3.to_checksum_address(token_address)).call()

    def get_tokens_by_creator(self, creator: str) -> list:
        """Returns all tokens created by a given address."""
        return self.contract.functions.getTokensByCreator(Web3.to_checksum_address(creator)).call()

    def get_fee_amount(self) -> int:
        """Returns the current fee amount for token creation."""
        return self.contract.functions.feeAmount().call()

    def remove_whitelist(self, token_address: str, wallet: str):
        """Removes a wallet from a token's whitelist."""
        checksum_token = Web3.to_checksum_address(token_address)
        checksum_wallet = Web3.to_checksum_address(wallet)
        token_contract = self.client.web3.eth.contract(address=checksum_token, abi=self.token_abi)
        func = token_contract.functions.RemoveWhitelist(checksum_wallet)
        return self._build_and_send_tx(func)

    def claim_rewards(self, token_address: str):
        """Claim accumulated USDB rewards from presale shares on a factory token."""
        checksum_addr = Web3.to_checksum_address(token_address)
        token_contract = self.client.web3.eth.contract(address=checksum_addr, abi=self.token_abi)
        func = token_contract.functions.claimRewards()
        return self._build_and_send_tx(func)

    def get_claimable_rewards(self, token_address: str, investor: str) -> int:
        """Get claimable USDB rewards for an address on a factory token."""
        checksum_addr = Web3.to_checksum_address(token_address)
        checksum_investor = Web3.to_checksum_address(investor)
        token_contract = self.client.web3.eth.contract(address=checksum_addr, abi=self.token_abi)
        return token_contract.functions.getClaimableRewards(checksum_investor).call()

    def get_token_state(self, token_address: str):
        checksum_addr = Web3.to_checksum_address(token_address)
        token_contract = self.client.web3.eth.contract(address=checksum_addr, abi=self.token_abi)
        
        frozen = token_contract.functions.frozen().call()
        has_bonded = token_contract.functions.hasBonded().call()
        total_supply = token_contract.functions.totalSupply().call()
        usd_price = token_contract.functions.getUSDPrice().call()

        return {
            'frozen': frozen,
            'hasBonded': has_bonded,
            'totalSupply': str(total_supply),
            'usdPrice': str(usd_price)
        }
