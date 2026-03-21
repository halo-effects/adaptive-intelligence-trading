from web3 import Web3
from .factory import load_abi


class MarketResolverModule:
    def __init__(self, client, resolver_address: str):
        self.client = client
        self.resolver_address = Web3.to_checksum_address(resolver_address)
        self.resolver_abi = load_abi('AMarketResolver.json')
        self.erc20_abi = load_abi('IERC20.json')
        self.contract = self.client.web3.eth.contract(address=self.resolver_address, abi=self.resolver_abi)

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

    # ------------------------------------------------------------------
    # Write methods
    # ------------------------------------------------------------------

    def propose_outcome(self, market_token: str, outcome_id: int):
        """Proposes an outcome for a market. Auto-approves USDB for the proposal bond."""
        checksum_market = Web3.to_checksum_address(market_token)
        proposal_bond = self.contract.functions.PROPOSAL_BOND().call()
        self._approve_if_needed(self.client.usdb_address, self.resolver_address, proposal_bond)
        func = self.contract.functions.proposeOutcome(checksum_market, outcome_id)
        return self._build_and_send_tx(func)

    def dispute(self, market_token: str, new_outcome_id: int):
        """Disputes a proposed outcome. Auto-approves USDB for the proposal bond."""
        checksum_market = Web3.to_checksum_address(market_token)
        proposal_bond = self.contract.functions.PROPOSAL_BOND().call()
        self._approve_if_needed(self.client.usdb_address, self.resolver_address, proposal_bond)
        func = self.contract.functions.dispute(checksum_market, new_outcome_id)
        return self._build_and_send_tx(func)

    def vote(self, market_token: str, outcome_id: int):
        """Votes for an outcome during a dispute round."""
        checksum_market = Web3.to_checksum_address(market_token)
        func = self.contract.functions.vote(checksum_market, outcome_id)
        return self._build_and_send_tx(func)

    def stake(self, token: str):
        """Stakes a token to become a voter. Auto-approves the minimum stake amount."""
        checksum_token = Web3.to_checksum_address(token)
        min_stake = self.contract.functions.MIN_STAKE_AMOUNT().call()
        self._approve_if_needed(checksum_token, self.resolver_address, min_stake)
        func = self.contract.functions.stake(checksum_token)
        return self._build_and_send_tx(func)

    def unstake(self, token: str):
        """Unstakes a token."""
        checksum_token = Web3.to_checksum_address(token)
        func = self.contract.functions.unstake(checksum_token)
        return self._build_and_send_tx(func)

    def finalize_uncontested(self, market_token: str):
        """Finalizes a market that had no disputes."""
        checksum_market = Web3.to_checksum_address(market_token)
        func = self.contract.functions.finalizeUncontested(checksum_market)
        return self._build_and_send_tx(func)

    def finalize_market(self, market_token: str):
        """Finalizes a market after dispute resolution."""
        checksum_market = Web3.to_checksum_address(market_token)
        func = self.contract.functions.finalizeMarket(checksum_market)
        return self._build_and_send_tx(func)

    def veto(self, market_token: str, proposed_outcome: int):
        """Vetoes a proposed outcome. Auto-approves USDB."""
        checksum_market = Web3.to_checksum_address(market_token)
        proposal_bond = self.contract.functions.PROPOSAL_BOND().call()
        self._approve_if_needed(self.client.usdb_address, self.resolver_address, proposal_bond)
        func = self.contract.functions.veto(checksum_market, proposed_outcome)
        return self._build_and_send_tx(func)

    def claim_bounty(self, market_token: str):
        """Claims the bounty for a resolved market."""
        checksum_market = Web3.to_checksum_address(market_token)
        func = self.contract.functions.claimBounty(checksum_market)
        return self._build_and_send_tx(func)

    def claim_early_bounty(self, market_token: str, round: int):
        """Claims an early bounty for a specific dispute round."""
        checksum_market = Web3.to_checksum_address(market_token)
        func = self.contract.functions.claimEarlyBounty(checksum_market, round)
        return self._build_and_send_tx(func)

    # ------------------------------------------------------------------
    # Read methods
    # ------------------------------------------------------------------

    def get_dispute_data(self, market_token: str):
        """Returns dispute data for a market."""
        checksum_market = Web3.to_checksum_address(market_token)
        return self.contract.functions.getDisputeData(checksum_market).call()

    def is_resolved(self, market_token: str) -> bool:
        """Checks if a market is resolved."""
        checksum_market = Web3.to_checksum_address(market_token)
        return self.contract.functions.resolved(checksum_market).call()

    def get_final_outcome(self, market_token: str) -> int:
        """Returns the final outcome ID of a resolved market."""
        checksum_market = Web3.to_checksum_address(market_token)
        return self.contract.functions.finalOutcome(checksum_market).call()

    def is_in_dispute(self, market_token: str) -> bool:
        """Checks if a market is currently in dispute."""
        checksum_market = Web3.to_checksum_address(market_token)
        return self.contract.functions.inDispute(checksum_market).call()

    def is_in_veto(self, market_token: str) -> bool:
        """Checks if a market is currently in veto period."""
        checksum_market = Web3.to_checksum_address(market_token)
        return self.contract.functions.inVeto(checksum_market).call()

    def get_current_round(self, market_token: str) -> int:
        """Returns the current dispute round for a market."""
        checksum_market = Web3.to_checksum_address(market_token)
        return self.contract.functions.currentRound(checksum_market).call()

    def get_vote_count(self, market_token: str, round: int, outcome_id: int) -> int:
        """Returns the vote count for a specific outcome in a dispute round."""
        checksum_market = Web3.to_checksum_address(market_token)
        return self.contract.functions.getVoteCount(checksum_market, round, outcome_id).call()

    def has_voted(self, market_token: str, round: int, voter: str) -> bool:
        """Checks if a voter has voted in a specific dispute round."""
        checksum_market = Web3.to_checksum_address(market_token)
        checksum_voter = Web3.to_checksum_address(voter)
        return self.contract.functions.hasVoted(checksum_market, round, checksum_voter).call()

    def get_voter_choice(self, market_token: str, round: int, voter: str) -> int:
        """Returns the outcome a voter chose in a dispute round."""
        checksum_market = Web3.to_checksum_address(market_token)
        checksum_voter = Web3.to_checksum_address(voter)
        return self.contract.functions.getVoterChoice(checksum_market, round, checksum_voter).call()

    def get_bounty_per_vote(self, market_token: str) -> int:
        """Returns the bounty per vote for a market."""
        checksum_market = Web3.to_checksum_address(market_token)
        return self.contract.functions.getBountyPerVote(checksum_market).call()

    def has_claimed(self, market_token: str, voter: str) -> bool:
        """Checks if a voter has claimed their bounty."""
        checksum_market = Web3.to_checksum_address(market_token)
        checksum_voter = Web3.to_checksum_address(voter)
        return self.contract.functions.hasClaimed(checksum_market, checksum_voter).call()

    def get_user_stake(self, voter: str) -> int:
        """Returns the stake amount for a voter."""
        checksum_voter = Web3.to_checksum_address(voter)
        return self.contract.functions.getUserStake(checksum_voter).call()

    def is_voter(self, voter: str) -> bool:
        """Checks if an address is a registered voter."""
        checksum_voter = Web3.to_checksum_address(voter)
        return self.contract.functions.isVoter(checksum_voter).call()

    def get_constants(self) -> dict:
        """Returns all system parameters/constants."""
        return self.contract.functions.getConstants().call()
