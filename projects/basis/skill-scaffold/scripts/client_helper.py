"""
client_helper.py — Shared Basis SDK client initialization and utilities

Used by all basis-defi skill scripts. Handles:
- BasisClient initialization (read-only, API key, or full mode)
- Environment variable loading
- Decimal conversion helpers
- Common output formatting
"""

import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()

# Contract addresses (defaults from SDK — can override via env)
MAINTOKEN = os.getenv("BASIS_MAINTOKEN", "0x60Cd4E22C62c23d094479f38b1a80a1829e8D361")
USDC = os.getenv("BASIS_USDC", "0xb957F3d754267B01bb1581344eFFe9726522F236")
MARKET_TRADING = os.getenv("BASIS_MARKET_TRADING", "0x35F4874425868efaba198CB32273F465DcEcb7cC")

# Decimal constants
USDC_DECIMALS = 6
TOKEN_DECIMALS = 18


def usdc_to_raw(amount: float) -> int:
    """Convert human-readable USDC to raw units (6 decimals)."""
    return int(amount * 10**USDC_DECIMALS)


def raw_to_usdc(raw: int) -> float:
    """Convert raw USDC units to human-readable."""
    return raw / 10**USDC_DECIMALS


def token_to_raw(amount: float) -> int:
    """Convert human-readable token amount to raw units (18 decimals)."""
    return int(amount * 10**TOKEN_DECIMALS)


def raw_to_token(raw: int) -> float:
    """Convert raw token units to human-readable."""
    return raw / 10**TOKEN_DECIMALS


def get_client(require_write: bool = False, register_agent: bool = False):
    """
    Initialize BasisClient from environment variables.
    
    Args:
        require_write: If True, requires BASIS_PRIVATE_KEY for write operations.
        register_agent: If True, auto-registers as ERC-8004 agent on first use.
    
    Returns:
        BasisClient instance
    """
    try:
        from basis import BasisClient
    except ImportError:
        print("ERROR: basis-sdk not installed.", file=sys.stderr)
        print("Install with: pip install basis-sdk", file=sys.stderr)
        print("Note: Package not yet published to PyPI — awaiting Alex's beta release.", file=sys.stderr)
        sys.exit(1)

    private_key = os.getenv("BASIS_PRIVATE_KEY")
    api_key = os.getenv("BASIS_API_KEY")
    rpc_url = os.getenv("BASIS_RPC_URL", "https://bsc-dataseed.binance.org/")

    if require_write and not private_key:
        print("ERROR: BASIS_PRIVATE_KEY required for write operations.", file=sys.stderr)
        print("Set it in your .env file or environment.", file=sys.stderr)
        sys.exit(1)

    if private_key:
        # Full mode: private key + auto SIWE auth + API key + on-chain writes
        kwargs = {"private_key": private_key}
        if rpc_url != "https://bsc-dataseed.binance.org/":
            kwargs["rpc_url"] = rpc_url
        if register_agent:
            kwargs["agent"] = True
        client = BasisClient.create(**kwargs)
    elif api_key:
        # API key mode: read-only + off-chain data
        client = BasisClient(api_key=api_key)
    else:
        # Read-only mode: on-chain reads only
        client = BasisClient()

    return client


def output_result(result: dict, json_output: bool = False):
    """Print result as JSON if requested, otherwise just return for custom formatting."""
    if json_output:
        print(json.dumps(result, indent=2, default=str))


def format_tx_result(result: dict) -> dict:
    """Extract common fields from SDK transaction result."""
    return {
        "tx_hash": result.get("hash", "unknown"),
        "status": "success",
    }
