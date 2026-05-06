#!/usr/bin/env python3
"""
Standalone trade reconciliation tool for V14PM live bot.

Connects to Aster DEX perps, fetches all fill history per symbol,
reconstructs closed deals, and compares against trades.csv.

Usage:
    python -m trading.spot.reconcile_trades            # dry-run (default)
    python -m trading.spot.reconcile_trades --dry-run  # explicit dry-run
    python -m trading.spot.reconcile_trades --fix      # rewrite CSV from exchange truth
    python -m trading.spot.reconcile_trades --since-days 90  # look back N days

Output reports:
    MISSING:   deals found on exchange but absent from trades.csv
    PHANTOM:   deals in trades.csv but no corresponding exchange fills
    MISMATCH:  deals in both but PnL or layer count differ by more than threshold
    DUPLICATE: deal_ids that appear more than once in trades.csv
"""

import argparse
import csv
import json
import logging
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import ccxt

# ── Paths ─────────────────────────────────────────────────────────────────────

_WORKSPACE = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR  = _WORKSPACE / "trading" / "spot" / "live" / "v14pm"
CSV_PATH    = OUTPUT_DIR / "trades.csv"
STATUS_PATH = OUTPUT_DIR / "status.json"

# ── Constants ─────────────────────────────────────────────────────────────────

# Aster DEX went live (and bot was launched) around 2026-03-19.
# We fetch fills starting from this date.
BOT_LAUNCH_DT    = datetime(2026, 3, 19, 0, 0, 0, tzinfo=timezone.utc)
BOT_LAUNCH_TS_MS = int(BOT_LAUNCH_DT.timestamp() * 1000)

# Coins where Aster reports prices/quantities in 1000-unit scale
THOUSAND_PREFIX_COINS = {"PEPE", "BONK", "FLOKI"}

# Symbols that are in the CSV but NOT tradeable as Aster perps (pre-bot or native token)
SKIP_EXCHANGE_FETCH = {"ASTER/USDT"}

# How close two trade close_times must be to count as the same deal (seconds)
MATCH_WINDOW_SECS = 300  # 5 minutes

# PnL tolerance for "mismatch" detection (USDT)
PNL_MISMATCH_THRESHOLD = 0.50

CSV_FIELDNAMES = [
    "deal_id", "symbol", "open_time", "close_time", "layers",
    "invested", "proceeds", "fee", "pnl", "return_pct",
    "duration_h", "fill_price", "recorded_at",
]

# Rate limit between API calls (seconds)
API_RATE_LIMIT = 0.5

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("reconcile")


# ── Exchange helpers ──────────────────────────────────────────────────────────

def create_exchange() -> "ccxt.aster":
    """Create authenticated Aster CCXT exchange object."""
    api_key    = os.environ.get("ASTER_API_KEY", "")
    api_secret = os.environ.get("ASTER_API_SECRET", "")
    if not (api_key and api_secret):
        print("ERROR: ASTER_API_KEY and ASTER_API_SECRET must be set", file=sys.stderr)
        sys.exit(1)
    ex = ccxt.aster({
        "apiKey":          api_key,
        "secret":          api_secret,
        "enableRateLimit": True,
        "options":         {"defaultType": "future"},
        "timeout":         15000,
    })
    ex.load_markets()
    return ex


def db_to_aster_symbol(db_symbol: str) -> str:
    """Convert DB symbol (PEPE/USDT) to Aster perp symbol (1000PEPE/USDT:USDT)."""
    base = db_symbol.split("/")[0]
    if base in THOUSAND_PREFIX_COINS:
        return f"1000{base}/USDT:USDT"
    return f"{base}/USDT:USDT"


def fetch_all_fills(exchange, aster_sym: str, since_ms: int) -> list:
    """
    Fetch ALL fills for a symbol, using a hybrid strategy.

    Aster's API behaves differently with vs without `since`:
      - with since: returns fills forward from that timestamp (but may return 0
        if the timestamp is very old and data was pruned for some symbols)
      - without since: returns the most recent fills

    Strategy:
      Phase 1: Forward-paginate from since_ms to get historical fills.
      Phase 2: Fetch most recent fills without `since` to capture anything missed.
      Deduplicate by fill ID.
    """
    seen_ids: set = set()
    all_fills: list = []

    # Phase 1: forward-paginate from since_ms
    since = since_ms
    max_pages = 50
    for page in range(max_pages):
        try:
            batch = exchange.fetch_my_trades(aster_sym, since=since, limit=1000)
        except Exception as e:
            logger.warning(f"  fetch_my_trades({aster_sym}, since={since}) failed: {e}")
            break
        if not batch:
            break
        for f in batch:
            fid = f.get("id")
            if fid not in seen_ids:
                seen_ids.add(fid)
                all_fills.append(f)
        if len(batch) < 1000:
            break
        since = batch[-1]["timestamp"] + 1
        time.sleep(API_RATE_LIMIT)

    time.sleep(API_RATE_LIMIT)

    # Phase 2: most recent fills (no since param) — catches fills the
    # forward-pagination missed due to Aster's data retention quirks.
    try:
        batch = exchange.fetch_my_trades(aster_sym, limit=1000)
        for f in (batch or []):
            fid = f.get("id")
            if fid not in seen_ids:
                seen_ids.add(fid)
                all_fills.append(f)
    except Exception as e:
        logger.warning(f"  fetch_my_trades({aster_sym}, no-since) failed: {e}")

    # Sort by timestamp ascending
    all_fills.sort(key=lambda f: f.get("timestamp", 0))
    return all_fills


# ── Deal reconstruction ───────────────────────────────────────────────────────

def reconstruct_deals(db_symbol: str, fills: list) -> Tuple[List[dict], Optional[dict]]:
    """
    Reconstruct closed deals and the current open position from exchange fills.

    Pattern: consecutive buys accumulate into a deal; a sell closes it.
    Any remaining buys at the end = open position (not a closed deal).

    Returns:
        closed_deals: list of deal dicts with all CSV fields
        open_deal:    current open position dict, or None
    """
    base    = db_symbol.split("/")[0]
    is_1000 = base in THOUSAND_PREFIX_COINS

    # Sort by timestamp ascending
    fills = sorted(fills, key=lambda f: f.get("timestamp", 0))

    closed_deals: List[dict] = []
    open_deal: Optional[dict] = None
    now_iso = datetime.now(timezone.utc).isoformat()

    for fill in fills:
        side   = (fill.get("side") or "").lower()
        ts_ms  = fill.get("timestamp") or 0

        raw_price  = float(fill.get("price")  or 0)
        raw_amount = float(fill.get("amount") or 0)

        # Price: divide by 1000 for 1000-prefix coins to get per-underlying price
        price = raw_price / 1000.0 if is_1000 else raw_price

        # Cost (USDT): use exchange-computed value directly — it is already in USDT
        # for both normal and 1000-prefix coins.
        cost_usdt = float(fill.get("cost") or 0)
        if not cost_usdt and raw_price and raw_amount:
            # Fallback: compute from raw price × amount (still USDT)
            cost_usdt = raw_price * raw_amount

        # Fee
        fee_info  = fill.get("fee") or {}
        fee_usdt  = float(fee_info.get("cost") or 0) if isinstance(fee_info, dict) else 0.0

        dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)

        if side == "buy":
            if open_deal is None:
                open_deal = {
                    "open_time":    dt.isoformat(),
                    "open_ts_ms":   ts_ms,
                    "layers":       0,
                    "invested":     0.0,
                    "total_fee":    0.0,
                }
            open_deal["layers"]   += 1
            open_deal["invested"] += cost_usdt
            open_deal["total_fee"] += fee_usdt

        elif side == "sell":
            if open_deal is None:
                # Sell with no prior buy — skip (shouldn't happen in normal flow)
                logger.warning(f"  Sell fill with no open deal for {db_symbol} at {dt.isoformat()}")
                continue

            proceeds   = cost_usdt
            total_fee  = open_deal["total_fee"] + fee_usdt
            pnl        = proceeds - open_deal["invested"] - total_fee
            ret_pct    = (pnl / open_deal["invested"] * 100) if open_deal["invested"] > 0 else 0.0

            open_ts      = datetime.fromisoformat(open_deal["open_time"])
            duration_h   = (dt - open_ts).total_seconds() / 3600.0

            closed_deals.append({
                "symbol":       db_symbol,
                "open_time":    open_deal["open_time"],
                "close_time":   dt.isoformat(),
                "close_ts_ms":  ts_ms,       # internal — used for matching, not in CSV
                "layers":       open_deal["layers"],
                "invested":     round(open_deal["invested"], 4),
                "proceeds":     round(proceeds, 4),
                "fee":          round(total_fee, 4),
                "pnl":          round(pnl, 4),
                "return_pct":   round(ret_pct, 2),
                "duration_h":   round(duration_h, 1),
                "fill_price":   round(price, 8),
                "recorded_at":  now_iso,
            })
            open_deal = None

    return closed_deals, open_deal


# ── CSV helpers ───────────────────────────────────────────────────────────────

def load_csv(csv_path: Path) -> List[dict]:
    """Load trades.csv, returning list of row dicts."""
    if not csv_path.exists():
        logger.warning(f"trades.csv not found at {csv_path}")
        return []
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_status_json(status_path: Path) -> dict:
    """Load status.json."""
    if not status_path.exists():
        return {}
    try:
        with open(status_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load status.json: {e}")
        return {}


def get_all_symbols(csv_rows: List[dict], status: dict) -> List[str]:
    """
    Build the full set of symbols to check on the exchange.
    Sources: CSV rows + status.json approved_symbols + status.json coins.
    Excludes ASTER/USDT (pre-bot, not a Aster perp we can query).
    """
    syms = set()

    for row in csv_rows:
        s = row.get("symbol", "").strip()
        if s:
            syms.add(s)

    for s in status.get("approved_symbols", []):
        syms.add(s)

    for s in status.get("coins", {}).keys():
        syms.add(s)

    # Remove symbols we can't/shouldn't query
    syms -= SKIP_EXCHANGE_FETCH

    return sorted(syms)


# ── Matching ──────────────────────────────────────────────────────────────────

def _parse_dt(s: str) -> Optional[datetime]:
    """Parse an ISO datetime string to a timezone-aware datetime."""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def find_matching_csv_row(ex_deal: dict, csv_rows: List[dict]) -> Optional[dict]:
    """
    Find a CSV row matching an exchange deal by symbol + close_time proximity.
    Returns the closest match within MATCH_WINDOW_SECS, or None.
    """
    close_ts_ms = ex_deal.get("close_ts_ms", 0)
    close_dt    = datetime.fromtimestamp(close_ts_ms / 1000.0, tz=timezone.utc)

    best      = None
    best_diff = float("inf")

    for row in csv_rows:
        csv_close_dt = _parse_dt(row.get("close_time", ""))
        if csv_close_dt is None:
            continue
        diff = abs((csv_close_dt - close_dt).total_seconds())
        if diff < MATCH_WINDOW_SECS and diff < best_diff:
            best_diff = diff
            best      = row

    return best


# ── Comparison ────────────────────────────────────────────────────────────────

def compare(
    ex_deals_by_sym: Dict[str, List[dict]],
    csv_rows_by_sym: Dict[str, List[dict]],
    all_symbols:     List[str],
    csv_rows_all:    List[dict],
) -> dict:
    """
    Compare exchange-reconstructed deals against CSV rows.

    Returns dict with keys: missing, phantom, mismatched, duplicates, open_positions.
    """
    missing:        List[dict] = []
    phantom:        List[dict] = []
    unverifiable:   List[dict] = []  # CSV rows where exchange returned 0 fills (API retention expired)
    mismatched:     List[dict] = []
    open_positions: List[dict] = []

    # Track which symbols had exchange data available
    syms_with_exchange_data = set(ex_deals_by_sym.keys())

    for sym in all_symbols:
        ex_deals  = ex_deals_by_sym.get(sym, [])
        csv_rows  = csv_rows_by_sym.get(sym, [])

        matched_csv_ids: set = set()

        for ex_deal in ex_deals:
            match = find_matching_csv_row(ex_deal, csv_rows)
            if match:
                matched_csv_ids.add(id(match))
                # Check for meaningful discrepancies
                try:
                    csv_pnl = float(match.get("pnl") or 0)
                except (ValueError, TypeError):
                    csv_pnl = 0.0
                ex_pnl = ex_deal["pnl"]
                pnl_diff = abs(ex_pnl - csv_pnl)

                try:
                    csv_layers = int(match.get("layers") or 0)
                except (ValueError, TypeError):
                    csv_layers = 0

                if pnl_diff > PNL_MISMATCH_THRESHOLD or csv_layers != ex_deal["layers"]:
                    mismatched.append({
                        "symbol":      sym,
                        "csv_deal_id": match.get("deal_id"),
                        "close_time":  ex_deal["close_time"],
                        "ex_pnl":      ex_pnl,
                        "csv_pnl":     csv_pnl,
                        "pnl_diff":    pnl_diff,
                        "ex_layers":   ex_deal["layers"],
                        "csv_layers":  csv_layers,
                    })
            else:
                missing.append(ex_deal)

        # CSV rows with no exchange match
        for row in csv_rows:
            if id(row) in matched_csv_ids:
                continue
            close_dt = _parse_dt(row.get("close_time", ""))
            if close_dt and close_dt < BOT_LAUNCH_DT:
                continue  # Pre-launch — can't verify, expected

            # If exchange returned 0 fills for this symbol, it's unverifiable
            # (API retention expired), not a phantom trade
            if sym not in syms_with_exchange_data:
                unverifiable.append(row)
            else:
                phantom.append(row)

    # Duplicate deal_ids in CSV
    deal_id_counts = Counter()
    for row in csv_rows_all:
        try:
            did = int(row.get("deal_id") or 0)
            deal_id_counts[did] += 1
        except (ValueError, TypeError):
            pass
    duplicates = {did: cnt for did, cnt in deal_id_counts.items() if cnt > 1}

    return {
        "missing":      missing,
        "phantom":      phantom,
        "unverifiable": unverifiable,
        "mismatched":   mismatched,
        "duplicates":   duplicates,
    }


# ── Reporting ─────────────────────────────────────────────────────────────────

def print_report(result: dict, csv_rows_all: List[dict]):
    print("\n" + "=" * 70)
    print("  V14PM TRADE RECONCILIATION REPORT")
    print("=" * 70)

    # Duplicate deal_ids
    duplicates = result["duplicates"]
    print(f"\n[DUPLICATE DEAL IDs] — {len(duplicates)} IDs appear multiple times:")
    if duplicates:
        for did, cnt in sorted(duplicates.items()):
            rows = [r for r in csv_rows_all if str(r.get("deal_id")) == str(did)]
            syms = ", ".join(r.get("symbol", "?") for r in rows)
            print(f"  deal_id={did} appears {cnt}× ({syms})")
    else:
        print("  None ✓")

    # Missing deals
    missing = result["missing"]
    print(f"\n[MISSING DEALS] — {len(missing)} on exchange but absent from CSV:")
    if missing:
        for d in sorted(missing, key=lambda x: x.get("close_time", "")):
            print(
                f"  {d['symbol']:15s} | "
                f"close={d['close_time'][:19]} | "
                f"layers={d['layers']} | "
                f"invested=${d['invested']:.2f} | "
                f"proceeds=${d['proceeds']:.2f} | "
                f"pnl=${d['pnl']:+.4f} ({d['return_pct']:+.2f}%)"
            )
    else:
        print("  None ✓")

    # Unverifiable deals (exchange API retention expired)
    unverifiable = result["unverifiable"]
    print(f"\n[UNVERIFIABLE] — {len(unverifiable)} in CSV, exchange API returned 0 fills (retention expired):")
    if unverifiable:
        syms_uv = Counter(r.get("symbol", "?") for r in unverifiable)
        for sym, cnt in sorted(syms_uv.items()):
            print(f"  {sym}: {cnt} trade(s) — kept as-is (cannot verify)")
    else:
        print("  None ✓")

    # Phantom deals
    phantom = result["phantom"]
    print(f"\n[PHANTOM DEALS] — {len(phantom)} in CSV but no matching exchange fill:")
    if phantom:
        for row in sorted(phantom, key=lambda r: r.get("close_time", "")):
            print(
                f"  deal_id={row.get('deal_id'):>4} | {row.get('symbol','?'):15s} | "
                f"close={str(row.get('close_time',''))[:19]} | "
                f"pnl=${row.get('pnl','?')}"
            )
    else:
        print("  None ✓")

    # Mismatched deals
    mismatched = result["mismatched"]
    print(f"\n[MISMATCHED DEALS] — {len(mismatched)} with PnL or layer discrepancies:")
    if mismatched:
        for m in sorted(mismatched, key=lambda x: x.get("close_time", "")):
            print(
                f"  deal_id={m['csv_deal_id']:>4} | {m['symbol']:15s} | "
                f"close={str(m['close_time'])[:19]}\n"
                f"    Exchange: pnl=${m['ex_pnl']:+.4f}, layers={m['ex_layers']}\n"
                f"    CSV:      pnl=${m['csv_pnl']:+.4f}, layers={m['csv_layers']}\n"
                f"    PnL diff: ${m['pnl_diff']:+.4f}"
            )
    else:
        print("  None ✓")

    # Summary
    total_issues = len(missing) + len(phantom) + len(mismatched) + len(duplicates)
    print("\n" + "-" * 70)
    print(f"  SUMMARY: {len(missing)} missing | {len(phantom)} phantom | "
          f"{len(mismatched)} mismatched | {len(duplicates)} duplicate IDs | "
          f"{len(unverifiable)} unverifiable")
    if total_issues == 0 and not unverifiable:
        print("  ✅ CSV matches exchange — no action needed.")
    elif total_issues == 0 and unverifiable:
        print(f"  ✅ All verifiable trades match. {len(unverifiable)} trades beyond API retention.")
    else:
        print(f"  ⚠️  {total_issues} issue(s) found. Run with --fix to repair.")
        print(f"  Note: --fix preserves unverifiable trades and reassigns monotonic deal IDs.")
    print("=" * 70 + "\n")


# ── Fix (rewrite CSV) ─────────────────────────────────────────────────────────

def backup_csv(csv_path: Path) -> Path:
    """Create a timestamped backup of trades.csv."""
    ts      = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bak     = csv_path.with_suffix(f".csv.bak.{ts}")
    import shutil
    shutil.copy2(csv_path, bak)
    logger.info(f"Backup created: {bak}")
    return bak


def write_fixed_csv(
    csv_path:          Path,
    ex_deals_by_sym:   Dict[str, List[dict]],
    csv_rows_all:      List[dict],
    result:            dict,
):
    """
    Rewrite trades.csv with corrections applied.

    Strategy (conservative — preserves data):
      1. For symbols WITH exchange data: use exchange-reconstructed deals
         (replaces any mismatched CSV rows for those symbols).
      2. For symbols WITHOUT exchange data (API retention expired):
         keep existing CSV rows as-is (unverifiable but presumed correct).
      3. Add any MISSING deals (on exchange but not in CSV).
      4. Sort all by close_time ascending.
      5. Assign sequential deal_ids (1, 2, 3, ...) — fixes all duplicates.
    """
    syms_with_exchange_data = set(ex_deals_by_sym.keys())

    def sort_key(d):
        dt = _parse_dt(d.get("close_time", ""))
        return dt or datetime.min.replace(tzinfo=timezone.utc)

    combined = []

    # Find the earliest exchange fill per symbol (anything before this is beyond retention)
    earliest_exchange_ts: Dict[str, datetime] = {}
    for sym, deals in ex_deals_by_sym.items():
        for deal in deals:
            dt = _parse_dt(deal.get("open_time", ""))
            if dt and (sym not in earliest_exchange_ts or dt < earliest_exchange_ts[sym]):
                earliest_exchange_ts[sym] = dt

    # 1. For symbols with exchange data: use exchange-reconstructed deals
    for sym, deals in ex_deals_by_sym.items():
        for deal in deals:
            combined.append({k: deal.get(k, "") for k in CSV_FIELDNAMES})

    # 2. For symbols without exchange data: keep ALL CSV rows
    #    For symbols WITH exchange data: keep CSV rows that closed BEFORE
    #    the earliest exchange fill (beyond API retention, presumed legitimate)
    for row in csv_rows_all:
        sym = row.get("symbol", "")
        if sym not in syms_with_exchange_data:
            # No exchange data at all — keep as-is
            combined.append({k: row.get(k, "") for k in CSV_FIELDNAMES})
        else:
            # Has exchange data — only keep CSV rows older than earliest exchange fill
            close_dt = _parse_dt(row.get("close_time", ""))
            earliest = earliest_exchange_ts.get(sym)
            if close_dt and earliest and close_dt < earliest:
                combined.append({k: row.get(k, "") for k in CSV_FIELDNAMES})

    # 3. Sort by close_time
    combined.sort(key=sort_key)

    # 4. Assign sequential deal_ids
    for idx, row in enumerate(combined, start=1):
        row["deal_id"] = idx

    # 5. Deduplicate by (symbol, close_time) — keep last occurrence
    seen = set()
    deduped = []
    for row in reversed(combined):
        key = (row.get("symbol", ""), str(row.get("close_time", ""))[:19])
        if key not in seen:
            seen.add(key)
            deduped.append(row)
    deduped.reverse()
    # Re-assign IDs after dedup
    for idx, row in enumerate(deduped, start=1):
        row["deal_id"] = idx

    # Atomic write
    tmp = csv_path.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(deduped)
    tmp.replace(csv_path)

    logger.info(f"Wrote {len(deduped)} deals to {csv_path} (was {len(csv_rows_all)})")
    return len(deduped)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Reconcile V14PM trades.csv against Aster DEX exchange fills."
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Rewrite trades.csv from exchange truth (replaces verifiable symbols). Creates .bak backup.",
    )
    parser.add_argument(
        "--fix-ids",
        action="store_true",
        help="Sort by close_time and reassign monotonic deal IDs without removing any trades. Creates .bak backup.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Report only, do not modify trades.csv (default).",
    )
    parser.add_argument(
        "--since-days",
        type=int,
        default=None,
        help="How many days of fill history to fetch (default: all since bot launch 2026-03-19).",
    )
    args = parser.parse_args()

    if args.fix or args.fix_ids:
        args.dry_run = False

    since_ms = BOT_LAUNCH_TS_MS
    if args.since_days:
        since_ms = int(
            (datetime.now(timezone.utc) - timedelta(days=args.since_days)).timestamp() * 1000
        )

    mode = "DRY RUN" if args.dry_run else "FIX MODE"
    logger.info(f"=== V14PM Trade Reconciliation — {mode} ===")
    since_dt = datetime.fromtimestamp(since_ms / 1000, tz=timezone.utc)
    logger.info(f"Fetching fills since {since_dt.strftime('%Y-%m-%d %H:%M UTC')}")

    # ── Load local data ───────────────────────────────────────────────────────

    csv_rows_all = load_csv(CSV_PATH)
    logger.info(f"Loaded {len(csv_rows_all)} rows from trades.csv")

    status = load_status_json(STATUS_PATH)
    all_symbols = get_all_symbols(csv_rows_all, status)
    logger.info(f"Symbols to reconcile: {all_symbols}")

    # Group CSV rows by symbol
    csv_rows_by_sym: Dict[str, List[dict]] = {}
    for row in csv_rows_all:
        sym = row.get("symbol", "")
        csv_rows_by_sym.setdefault(sym, []).append(row)

    # ── Connect to exchange ───────────────────────────────────────────────────

    logger.info("Connecting to Aster DEX...")
    try:
        exchange = create_exchange()
        logger.info("Connected ✓")
    except SystemExit:
        raise
    except Exception as e:
        logger.error(f"Failed to connect to exchange: {e}")
        sys.exit(1)

    # ── Fetch fills and reconstruct deals ─────────────────────────────────────

    ex_deals_by_sym: Dict[str, List[dict]] = {}
    ex_open_by_sym:  Dict[str, dict]       = {}

    for db_sym in all_symbols:
        if db_sym in SKIP_EXCHANGE_FETCH:
            logger.info(f"Skipping {db_sym} (pre-bot / not an Aster perp)")
            continue

        aster_sym = db_to_aster_symbol(db_sym)
        logger.info(f"Fetching fills for {db_sym} ({aster_sym}) ...")

        try:
            fills = fetch_all_fills(exchange, aster_sym, since_ms)
        except Exception as e:
            logger.warning(f"  Failed to fetch fills for {db_sym}: {e}")
            time.sleep(API_RATE_LIMIT)
            continue

        logger.info(f"  Got {len(fills)} fills")
        time.sleep(API_RATE_LIMIT)

        if not fills:
            continue

        closed_deals, open_deal = reconstruct_deals(db_sym, fills)
        logger.info(f"  Reconstructed {len(closed_deals)} closed deal(s)"
                    + (f" + 1 open position" if open_deal else ""))

        if closed_deals:
            ex_deals_by_sym[db_sym] = closed_deals
        if open_deal:
            ex_open_by_sym[db_sym] = open_deal

    # ── Compare ───────────────────────────────────────────────────────────────

    logger.info("Comparing exchange deals to CSV...")
    result = compare(ex_deals_by_sym, csv_rows_by_sym, all_symbols, csv_rows_all)

    # ── Report ────────────────────────────────────────────────────────────────

    print_report(result, csv_rows_all)

    # Show current open positions (informational)
    if ex_open_by_sym:
        print("[CURRENT OPEN POSITIONS (not counted as closed deals)]")
        for sym, pos in ex_open_by_sym.items():
            print(
                f"  {sym:15s} | layers={pos['layers']} | "
                f"invested=${pos['invested']:.2f} | "
                f"open_time={pos['open_time'][:19]}"
            )
        print()

    # ── Fix ───────────────────────────────────────────────────────────────────

    if args.fix_ids and not args.fix:
        # --fix-ids: sort + reassign IDs only, keep all trades
        logger.info("--fix-ids mode: sorting and reassigning deal IDs...")
        bak = backup_csv(CSV_PATH)
        print(f"Backup saved: {bak}")

        def sort_key_csv(d):
            dt = _parse_dt(d.get("close_time", ""))
            return dt or datetime.min.replace(tzinfo=timezone.utc)

        sorted_rows = sorted(csv_rows_all, key=sort_key_csv)
        for idx, row in enumerate(sorted_rows, start=1):
            row["deal_id"] = idx

        tmp = CSV_PATH.with_suffix(".tmp")
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(sorted_rows)
        tmp.replace(CSV_PATH)
        print(f"Done: {len(sorted_rows)} trades sorted, IDs reassigned 1-{len(sorted_rows)}.")

    elif args.fix and not args.dry_run and (
        result["missing"] or result["phantom"] or result["mismatched"] or result["duplicates"]
    ):
        logger.info("--fix mode: rewriting trades.csv from exchange truth...")
        bak = backup_csv(CSV_PATH)
        print(f"Backup saved: {bak}")

        n = write_fixed_csv(CSV_PATH, ex_deals_by_sym, csv_rows_all, result)
        print(f"Done: trades.csv rewritten with {n} deals (monotonic IDs assigned).")

    elif not args.dry_run:
        print("No issues found. No changes made.")

    # Exit code: 0 = clean, 1 = issues found (useful for CI/alerts)
    total_issues = (
        len(result["missing"]) + len(result["phantom"]) +
        len(result["mismatched"]) + len(result["duplicates"])
    )
    sys.exit(0 if total_issues == 0 else 1)


if __name__ == "__main__":
    main()
