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
        factory_address: str = "0xd80850a3b712E6B9dB4d3e487c76b7c1F904E273",
        swap_address: str = "0xa2483dd5d22D1A8a01473878f247fEC8dC952f1e",
        market_trading_address: str = "0x69e4b11346f928f29Affe6B52a8e3Ebd115DE7a6",
        loan_hub_address: str = "0x504AeDa510D4cb5Fe6E29D000Dfc377f3f50cC30",
        vesting_address: str = "0x82D1a54fd9671Cd4fE8774f0f85A0CB8A96dee3b",
        usdb_address: str = "0x217B82e4bAc4E4647B1F189F33554229Ce27c51A",
        main_token_address: str = "0xE4b1ed74C77984EbFf1CE871E7F7c9414e5dd73b",
        staking_address: str = "0x8E2C5267f2BA1A142A88a333C075E21719E330aC",
        resolver_address: str = "0x1AB2C2551429Bd4f9a5D8c781BEb5BC5497a42bd",
        private_market_address: str = "0x4eCDD0A082b3f523c31F61eC8bEfF69A8182C0aD",
        reader_address: str = "0xC8652aF90B1C2C9012ADe56B58EfA9572122d342",
        leverage_address: str = "0x0030d46D3ba98287e7D62482c14E4395FbF52904",
        taxes_address: str = "0x3CE0381C6515b7771a6E47d99abf1e42054121CD",
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
