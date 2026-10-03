"""
CFGI.io Per-Coin Fear & Greed Index API Client
https://cfgi.io/api
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)


class CFGIError(Exception):
    """Base CFGI API error."""
    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        super().__init__(message)


class CFGIRateLimitError(CFGIError):
    pass


class CFGIAuthError(CFGIError):
    pass


class CFGICreditsExhausted(CFGIError):
    pass


# v3 migration (2026-09-30): v2 `api_request_v2.php` was sunset (HTTP 410).
# v3 batches multiple symbols in one call and returns a flat `data[]` array.
# The old `cfgi` field is now `score`; get_current() exposes BOTH keys for
# backward compatibility with callers that read `.cfgi`.
ENDPOINT = "https://cfgi.io/api/v3/scores"
ENDPOINT_V2_LEGACY = "https://cfgi.io/api/api_request_v2.php"  # sunset, kept for reference

VALID_TOKENS = [
    "BTC", "ETH", "SOL", "BNB", "HYPE", "ASTER", "DOGE", "PEPE",
    "AVAX", "ADA", "XRP", "DOT", "LINK", "UNI", "AAVE", "SUI",
    "TON", "ARB", "INJ", "TRUMP", "MARKET",
]

VALID_FIELDS = [
    "cfgi", "price", "volatility", "volume", "impulse",
    "dominance", "technical", "social", "trends", "whales", "orders",
]

PERIODS = {1: "15m", 2: "1h", 3: "4h", 4: "1d"}


def _period_str(period) -> str:
    """Map a legacy integer period code (1-4) to a v3 period string.
    Accepts already-stringified periods ("1d", "4h", ...) and passes them through.
    """
    if isinstance(period, str):
        return period
    return PERIODS.get(period, "1d")


class CFGIClient:
    def __init__(self, api_key: str, cache_dir: str = None):
        self.api_key = api_key
        self.cache_dir = Path(cache_dir or os.path.join(os.path.dirname(__file__), "data", "cfgi_cache"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_request_time = 0.0
        self._credits_remaining = None
        self._credits_used_last = None

        if requests is None:
            raise ImportError("requests library required — pip install requests")
        self._session = requests.Session()

    # ── Core request ──────────────────────────────────────────────

    def _request(self, params: dict) -> dict:
        """Make a rate-limited GET request to the API."""
        # Rate limit: 1 req/sec
        elapsed = time.time() - self._last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

        params["api_key"] = self.api_key
        url = f"{ENDPOINT}?{urlencode(params)}"
        logger.debug(f"CFGI request: {ENDPOINT}?{urlencode({k:v for k,v in params.items() if k != 'api_key'})}")

        self._last_request_time = time.time()
        resp = self._session.get(url, timeout=30)

        # Track credits from headers
        self._credits_used_last = resp.headers.get("X-Credits-Used")
        remaining = resp.headers.get("X-Credits-Remaining")
        if remaining is not None:
            self._credits_remaining = int(remaining)

        logger.info(f"CFGI: credits_used={self._credits_used_last} remaining={self._credits_remaining}")

        # Error handling
        if resp.status_code == 401:
            raise CFGIAuthError("Invalid API key", 401)
        if resp.status_code == 402:
            raise CFGICreditsExhausted("Credits exhausted", 402)
        if resp.status_code == 429:
            raise CFGIRateLimitError("Rate limit exceeded", 429)
        if resp.status_code >= 400:
            raise CFGIError(f"API error {resp.status_code}: {resp.text}", resp.status_code)

        return resp.json()

    # ── Public methods ────────────────────────────────────────────

    def get_current(self, tokens: list, period: int = 4, fields: str = "cfgi") -> dict:
        """Fetch latest score for given tokens (v3 /api/v3/scores).

        Batches all tokens in a single request. Returns
        {token: {"cfgi": score, "score": score, "classification": str,
                 "components": dict, "price": float, "stale": bool}}.

        Backward-compat: value exposed under BOTH `cfgi` (legacy v2 key) and
        `score` (v3 key) so callers reading `.get("cfgi")` keep working. The
        `fields` arg is accepted for signature compatibility but ignored — v3
        always returns the full object.
        """
        params = {
            "symbols": ",".join(tokens),
            "period": _period_str(period),
        }
        data = self._request(params)
        return self._parse_multi_token(data, tokens)

    def get_history(self, token: str, period: int, start: str, end: str, fields: str = "cfgi") -> list:
        """Historical range fetch — NOT YET MIGRATED TO v3 (P2, 2026-09-30).

        The v2 history path (`api_request_v2.php` with `token`/`start`/`end`/
        `values` params) was sunset (HTTP 410). This method has NOT been
        ported to the v3 history endpoint yet. It is used ONLY by backtest
        helpers (`get_bulk_history`, `get_roc3d`, `get_cfgi_for_backtest`),
        never by the live bot's `_poll_cfgi()`.

        Fails loud on purpose: returning empty/partial data would silently
        corrupt a backtest. When CFGI history is next needed for a backtest,
        migrate this to the v3 history endpoint (probe `/api/v3/history` or
        equivalent) and remove this guard.
        """
        raise NotImplementedError(
            "CFGI get_history() is not migrated to v3 yet (P2, 2026-09-30). "
            "v2 history endpoint was sunset. Live polling uses get_current() (v3, "
            "already migrated). Migrate the v3 history endpoint before using this "
            "in a backtest. See projects/ait/log.md 2026-09-30."
        )

    def get_bulk_history(self, token: str, period: int, start: str, end: str,
                         fields: str = "cfgi", cache: bool = True) -> list:
        """Like get_history but with disk caching for backtesting."""
        cache_key = f"{token}_{period}_{start}_{end}_{fields}.json"
        cache_path = self.cache_dir / cache_key

        if cache and cache_path.exists():
            logger.info(f"CFGI cache hit: {cache_key}")
            with open(cache_path, "r") as f:
                return json.load(f)

        data = self.get_history(token, period, start, end, fields)

        if cache and data:
            with open(cache_path, "w") as f:
                json.dump(data, f)
            logger.info(f"CFGI cached: {cache_key} ({len(data)} rows)")

        return data

    def credits_remaining(self) -> int:
        """Return remaining credits from last response."""
        return self._credits_remaining

    def get_roc3d(self, token: str) -> Optional[float]:
        """Get CFGI 3-day rate of change for a single token.

        Fetches last 4 daily values and returns current - 3_days_ago.
        Handles errors gracefully (returns None).

        NOTE (P2, 2026-09-30): depends on get_history(), which is NOT yet
        migrated to v3 and will raise NotImplementedError. This method catches
        that and returns None (fail-soft) — callers must treat None as "CFGI ROC
        unavailable". Not used by the live bot.
        """
        try:
            from datetime import datetime, timedelta
            
            # Get last 4 daily values
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%d')
            
            rows = self.get_history(token, period=4, start=start_date, end=end_date, fields="cfgi")
            
            if len(rows) < 4:
                return None
                
            # Sort by date to ensure correct order
            rows_sorted = sorted(rows, key=lambda x: x.get("date", ""))
            
            # Get CFGI values
            current_cfgi = rows_sorted[-1].get("cfgi") or rows_sorted[-1].get("value")
            old_cfgi = rows_sorted[-4].get("cfgi") or rows_sorted[-4].get("value")
            
            if current_cfgi is None or old_cfgi is None:
                return None
                
            return current_cfgi - old_cfgi
            
        except Exception as e:
            logger.warning("Error computing CFGI ROC-3d for %s: %s", token, e)
            return None

    @staticmethod
    def estimate_credits(tokens: int, fields: int, rows: int) -> int:
        """Estimate credit cost: fields × tokens × rows."""
        return fields * tokens * rows

    # ── Parsing helpers ───────────────────────────────────────────

    def _parse_multi_token(self, data: dict, tokens: list) -> dict:
        """Parse v3 /api/v3/scores response into {token: {cfgi, score, ...}}.

        v3 shape:
            {"data": [{"symbol": "BTC", "score": 52.5, "classification": ...,
                       "components": {...}, "price": ..., "stale": bool}, ...],
             "meta": {"unknown_symbols": [...]}}

        Matches on `item["symbol"]`. Exposes the score under both `cfgi` and
        `score` for backward compatibility.
        """
        result = {}
        rows = []
        if isinstance(data, dict):
            rows = data.get("data", []) or []
            meta = data.get("meta", {}) or {}
            unknown = meta.get("unknown_symbols")
            if unknown:
                logger.debug(f"CFGI v3 unknown_symbols: {unknown}")
        elif isinstance(data, list):
            rows = data  # defensive: bare array fallback

        token_set = set(tokens)
        for item in rows:
            if not isinstance(item, dict):
                continue
            sym = item.get("symbol", "")
            if sym not in token_set:
                continue
            score = item.get("score")
            entry = dict(item)  # preserve full v3 object (components, price, stale, ...)
            entry["cfgi"] = score   # legacy alias for backward compat
            entry["score"] = score
            result[sym] = entry
        return result

    def _parse_single_token(self, data: dict, token: str) -> list:
        """Parse API response for a single token history."""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            token_data = data.get(token, data.get(token.upper(), data.get(token.lower())))
            if isinstance(token_data, list):
                return token_data
            # Maybe the dict itself is a single row
            if "date" in data:
                return [data]
        return []


# ── Integration helper ────────────────────────────────────────────

def get_cfgi_for_backtest(token: str, start_date: str, end_date: str, period: int = 4) -> dict:
    """
    Returns {date_str: cfgi_score} dict for easy lookup during backtesting.
    Uses cache. Period 4 = daily (cheapest).
    """
    api_key = os.environ.get("CFGI_API_KEY")
    if not api_key:
        raise ValueError("CFGI_API_KEY environment variable not set")

    client = CFGIClient(api_key)
    rows = client.get_bulk_history(token, period, start_date, end_date, fields="cfgi", cache=True)
    return {row["date"]: row.get("cfgi", row.get("value")) for row in rows if "date" in row}
