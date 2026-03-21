import io
import os
import requests
import logging
from typing import Optional, Dict, Any, List, Union

logger = logging.getLogger(__name__)


class BasisAPI:
    """HTTP client for the Basis off-chain API.

    Provides two request modes:
    - Session-authenticated requests (cookie-based, for auth/metadata/comments)
    - API-key-authenticated requests (X-API-Key header, for v1 data endpoints)
    """

    def __init__(self, client: Any) -> None:
        self.client = client
        self.session = requests.Session()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _session_request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> Any:
        """Make a request using the cookie-authenticated session.

        The ``requests.Session`` automatically persists cookies set by the
        server (e.g. after SIWE verification), so no manual cookie handling
        is required.
        """
        url = f"{self.client.api_domain}/api{endpoint}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        # Some endpoints return plain text (e.g. image upload returns a URL)
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return response.json()
        text = response.text.strip()
        # Try JSON parse as fallback
        try:
            return response.json()
        except (ValueError, requests.exceptions.JSONDecodeError):
            return text

    def _api_key_request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> Any:
        """Make a request using the API key via ``X-API-Key`` header."""
        api_key = self.client.api_key
        if not api_key:
            raise ValueError(
                "An API key is required for this request. "
                "Provide one via BasisClient(api_key=...) or use "
                "BasisClient.create(...) to auto-provision a key."
            )
        headers = kwargs.pop("headers", {})
        headers["X-API-Key"] = api_key
        url = f"{self.client.api_domain}/api{endpoint}"
        response = self.session.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Authentication endpoints (session)
    # ------------------------------------------------------------------

    def get_nonce(self, address: str) -> Dict[str, Any]:
        """Fetch a SIWE nonce for the given wallet address.

        ``GET /api/auth/nonce?address={address}``
        """
        return self._session_request("GET", "/auth/nonce", params={"address": address})

    def verify(self, message: str, signature: str) -> Dict[str, Any]:
        """Verify a signed SIWE message and establish a session.

        ``POST /api/auth/verify``

        The server returns a Set-Cookie header which is automatically stored
        by the ``requests.Session``.
        """
        return self._session_request(
            "POST",
            "/auth/verify",
            json={"message": message, "signature": signature},
        )

    def get_me(self, address: Optional[str] = None) -> Dict[str, Any]:
        """Get the current session status.

        ``GET /api/auth/me``
        """
        params: Dict[str, str] = {}
        if address is not None:
            params["address"] = address
        return self._session_request("GET", "/auth/me", params=params)

    def logout(self, address: str) -> Dict[str, Any]:
        """Log out / delete session for a specific address.

        ``DELETE /api/auth/me?address={address}``
        """
        return self._session_request("DELETE", "/auth/me", params={"address": address})

    # ------------------------------------------------------------------
    # API key management (session required)
    # ------------------------------------------------------------------

    def create_api_key(self, label: str = "basis-sdk-auto") -> Dict[str, Any]:
        """Create a new API key (max 1 per wallet).

        ``POST /api/v1/auth/keys``
        """
        return self._session_request("POST", "/v1/auth/keys", json={"label": label})

    def list_api_keys(self) -> Dict[str, Any]:
        """List all API keys for the authenticated wallet.

        ``GET /api/v1/auth/keys``
        """
        return self._session_request("GET", "/v1/auth/keys")

    def delete_api_key(self, key_id: str) -> Dict[str, Any]:
        """Delete an API key by id.

        ``DELETE /api/v1/auth/keys/{id}``
        """
        return self._session_request("DELETE", f"/v1/auth/keys/{key_id}")

    # ------------------------------------------------------------------
    # Image upload (session required)
    # ------------------------------------------------------------------

    def upload_image(self, file_path: str) -> str:
        """Upload an image file and return the hosted URL.

        ``POST /api/images`` (multipart/form-data)

        Allowed formats: jpeg, png, webp, gif. Max 5 MB.
        """
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            return self._session_request("POST", "/images", files=files)

    def upload_image_from_url(self, image_url: str, contract_address: Optional[str] = None) -> str:
        """Download an image from a URL, resize to 512x512 center-crop,
        convert to WebP, and upload to IPFS via /api/images.

        Requires ``Pillow`` to be installed (``pip install Pillow``).

        Returns the hosted IPFS URL string.
        """
        from PIL import Image

        # 1. Download
        resp = requests.get(image_url)
        resp.raise_for_status()

        # 2. Resize to 512x512 center-crop and convert to WebP
        img = Image.open(io.BytesIO(resp.content))
        # Center-crop to square
        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))
        img = img.resize((512, 512), Image.LANCZOS)
        # Convert to WebP
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=90)
        buf.seek(0)

        # 3. Upload — name file after contract address if provided
        import time
        filename = f"{contract_address}.webp" if contract_address else f"image_{int(time.time())}.webp"
        files = {"file": (filename, buf, "image/webp")}
        return self._session_request("POST", "/images", files=files)

    # ------------------------------------------------------------------
    # Metadata (session required, must be creator)
    # ------------------------------------------------------------------

    def update_metadata(
        self,
        address: str,
        description: Optional[str] = None,
        website: Optional[str] = None,
        telegram: Optional[str] = None,
        twitterx: Optional[str] = None,
        image: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or update on-chain metadata for a token.

        ``POST /api/metadata``
        """
        body: Dict[str, str] = {"address": address}
        if description is not None:
            body["description"] = description
        if website is not None:
            body["website"] = website
        if telegram is not None:
            body["telegram"] = telegram
        if twitterx is not None:
            body["twitterx"] = twitterx
        if image is not None:
            body["image"] = image
        return self._session_request("POST", "/metadata", json=body)

    # ------------------------------------------------------------------
    # Project updates (session required, must be dev)
    # ------------------------------------------------------------------

    def update_project(
        self,
        address: str,
        data: Optional[Dict[str, Any]] = None,
        image_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Post a project update.

        ``POST /api/projects/{address}``

        When *image_path* is provided the request is sent as multipart
        form-data; otherwise plain JSON.
        """
        if image_path is not None:
            # Multipart form-data mode
            files = {}
            form_data: Dict[str, Any] = {}
            with open(image_path, "rb") as f:
                files["image"] = (os.path.basename(image_path), f)
                if data:
                    for key, value in data.items():
                        form_data[key] = value
                return self._session_request(
                    "POST", f"/projects/{address}", data=form_data, files=files
                )
        else:
            return self._session_request(
                "POST", f"/projects/{address}", json=data or {}
            )

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    def get_comments(
        self,
        project_id: int,
        page: int = 1,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Fetch comments for a project.

        ``GET /api/comments``
        """
        return self._session_request(
            "GET",
            "/comments",
            params={"projectId": project_id, "page": page, "limit": limit},
        )

    def create_comment(
        self,
        project_id: int,
        content: str,
        author_address: str,
    ) -> Dict[str, Any]:
        """Post a comment on a project.

        ``POST /api/comments``
        """
        return self._session_request(
            "POST",
            "/comments",
            json={
                "projectId": project_id,
                "content": content,
                "authorAddress": author_address,
            },
        )

    def delete_comment(self, comment_id: int, author_address: str) -> Dict[str, Any]:
        """Soft-delete a comment.

        ``DELETE /api/comments``
        """
        return self._session_request(
            "DELETE",
            "/comments",
            params={"id": comment_id, "authorAddress": author_address},
        )

    # ------------------------------------------------------------------
    # v1 Data endpoints (API key required)
    # ------------------------------------------------------------------

    def get_tokens(
        self,
        search: Optional[str] = None,
        is_prediction: Optional[bool] = None,
        sort: str = "newest",
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """List tokens.

        ``GET /api/v1/tokens``
        """
        params: Dict[str, Any] = {"sort": sort, "page": page, "limit": limit}
        if search is not None:
            params["search"] = search
        if is_prediction is not None:
            params["isPrediction"] = str(is_prediction).lower()
        return self._api_key_request("GET", "/v1/tokens", params=params)

    def get_token(self, address: str) -> Dict[str, Any]:
        """Get details for a single token.

        ``GET /api/v1/tokens/{address}``
        """
        return self._api_key_request("GET", f"/v1/tokens/{address}")

    def get_token_candles(
        self,
        address: str,
        interval: str = "1h",
        from_ts: Optional[str] = None,
        to_ts: Optional[str] = None,
        limit: int = 500,
    ) -> Any:
        """Fetch OHLCV candle data for a token.

        ``GET /api/v1/tokens/{address}/candles``
        """
        params: Dict[str, Any] = {"interval": interval, "limit": limit}
        if from_ts is not None:
            params["from"] = from_ts
        if to_ts is not None:
            params["to"] = to_ts
        return self._api_key_request("GET", f"/v1/tokens/{address}/candles", params=params)

    def get_token_trades(
        self,
        address: str,
        cursor: Optional[str] = None,
        limit: int = 20,
        trade_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch trades for a token.

        ``GET /api/v1/tokens/{address}/trades``
        """
        params: Dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        if trade_type is not None:
            params["type"] = trade_type
        return self._api_key_request("GET", f"/v1/tokens/{address}/trades", params=params)

    def get_token_orders(
        self,
        address: str,
        status: Optional[str] = None,
        outcome_id: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Fetch orders for a token.

        ``GET /api/v1/tokens/{address}/orders``
        """
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if status is not None:
            params["status"] = status
        if outcome_id is not None:
            params["outcomeId"] = outcome_id
        return self._api_key_request("GET", f"/v1/tokens/{address}/orders", params=params)

    def get_token_comments(
        self,
        address: str,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Fetch comments for a token.

        ``GET /api/v1/tokens/{address}/comments``
        """
        return self._api_key_request(
            "GET",
            f"/v1/tokens/{address}/comments",
            params={"page": page, "limit": limit},
        )

    def get_token_whitelist(
        self,
        address: str,
        wallet: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Fetch whitelist entries for a token.

        ``GET /api/v1/tokens/{address}/whitelist``
        """
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if wallet is not None:
            params["wallet"] = wallet
        return self._api_key_request(
            "GET", f"/v1/tokens/{address}/whitelist", params=params
        )

    def get_wallet_transactions(
        self,
        address: str,
        cursor: Optional[str] = None,
        limit: int = 20,
        tx_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch transactions for a wallet.

        ``GET /api/v1/wallet/{address}/transactions``
        """
        params: Dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        if tx_type is not None:
            params["type"] = tx_type
        return self._api_key_request(
            "GET", f"/v1/wallet/{address}/transactions", params=params
        )

    def get_market_liquidity(
        self,
        address: str,
        cursor: Optional[str] = None,
        limit: int = 20,
        outcome_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch liquidity events for a prediction market.

        ``GET /api/v1/markets/{address}/liquidity``
        """
        params: Dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        if outcome_id is not None:
            params["outcomeId"] = outcome_id
        return self._api_key_request(
            "GET", f"/v1/markets/{address}/liquidity", params=params
        )

    # ------------------------------------------------------------------
    # Order sync (session or API key)
    # ------------------------------------------------------------------

    def sync_order(self, tx_hash: str, market_type: str = "public") -> Dict[str, Any]:
        """Sync an on-chain order event to the database.

        ``POST /api/v1/orders/sync``

        Call after listOrder, cancelOrder, or buyOrder transactions.
        Accepts either session cookie or API key.
        """
        body = {"txHash": tx_hash, "marketType": market_type}
        api_key = self.client.api_key
        if api_key:
            return self._api_key_request("POST", "/v1/orders/sync", json=body)
        else:
            return self._session_request("POST", "/v1/orders/sync", json=body)

    # ------------------------------------------------------------------
    # Loan & Vault sync (public, no auth required)
    # ------------------------------------------------------------------

    def sync_loan(self, tx_hash: str) -> Dict[str, Any]:
        """Sync an on-chain loan or vault event to the database.

        ``POST /api/v1/sync``

        Call after any loan, vault staking, or leverage transaction.
        No authentication required (public on-chain data). Rate limited to 20 req/min.
        Idempotent — submitting the same txHash twice is safe.
        """
        url = f"{self.client.api_domain}/api/v1/sync"
        response = self.session.post(url, json={"txHash": tx_hash})
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Loans, Vault & Vesting read endpoints (session or API key)
    # ------------------------------------------------------------------

    def _auth_request(self, method: str, endpoint: str, **kwargs: Any) -> Any:
        """Make a request using API key (preferred) or session cookie."""
        api_key = self.client.api_key
        if api_key:
            return self._api_key_request(method, endpoint, **kwargs)
        else:
            return self._session_request(method, endpoint, **kwargs)

    def get_loans(
        self,
        source: Optional[str] = None,
        active: Optional[bool] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """List loans for the authenticated wallet.

        ``GET /api/v1/loans``

        Params: source (hub|vault|leverage|vesting), active (true|false), page, limit.
        """
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if source is not None:
            params["source"] = source
        if active is not None:
            params["active"] = str(active).lower()
        return self._auth_request("GET", "/v1/loans", params=params)

    def get_loan_events(
        self,
        source: Optional[str] = None,
        action: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """List loan lifecycle events for the authenticated wallet.

        ``GET /api/v1/loans/events``

        Params: source, action (created|repaid|extended|increased|liquidated|partial_sell|liquidation_claimed), page, limit.
        """
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if source is not None:
            params["source"] = source
        if action is not None:
            params["action"] = action
        return self._auth_request("GET", "/v1/loans/events", params=params)

    def get_vault_events(
        self,
        action: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """List vault staking events for the authenticated wallet.

        ``GET /api/v1/vault/events``

        Params: action (wrap|unwrap|lock|unlock), page, limit.
        """
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if action is not None:
            params["action"] = action
        return self._auth_request("GET", "/v1/vault/events", params=params)

    def get_vesting_events(
        self,
        action: Optional[str] = None,
        vesting_id: Optional[int] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """List vesting events for the authenticated wallet.

        ``GET /api/v1/vesting/events``

        Params: action (created|claimed|extended|beneficiary_changed), vestingId, page, limit.
        """
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if action is not None:
            params["action"] = action
        if vesting_id is not None:
            params["vestingId"] = vesting_id
        return self._auth_request("GET", "/v1/vesting/events", params=params)

    # ------------------------------------------------------------------
    # Twitter / X Verification
    # ------------------------------------------------------------------

    def request_twitter_challenge(self) -> Dict[str, Any]:
        """Request a verification code for X/Twitter linking.

        ``POST /api/auth/twitter/challenge``

        Returns a code to include in a tweet and a pre-built tweet template.
        Accepts either session cookie or API key.
        """
        api_key = self.client.api_key
        if api_key:
            return self._api_key_request("POST", "/auth/twitter/challenge")
        else:
            return self._session_request("POST", "/auth/twitter/challenge")

    def verify_twitter(self, tweet_url: str) -> Dict[str, Any]:
        """Verify a tweet containing the challenge code and link the X account.

        ``POST /api/auth/twitter/verify-tweet``

        Accepts either session cookie or API key.
        """
        body = {"tweetUrl": tweet_url}
        api_key = self.client.api_key
        if api_key:
            return self._api_key_request("POST", "/auth/twitter/verify-tweet", json=body)
        else:
            return self._session_request("POST", "/auth/twitter/verify-tweet", json=body)
