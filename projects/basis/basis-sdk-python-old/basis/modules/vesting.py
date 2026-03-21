from web3 import Web3
from .factory import load_abi


class VestingModule:
    def __init__(self, client, vesting_address: str):
        self.client = client
        self.vesting_address = Web3.to_checksum_address(vesting_address)
        self.vesting_abi = load_abi('A_VestingContract.json')
        self.erc20_abi = load_abi('IERC20.json')
        self.contract = self.client.web3.eth.contract(address=self.vesting_address, abi=self.vesting_abi)

    def _approve_if_needed(self, token_address: str, spender: str, amount: int):
        if not self.client.account:
            raise ValueError("Wallet account is required for approval.")
        checksum_token = Web3.to_checksum_address(token_address)
        checksum_spender = Web3.to_checksum_address(spender)
        token_contract = self.client.web3.eth.contract(address=checksum_token, abi=self.erc20_abi)
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

    def _get_fee_amount(self) -> int:
        try:
            return self.contract.functions.feeAmount().call()
        except Exception:
            return 0

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

    def create_gradual_vesting(self, beneficiary: str, token: str, total_amount: int, start_time: int, duration_in_days: int, time_unit: int, memo: str, ecosystem: str):
        """Creates a gradual vesting. Auto-approves token and attaches fee."""
        self._approve_if_needed(token, self.vesting_address, total_amount)
        fee = self._get_fee_amount()
        func = self.contract.functions.createGradualVesting(
            Web3.to_checksum_address(beneficiary),
            Web3.to_checksum_address(token),
            total_amount, start_time, duration_in_days, time_unit, memo,
            Web3.to_checksum_address(ecosystem)
        )
        return self._build_and_send_tx(func, value=fee)

    def create_cliff_vesting(self, beneficiary: str, token: str, total_amount: int, unlock_time: int, memo: str, ecosystem: str):
        """Creates a cliff vesting. Auto-approves token and attaches fee."""
        self._approve_if_needed(token, self.vesting_address, total_amount)
        fee = self._get_fee_amount()
        func = self.contract.functions.createCliffVesting(
            Web3.to_checksum_address(beneficiary),
            Web3.to_checksum_address(token),
            total_amount, unlock_time, memo,
            Web3.to_checksum_address(ecosystem)
        )
        return self._build_and_send_tx(func, value=fee)

    def claim_tokens(self, vesting_id: int):
        func = self.contract.functions.claimTokens(vesting_id)
        return self._build_and_send_tx(func)

    def take_loan_on_vesting(self, vesting_id: int):
        func = self.contract.functions.takeLoanOnVesting(vesting_id)
        return self._build_and_send_tx(func)

    def repay_loan_on_vesting(self, vesting_id: int):
        """Repays a loan on vesting. Auto-approves USDB to vesting contract."""
        if not self.client.account:
            raise ValueError("Stateful initialization (private_key) is required.")
        usdb_contract = self.client.web3.eth.contract(
            address=Web3.to_checksum_address(self.client.usdb_address), abi=self.erc20_abi
        )
        balance = usdb_contract.functions.balanceOf(self.client.account.address).call()
        if balance > 0:
            self._approve_if_needed(self.client.usdb_address, self.vesting_address, balance)
        func = self.contract.functions.repayLoanOnVesting(vesting_id)
        return self._build_and_send_tx(func)

    def get_vesting_details(self, vesting_id: int):
        return self.contract.functions.getVestingDetails(vesting_id).call()

    def get_claimable_amount(self, vesting_id: int):
        return self.contract.functions.getClaimableAmount(vesting_id).call()

    def batch_create_gradual_vesting(self, beneficiaries: list[str], token: str, total_amounts: list[int], user_memos: list[str], start_time: int, duration_in_days: int, time_unit: int, ecosystem: str):
        """Creates gradual vestings for multiple beneficiaries. Auto-approves sum of amounts and attaches fee."""
        checksum_beneficiaries = [Web3.to_checksum_address(b) for b in beneficiaries]
        checksum_token = Web3.to_checksum_address(token)
        checksum_ecosystem = Web3.to_checksum_address(ecosystem)
        total = sum(total_amounts)
        self._approve_if_needed(token, self.vesting_address, total)
        fee = self._get_fee_amount()
        func = self.contract.functions.batchCreateGradualVesting(
            checksum_beneficiaries, checksum_token, total_amounts, user_memos,
            start_time, duration_in_days, time_unit, checksum_ecosystem
        )
        return self._build_and_send_tx(func, value=fee)

    def batch_create_cliff_vesting(self, beneficiaries: list[str], token: str, total_amounts: list[int], unlock_time: int, user_memos: list[str], ecosystem: str):
        """Creates cliff vestings for multiple beneficiaries. Auto-approves sum of amounts and attaches fee."""
        checksum_beneficiaries = [Web3.to_checksum_address(b) for b in beneficiaries]
        checksum_token = Web3.to_checksum_address(token)
        checksum_ecosystem = Web3.to_checksum_address(ecosystem)
        total = sum(total_amounts)
        self._approve_if_needed(token, self.vesting_address, total)
        fee = self._get_fee_amount()
        func = self.contract.functions.batchCreateCliffVesting(
            checksum_beneficiaries, checksum_token, total_amounts, unlock_time,
            user_memos, checksum_ecosystem
        )
        return self._build_and_send_tx(func, value=fee)

    def change_beneficiary(self, vesting_id: int, new_beneficiary: str):
        """Changes the beneficiary of a vesting."""
        func = self.contract.functions.changeBeneficiary(vesting_id, Web3.to_checksum_address(new_beneficiary))
        return self._build_and_send_tx(func)

    def extend_vesting_period(self, vesting_id: int, additional_days: int):
        """Extends the vesting period by additional days."""
        func = self.contract.functions.extendVestingPeriod(vesting_id, additional_days)
        return self._build_and_send_tx(func)

    def add_tokens_to_vesting(self, vesting_id: int, additional_amount: int):
        """Adds tokens to an existing vesting. Reads vesting details to get token, then approves."""
        details = self.get_vesting_details(vesting_id)
        token = details[1]  # token address from vesting details
        self._approve_if_needed(token, self.vesting_address, additional_amount)
        func = self.contract.functions.addTokensToVesting(vesting_id, additional_amount)
        return self._build_and_send_tx(func)

    def transfer_creator_role(self, vesting_id: int, new_creator: str):
        """Transfers the creator role of a vesting to a new address."""
        func = self.contract.functions.transferCreatorRole(vesting_id, Web3.to_checksum_address(new_creator))
        return self._build_and_send_tx(func)

    def get_vestings_by_beneficiary(self, beneficiary: str) -> list:
        """Returns all vesting IDs for a beneficiary."""
        return self.contract.functions.getVestingsByBeneficiary(Web3.to_checksum_address(beneficiary)).call()

    def get_vestings_by_creator(self, creator: str) -> list:
        """Returns all vesting IDs for a creator."""
        return self.contract.functions.getVestingsByCreator(Web3.to_checksum_address(creator)).call()
