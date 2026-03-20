import logging
from web3 import Web3
from .factory import load_abi

logger = logging.getLogger(__name__)


class OrderBookModule:
    def __init__(self, client, market_trading_address: str):
        self.client = client
        self.market_trading_address = Web3.to_checksum_address(market_trading_address)
        self.market_trading_abi = load_abi('AMarketTrading.json')
        self.contract = self.client.web3.eth.contract(address=self.market_trading_address, abi=self.market_trading_abi)

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

    def _sync_order(self, tx_hash: str, market_type: str = "public"):
        """Sync order tx to backend. Non-fatal on failure."""
        try:
            # Ensure 0x prefix
            if not tx_hash.startswith("0x"):
                tx_hash = "0x" + tx_hash
            self.client.api.sync_order(tx_hash, market_type)
        except Exception as e:
            logger.warning("Order sync warning: %s", e)

    def list_order(self, market_token: str, outcome_id: int, amount: int, price_per_share: int):
        checksum_market = Web3.to_checksum_address(market_token)
        func = self.contract.functions.listOrder(checksum_market, outcome_id, amount, price_per_share)
        result = self._build_and_send_tx(func)
        self._sync_order(result['hash'])
        return result

    def cancel_order(self, market_token: str, order_id: int):
        checksum_market = Web3.to_checksum_address(market_token)
        func = self.contract.functions.cancelOrder(checksum_market, order_id)
        result = self._build_and_send_tx(func)
        self._sync_order(result['hash'])
        return result

    def buy_order(self, market_token: str, order_id: int, fill: int):
        checksum_market = Web3.to_checksum_address(market_token)
        func = self.contract.functions.buyOrder(checksum_market, order_id, fill)
        result = self._build_and_send_tx(func)
        self._sync_order(result['hash'])
        return result

    def buy_multiple_orders(self, market_token: str, order_ids: list[int], usdb_amount: int):
        checksum_market = Web3.to_checksum_address(market_token)
        func = self.contract.functions.buyMultipleOrders(checksum_market, order_ids, usdb_amount)
        result = self._build_and_send_tx(func)
        self._sync_order(result['hash'])
        return result

    def get_buy_order_cost(self, market_token: str, order_id: int, fill: int):
        checksum_market = Web3.to_checksum_address(market_token)
        return self.contract.functions.getBuyOrderCost(checksum_market, order_id, fill).call()

    def get_buy_order_amounts_out(self, market_token: str, order_id: int, usdb_amount: int):
        """Preview how many shares can be bought for a given USDB amount on a P2P order."""
        checksum_market = Web3.to_checksum_address(market_token)
        return self.contract.functions.getBuyOrderAmountsOut(checksum_market, order_id, usdb_amount).call()
