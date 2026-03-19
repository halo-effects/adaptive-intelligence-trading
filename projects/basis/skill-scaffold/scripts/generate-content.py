"""
generate-content.py — Generate ready-to-post social media content from Basis activity

Pulls real on-chain / API data from Basis and formats it into social posts.
Validates that the relevant transaction, market, or token actually exists before
generating content — no hallucinated posts.

Actions (via --action):
  trade-receipt      Post about a recent token buy
  market-launch      Post about a prediction market you created
  token-launch       Post about a token you launched
  portfolio-summary  Weekly/daily P&L activity summary
  agent-intro        Introduction post for a newly registered agent

Usage:
    python generate-content.py --action trade-receipt --wallet 0xYOUR_WALLET
    python generate-content.py --action trade-receipt --wallet 0xYOUR_WALLET --tx-index 0
    python generate-content.py --action market-launch --wallet 0xYOUR_WALLET --market-address 0xMARKET
    python generate-content.py --action token-launch --wallet 0xYOUR_WALLET --token-address 0xTOKEN
    python generate-content.py --action portfolio-summary --wallet 0xYOUR_WALLET --period weekly
    python generate-content.py --action agent-intro --wallet 0xYOUR_WALLET --agent-name "MyBot"
    python generate-content.py --action trade-receipt --wallet 0xYOUR_WALLET --dry-run
    python generate-content.py --action trade-receipt --wallet 0xYOUR_WALLET --json-output

Env vars:
    BASIS_API_KEY       API key for Basis (required for most actions)
    BASIS_RPC_URL       Optional custom RPC endpoint
    BASIS_PRIVATE_KEY   Optional, only needed for on-chain identity checks
"""

import argparse
import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client_helper import get_client, raw_to_usdb, raw_to_token, output_result

BASE_URL = "https://launchonbasis.com"

# ─── Templates ──────────────────────────────────────────────────────────────

TRADE_RECEIPT_TEMPLATES = [
    "Just scooped up {amount} of ${symbol} on Basis 🦞 Price: {price} | {base_url}/token/{address}",
    "📊 Trade Alert | Bought ${symbol} | Entry: {price} | Amount: {amount} USDB | via Basis DEX | {base_url}/token/{address}",
    "Loading up on ${symbol}! Another bag secured on Basis 🦞 | {base_url}/token/{address}",
]

MARKET_LAUNCH_TEMPLATES = [
    "🔮 New market: {name}? | Trade your conviction → {base_url}/token/{address}",
    "Just created a prediction market on Basis: {name} | What do you think? → {base_url}/token/{address}",
    "Let's settle this: {name} | Put your prediction where your mouth is 🦞 → {base_url}/token/{address}",
]

TOKEN_LAUNCH_TEMPLATES = [
    "Just launched ${symbol} on Basis 🦞 | {type} token, price only goes up | {base_url}/token/{address}",
    "New token alert: ${symbol} ({name}) is live on Basis | {type} mechanics | {base_url}/token/{address}",
]

PORTFOLIO_SUMMARY_TEMPLATES = {
    "weekly": [
        "Week on Basis 💎 | {trade_count} trades across {unique_tokens} tokens | Mining multiplier: active 🦞 | {base_url}/profile/{wallet}",
        "Basis activity report 📊 | {trade_count} buys this week | Exploring the agent economy | {base_url}/profile/{wallet}",
    ],
    "daily": [
        "Basis activity report 📊 | {trade_count} buys today | Exploring the agent economy | {base_url}/profile/{wallet}",
        "Daily grind on Basis 🦞 | {trade_count} trades across {unique_tokens} tokens | {base_url}/profile/{wallet}",
    ],
}

AGENT_INTRO_TEMPLATES = [
    "gm! I'm {agent_name}, a DeFi agent mining on Basis 🦞 | I trade tokens, predict markets, and earn points | AMA about the Basis ecosystem | {base_url}/profile/{wallet}",
    "Just registered as an ERC-8004 agent on Basis | On-chain identity + DeFi skills = economic alignment 🦞 | {base_url}/profile/{wallet}",
]


# ─── Helpers ────────────────────────────────────────────────────────────────

def format_usdb(raw_amount: int) -> str:
    """Format raw 18-decimal USDB amount to human-readable string."""
    amount = raw_to_usdb(raw_amount)
    if amount >= 1000:
        return f"{amount:,.2f}"
    return f"{amount:.4f}"


def format_price(price_raw) -> str:
    """Format a price value (may already be float or raw int)."""
    if isinstance(price_raw, int) and price_raw > 10**15:
        # Looks like 18-decimal raw
        price = raw_to_usdb(price_raw)
    else:
        price = float(price_raw)

    if price < 0.0001:
        return f"${price:.8f}"
    elif price < 1:
        return f"${price:.6f}"
    else:
        return f"${price:,.4f}"


def period_cutoff(period: str) -> datetime:
    """Return UTC datetime cutoff for the given period."""
    now = datetime.now(timezone.utc)
    if period == "daily":
        return now - timedelta(days=1)
    return now - timedelta(days=7)


def build_platform_links(address: str = None, wallet: str = None) -> dict:
    links = {}
    if address:
        links["basis_token"] = f"{BASE_URL}/token/{address}"
    if wallet:
        links["basis_profile"] = f"{BASE_URL}/profile/{wallet}"
    return links


# ─── Actions ────────────────────────────────────────────────────────────────

def action_trade_receipt(args, client):
    """Generate a post about a recent token buy."""
    wallet = args.wallet

    if args.dry_run:
        print(f"[DRY RUN] Would fetch: client.api.get_wallet_transactions({wallet!r})")
        print(f"[DRY RUN] Would select tx-index={args.tx_index or 'most recent buy'}")
        print("[DRY RUN] No API calls made.")
        result = {"status": "dry_run", "action": "trade-receipt", "wallet": wallet}
        output_result(result, args.json_output)
        return

    print(f"Fetching transactions for {wallet}...")
    try:
        transactions = client.api.get_wallet_transactions(wallet)
    except Exception as e:
        print(f"❌ Failed to fetch transactions: {e}", file=sys.stderr)
        sys.exit(1)

    # Filter to buys only
    buys = [tx for tx in transactions if tx.get("type", "").lower() == "buy"]

    if not buys:
        print(f"❌ No buy transactions found for wallet {wallet}", file=sys.stderr)
        sys.exit(1)

    # Select the right transaction
    idx = args.tx_index if args.tx_index is not None else 0
    if idx >= len(buys):
        print(f"❌ tx-index {idx} out of range — wallet only has {len(buys)} buy(s)", file=sys.stderr)
        sys.exit(1)

    tx = buys[idx]

    # Validate it's a buy for this wallet
    tx_wallet = tx.get("wallet") or tx.get("user") or tx.get("from", "")
    if tx_wallet.lower() != wallet.lower():
        print(f"❌ Transaction does not belong to wallet {wallet}", file=sys.stderr)
        sys.exit(1)

    # Extract fields (SDK returns various shapes — handle gracefully)
    token_address = tx.get("contractAddress") or tx.get("tokenAddress") or tx.get("token", "unknown")
    symbol = tx.get("symbol") or tx.get("tokenSymbol") or "???"
    token_name = tx.get("name") or tx.get("tokenName") or symbol

    # Amount: amountUSDC / amountUSDB may be raw 18-decimal string or float
    raw_amount = tx.get("amountUSDC") or tx.get("amountUSDB") or tx.get("usdcAmount") or 0
    if isinstance(raw_amount, str):
        raw_amount = int(raw_amount)
    amount_str = format_usdb(raw_amount)

    # Price
    price_raw = tx.get("price") or tx.get("priceUSD") or tx.get("usdPrice") or 0
    price_str = format_price(price_raw)

    template = random.choice(TRADE_RECEIPT_TEMPLATES)
    content = template.format(
        amount=amount_str,
        symbol=symbol,
        price=price_str,
        address=token_address,
        base_url=BASE_URL,
    )

    print(f"\n✅ Generated trade receipt post:\n")
    print(content)

    result = {
        "content": content,
        "platform_links": build_platform_links(address=token_address, wallet=wallet),
        "validated": True,
        "tx_index": idx,
        "token": token_address,
        "symbol": symbol,
    }
    output_result(result, args.json_output)


def action_market_launch(args, client):
    """Generate a post about a prediction market you created."""
    wallet = args.wallet
    market_address = args.market_address

    if not market_address:
        print("❌ --market-address is required for market-launch", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"[DRY RUN] Would fetch: client.api.get_token({market_address!r})")
        print(f"[DRY RUN] Would validate: isPrediction=True, creator={wallet!r}")
        print("[DRY RUN] No API calls made.")
        result = {"status": "dry_run", "action": "market-launch", "market_address": market_address}
        output_result(result, args.json_output)
        return

    print(f"Fetching market data for {market_address}...")
    try:
        token = client.api.get_token(market_address)
    except Exception as e:
        print(f"❌ Failed to fetch market: {e}", file=sys.stderr)
        sys.exit(1)

    if not token:
        print(f"❌ Market {market_address} not found", file=sys.stderr)
        sys.exit(1)

    # Validate: must be a prediction market
    is_prediction = token.get("isPrediction") or token.get("is_prediction") or False
    if not is_prediction:
        print(f"❌ Token {market_address} is not a prediction market", file=sys.stderr)
        sys.exit(1)

    # Validate: must be created by this wallet
    creator = token.get("dev") or token.get("creator") or token.get("deployedBy") or ""
    if creator.lower() != wallet.lower():
        print(f"❌ Market {market_address} was not created by {wallet} (creator: {creator})", file=sys.stderr)
        sys.exit(1)

    market_name = token.get("name") or token.get("question") or "Unknown Market"

    template = random.choice(MARKET_LAUNCH_TEMPLATES)
    content = template.format(
        name=market_name,
        address=market_address,
        base_url=BASE_URL,
    )

    print(f"\n✅ Generated market launch post:\n")
    print(content)

    result = {
        "content": content,
        "platform_links": build_platform_links(address=market_address, wallet=wallet),
        "validated": True,
        "market_address": market_address,
        "market_name": market_name,
    }
    output_result(result, args.json_output)


def action_token_launch(args, client):
    """Generate a post about a token you created."""
    wallet = args.wallet
    token_address = args.token_address

    if not token_address:
        print("❌ --token-address is required for token-launch", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"[DRY RUN] Would fetch: client.api.get_token({token_address!r})")
        print(f"[DRY RUN] Would fetch: client.factory.get_token_state({token_address!r})")
        print(f"[DRY RUN] Would validate: creator={wallet!r}, supply > 0")
        print("[DRY RUN] No API calls made.")
        result = {"status": "dry_run", "action": "token-launch", "token_address": token_address}
        output_result(result, args.json_output)
        return

    print(f"Fetching token data for {token_address}...")
    try:
        token = client.api.get_token(token_address)
    except Exception as e:
        print(f"❌ Failed to fetch token: {e}", file=sys.stderr)
        sys.exit(1)

    if not token:
        print(f"❌ Token {token_address} not found", file=sys.stderr)
        sys.exit(1)

    # Validate: must be created by this wallet
    creator = token.get("dev") or token.get("creator") or token.get("deployedBy") or ""
    if creator.lower() != wallet.lower():
        print(f"❌ Token {token_address} was not created by {wallet} (creator: {creator})", file=sys.stderr)
        sys.exit(1)

    # Validate: must not be a prediction market
    is_prediction = token.get("isPrediction") or token.get("is_prediction") or False
    if is_prediction:
        print(f"❌ {token_address} is a prediction market — use market-launch instead", file=sys.stderr)
        sys.exit(1)

    # Get on-chain state for supply check
    try:
        state = client.factory.get_token_state(token_address)
        supply_raw = state.get("totalSupply") or state.get("supply") or 0
        if isinstance(supply_raw, str):
            supply_raw = int(supply_raw)
        if supply_raw == 0:
            print(f"❌ Token {token_address} has zero supply — launch may not have completed", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"⚠️  Could not verify on-chain supply: {e} — proceeding anyway")
        state = {}

    symbol = token.get("symbol") or "???"
    name = token.get("name") or symbol

    # Determine type: Stable+ or Floor+
    token_type = token.get("tokenType") or token.get("type") or ""
    if "floor" in token_type.lower():
        type_label = "Floor+"
    else:
        type_label = "Stable+"

    template = random.choice(TOKEN_LAUNCH_TEMPLATES)
    content = template.format(
        symbol=symbol,
        name=name,
        type=type_label,
        address=token_address,
        base_url=BASE_URL,
    )

    print(f"\n✅ Generated token launch post:\n")
    print(content)

    result = {
        "content": content,
        "platform_links": build_platform_links(address=token_address, wallet=wallet),
        "validated": True,
        "token_address": token_address,
        "symbol": symbol,
        "token_type": type_label,
    }
    output_result(result, args.json_output)


def action_portfolio_summary(args, client):
    """Generate a P&L activity summary post."""
    wallet = args.wallet
    period = args.period or "weekly"

    if period not in ("daily", "weekly"):
        print(f"❌ --period must be 'daily' or 'weekly', got: {period!r}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"[DRY RUN] Would fetch: client.api.get_wallet_transactions({wallet!r})")
        print(f"[DRY RUN] Would filter to last {'7 days' if period == 'weekly' else '24 hours'}")
        print("[DRY RUN] No API calls made.")
        result = {"status": "dry_run", "action": "portfolio-summary", "wallet": wallet, "period": period}
        output_result(result, args.json_output)
        return

    print(f"Fetching transactions for {wallet}...")
    try:
        transactions = client.api.get_wallet_transactions(wallet)
    except Exception as e:
        print(f"❌ Failed to fetch transactions: {e}", file=sys.stderr)
        sys.exit(1)

    cutoff = period_cutoff(period)

    # Filter to buys within the period
    period_buys = []
    for tx in transactions:
        if tx.get("type", "").lower() != "buy":
            continue

        # Parse timestamp — may be ISO string or unix seconds
        ts_raw = tx.get("timestamp") or tx.get("createdAt") or tx.get("blockTimestamp")
        if not ts_raw:
            continue
        try:
            if isinstance(ts_raw, (int, float)):
                ts = datetime.fromtimestamp(ts_raw, tz=timezone.utc)
            else:
                ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
        except Exception:
            continue

        if ts >= cutoff:
            period_buys.append(tx)

    if not period_buys:
        period_label = "today" if period == "daily" else "this week"
        print(f"❌ No buy transactions found for {wallet} {period_label}", file=sys.stderr)
        sys.exit(1)

    trade_count = len(period_buys)
    unique_tokens = len(set(
        tx.get("contractAddress") or tx.get("tokenAddress") or tx.get("token", "")
        for tx in period_buys
    ))

    templates = PORTFOLIO_SUMMARY_TEMPLATES.get(period, PORTFOLIO_SUMMARY_TEMPLATES["weekly"])
    template = random.choice(templates)
    content = template.format(
        trade_count=trade_count,
        unique_tokens=unique_tokens,
        period=period,
        wallet=wallet,
        base_url=BASE_URL,
    )

    print(f"\n✅ Generated portfolio summary post:\n")
    print(content)

    result = {
        "content": content,
        "platform_links": build_platform_links(wallet=wallet),
        "validated": True,
        "period": period,
        "trade_count": trade_count,
        "unique_tokens": unique_tokens,
    }
    output_result(result, args.json_output)


def action_agent_intro(args, client):
    """Generate an introduction post for a newly registered agent."""
    wallet = args.wallet
    agent_name = args.agent_name or os.getenv("BASIS_AGENT_NAME", "BasisAgent")

    if args.dry_run:
        print(f"[DRY RUN] Would check if {wallet!r} is registered as an ERC-8004 agent")
        print("[DRY RUN] No API calls made.")
        result = {"status": "dry_run", "action": "agent-intro", "wallet": wallet}
        output_result(result, args.json_output)
        return

    # Validate: wallet must be registered as an agent
    print(f"Checking agent registration for {wallet}...")
    is_agent = False
    try:
        # Try SDK agent identity check
        identity = client.agent.get_identity(wallet)
        is_agent = bool(identity)
        if is_agent and not agent_name:
            agent_name = identity.get("name") or agent_name
    except AttributeError:
        pass
    except Exception:
        pass

    if not is_agent:
        # Fallback: try API
        try:
            agent_data = client.api.get_agent(wallet)
            is_agent = bool(agent_data)
            if is_agent and not agent_name:
                agent_name = agent_data.get("name") or agent_name
        except Exception:
            pass

    if not is_agent:
        print(f"❌ Wallet {wallet} is not registered as an ERC-8004 agent", file=sys.stderr)
        print(f"   Register first with the SDK: client.agent.register()", file=sys.stderr)
        sys.exit(1)

    template = random.choice(AGENT_INTRO_TEMPLATES)
    content = template.format(
        agent_name=agent_name,
        wallet=wallet,
        base_url=BASE_URL,
    )

    print(f"\n✅ Generated agent intro post:\n")
    print(content)

    result = {
        "content": content,
        "platform_links": build_platform_links(wallet=wallet),
        "validated": True,
        "agent_name": agent_name,
        "wallet": wallet,
    }
    output_result(result, args.json_output)


# ─── CLI ────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate ready-to-post social media content from Basis on-chain activity"
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["trade-receipt", "market-launch", "token-launch", "portfolio-summary", "agent-intro"],
        help="Content type to generate",
    )
    parser.add_argument("--wallet", required=True, help="Agent wallet address (0x...)")

    # trade-receipt
    parser.add_argument(
        "--tx-index",
        type=int,
        default=None,
        help="Buy transaction index (0 = most recent buy, default: most recent)",
    )

    # market-launch
    parser.add_argument("--market-address", help="Prediction market contract address (0x...)")

    # token-launch
    parser.add_argument("--token-address", help="Token contract address (0x...)")

    # portfolio-summary
    parser.add_argument(
        "--period",
        choices=["daily", "weekly"],
        default="weekly",
        help="Summary period (default: weekly)",
    )

    # agent-intro
    parser.add_argument("--agent-name", help="Agent display name for intro post")

    parser.add_argument("--dry-run", action="store_true", help="Show what would be fetched, no API calls")
    parser.add_argument("--json-output", action="store_true", help="Output result as JSON")
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Basis Content Generator — {args.action}")
    print("=" * 60)
    print(f"  Action:  {args.action}")
    print(f"  Wallet:  {args.wallet}")

    if args.dry_run:
        client = None
    else:
        client = get_client(require_write=False)

    dispatch = {
        "trade-receipt": action_trade_receipt,
        "market-launch": action_market_launch,
        "token-launch": action_token_launch,
        "portfolio-summary": action_portfolio_summary,
        "agent-intro": action_agent_intro,
    }

    dispatch[args.action](args, client)


if __name__ == "__main__":
    main()
