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


ENDPOINT = "https://cfgi.io/api/api_request_v2.php"

# Coins with CFGI coin-specific index data.
# Only include coins that the CFGI API actually supports.
# Updated 2026-03-19 to align with 50-coin Aster universe.
# New coins (BERA, MOVE, INIT, etc.) may not have CFGI data yet — excluded.
VALID_TOKENS = [
    # Core (high confidence CFGI support)
    "BTC", "ETH", "SOL", "DOGE", "PEPE", "AVAX", "ADA", "XRP",
    "DOT", "LINK", "UNI", "AAVE", "SUI", "ARB", "INJ", "TRUMP",
    "HYPE", "NEAR", "ATOM", "FIL",
    # Extended (likely supported — verify against API)
    "ONDO", "ENA", "TIA", "APT", "SEI", "FET", "TAO",
    "PENDLE", "STX", "JUP", "ZRO", "EIGEN",
    # Special
    "MARKET",
]

VALID_FIELDS = [
    "cfgi", "price", "volatility", "volume", "impulse",
    "dominance", "technical", "social", "trends", "whales", "orders",
]

PERIODS = {1: "15m", 2: "1h", 3: "4h", 4: "1d"}


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
        """Fetch latest value for given tokens. Returns {token: {field: value, ...}}."""
        params = {
            "token": ",".join(tokens),
            "period": period,
            "values": 1,
            "fields": fields,
        }
        data = self._request(params)
        return self._parse_multi_token(data, tokens)

    def get_history(self, token: str, period: int, start: str, end: str, fields: str = "cfgi") -> list:
        """Fetch historical range with auto-pagination (max 1200 per request)."""
        all_data = []
        current_start = start

        while True:
            params = {
                "token": token,
                "period": period,
                "start": current_start,
                "end": end,
                "fields": fields,
                "values": 1200,
            }
            data = self._request(params)
            rows = self._parse_single_token(data, token)
            if not rows:
                break
            all_data.extend(rows)
            if len(rows) < 1200:
                break
            # Next page starts after last row's date
            last_date = rows[-1].get("date", "")
            if not last_date or last_date >= end:
                break
            current_start = last_date

        # Deduplicate by date and sort
        seen = {}
        for r in all_data:
            seen[r.get("date", "")] = r
        return sorted(seen.values(), key=lambda x: x.get("date", ""))

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
        """Parse API response for multiple tokens."""
        result = {}
        if isinstance(data, dict):
            for token in tokens:
                token_data = data.get(token, data.get(token.upper(), data.get(token.lower())))
                if token_data is None and len(tokens) == 1:
                    # Single token response might not be nested
                    token_data = data
                if isinstance(token_data, list) and token_data:
                    result[token] = token_data[0] if len(token_data) == 1 else token_data[-1]
                elif isinstance(token_data, dict):
                    result[token] = token_data
        elif isinstance(data, list):
            # API returns flat list with "token" field per entry
            for item in data:
                if isinstance(item, dict):
                    t = item.get("token", "")
                    if t in tokens:
                        result[t] = item
            # Fallback: single token, flat list
            if not result and len(tokens) == 1 and data:
                result[tokens[0]] = data[-1] if isinstance(data[-1], dict) else {"cfgi": data[-1]}
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
