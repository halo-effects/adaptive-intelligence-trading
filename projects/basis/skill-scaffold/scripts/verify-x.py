"""
verify-x.py — Verify X/Twitter posts mentioning Basis and submit for points

Uses X's official oEmbed API (free, no API key needed) to confirm a tweet exists,
was posted by the expected account, and mentions Basis. Verified posts can be
submitted to the Basis API for social activity points.

Actions (via --action):
  verify        Verify a single tweet URL
  submit        Verify and submit to Basis API for points
  batch-verify  Verify multiple tweets from a file (one URL per line)

Usage:
    python verify-x.py --action verify --tweet-url https://x.com/user/status/123
    python verify-x.py --action verify --tweet-url https://x.com/user/status/123 --expected-handle MyBot
    python verify-x.py --action submit --tweet-url https://x.com/user/status/123 --wallet 0xYOUR_WALLET
    python verify-x.py --action batch-verify --input-file tweets.txt --expected-handle MyBot
    python verify-x.py --action verify --tweet-url https://x.com/user/status/123 --dry-run
    python verify-x.py --action verify --tweet-url https://x.com/user/status/123 --json-output

Env vars:
    BASIS_API_DOMAIN    Base URL for Basis API (default: https://launchonbasis.com)
    BASIS_API_KEY       Required for submit action
"""

import argparse
import json
import os
import re
import sys
import time
from html.parser import HTMLParser
from urllib.parse import urlencode, quote_plus
from dotenv import load_dotenv

load_dotenv()

BASIS_API_DOMAIN = os.getenv("BASIS_API_DOMAIN", "https://launchonbasis.com")
OEMBED_URL = "https://publish.twitter.com/oembed"
BASIS_KEYWORDS = ["basis", "launchonbasis"]

# Rate limit between batch requests (200ms)
BATCH_DELAY_SEC = 0.2


# ─── Helpers ────────────────────────────────────────────────────────────────

def get_requests():
    """Import requests, fail gracefully if not installed."""
    try:
        import requests
        return requests
    except ImportError:
        print("ERROR: requests not installed.", file=sys.stderr)
        print("Install with: pip install requests", file=sys.stderr)
        sys.exit(1)


class BlockquoteTextExtractor(HTMLParser):
    """Extract plain text from the tweet blockquote in oEmbed HTML."""

    def __init__(self):
        super().__init__()
        self._in_blockquote = False
        self._depth = 0
        self._parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "blockquote":
            self._in_blockquote = True
            self._depth = 0
        elif self._in_blockquote:
            self._depth += 1

    def handle_endtag(self, tag):
        if tag == "blockquote" and self._in_blockquote:
            self._in_blockquote = False
        elif self._in_blockquote and self._depth > 0:
            self._depth -= 1

    def handle_data(self, data):
        if self._in_blockquote:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped)

    def get_text(self) -> str:
        return " ".join(self._parts)


def extract_tweet_text(html: str) -> str:
    """Extract clean tweet text from oEmbed HTML."""
    # Try HTML parser first
    parser = BlockquoteTextExtractor()
    try:
        parser.feed(html)
        text = parser.get_text()
        if text:
            return text
    except Exception:
        pass

    # Fallback: regex strip
    # Pull out blockquote content
    bq_match = re.search(r"<blockquote[^>]*>(.*?)</blockquote>", html, re.DOTALL | re.IGNORECASE)
    if bq_match:
        inner = bq_match.group(1)
        # Strip all tags
        clean = re.sub(r"<[^>]+>", " ", inner)
        # Collapse whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    return ""


def parse_handle_from_url(author_url: str) -> str:
    """
    Parse X handle from author_url.
    e.g. https://twitter.com/ChairmanAtlas → ChairmanAtlas
         https://x.com/BasisAgent → BasisAgent
    """
    match = re.search(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]+)/?$", author_url)
    if match:
        return match.group(1)
    # Fallback: last path segment
    parts = [p for p in author_url.rstrip("/").split("/") if p]
    return parts[-1] if parts else ""


def normalize_handle(handle: str) -> str:
    """Normalize handle for comparison (strip @, lowercase)."""
    return handle.lstrip("@").lower()


def mentions_basis(text: str) -> bool:
    """Check if tweet text mentions Basis (case-insensitive)."""
    lower = text.lower()
    return any(kw in lower for kw in BASIS_KEYWORDS)


def validate_tweet_url(url: str) -> str:
    """Basic validation that URL looks like a tweet URL."""
    if not url:
        return "Empty URL"
    if not re.match(r"https?://(www\.)?(twitter\.com|x\.com)/.+/status/\d+", url):
        return f"URL does not look like a tweet: {url}"
    return ""


# ─── Core verify logic ───────────────────────────────────────────────────────

def fetch_oembed(tweet_url: str, requests_mod) -> dict:
    """
    Call the oEmbed API and return parsed JSON.
    Returns dict with keys: ok, status_code, data, error
    """
    params = {"url": tweet_url, "omit_script": "true"}
    endpoint = f"{OEMBED_URL}?{urlencode(params)}"

    try:
        response = requests_mod.get(endpoint, timeout=10)
        if response.status_code == 200:
            return {"ok": True, "status_code": 200, "data": response.json(), "error": None}
        elif response.status_code == 404:
            return {"ok": False, "status_code": 404, "data": None, "error": "Tweet not found (deleted or never existed)"}
        elif response.status_code == 403:
            return {"ok": False, "status_code": 403, "data": None, "error": "Access denied (account may be private or suspended)"}
        elif response.status_code == 401:
            return {"ok": False, "status_code": 401, "data": None, "error": "Unauthorized — account may be protected"}
        else:
            return {"ok": False, "status_code": response.status_code, "data": None,
                    "error": f"Unexpected HTTP {response.status_code}"}
    except Exception as e:
        return {"ok": False, "status_code": None, "data": None, "error": f"Request failed: {e}"}


def verify_tweet(tweet_url: str, expected_handle: str = None, requests_mod=None) -> dict:
    """
    Core verification logic. Returns structured result dict.
    """
    result = {
        "verified": False,
        "tweet_url": tweet_url,
        "author_handle": None,
        "mentions_basis": False,
        "tweet_text": "",
        "checks": {
            "tweet_exists": False,
            "author_matches": None,  # None = not checked (no expected_handle given)
            "mentions_basis": False,
        },
        "error": None,
    }

    # Step 1: Validate URL format
    url_err = validate_tweet_url(tweet_url)
    if url_err:
        result["error"] = url_err
        return result

    # Step 2: Fetch oEmbed
    oembed = fetch_oembed(tweet_url, requests_mod)

    if not oembed["ok"]:
        result["error"] = oembed["error"]
        result["checks"]["tweet_exists"] = False
        return result

    result["checks"]["tweet_exists"] = True
    data = oembed["data"]

    # Step 3: Extract author handle
    author_url = data.get("author_url", "")
    handle = parse_handle_from_url(author_url)
    result["author_handle"] = handle

    # Step 4: Extract tweet text
    html = data.get("html", "")
    tweet_text = extract_tweet_text(html)
    result["tweet_text"] = tweet_text

    # Step 5: Check author match
    if expected_handle:
        author_matches = normalize_handle(handle) == normalize_handle(expected_handle)
        result["checks"]["author_matches"] = author_matches
        if not author_matches:
            result["error"] = f"Author mismatch: expected @{expected_handle}, got @{handle}"
    else:
        result["checks"]["author_matches"] = None  # not checked

    # Step 6: Check Basis mention
    basis_mention = mentions_basis(tweet_text)
    result["mentions_basis"] = basis_mention
    result["checks"]["mentions_basis"] = basis_mention

    # Step 7: Overall verified flag
    # Must: exist + pass author check (if requested) + mention Basis
    author_ok = (result["checks"]["author_matches"] is not False)
    result["verified"] = (
        result["checks"]["tweet_exists"]
        and author_ok
        and basis_mention
    )

    return result


def print_verification_result(result: dict):
    """Pretty-print a single verification result."""
    tweet_url = result.get("tweet_url", "")
    checks = result.get("checks", {})

    print(f"\n  Tweet URL:     {tweet_url}")
    print(f"  Author:        @{result.get('author_handle') or 'unknown'}")
    print(f"  Tweet text:    {result.get('tweet_text', '')[:120]}")
    print()

    def check_icon(val):
        if val is True:
            return "✅"
        elif val is False:
            return "❌"
        return "—"

    print(f"  {check_icon(checks.get('tweet_exists'))}  Tweet exists")

    author_check = checks.get("author_matches")
    if author_check is None:
        print(f"  —  Author match (not checked — no --expected-handle given)")
    else:
        print(f"  {check_icon(author_check)}  Author matches expected handle")

    print(f"  {check_icon(checks.get('mentions_basis'))}  Mentions Basis")
    print()

    if result.get("verified"):
        print(f"  ✅ VERIFIED — Post qualifies for Basis social points")
    else:
        err = result.get("error", "")
        if err:
            print(f"  ❌ FAILED — {err}")
        elif not checks.get("mentions_basis"):
            print(f"  ❌ FAILED — Tweet does not mention 'basis' or 'launchonbasis'")
        else:
            print(f"  ❌ FAILED — Verification failed")


# ─── Actions ────────────────────────────────────────────────────────────────

def action_verify(args, requests_mod):
    """Verify a single tweet."""
    if args.dry_run:
        print(f"[DRY RUN] Would call: GET {OEMBED_URL}?url={quote_plus(args.tweet_url)}")
        if args.expected_handle:
            print(f"[DRY RUN] Would check author == @{args.expected_handle}")
        print(f"[DRY RUN] Would check tweet text for 'basis' or 'launchonbasis'")
        print("[DRY RUN] No network calls made.")
        result = {"status": "dry_run", "action": "verify", "tweet_url": args.tweet_url}
        if args.json_output:
            print(json.dumps(result, indent=2))
        return

    result = verify_tweet(args.tweet_url, args.expected_handle, requests_mod)
    print_verification_result(result)

    if args.json_output:
        print(json.dumps(result, indent=2, default=str))

    if not result["verified"]:
        sys.exit(1)


def action_submit(args, requests_mod):
    """Verify tweet and submit to Basis API for points."""
    wallet = args.wallet
    if not wallet:
        print("❌ --wallet is required for submit action", file=sys.stderr)
        sys.exit(1)

    api_key = os.getenv("BASIS_API_KEY")
    if not api_key:
        print("⚠️  BASIS_API_KEY not set — submission will be attempted without auth")

    if args.dry_run:
        print(f"[DRY RUN] Would call: GET {OEMBED_URL}?url={quote_plus(args.tweet_url)}")
        print(f"[DRY RUN] Would POST to: {BASIS_API_DOMAIN}/api/v1/social/verify-tweet")
        print(f"[DRY RUN] Payload: {{tweetUrl, wallet={wallet!r}, authorHandle, tweetText, mentionsBasis}}")
        print("[DRY RUN] No network calls made.")
        result = {"status": "dry_run", "action": "submit", "tweet_url": args.tweet_url, "wallet": wallet}
        if args.json_output:
            print(json.dumps(result, indent=2))
        return

    # Step 1: Verify
    print(f"Verifying tweet...")
    result = verify_tweet(args.tweet_url, expected_handle=None, requests_mod=requests_mod)
    print_verification_result(result)

    if not result["verified"]:
        print("❌ Tweet did not pass verification — not submitting to API", file=sys.stderr)
        if args.json_output:
            result["submission"] = {"status": "skipped", "reason": "verification_failed"}
            print(json.dumps(result, indent=2, default=str))
        sys.exit(1)

    # Step 2: Submit to Basis API
    submit_url = f"{BASIS_API_DOMAIN}/api/v1/social/verify-tweet"
    payload = {
        "tweetUrl": args.tweet_url,
        "wallet": wallet,
        "authorHandle": result.get("author_handle", ""),
        "tweetText": result.get("tweet_text", ""),
        "mentionsBasis": result.get("mentions_basis", False),
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    print(f"\nSubmitting to Basis API: {submit_url}")
    try:
        response = requests_mod.post(submit_url, json=payload, headers=headers, timeout=10)

        if response.status_code == 200:
            print(f"✅ Submission accepted — points will be credited to {wallet}")
            submission_result = response.json() if response.content else {}
            result["submission"] = {"status": "accepted", "response": submission_result}
        elif response.status_code == 404:
            print(f"⚠️  Submission endpoint not yet live (404) — tweet is verified but not submitted")
            print(f"    Verified data ready for when {submit_url} is deployed:")
            print(f"    {json.dumps(payload, indent=4)}")
            result["submission"] = {"status": "endpoint_not_found", "payload": payload}
        elif response.status_code == 409:
            print(f"⚠️  Tweet already submitted (409 Conflict)")
            result["submission"] = {"status": "duplicate"}
        else:
            print(f"❌ Submission failed: HTTP {response.status_code} — {response.text[:200]}")
            result["submission"] = {"status": "failed", "http_status": response.status_code}

    except Exception as e:
        print(f"❌ Submission request failed: {e}", file=sys.stderr)
        result["submission"] = {"status": "error", "error": str(e)}

    if args.json_output:
        print(json.dumps(result, indent=2, default=str))


def action_batch_verify(args, requests_mod):
    """Verify multiple tweets from a file."""
    input_file = args.input_file
    if not input_file:
        print("❌ --input-file is required for batch-verify", file=sys.stderr)
        sys.exit(1)

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        print(f"❌ Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to read input file: {e}", file=sys.stderr)
        sys.exit(1)

    if not lines:
        print(f"❌ Input file is empty: {input_file}", file=sys.stderr)
        sys.exit(1)

    print(f"Batch verifying {len(lines)} tweet(s) from {input_file}...")
    if args.expected_handle:
        print(f"Expected handle: @{args.expected_handle}")
    print()

    results = []
    passed = 0
    failed = 0

    for i, url in enumerate(lines, 1):
        print(f"[{i}/{len(lines)}] {url}")

        if args.dry_run:
            print(f"  [DRY RUN] Would verify this URL")
            results.append({"tweet_url": url, "status": "dry_run"})
            continue

        result = verify_tweet(url, args.expected_handle, requests_mod)
        results.append(result)

        if result["verified"]:
            print(f"  ✅ VERIFIED — @{result.get('author_handle')}")
            passed += 1
        else:
            err = result.get("error", "Failed")
            print(f"  ❌ FAILED — {err}")
            failed += 1

        # Respect rate limit
        if i < len(lines):
            time.sleep(BATCH_DELAY_SEC)

    # Summary
    print()
    print("=" * 50)
    print(f"Batch Results: {passed} passed, {failed} failed, {len(lines)} total")

    if args.json_output:
        summary = {
            "total": len(lines),
            "passed": passed,
            "failed": failed,
            "results": results,
        }
        print(json.dumps(summary, indent=2, default=str))

    if failed > 0:
        sys.exit(1)


# ─── CLI ────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Verify X/Twitter posts mentioning Basis and optionally submit for points"
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["verify", "submit", "batch-verify"],
        help="Action to perform",
    )

    # verify / submit
    parser.add_argument("--tweet-url", help="Tweet URL to verify (https://x.com/user/status/...)")
    parser.add_argument(
        "--expected-handle",
        help="Expected X handle (without @) — if given, author must match",
    )

    # submit
    parser.add_argument("--wallet", help="Wallet address to credit points to (submit action)")

    # batch-verify
    parser.add_argument("--input-file", help="Path to file with one tweet URL per line (batch-verify)")

    parser.add_argument("--dry-run", action="store_true", help="Show what would be verified/submitted, no calls")
    parser.add_argument("--json-output", action="store_true", help="Output result as JSON")
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Basis X Verification — {args.action}")
    print("=" * 60)

    requests_mod = get_requests()

    # Validate required args per action
    if args.action in ("verify", "submit") and not args.tweet_url:
        print(f"❌ --tweet-url is required for {args.action}", file=sys.stderr)
        sys.exit(1)

    if args.action == "submit" and not args.wallet:
        print("❌ --wallet is required for submit", file=sys.stderr)
        sys.exit(1)

    if args.action == "batch-verify" and not args.input_file:
        print("❌ --input-file is required for batch-verify", file=sys.stderr)
        sys.exit(1)

    dispatch = {
        "verify": action_verify,
        "submit": action_submit,
        "batch-verify": action_batch_verify,
    }

    dispatch[args.action](args, requests_mod)


if __name__ == "__main__":
    main()
