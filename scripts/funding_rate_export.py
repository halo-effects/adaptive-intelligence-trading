#!/usr/bin/env python3
"""
Funding-Rate Signal Data Pull — Spec v1.0
Pure mechanical export: funding rates, candles, state files, manifest.
No analysis, no filtering, no smoothing, no interpolation.
"""

import csv
import io
import json
import os
import shutil
import sqlite3
import sys
import time
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

WORKSPACE = Path(__file__).resolve().parent.parent
DB_PATH = WORKSPACE / "trading" / "spot" / "data" / "candles.db"
OUTPUT_DIR = WORKSPACE / "exports" / "funding-rate-signal-export"
EXPORT_TS = datetime.now(timezone.utc)

# 45-coin scanner universe (from v14_cycle_scanner.py COINS)
COINS = [
    'BTC', 'ETH', 'SOL', 'XRP', 'LINK', 'DOGE', 'ADA', 'LTC', 'AVAX', 'DOT',
    'UNI', 'ATOM', 'NEAR', 'HBAR', 'INJ', 'FIL', 'RUNE', 'CRV', 'SNX', 'COMP',
    'ENS', 'DYDX', 'LDO', 'ARB', 'OP', 'STX', 'SEI', 'RENDER', 'SUI', 'FET',
    'TAO', 'GRAM', 'JUP', 'KAS', 'PENDLE', 'PYTH', 'TIA', 'ONDO', 'ENA',
    'EIGEN', 'W', 'ZRO', 'HYPE', 'ASTER', 'AAVE',
]

# 18 months back target
LOOKBACK_MS = int((EXPORT_TS - timedelta(days=548)).timestamp() * 1000)


def ms_to_iso(ms: int) -> str:
    """Convert milliseconds epoch to ISO-8601 UTC string."""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def detect_gaps(timestamps_ms: list[int], expected_interval_ms: int, threshold_mult: float = 2.0) -> list[dict]:
    """Detect gaps > threshold_mult × expected_interval."""
    gaps = []
    threshold = expected_interval_ms * threshold_mult
    for i in range(1, len(timestamps_ms)):
        delta = timestamps_ms[i] - timestamps_ms[i - 1]
        if delta > threshold:
            gaps.append({
                "from": ms_to_iso(timestamps_ms[i - 1]),
                "to": ms_to_iso(timestamps_ms[i]),
                "gap_hours": round(delta / 3_600_000, 1),
            })
    return gaps


# ─── D-1: Funding Rate History ─────────────────────────────────────────────

def fetch_funding_rates(coin: str) -> tuple[list[dict], str | None]:
    """Fetch funding rate history from Binance USDT-M futures.
    Returns (rows, error_or_none). Paginated, 1000/page, 8h intervals.
    """
    import requests

    # Binance futures symbol
    bn_symbol = coin + "USDT"
    endpoint = "https://fapi.binance.com/fapi/v1/fundingRate"
    
    all_rows = []
    start_time = LOOKBACK_MS
    
    try:
        while True:
            params = {
                "symbol": bn_symbol,
                "startTime": start_time,
                "limit": 1000,
            }
            
            retries = 0
            while retries < 3:
                try:
                    resp = requests.get(endpoint, params=params, timeout=15)
                    if resp.status_code == 429:
                        wait = int(resp.headers.get("Retry-After", 5))
                        print(f"    Rate limited, waiting {wait}s...")
                        time.sleep(wait)
                        retries += 1
                        continue
                    resp.raise_for_status()
                    break
                except requests.exceptions.RequestException as e:
                    retries += 1
                    if retries >= 3:
                        return all_rows, f"Request failed after 3 retries: {e}"
                    time.sleep(2 * retries)
            
            data = resp.json()
            if not data:
                break
            
            for item in data:
                all_rows.append({
                    "funding_time_utc": ms_to_iso(int(item["fundingTime"])),
                    "funding_time_ms": int(item["fundingTime"]),
                    "funding_rate": item["fundingRate"],
                })
            
            # Paginate forward
            last_ts = int(data[-1]["fundingTime"])
            if last_ts <= start_time:
                break
            start_time = last_ts + 1
            
            if len(data) < 1000:
                break
            
            time.sleep(0.3)  # Rate limit courtesy
        
        return all_rows, None
    
    except Exception as e:
        return all_rows, str(e)


def write_funding_csv(coin: str, rows: list[dict], output_dir: Path):
    """Write funding-{SYMBOL}.csv."""
    path = output_dir / f"funding-{coin}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["funding_time_utc", "funding_rate"])
        for row in rows:
            writer.writerow([row["funding_time_utc"], row["funding_rate"]])


# ─── D-2: Candle Export ────────────────────────────────────────────────────

def resolve_db_symbol(conn: sqlite3.Connection, coin: str) -> tuple[str | None, str | None]:
    """Find the best DB symbol for a coin (try USDT then USDC)."""
    for quote in ["USDT", "USDC"]:
        sym = f"{coin}/{quote}"
        row = conn.execute(
            "SELECT COUNT(*) FROM candles WHERE symbol = ? AND timeframe = '1h'", (sym,)
        ).fetchone()
        if row[0] > 0:
            return sym, None
    return None, f"No candle data found for {coin}"


def export_1h_candles(conn: sqlite3.Connection, db_symbol: str, coin: str, output_dir: Path) -> dict:
    """Export 1h candles to CSV. Returns stats dict."""
    rows = conn.execute(
        "SELECT timestamp, open, high, low, close, volume "
        "FROM candles WHERE symbol = ? AND timeframe = '1h' "
        "ORDER BY timestamp ASC", (db_symbol,)
    ).fetchall()
    
    path = output_dir / f"candles1h-{coin}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["open_time_utc", "open", "high", "low", "close", "volume"])
        for ts, o, h, l, c, v in rows:
            writer.writerow([ms_to_iso(ts), o, h, l, c, v])
    
    timestamps = [r[0] for r in rows]
    return {
        "rows": len(rows),
        "first": ms_to_iso(timestamps[0]) if timestamps else None,
        "last": ms_to_iso(timestamps[-1]) if timestamps else None,
        "gaps": detect_gaps(timestamps, 3_600_000),  # 1h = 3.6M ms, gap > 2h
    }


def export_daily_candles(conn: sqlite3.Connection, db_symbol: str, coin: str, output_dir: Path) -> dict:
    """Export daily candles with indicators to CSV."""
    # Get all columns from candles_daily
    cursor = conn.execute("PRAGMA table_info(candles_daily)")
    all_cols = [r[1] for r in cursor.fetchall()]
    
    # Columns to export: OHLCV + indicators
    export_cols = ["date", "timestamp", "open", "high", "low", "close", "volume"]
    indicator_cols = [c for c in all_cols if c in (
        "sma20", "sma50", "sma200", "bb_width", "bb_pct",
        "atr14", "atr_pct", "adx", "plus_di", "minus_di", "rsi14",
        "consec_hh_hl", "consec_lh_ll", "sma50_slope", "sma200_slope",
        "price_vs_sma50", "price_vs_sma200", "candle_count"
    )]
    select_cols = export_cols + indicator_cols
    
    rows = conn.execute(
        f"SELECT {', '.join(select_cols)} FROM candles_daily "
        f"WHERE symbol = ? ORDER BY timestamp ASC", (db_symbol,)
    ).fetchall()
    
    path = output_dir / f"candlesD-{coin}.csv"
    header = ["open_time_utc"] + [c for c in select_cols if c not in ("date", "timestamp")]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in rows:
            row_dict = dict(zip(select_cols, row))
            ts = row_dict["timestamp"]
            out = [ms_to_iso(ts)] + [row_dict[c] for c in select_cols if c not in ("date", "timestamp")]
            writer.writerow(out)
    
    timestamps = [dict(zip(select_cols, r))["timestamp"] for r in rows]
    return {
        "rows": len(rows),
        "first": ms_to_iso(timestamps[0]) if timestamps else None,
        "last": ms_to_iso(timestamps[-1]) if timestamps else None,
        "gaps": detect_gaps(timestamps, 86_400_000),  # 1d = 86.4M ms, gap > 2d
    }


# ─── D-3: State Files ──────────────────────────────────────────────────────

def copy_state_files(output_dir: Path):
    """Copy trades.csv and cycle_scanner.json."""
    state_dir = output_dir / "state"
    state_dir.mkdir(exist_ok=True)
    
    # trades.csv from live PM bot
    trades_src = WORKSPACE / "trading" / "spot" / "live" / "v14pm" / "trades.csv"
    if trades_src.exists():
        shutil.copy2(trades_src, state_dir / "trades.csv")
        print(f"  Copied trades.csv ({trades_src.stat().st_size:,} bytes)")
    else:
        print(f"  WARNING: trades.csv not found at {trades_src}")
    
    # cycle_scanner.json
    scanner_src = WORKSPACE / "docs" / "data" / "v14" / "cycle_scanner.json"
    if scanner_src.exists():
        shutil.copy2(scanner_src, state_dir / "cycle_scanner.json")
        print(f"  Copied cycle_scanner.json ({scanner_src.stat().st_size:,} bytes)")
    else:
        print(f"  WARNING: cycle_scanner.json not found at {scanner_src}")


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    print(f"Funding-Rate Signal Data Pull — {EXPORT_TS.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Coins: {len(COINS)} | Lookback: 18 months | Output: {OUTPUT_DIR}")
    print()
    
    # Setup output directories
    funding_dir = OUTPUT_DIR / "funding"
    candles_dir = OUTPUT_DIR / "candles"
    funding_dir.mkdir(parents=True, exist_ok=True)
    candles_dir.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(DB_PATH))
    manifest = {
        "export_timestamp": EXPORT_TS.isoformat(),
        "spec_version": "1.0",
        "coins_requested": len(COINS),
        "lookback_target": "18 months",
        "lookback_start": ms_to_iso(LOOKBACK_MS),
        "coins": {},
    }
    
    # ── D-1: Funding Rates ──
    print("=" * 60)
    print("D-1: Funding Rate History (Binance USDT-M Futures)")
    print("=" * 60)
    
    for i, coin in enumerate(COINS, 1):
        print(f"  [{i:02d}/{len(COINS)}] {coin}...", end=" ", flush=True)
        
        rows, error = fetch_funding_rates(coin)
        
        coin_manifest = {
            "funding": {
                "source": "binance",
                "endpoint": "/fapi/v1/fundingRate",
                "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol_used": coin + "USDT",
                "rows": len(rows),
                "first": rows[0]["funding_time_utc"] if rows else None,
                "last": rows[-1]["funding_time_utc"] if rows else None,
                "error": error,
            }
        }
        
        if rows:
            write_funding_csv(coin, rows, funding_dir)
            # Gap detection (8h intervals, gap > 16h)
            timestamps = [r["funding_time_ms"] for r in rows]
            coin_manifest["funding"]["gaps"] = detect_gaps(timestamps, 28_800_000)  # 8h
            print(f"{len(rows)} rates ({rows[0]['funding_time_utc'][:10]} to {rows[-1]['funding_time_utc'][:10]})")
        else:
            print(f"NO DATA" + (f" — {error}" if error else ""))
        
        manifest["coins"][coin] = coin_manifest
        time.sleep(0.3)
    
    # ── D-2: Candle Export ──
    print()
    print("=" * 60)
    print("D-2: Candle Export (from candles.db)")
    print("=" * 60)
    
    for i, coin in enumerate(COINS, 1):
        print(f"  [{i:02d}/{len(COINS)}] {coin}...", end=" ", flush=True)
        
        db_symbol, err = resolve_db_symbol(conn, coin)
        if err:
            print(f"SKIP — {err}")
            manifest["coins"][coin]["candles_1h"] = {"error": err, "rows": 0}
            manifest["coins"][coin]["candles_daily"] = {"error": err, "rows": 0}
            continue
        
        # 1h candles
        stats_1h = export_1h_candles(conn, db_symbol, coin, candles_dir)
        manifest["coins"][coin]["candles_1h"] = {
            "db_symbol": db_symbol,
            **stats_1h,
        }
        
        # Daily candles
        stats_d = export_daily_candles(conn, db_symbol, coin, candles_dir)
        manifest["coins"][coin]["candles_daily"] = {
            "db_symbol": db_symbol,
            **stats_d,
        }
        
        print(f"1h:{stats_1h['rows']:,}  daily:{stats_d['rows']:,}  ({db_symbol})")
    
    conn.close()
    
    # ── D-3: State Files ──
    print()
    print("=" * 60)
    print("D-3: State Files")
    print("=" * 60)
    copy_state_files(OUTPUT_DIR)
    
    # ── D-4: Manifest ──
    print()
    print("=" * 60)
    print("D-4: Manifest")
    print("=" * 60)
    
    # Summary stats
    total_funding = sum(m.get("funding", {}).get("rows", 0) for m in manifest["coins"].values())
    total_1h = sum(m.get("candles_1h", {}).get("rows", 0) for m in manifest["coins"].values())
    total_daily = sum(m.get("candles_daily", {}).get("rows", 0) for m in manifest["coins"].values())
    coins_with_errors = [c for c, m in manifest["coins"].items() 
                         if m.get("funding", {}).get("error") or 
                            m.get("candles_1h", {}).get("error")]
    
    manifest["summary"] = {
        "total_funding_rows": total_funding,
        "total_candle_1h_rows": total_1h,
        "total_candle_daily_rows": total_daily,
        "coins_with_errors": coins_with_errors,
        "coins_exported": len(COINS),
    }
    
    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"  Written: {manifest_path}")
    print(f"  Funding: {total_funding:,} total rows")
    print(f"  1h candles: {total_1h:,} total rows")
    print(f"  Daily candles: {total_daily:,} total rows")
    if coins_with_errors:
        print(f"  Errors: {coins_with_errors}")
    
    # ── Zip ──
    print()
    print("=" * 60)
    print("Creating ZIP archive")
    print("=" * 60)
    
    zip_path = OUTPUT_DIR.parent / f"funding-rate-signal-export-{EXPORT_TS.strftime('%Y%m%d')}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(OUTPUT_DIR):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(OUTPUT_DIR)
                zf.write(file_path, arcname)
    
    zip_size_mb = zip_path.stat().st_size / 1_048_576
    print(f"  ZIP: {zip_path}")
    print(f"  Size: {zip_size_mb:.1f} MB")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
