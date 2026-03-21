import logging
from web3 import Web3
from .factory import load_abi

logger = logging.getLogger(__name__)


class PrivateMarketsModule:
    def __init__(self, client, private_market_address: str):
        self.client = client
        self.private_market_address = Web3.to_checksum_address(private_market_address)
        self.private_market_abi = load_abi('APrivateTradingMarket.json')
        self.erc20_abi = load_abi('IERC20.json')
        self.contract = self.client.web3.eth.contract(address=self.private_market_address, abi=self.private_market_abi)

    def _approve_if_needed(self, token_address: str, amount: int):
        if not self.client.account:
            raise ValueError("Wallet account is required for approval.")

        checksum_addr = Web3.to_checksum_address(token_address)
        token_contract = self.client.web3.eth.contract(address=checksum_addr, abi=self.erc20_abi)

        allowance = token_contract.functions.allowance(
            self.client.account.address, self.private_market_address
        ).call()

        if allowance < amount:
            func = token_contract.functions.approve(self.private_market_address, amount)
            tx = func.build_transaction({
                'from': self.client.account.address,
                'nonce': self.client.web3.eth.get_transaction_count(self.client.account.address),
            })
            signed_tx = self.client.web3.eth.account.sign_transaction(tx, private_key=self.client.account.key)
            tx_hash = self.client.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            self.client.web3.eth.wait_for_transaction_receipt(tx_hash)

    def _build_and_send_tx(self, function_call, value=0):
        if not self.client.account:
            raise ValueError("Stateful initialization (private_key) is required for write methods.")

        tx = function_call.build_transaction({
            'from': self.client.account.address,
            'nonce': self.client.web3.eth.get_transaction_count(self.client.account.address),
            'value': value,
        })

        signed_tx = self.client.web3.eth.account.sign_transaction(tx, private_key=self.client.account.key)
        tx_hash = self.client.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = self.client.web3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            'hash': tx_hash.hex(),
            'receipt': receipt
        }

    def _sync_order(self, tx_hash: str):
        """Sync order tx to backend. Non-fatal on failure."""
        try:
            if not tx_hash.startswith("0x"):
                tx_hash = "0x" + tx_hash
            self.client.api.sync_order(tx_hash, 'private')
        except Exception as e:
            logger.warning("Order sync warning: %s", e)

    # ------------------------------------------------------------------
    # Write methods
    # ------------------------------------------------------------------

    def create_market(self, market_name: str, symbol: str, end_time: int, option_names: list[str], maintoken: str, frozen: bool, bonding: int, seed_amount: int = 0):
        """Creates a private prediction market. Auto-fetches and attaches the creation fee."""
        checksum_maintoken = Web3.to_checksum_address(maintoken)
        eco_data = self.contract.functions.ecosystems(checksum_maintoken).call()
        factory_address = eco_data[0]
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

    def buy(self, market_token: str, outcome_id: int, input_token: str, input_amount: int, min_usdb: int, min_shares: int):
        """Buys shares in a private market outcome. Auto-approves input token."""
        checksum_market = Web3.to_checksum_address(market_token)
        checksum_input = Web3.to_checksum_address(input_token)
        self._approve_if_needed(checksum_input, input_amount)
        func = self.contract.functions.buy(checksum_market, outcome_id, checksum_input, input_amount, min_usdb, min_shares)
        return self._build_and_send_tx(func)

    def redeem(self, market_token: str):
        """Redeems shares from a resolved private market."""
        checksum_market = Web3.to_checksum_address(market_token)
        func = self.contract.functions.redeem(checksum_market)
        return self._build_and_send_tx(func)

    def list_order(self, market_token: str, outcome_id: int, amount: int, price_per_share: int):
        """Lists a sell order on the private market order book."""
        checksum_market = Web3.to_checksum_address(market_token)
        func = self.contract.functions.listOrder(checksum_market, outcome_id, amount, price_per_share)
        result = self._build_and_send_tx(func)
        self._sync_order(result['hash'])
        return result

    def cancel_order(self, market_token: str, order_id: int):
        """Cancels an existing order on the private market."""
        checksum_market = Web3.to_checksum_address(market_token)
        func = self.contract.functions.cancelOrder(checksum_market, order_id)
        result = self._build_and_send_tx(func)
        self._sync_order(result['hash'])
        return result

    def buy_order(self, market_token: str, order_id: int, fill: int):
        """Buys from an existing order on the private market."""
        checksum_market = Web3.to_checksum_address(market_token)
        func = self.contract.functions.buyOrder(checksum_market, order_id, fill)
        result = self._build_and_send_tx(func)
        self._sync_order(result['hash'])
        return result

    def buy_multiple_orders(self, market_token: str, order_ids: list[int], usdb_amount: int):
        """Buys from multiple orders on the private market."""
        checksum_market = Web3.to_checksum_address(market_token)
        func = self.contract.functions.buyMultipleOrders(checksum_market, order_ids, usdb_amount)
        result = self._build_and_send_tx(func)
        self._sync_order(result['hash'])
        return result

    def buy_orders_and_contract(self, market_token: str, outcome_id: int, order_ids: list[int], input_token: str, total_input: int, min_shares: int):
        """Buys from order book and AMM in a single transaction. Auto-approves input token."""
        checksum_market = Web3.to_checksum_address(market_token)
        checksum_input = Web3.to_checksum_address(input_token)
        self._approve_if_needed(checksum_input, total_input)
        func = self.contract.functions.buyOrdersAndContract(checksum_market, outcome_id, order_ids, checksum_input, total_input, min_shares)
        result = self._build_and_send_tx(func)
        self._sync_order(result['hash'])
        return result

    # ------------------------------------------------------------------
    # Read methods
    # ------------------------------------------------------------------

    def get_market_data(self, market_token: str):
        """Returns market data for a private market."""
        checksum_market = Web3.to_checksum_address(market_token)
        return self.contract.functions.getMarketData(checksum_market).call()

    def get_outcome(self, market_token: str, outcome_id: int):
        """Returns outcome data for a specific outcome."""
        checksum_market = Web3.to_checksum_address(market_token)
        return self.contract.functions.getOutcome(checksum_market, outcome_id).call()

    def get_user_shares(self, market_token: str, user: str, outcome_id: int):
        """Returns a user's shares for a specific outcome."""
        checksum_market = Web3.to_checksum_address(market_token)
        checksum_user = Web3.to_checksum_address(user)
        return self.contract.functions.getUserShares(checksum_market, checksum_user, outcome_id).call()

    def get_buy_order_cost(self, market_token: str, order_id: int, fill: int):
        """Returns the cost to buy a specific order fill amount."""
        checksum_market = Web3.to_checksum_address(market_token)
        return self.contract.functions.getBuyOrderCost(checksum_market, order_id, fill).call()

    def get_initial_reserves(self, num_outcomes: int) -> int:
        """Returns the initial reserves required for a given number of outcomes."""
        return self.contract.functions.getInitialReserves(num_outcomes).call()
