from web3 import Web3
from .factory import load_abi


class TaxesModule:
    def __init__(self, client, taxes_address: str):
        self.client = client
        self.taxes_address = Web3.to_checksum_address(taxes_address)
        self.taxes_abi = load_abi('ATaxes.json')
        self.contract = self.client.web3.eth.contract(address=self.taxes_address, abi=self.taxes_abi)

    # ------------------------------------------------------------------
    # Read methods
    # ------------------------------------------------------------------

    def get_tax_rate(self, token: str, user: str) -> int:
        """Returns the tax rate in basis points for a token/user pair."""
        checksum_token = Web3.to_checksum_address(token)
        checksum_user = Web3.to_checksum_address(user)
        return self.contract.functions.getTaxRate(checksum_token, checksum_user).call()

    def get_current_surge_tax(self, token: str) -> int:
        """Returns the current surge tax for a token."""
        checksum_token = Web3.to_checksum_address(token)
        return self.contract.functions.getCurrentSurgeTax(checksum_token).call()

    def get_available_surge_quota(self, token: str) -> int:
        """Returns the available surge quota for a token."""
        checksum_token = Web3.to_checksum_address(token)
        return self.contract.functions.availableSurgeQuota(checksum_token).call()

    def get_base_tax_rates(self) -> dict:
        """Returns the base tax rates for all token types."""
        stasis = self.contract.functions._taxRateStasis().call()
        stable = self.contract.functions._taxRateStable().call()
        default = self.contract.functions._taxRateDefault().call()
        prediction = self.contract.functions._taxRatePrediction().call()
        return {
            'stasis': stasis,
            'stable': stable,
            'default': default,
            'prediction': prediction,
        }
