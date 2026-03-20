import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct

from .api import BasisAPI
from .modules.factory import FactoryModule
from .modules.trading import TradingModule
from .modules.prediction_markets import PredictionMarketsModule
from .modules.order_book import OrderBookModule
from .modules.loans import LoansModule
from .modules.vesting import VestingModule
from .modules.staking import StakingModule
from .modules.market_resolver import MarketResolverModule
from .modules.private_markets import PrivateMarketsModule
from .modules.agent_identity import AgentIdentityModule
from .modules.market_reader import MarketReaderModule
from .modules.leverage_simulator import LeverageSimulatorModule
from .modules.taxes import TaxesModule

logger = logging.getLogger(__name__)

DEFAULT_RPC_URL = "https://bsc-dataseed.binance.org/"
BSC_CHAIN_ID = 56


class BasisClient:
    """Client for the Basis protocol on BSC.

    The constructor is synchronous and lightweight -- it does **not** perform
    network calls.  Use the :meth:`create` classmethod when you want
    automatic RPC validation, SIWE authentication, and API-key provisioning.
    """

    def __init__(
        self,
        rpc_url: str = DEFAULT_RPC_URL,
        private_key: Optional[str] = None,
        api_key: Optional[str] = None,
        api_domain: str = "https://launchonbasis.com",
        factory_address: str = "0x2A6aa5A45FB4b1d1836B06ca830df92a6C19946e",
        swap_address: str = "0x4Fb70115DE58efFb4F5375A0acf96905F877f4d4",
        market_trading_address: str = "0xCb64910a19B3641eb600b904741a074578Dda3F7",
        loan_hub_address: str = "0xA11A1f22fE398903F4108c299008D398fF47ECc7",
        vesting_address: str = "0x4CE85393dD457233f80b3e532ec88da60D945C35",
        usdb_address: str = "0x78dD776204aA7e06BaF488959a90142f0B3027CE",
        main_token_address: str = "0x76ACb5F98A422995a801008c8b7b28dBC23946Ff",
        staking_address: str = "0xb4D72acEa5E26B8438e3604b49A153eB58A7C578",
        resolver_address: str = "0x9A3E39D819Fad125d3116CE0bCC788955238d856",
        private_market_address: str = "0xab38766d7E51B066858671D19e804B5470554196",
        reader_address: str = "0x59EBF4D09AfEA6073c950a89382E500178D46643",
        leverage_address: str = "0xCa73033C4A35df22d5F375D1f8F5555dA071e522",
        taxes_address: str = "0x03F61633694aDf1424D90746e314a232256ec508",
    ):
        self.rpc_url = rpc_url
        self.api_domain = api_domain
        self.api_key: Optional[str] = api_key
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        # BSC is a PoA chain — inject the middleware to handle extraData
        try:
            from web3.middleware import ExtraDataToPOAMiddleware
            self.web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        except ImportError:
            # Older web3.py versions use geth_poa_middleware
            from web3.middleware import geth_poa_middleware
            self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.account = None
        self.usdb_address = Web3.to_checksum_address(usdb_address)
        self.main_token_address = Web3.to_checksum_address(main_token_address)

        if private_key:
            self.account = Account.from_key(private_key)
            logger.info("BasisClient initialized with private key.")
        else:
            logger.info("BasisClient initialized in stateless mode.")

        # Initialize API wrapper
        self.api = BasisAPI(self)

        # Initialize on-chain modules
        self.factory = FactoryModule(self, factory_address)
        self.trading = TradingModule(self, swap_address)
        self.prediction_markets = PredictionMarketsModule(self, market_trading_address)
        self.order_book = OrderBookModule(self, market_trading_address)
        self.loans = LoansModule(self, loan_hub_address)
        self.vesting = VestingModule(self, vesting_address)
        self.staking = StakingModule(self, staking_address)
        self.resolver = MarketResolverModule(self, resolver_address)
        self.private_markets = PrivateMarketsModule(self, private_market_address)
        self.market_reader = MarketReaderModule(self, reader_address)
        self.leverage_simulator = LeverageSimulatorModule(self, leverage_address)
        self.taxes = TaxesModule(self, taxes_address)
        self.agent = AgentIdentityModule(self)

    # ------------------------------------------------------------------
    # Factory class method
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        rpc_url: str = DEFAULT_RPC_URL,
        private_key: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs: Any,
    ) -> "BasisClient":
        """Create a fully-initialised :class:`BasisClient`.

        Compared to the plain constructor this additionally:

        1. Validates the RPC endpoint if a custom *rpc_url* is provided
           (must return chain-id 56 for BSC).
        2. Performs SIWE authentication when a *private_key* is supplied
           without an *api_key*.
        3. Auto-provisions an API key after successful authentication.

        Parameters
        ----------
        rpc_url:
            JSON-RPC endpoint URL. Defaults to the public BSC data-seed.
        private_key:
            Hex-encoded private key for signing transactions and SIWE.
        api_key:
            Pre-existing Basis API key (``bsk_...``).  When provided the
            SIWE auth step is skipped.
        **kwargs:
            Forwarded to :class:`BasisClient.__init__`.
        """
        client = cls(
            rpc_url=rpc_url,
            private_key=private_key,
            api_key=api_key,
            **kwargs,
        )

        # 1. Validate RPC if not using the default
        if rpc_url != DEFAULT_RPC_URL:
            client._validate_rpc()

        # 2. Auth + key provisioning
        if private_key and not api_key:
            client.authenticate()
            client.ensure_api_key()

        return client

    # ------------------------------------------------------------------
    # RPC validation
    # ------------------------------------------------------------------

    def _validate_rpc(self) -> None:
        """Check that the RPC endpoint is reachable and on BSC (chain 56)."""
        if not self.web3.is_connected():
            raise ConnectionError(
                f"Unable to connect to RPC endpoint: {self.rpc_url}"
            )
        chain_id = self.web3.eth.chain_id
        if chain_id != BSC_CHAIN_ID:
            raise ValueError(
                f"RPC returned chain ID {chain_id}, expected {BSC_CHAIN_ID} (BSC). "
                f"Please provide a valid BSC RPC URL."
            )
        logger.info("RPC validated: connected to BSC (chain ID %d).", chain_id)

    # ------------------------------------------------------------------
    # SIWE authentication
    # ------------------------------------------------------------------

    def authenticate(self) -> Dict[str, Any]:
        """Perform SIWE authentication to establish a cookie-based session.

        1. Fetch a nonce from the server.
        2. Build a SIWE message string.
        3. Sign it with the configured private key.
        4. POST the message + signature to ``/api/auth/verify``.

        The ``requests.Session`` inside :attr:`api` automatically stores the
        ``Set-Cookie`` header returned by the server so all subsequent
        session-authenticated requests work transparently.

        Returns the parsed JSON response from the verify endpoint.
        """
        if not self.account:
            raise ValueError("A private key is required to authenticate.")

        address = self.account.address

        # 1. Get nonce
        nonce_resp = self.api.get_nonce(address)
        nonce = nonce_resp["nonce"]

        # 2. Build SIWE message
        issued_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        message = (
            f"launchonbasis.com wants you to sign in with your Ethereum account:\n"
            f"{address}\n"
            f"\n"
            f"Sign in to Basis API.\n"
            f"\n"
            f"URI: {self.api_domain}\n"
            f"Version: 1\n"
            f"Chain ID: {BSC_CHAIN_ID}\n"
            f"Nonce: {nonce}\n"
            f"Issued At: {issued_at}"
        )

        # 3. Sign
        signable = encode_defunct(text=message)
        signed = self.account.sign_message(signable)
        signature = "0x" + signed.signature.hex()

        # 4. Verify
        result = self.api.verify(message, signature)
        logger.info("SIWE authentication successful for %s.", address)
        return result

    # ------------------------------------------------------------------
    # API key management helpers
    # ------------------------------------------------------------------

    def ensure_api_key(self) -> str:
        """Ensure an API key exists, creating one if necessary.

        After this call :pyattr:`api_key` is guaranteed to be set.

        Returns the API key string.
        """
        keys_resp = self.api.list_api_keys()
        keys = keys_resp.get("keys", [])

        if keys and keys[0].get("key"):
            self.api_key = keys[0]["key"]
            logger.info("Using existing API key: %s...", self.api_key[:12])
        else:
            # Delete existing key with null value before creating new one
            if keys and not keys[0].get("key"):
                self.api.delete_api_key(keys[0]["id"])
            create_resp = self.api.create_api_key(label="basis-sdk-auto")
            self.api_key = create_resp["key"]
            logger.info("Created new API key: %s...", self.api_key[:12])

        return self.api_key

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------

    def get_session(self, address: Optional[str] = None) -> Dict[str, Any]:
        """Return current session info.

        Wraps ``GET /api/auth/me``.
        """
        return self.api.get_me(address=address)

    def logout(self) -> Dict[str, Any]:
        """Log out the current session.

        Wraps ``DELETE /api/auth/me``.
        """
        if not self.account:
            raise ValueError("No account is associated with this client.")
        return self.api.logout(self.account.address)
