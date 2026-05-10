#!/usr/bin/env python3
"""
Resample 1h candles → daily candles for all coins in candles_daily.

Ensures candles_daily stays up-to-date for coins that only have 1h data
from the Hyperliquid collector. Existing daily data is preserved (INSERT OR IGNORE).

Run after collect_scanner_candles.py in the hourly pipeline.
"""

import sqlite3
import sys
import io
import logging
import numpy as np
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("resample_daily")

DB_PATH = Path(__file__).resolve().parent / "data" / "candles.db"


def ensure_daily_table(conn: sqlite3.Connection):
    """Ensure candles_daily exists. Uses the existing schema if table is present."""
    # Check if table already exists
    exists = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='candles_daily'"
    ).fetchone()[0]
    if not exists:
        conn.execute("""
            CREATE TABLE candles_daily (
                symbol TEXT, date TEXT, timestamp INTEGER,
                open REAL, high REAL, low REAL, close REAL, volume REAL,
                candle_count INTEGER DEFAULT 0,
                PRIMARY KEY (symbol, timestamp)
            )
        """)
        conn.commit()


def resample_coin(conn: sqlite3.Connection, symbol: str) -> int:
    """Resample 1h candles to daily for one symbol. Returns new rows inserted."""
    # Get all 1h candles
    rows = conn.execute(
        "SELECT timestamp, open, high, low, close, volume "
        "FROM candles WHERE symbol = ? AND timeframe = '1h' ORDER BY timestamp",
        (symbol,)
    ).fetchall()

    if not rows:
        return 0

    # Group by day (UTC midnight boundary)
    days = {}
    for ts_ms, o, h, l, c, v in rows:
        day_ms = (ts_ms // 86_400_000) * 86_400_000
        if day_ms not in days:
            days[day_ms] = {"open": o, "high": h, "low": l, "close": c, "volume": v, "count": 1}
        else:
            d = days[day_ms]
            d["high"] = max(d["high"], h)
            d["low"] = min(d["low"], l)
            d["close"] = c
            d["volume"] += v
            d["count"] += 1

    # Insert (ignore duplicates — existing daily data from other sources is preserved)
    from datetime import datetime, timezone
    before = conn.total_changes
    for day_ms, d in sorted(days.items()):
        date_str = datetime.fromtimestamp(day_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        conn.execute(
            "INSERT OR IGNORE INTO candles_daily "
            "(symbol, date, timestamp, open, high, low, close, volume, candle_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (symbol, date_str, day_ms, d["open"], d["high"], d["low"], d["close"], d["volume"], d["count"])
        )

    return conn.total_changes - before


def compute_and_update_indicators(conn: sqlite3.Connection, symbol: str) -> int:
    """Compute technical indicators for a symbol's daily candles and update in-place.

    Reads all daily rows, computes SMA20/50/200, BB, ATR, ADX, RSI, HH/HL streaks,
    slopes, and price-vs-SMA. Updates rows that are missing indicators.
    Returns number of rows updated.
    """
    rows = conn.execute(
        "SELECT timestamp, open, high, low, close, volume FROM candles_daily "
        "WHERE symbol = ? ORDER BY timestamp",
        (symbol,)
    ).fetchall()
    if len(rows) < 50:  # Need at least 50 rows for SMA50
        return 0

    ts = [r[0] for r in rows]
    o = np.array([r[1] for r in rows], dtype=float)
    h = np.array([r[2] for r in rows], dtype=float)
    l = np.array([r[3] for r in rows], dtype=float)
    c = np.array([r[4] for r in rows], dtype=float)

    n = len(c)

    def _rolling_mean(arr, w):
        out = np.full(n, np.nan)
        for i in range(w - 1, n):
            out[i] = np.mean(arr[i - w + 1:i + 1])
        return out

    def _ewm(arr, alpha):
        out = np.full(n, np.nan)
        first_valid = None
        for i in range(n):
            if np.isnan(arr[i]):
                continue
            if first_valid is None:
                first_valid = i
                out[i] = arr[i]
            else:
                out[i] = alpha * arr[i] + (1 - alpha) * out[i - 1]
        return out

    # SMAs
    sma20 = _rolling_mean(c, 20)
    sma50 = _rolling_mean(c, 50)
    sma200 = _rolling_mean(c, 200)

    # Bollinger Bands
    bb_width = np.full(n, np.nan)
    bb_pct = np.full(n, np.nan)
    for i in range(19, n):
        window = c[i - 19:i + 1]
        std = np.std(window, ddof=1)
        mid = sma20[i]
        if mid and mid > 0:
            upper = mid + 2 * std
            lower = mid - 2 * std
            bb_width[i] = (upper - lower) / mid * 100
            denom = upper - lower
            if denom > 0:
                bb_pct[i] = (c[i] - lower) / denom * 100

    # ATR(14)
    tr = np.full(n, np.nan)
    tr[0] = h[0] - l[0]
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    atr14 = _ewm(tr, 1.0 / 14)
    atr_pct = np.where(c > 0, atr14 / c * 100, np.nan)

    # Directional Movement + ADX(14)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    for i in range(1, n):
        up = h[i] - h[i - 1]
        down = l[i - 1] - l[i]
        if up > down and up > 0:
            plus_dm[i] = up
        if down > up and down > 0:
            minus_dm[i] = down
    smooth_plus = _ewm(plus_dm, 1.0 / 14)
    smooth_minus = _ewm(minus_dm, 1.0 / 14)
    smooth_tr = _ewm(tr, 1.0 / 14)
    plus_di = np.where(smooth_tr > 0, smooth_plus / smooth_tr * 100, np.nan)
    minus_di = np.where(smooth_tr > 0, smooth_minus / smooth_tr * 100, np.nan)
    dx = np.where(
        (plus_di + minus_di) > 0,
        np.abs(plus_di - minus_di) / (plus_di + minus_di) * 100,
        np.nan
    )
    adx = _ewm(dx, 1.0 / 14)

    # RSI(14)
    delta = np.diff(c, prepend=np.nan)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = _ewm(gain, 1.0 / 14)
    avg_loss = _ewm(loss, 1.0 / 14)
    rsi14 = np.where(avg_loss > 0, 100 - (100 / (1 + avg_gain / avg_loss)), np.nan)

    # Consecutive HH/HL and LH/LL
    consec_hh_hl = np.zeros(n, dtype=int)
    consec_lh_ll = np.zeros(n, dtype=int)
    for i in range(1, n):
        if h[i] > h[i - 1] and l[i] > l[i - 1]:
            consec_hh_hl[i] = consec_hh_hl[i - 1] + 1
        if h[i] < h[i - 1] and l[i] < l[i - 1]:
            consec_lh_ll[i] = consec_lh_ll[i - 1] + 1

    # Slopes and price vs SMA
    sma50_slope = np.full(n, np.nan)
    sma200_slope = np.full(n, np.nan)
    for i in range(5, n):
        if not np.isnan(sma50[i]) and not np.isnan(sma50[i - 5]):
            sma50_slope[i] = sma50[i] - sma50[i - 5]
        if not np.isnan(sma200[i]) and not np.isnan(sma200[i - 5]):
            sma200_slope[i] = sma200[i] - sma200[i - 5]
    price_vs_sma50 = np.where(sma50 > 0, (c - sma50) / sma50 * 100, np.nan)
    price_vs_sma200 = np.where(sma200 > 0, (c - sma200) / sma200 * 100, np.nan)

    # Update rows
    updated = 0
    for i in range(n):
        vals = (
            _f(sma20[i]), _f(sma50[i]), _f(sma200[i]),
            _f(bb_width[i]), _f(bb_pct[i]),
            _f(atr14[i]), _f(atr_pct[i]),
            _f(adx[i]), _f(plus_di[i]), _f(minus_di[i]),
            _f(rsi14[i]),
            int(consec_hh_hl[i]), int(consec_lh_ll[i]),
            _f(sma50_slope[i]), _f(sma200_slope[i]),
            _f(price_vs_sma50[i]), _f(price_vs_sma200[i]),
            symbol, ts[i]
        )
        conn.execute(
            "UPDATE candles_daily SET "
            "sma20=?, sma50=?, sma200=?, bb_width=?, bb_pct=?, "
            "atr14=?, atr_pct=?, adx=?, plus_di=?, minus_di=?, rsi14=?, "
            "consec_hh_hl=?, consec_lh_ll=?, sma50_slope=?, sma200_slope=?, "
            "price_vs_sma50=?, price_vs_sma200=? "
            "WHERE symbol=? AND timestamp=?",
            vals
        )
        updated += 1
    conn.commit()
    return updated


def _f(v):
    """Convert numpy value to Python float or None."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    try:
        fv = float(v)
        return None if np.isnan(fv) else fv
    except (TypeError, ValueError):
        return None


def main():
    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    ensure_daily_table(conn)

    # Get all symbols that have 1h candles
    hourly_symbols = [r[0] for r in conn.execute(
        "SELECT DISTINCT symbol FROM candles WHERE timeframe = '1h' ORDER BY symbol"
    ).fetchall()]

    # Get symbols that already have daily candles
    daily_symbols = set(r[0] for r in conn.execute(
        "SELECT DISTINCT symbol FROM candles_daily ORDER BY symbol"
    ).fetchall())

    logger.info(f"Resampling {len(hourly_symbols)} hourly symbols → daily")
    logger.info(f"  Already have daily data: {len(daily_symbols)} symbols")

    total_new = 0
    updated = 0

    for symbol in hourly_symbols:
        # Get latest daily timestamp for this symbol
        latest_daily = conn.execute(
            "SELECT MAX(timestamp) FROM candles_daily WHERE symbol = ?",
            (symbol,)
        ).fetchone()[0]

        # Get latest hourly timestamp
        latest_hourly = conn.execute(
            "SELECT MAX(timestamp) FROM candles WHERE symbol = ? AND timeframe = '1h'",
            (symbol,)
        ).fetchone()[0]

        if latest_daily and latest_hourly:
            # Only resample if hourly data is ahead of daily by >24h
            if latest_hourly - latest_daily < 86_400_000:
                continue

        new = resample_coin(conn, symbol)
        if new > 0:
            updated += 1
            total_new += new
            status = "NEW" if symbol not in daily_symbols else "updated"
            logger.info(f"  {symbol}: +{new} daily candles ({status})")

    conn.commit()

    # Step 2: Compute/update indicators for all daily symbols
    all_daily_syms = [r[0] for r in conn.execute(
        "SELECT DISTINCT symbol FROM candles_daily ORDER BY symbol"
    ).fetchall()]
    logger.info(f"Computing indicators for {len(all_daily_syms)} daily symbols...")
    ind_updated = 0
    for symbol in all_daily_syms:
        try:
            n = compute_and_update_indicators(conn, symbol)
            if n > 0:
                ind_updated += 1
        except Exception as e:
            logger.warning(f"  {symbol}: indicator computation failed: {e}")
    logger.info(f"Indicators updated for {ind_updated} symbols.")

    conn.close()
    logger.info(f"Done. {updated} symbols resampled ({total_new} new candles), {ind_updated} indicator sets updated.")


if __name__ == "__main__":
    main()
