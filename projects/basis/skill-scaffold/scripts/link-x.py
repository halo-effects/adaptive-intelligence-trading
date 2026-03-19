"""
link-x.py — Link an X/Twitter account to a Basis wallet via verification tweet

Proves ownership of an X account by posting a challenge code, then confirming
via X's official oEmbed API. No browser automation, no X API credits needed
on the Basis side.

Flow:
  1. Request a challenge code from Basis API
  2. Post the challenge as a tweet (agent uses its own X API keys)
  3. Submit the tweet URL back to Basis for verification
  4. Backend confirms via oEmbed: author matches + challenge code present
  5. X account linked to wallet. Done.

For human operators: do steps 1-3 manually (post the tweet yourself),
then run step 3 with --action confirm.

Usage:
    # Full automated flow (agent has X API keys):
    python link-x.py --action link --wallet 0x... --x-handle MyAgentBot

    # Manual flow — get challenge code:
    python link-x.py --action challenge --wallet 0x... --x-handle MyAgentBot

    # Manual flow — confirm after posting tweet yourself:
    python link-x.py --action confirm --wallet 0x... --tweet-url https://x.com/...

    # Check if a wallet has a linked X account:
    python link-x.py --action status --wallet 0x...

Requires:
    pip install requests python-dotenv

Env vars:
    BASIS_API_KEY          — Basis API key (required for all actions)
    BASIS_API_DOMAIN       — API base URL (default: https://launchonbasis.com)
    X_BEARER_TOKEN         — X API v2 bearer token (required for --action link)
    X_API_KEY              — X API key (alternative OAuth 1.0a auth)
    X_API_SECRET           — X API secret
    X_ACCESS_TOKEN         — X user access token
    X_ACCESS_TOKEN_SECRET  — X user access token secret
"""

import argparse
import json
import os
import sys
import time
import requests
from dotenv import load_dotenv

load_dotenv()

BASIS_API_DOMAIN = os.getenv("BASIS_API_DOMAIN", "https://launchonbasis.com")
BASIS_API_KEY = os.getenv("BASIS_API_KEY", "")

OEMBED_URL = "https://publish.twitter.com/oembed"


# ---------------------------------------------------------------------------
# X posting helpers
# ---------------------------------------------------------------------------

def post_tweet_oauth2(text: str) -> dict:
    """Post a tweet using X API v2 with OAuth 2.0 Bearer + user token."""
    token = os.getenv("X_BEARER_TOKEN", "")
    if not token:
        raise ValueError(
            "X_BEARER_TOKEN env var is required to post tweets. "
            "Set it to your X API v2 user access token."
        )
    resp = requests.post(
        "https://api.twitter.com/2/tweets",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"text": text},
    )
    if resp.status_code == 201:
        data = resp.json()
        tweet_id = data["data"]["id"]
        # We need the handle to construct the URL — caller provides it
        return {"id": tweet_id, "text": text}
    else:
        raise RuntimeError(
            f"Failed to post tweet (HTTP {resp.status_code}): {resp.text}"
        )


def post_tweet_oauth1(text: str) -> dict:
    """Post a tweet using OAuth 1.0a (requires requests-oauthlib)."""
    try:
        from requests_oauthlib import OAuth1
    except ImportError:
        raise ImportError(
            "requests-oauthlib is required for OAuth 1.0a posting. "
            "Install it: pip install requests-oauthlib"
        )

    auth = OAuth1(
        os.getenv("X_API_KEY", ""),
        os.getenv("X_API_SECRET", ""),
        os.getenv("X_ACCESS_TOKEN", ""),
        os.getenv("X_ACCESS_TOKEN_SECRET", ""),
    )
    resp = requests.post(
        "https://api.twitter.com/2/tweets",
        auth=auth,
        json={"text": text},
    )
    if resp.status_code == 201:
        data = resp.json()
        return {"id": data["data"]["id"], "text": text}
    else:
        raise RuntimeError(
            f"Failed to post tweet (HTTP {resp.status_code}): {resp.text}"
        )


def post_tweet(text: str) -> dict:
    """Post a tweet using whichever X auth method is configured."""
    if os.getenv("X_BEARER_TOKEN"):
        return post_tweet_oauth2(text)
    elif os.getenv("X_API_KEY") and os.getenv("X_ACCESS_TOKEN"):
        return post_tweet_oauth1(text)
    else:
        raise ValueError(
            "No X API credentials found. Set either:\n"
            "  - X_BEARER_TOKEN (OAuth 2.0), or\n"
            "  - X_API_KEY + X_API_SECRET + X_ACCESS_TOKEN + X_ACCESS_TOKEN_SECRET (OAuth 1.0a)"
        )


# ---------------------------------------------------------------------------
# oEmbed verification
# ---------------------------------------------------------------------------

def verify_tweet(tweet_url: str) -> dict:
    """Fetch tweet via oEmbed and extract author + text."""
    resp = requests.get(OEMBED_URL, params={"url": tweet_url}, timeout=10)

    if resp.status_code == 404:
        return {"exists": False, "error": "Tweet not found (deleted or private)"}
    if resp.status_code == 403:
        return {"exists": False, "error": "Tweet is from a private/protected account"}

    resp.raise_for_status()
    data = resp.json()

    # Extract handle from author_url: "https://twitter.com/ChairmanAtlas" → "ChairmanAtlas"
    author_url = data.get("author_url", "")
    author_handle = author_url.rstrip("/").split("/")[-1] if author_url else ""

    # Extract text from HTML blockquote
    html = data.get("html", "")
    import re
    from html.parser import HTMLParser

    class TweetTextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.in_p = False
            self.text_parts = []

        def handle_starttag(self, tag, attrs):
            if tag == "p":
                self.in_p = True

        def handle_endtag(self, tag):
            if tag == "p":
                self.in_p = False

        def handle_data(self, data):
            if self.in_p:
                self.text_parts.append(data)

    extractor = TweetTextExtractor()
    extractor.feed(html)
    tweet_text = " ".join(extractor.text_parts).strip()

    # Fallback: regex
    if not tweet_text:
        match = re.search(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
        if match:
            tweet_text = re.sub(r'<[^>]+>', '', match.group(1)).strip()

    return {
        "exists": True,
        "author_handle": author_handle,
        "author_name": data.get("author_name", ""),
        "tweet_text": tweet_text,
        "url": data.get("url", tweet_url),
    }


# ---------------------------------------------------------------------------
# Basis API helpers
# ---------------------------------------------------------------------------

def basis_request(method: str, endpoint: str, **kwargs) -> dict:
    """Make an authenticated request to the Basis API."""
    if not BASIS_API_KEY:
        raise ValueError("BASIS_API_KEY env var is required.")

    headers = kwargs.pop("headers", {})
    headers["X-API-Key"] = BASIS_API_KEY
    url = f"{BASIS_API_DOMAIN}/api{endpoint}"

    resp = requests.request(method, url, headers=headers, timeout=15, **kwargs)

    if resp.status_code == 404:
        return {"error": "Endpoint not found (not deployed yet?)", "status": 404}

    resp.raise_for_status()
    return resp.json()


def request_challenge(wallet: str, x_handle: str) -> dict:
    """Request a verification challenge code from Basis."""
    return basis_request(
        "POST",
        "/v1/social/link-x",
        json={"wallet": wallet, "xHandle": x_handle},
    )


def confirm_link(wallet: str, tweet_url: str) -> dict:
    """Submit the verification tweet for confirmation."""
    # Pre-verify via oEmbed first
    tweet_data = verify_tweet(tweet_url)
    if not tweet_data.get("exists"):
        return {"verified": False, "error": tweet_data.get("error", "Tweet not found")}

    return basis_request(
        "POST",
        "/v1/social/confirm-link",
        json={
            "wallet": wallet,
            "tweetUrl": tweet_url,
            "authorHandle": tweet_data["author_handle"],
            "tweetText": tweet_data["tweet_text"],
        },
    )


def check_status(wallet: str) -> dict:
    """Check if a wallet has a linked X account."""
    return basis_request("GET", f"/v1/social/link-status/{wallet}")


# ---------------------------------------------------------------------------
# CLI actions
# ---------------------------------------------------------------------------

def action_challenge(args):
    """Request a challenge code."""
    if args.dry_run:
        print(f"[DRY RUN] Would request challenge for wallet={args.wallet}, x_handle={args.x_handle}")
        return

    result = request_challenge(args.wallet, args.x_handle)

    if result.get("status") == 404:
        print("⚠️  Endpoint not deployed yet. Here's what the request would look like:")
        print(f"   POST /api/v1/social/link-x")
        print(f"   Body: {{\"wallet\": \"{args.wallet}\", \"xHandle\": \"{args.x_handle}\"}}")
        print(f"\n   Expected response: {{\"challenge\": \"basis-verify-XXXXXX\", \"expiresIn\": \"10 minutes\"}}")
        print(f"\n   Once Alex deploys this endpoint, run this command again.")
        return

    challenge = result.get("challenge", "")
    expires = result.get("expiresIn", "10 minutes")

    print(f"✅ Challenge code: {challenge}")
    print(f"   Expires in: {expires}")
    print(f"\n   Post this tweet from @{args.x_handle}:")
    print(f'   "Verifying my Basis wallet: {challenge} @LaunchOnBasis 🦞"')
    print(f"\n   Then run:")
    print(f"   python link-x.py --action confirm --wallet {args.wallet} --tweet-url <your_tweet_url>")

    if args.json_output:
        print(json.dumps(result, indent=2))


def action_confirm(args):
    """Confirm link by submitting the verification tweet."""
    if not args.tweet_url:
        print("❌ --tweet-url is required for confirm action")
        sys.exit(1)

    if args.dry_run:
        print(f"[DRY RUN] Would verify tweet: {args.tweet_url}")
        print(f"[DRY RUN] Would submit confirmation for wallet: {args.wallet}")
        return

    # First, verify the tweet ourselves
    print(f"Verifying tweet: {args.tweet_url}")
    tweet_data = verify_tweet(args.tweet_url)

    if not tweet_data.get("exists"):
        print(f"❌ {tweet_data.get('error', 'Tweet not found')}")
        sys.exit(1)

    print(f"   Author: @{tweet_data['author_handle']} ({tweet_data['author_name']})")
    print(f"   Text: {tweet_data['tweet_text'][:100]}...")

    # Check for Basis mention
    text_lower = tweet_data["tweet_text"].lower()
    has_basis = "basis" in text_lower or "launchonbasis" in text_lower
    print(f"   Mentions Basis: {'✅' if has_basis else '❌'}")

    # Submit to backend
    print(f"\nSubmitting to Basis API...")
    result = confirm_link(args.wallet, args.tweet_url)

    if result.get("status") == 404:
        print("⚠️  Endpoint not deployed yet. Pre-verification results above are valid.")
        print(f"   When Alex deploys POST /api/v1/social/confirm-link, this will work automatically.")
    elif result.get("verified") is False:
        print(f"❌ Verification failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)
    else:
        print(f"✅ X account @{tweet_data['author_handle']} linked to wallet {args.wallet}")

    if args.json_output:
        output = {**tweet_data, **result, "mentions_basis": has_basis}
        print(json.dumps(output, indent=2))


def action_link(args):
    """Full automated flow: challenge → post tweet → confirm."""
    if not args.x_handle:
        print("❌ --x-handle is required for link action")
        sys.exit(1)

    if args.dry_run:
        print(f"[DRY RUN] Full link flow for wallet={args.wallet}, x_handle={args.x_handle}")
        print(f"[DRY RUN] 1. Request challenge from Basis API")
        print(f"[DRY RUN] 2. Post verification tweet via X API")
        print(f"[DRY RUN] 3. Submit tweet URL to Basis for confirmation")
        return

    # Step 1: Get challenge
    print(f"Step 1: Requesting challenge code...")
    result = request_challenge(args.wallet, args.x_handle)

    if result.get("status") == 404:
        print("⚠️  Challenge endpoint not deployed yet.")
        print("   Use --action challenge to see the expected request format.")
        return

    challenge = result.get("challenge", "")
    if not challenge:
        print(f"❌ No challenge code returned: {result}")
        sys.exit(1)

    print(f"   Challenge: {challenge}")

    # Step 2: Post tweet
    tweet_text = f"Verifying my Basis wallet: {challenge} @LaunchOnBasis 🦞"
    print(f"\nStep 2: Posting verification tweet...")
    print(f'   "{tweet_text}"')

    try:
        tweet_result = post_tweet(tweet_text)
    except Exception as e:
        print(f"❌ Failed to post tweet: {e}")
        print(f"\n   Post it manually from @{args.x_handle}, then run:")
        print(f"   python link-x.py --action confirm --wallet {args.wallet} --tweet-url <url>")
        sys.exit(1)

    tweet_id = tweet_result["id"]
    tweet_url = f"https://x.com/{args.x_handle}/status/{tweet_id}"
    print(f"   Posted: {tweet_url}")

    # Step 3: Wait for tweet to propagate, then confirm
    print(f"\nStep 3: Waiting 5 seconds for propagation...")
    time.sleep(5)

    print(f"   Submitting confirmation...")
    confirm_result = confirm_link(args.wallet, tweet_url)

    if confirm_result.get("status") == 404:
        print(f"⚠️  Confirm endpoint not deployed yet.")
        print(f"   Tweet posted successfully: {tweet_url}")
        print(f"   Run confirm manually when endpoint is ready:")
        print(f"   python link-x.py --action confirm --wallet {args.wallet} --tweet-url {tweet_url}")
    elif confirm_result.get("verified") is False:
        print(f"❌ Verification failed: {confirm_result.get('error')}")
        sys.exit(1)
    else:
        print(f"\n✅ Success! @{args.x_handle} linked to wallet {args.wallet}")

    if args.json_output:
        print(json.dumps({
            "wallet": args.wallet,
            "x_handle": args.x_handle,
            "tweet_url": tweet_url,
            "tweet_id": tweet_id,
            "challenge": challenge,
            "confirmed": confirm_result.get("verified", None),
        }, indent=2))


def action_status(args):
    """Check link status for a wallet."""
    if args.dry_run:
        print(f"[DRY RUN] Would check link status for wallet: {args.wallet}")
        return

    result = check_status(args.wallet)

    if result.get("status") == 404:
        print(f"⚠️  Status endpoint not deployed yet.")
        return

    linked = result.get("linked", False)
    handle = result.get("xHandle", "")

    if linked:
        print(f"✅ Wallet {args.wallet} is linked to @{handle}")
    else:
        print(f"❌ Wallet {args.wallet} has no linked X account")

    if args.json_output:
        print(json.dumps(result, indent=2))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Link an X/Twitter account to a Basis wallet via verification tweet"
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["link", "challenge", "confirm", "status"],
        help="Action to perform",
    )
    parser.add_argument("--wallet", required=True, help="Basis wallet address (0x...)")
    parser.add_argument("--x-handle", help="X/Twitter handle (without @)")
    parser.add_argument("--tweet-url", help="URL of the verification tweet (for confirm)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without making calls")
    parser.add_argument("--json-output", action="store_true", help="Output structured JSON")

    args = parser.parse_args()

    actions = {
        "challenge": action_challenge,
        "confirm": action_confirm,
        "link": action_link,
        "status": action_status,
    }

    try:
        actions[args.action](args)
    except requests.exceptions.HTTPError as e:
        print(f"❌ API error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
