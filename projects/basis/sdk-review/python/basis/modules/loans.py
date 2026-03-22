import logging
from web3 import Web3
from .factory import load_abi

logger = logging.getLogger(__name__)


class LoansModule:
    def __init__(self, client, loan_hub_address: str):
        self.client = client
        self.loan_hub_address = Web3.to_checksum_address(loan_hub_address)
        self.loan_hub_abi = load_abi('ALOAN_HUB.json')
        self.contract = self.client.web3.eth.contract(address=self.loan_hub_address, abi=self.loan_hub_abi)

    def _sync_loan(self, tx_hash: str):
        """Sync loan tx to backend. Non-fatal on failure."""
        try:
            if not tx_hash.startswith("0x"):
                tx_hash = "0x" + tx_hash
            self.client.api.sync_loan(tx_hash)
        except Exception as e:
            logger.warning("Loan sync warning: %s", e)

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

    def _approve_if_needed(self, token_address: str, spender: str, amount: int):
        if not self.client.account:
            raise ValueError("Wallet account is required for approval.")
        checksum_token = Web3.to_checksum_address(token_address)
        checksum_spender = Web3.to_checksum_address(spender)
        erc20_abi = load_abi('IERC20.json')
        token_contract = self.client.web3.eth.contract(address=checksum_token, abi=erc20_abi)
        allowance = token_contract.functions.allowance(
            self.client.account.address, checksum_spender
        ).call()
        if allowance < amount:
            func = token_contract.functions.approve(checksum_spender, amount)
            tx = func.build_transaction({
                'from': self.client.account.address,
                'nonce': self.client.web3.eth.get_transaction_count(self.client.account.address),
            })
            signed_tx = self.client.web3.eth.account.sign_transaction(tx, private_key=self.client.account.key)
            tx_hash = self.client.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            self.client.web3.eth.wait_for_transaction_receipt(tx_hash)

    def take_loan(self, ecosystem: str, collateral: str, amount: int, days_count: int):
        """Takes a loan. Auto-approves the collateral token to the LoanHub."""
        checksum_ecosystem = Web3.to_checksum_address(ecosystem)
        checksum_collateral = Web3.to_checksum_address(collateral)
        self._approve_if_needed(collateral, self.loan_hub_address, amount)
        func = self.contract.functions.takeLoan(checksum_ecosystem, checksum_collateral, amount, days_count)
        result = self._build_and_send_tx(func)
        self._sync_loan(result['hash'])
        return result

    def repay_loan(self, hub_id: int):
        """Repays a loan. Auto-approves the borrowed token (USDB) to the LoanHub."""
        if not self.client.account:
            raise ValueError("Stateful initialization (private_key) is required for write methods.")
        loan_details = self.get_user_loan_details(self.client.account.address, hub_id)
        # fullAmount is index 4 in the struct tuple
        # FullLoanDetails struct: [0]=hubId, [1]=ecosystem, [2]=loanId, [3]=token,
        # [4]=collateral, [5]=collateralAmount, [6]=liquidatedAmount, [7]=fullAmount, [8]=borrowedAmount, ...
        full_amount = int(loan_details[7]) if isinstance(loan_details, (list, tuple)) else int(loan_details.get('fullAmount', 0))
        if full_amount > 0:
            self._approve_if_needed(self.client.usdb_address, self.loan_hub_address, full_amount)
        func = self.contract.functions.repayLoan(hub_id)
        result = self._build_and_send_tx(func)
        self._sync_loan(result['hash'])
        return result

    def extend_loan(self, hub_id: int, add_days: int, pay_in_stable: bool, refinance: bool):
        """Extends a loan. When pay_in_stable is True, auto-approves USDB to the LoanHub."""
        if pay_in_stable and self.client.account:
            erc20_abi = load_abi('IERC20.json')
            usdb = self.client.web3.eth.contract(
                address=Web3.to_checksum_address(self.client.usdb_address), abi=erc20_abi
            )
            balance = usdb.functions.balanceOf(self.client.account.address).call()
            if balance > 0:
                self._approve_if_needed(self.client.usdb_address, self.loan_hub_address, balance)
        func = self.contract.functions.extendLoan(hub_id, add_days, pay_in_stable, refinance)
        result = self._build_and_send_tx(func)
        self._sync_loan(result['hash'])
        return result

    def claim_liquidation(self, hub_id: int):
        func = self.contract.functions.claimLiquidation(hub_id)
        result = self._build_and_send_tx(func)
        self._sync_loan(result['hash'])
        return result

    def get_user_loan_details(self, user: str, hub_id: int):
        checksum_user = Web3.to_checksum_address(user)
        return self.contract.functions.getUserLoanDetails(checksum_user, hub_id).call()

    def increase_loan(self, hub_id: int, amount_to_add: int):
        """Increases collateral on an existing loan. Auto-approves the collateral token."""
        loan_details = self.get_user_loan_details(self.client.account.address, hub_id)
        collateral = loan_details[3]  # collateralToken at index 3 in FullLoanDetails struct
        self._approve_if_needed(collateral, self.loan_hub_address, amount_to_add)
        func = self.contract.functions.increaseLoan(hub_id, amount_to_add)
        result = self._build_and_send_tx(func)
        self._sync_loan(result['hash'])
        return result

    def hub_partial_loan_sell(self, hub_id: int, percentage: int, is_leverage: bool, min_out: int = 0):
        """Partially sell collateral from a hub loan position."""
        func = self.contract.functions.hubPartialLoanSell(hub_id, percentage, is_leverage, min_out)
        result = self._build_and_send_tx(func)
        self._sync_loan(result['hash'])
        return result

    def get_user_loan_count(self, user: str) -> int:
        """Returns the number of loans for a user."""
        return self.contract.functions.userLoanCount(Web3.to_checksum_address(user)).call()
