from web3 import Web3
from .factory import load_abi

class PredictionMarketsModule:
    def __init__(self, client, market_trading_address: str):
        self.client = client
        self.market_trading_address = Web3.to_checksum_address(market_trading_address)
        self.market_trading_abi = load_abi('AMarketTrading.json')
        self.erc20_abi = load_abi('IERC20.json')
        self.contract = self.client.web3.eth.contract(address=self.market_trading_address, abi=self.market_trading_abi)

    def _approve_if_needed(self, token_address: str, amount: int):
        if not self.client.account:
            raise ValueError("Wallet account is required for approval.")

        checksum_addr = Web3.to_checksum_address(token_address)
        token_contract = self.client.web3.eth.contract(address=checksum_addr, abi=self.erc20_abi)
        
        allowance = token_contract.functions.allowance(
            self.client.account.address, self.market_trading_address
        ).call()

        if allowance < amount:
            func = token_contract.functions.approve(self.market_trading_address, amount)
            tx = func.build_transaction({
                'from': self.client.account.address,
                'nonce': self.client.web3.eth.get_transaction_count(self.client.account.address),
            })
            signed_tx = self.client.web3.eth.account.sign_transaction(tx, private_key=self.client.account.key)
            tx_hash = self.client.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            self.client.web3.eth.wait_for_transaction_receipt(tx_hash)

    def _build_and_send_tx(self, function_call):
        if not self.client.account:
            raise ValueError("Stateful initialization (private_key) is required for write methods.")
        
        tx = function_call.build_transaction({
            'from': self.client.account.address,
            'nonce': self.client.web3.eth.get_transaction_count(self.client.account.address),
        })

        signed_tx = self.client.web3.eth.account.sign_transaction(tx, private_key=self.client.account.key)
        tx_hash = self.client.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = self.client.web3.eth.wait_for_transaction_receipt(tx_hash)
        
        return {
            'hash': tx_hash.hex(),
            'receipt': receipt
        }

    def _create_market(self, market_name: str, symbol: str, end_time: int, option_names: list[str], maintoken: str, frozen: bool, bonding: int, seed_amount: int = 0):
        """Internal: creates a market on-chain. Use create_market_with_metadata(). Auto-fetches and attaches the creation fee."""
        checksum_maintoken = Web3.to_checksum_address(maintoken)
        # Read ecosystem's factory address, then fetch fee
        eco_data = self.contract.functions.ecosystems(checksum_maintoken).call()
        factory_address = eco_data[0]  # factory is first field in Ecosystem struct
        factory_abi = load_abi('ATokenFactory.json')
        factory_contract = self.client.web3.eth.contract(address=factory_address, abi=factory_abi)
        fee_amount = factory_contract.functions.feeAmount().call()

        # Auto-approve USDB for seed amount if needed
        if seed_amount > 0:
            self._approve_if_needed(self.client.usdb_address, seed_amount)

        func = self.contract.functions.createMarket(market_name, symbol, end_time, option_names, checksum_maintoken, frozen, bonding, seed_amount)
        if not self.client.account:
            raise ValueError("Stateful initialization (private_key) is required for write methods.")
        tx = func.build_transaction({
            'from': self.client.account.address,
            'nonce': self.client.web3.eth.get_transaction_count(self.client.account.address),
            'value': fee_amount,
        })
        signed_tx = self.client.web3.eth.account.sign_transaction(tx, private_key=self.client.account.key)
        tx_hash = self.client.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = self.client.web3.eth.wait_for_transaction_receipt(tx_hash)
        return {'hash': tx_hash.hex(), 'receipt': receipt}

    def create_market_with_metadata(
        self,
        market_name: str,
        symbol: str,
        end_time: int,
        option_names: list[str],
        maintoken: str,
        description: str = None,
        image_url: str = None,
        website: str = None,
        telegram: str = None,
        twitterx: str = None,
        frozen: bool = False,
        bonding: int = 0,
        seed_amount: int = 0,
    ):
        """Creates a prediction market and registers metadata on IPFS in one call.

        Requires SIWE authentication.
        Returns dict with hash, receipt, market_token_address, image_url, metadata.
        """
        create_result = self._create_market(
            market_name, symbol, end_time, option_names,
            maintoken, frozen, bonding, seed_amount,
        )

        receipt = create_result['receipt']
        if receipt.get('status') == 0:
            raise RuntimeError(f"Market creation reverted (tx: {create_result['hash']})")

        # Parse market token from MarketCreated event
        market_created_topic = Web3.keccak(text="MarketCreated(address,address,address)").hex()
        mt_lower = self.market_trading_address.lower()
        market_token_address = None
        for log_entry in receipt.get('logs', []):
            addr = log_entry.get('address', '')
            if addr.lower() != mt_lower:
                continue
            topics = log_entry.get('topics', [])
            if not topics:
                continue
            t0 = topics[0].hex() if isinstance(topics[0], bytes) else str(topics[0])
            if t0 == market_created_topic and len(topics) > 1:
                raw = topics[1].hex() if isinstance(topics[1], bytes) else str(topics[1])
                market_token_address = Web3.to_checksum_address("0x" + raw[-40:])
                break

        if not market_token_address:
            raise RuntimeError("Could not extract market address from creation logs.")

        # Upload image if provided
        uploaded_image_url = None
        if image_url:
            uploaded_image_url = self.client.api.upload_image_from_url(image_url, contract_address=market_token_address)

        # Create metadata
        metadata = self.client.api.update_metadata(
            address=market_token_address,
            description=description,
            image=uploaded_image_url,
            website=website,
            telegram=telegram,
            twitterx=twitterx,
        )

        return {
            'hash': create_result['hash'],
            'receipt': receipt,
            'market_token_address': market_token_address,
            'image_url': uploaded_image_url,
            'metadata': metadata,
        }

    def buy(self, market_token: str, outcome_id: int, input_token: str, input_amount: int, min_usdb: int, min_shares: int):
        checksum_market = Web3.to_checksum_address(market_token)
        checksum_input = Web3.to_checksum_address(input_token)
        
        self._approve_if_needed(checksum_input, input_amount)
        
        func = self.contract.functions.buy(checksum_market, outcome_id, checksum_input, input_amount, min_usdb, min_shares)
        return self._build_and_send_tx(func)

    def redeem(self, market_token: str):
        checksum_market = Web3.to_checksum_address(market_token)
        func = self.contract.functions.redeem(checksum_market)
        return self._build_and_send_tx(func)

    def get_market_data(self, market_token: str):
        checksum_market = Web3.to_checksum_address(market_token)
        return self.contract.functions.getMarketData(checksum_market).call()

    def get_outcome(self, market_token: str, outcome_id: int):
        checksum_market = Web3.to_checksum_address(market_token)
        return self.contract.functions.getOutcome(checksum_market, outcome_id).call()

    def get_user_shares(self, market_token: str, user: str, outcome_id: int):
        checksum_market = Web3.to_checksum_address(market_token)
        checksum_user = Web3.to_checksum_address(user)
        return self.contract.functions.getUserShares(checksum_market, checksum_user, outcome_id).call()

    def buy_orders_and_contract(self, market_token: str, outcome_id: int, order_ids: list[int], input_token: str, total_input: int, min_shares: int):
        """Buys from order book and AMM in a single transaction. Auto-approves input token."""
        checksum_market = Web3.to_checksum_address(market_token)
        checksum_input = Web3.to_checksum_address(input_token)
        self._approve_if_needed(checksum_input, total_input)
        func = self.contract.functions.buyOrdersAndContract(checksum_market, outcome_id, order_ids, checksum_input, total_input, min_shares)
        return self._build_and_send_tx(func)

    def get_initial_reserves(self, num_outcomes: int) -> tuple:
        """Returns (perOutcome, totalReserve) for a given number of outcomes."""
        return self.contract.functions.getInitialReserves(num_outcomes).call()

    def get_num_outcomes(self, market_token: str) -> int:
        return self.contract.functions.getNumOutcomes(Web3.to_checksum_address(market_token)).call()

    def get_option_names(self, market_token: str) -> list:
        return self.contract.functions.getOptionNames(Web3.to_checksum_address(market_token)).call()

    def has_betted_on_market(self, market_token: str, user: str) -> bool:
        return self.contract.functions.hasBettedOnMarket(
            Web3.to_checksum_address(market_token), Web3.to_checksum_address(user)
        ).call()

    def get_bounty_pool(self, market_token: str) -> int:
        return self.contract.functions.getBountyPool(Web3.to_checksum_address(market_token)).call()

    def get_general_pot(self, market_token: str) -> int:
        return self.contract.functions.getGeneralPot(Web3.to_checksum_address(market_token)).call()

    def get_buy_order_amounts_out(self, market_token: str, order_id: int, usdb_amount: int):
        return self.contract.functions.getBuyOrderAmountsOut(
            Web3.to_checksum_address(market_token), order_id, usdb_amount
        ).call()
