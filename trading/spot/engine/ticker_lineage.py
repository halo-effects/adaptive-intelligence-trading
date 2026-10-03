"""
Ticker lineage / candle continuity (D3, 2026-09-30).

When an asset's ticker is renamed (e.g. TON -> GRAM on 2026-06-15), the new ticker
starts a fresh candle history even though it is the SAME asset. The per-signal
daily loaders select by `LIKE '{base}/%'`, so the renamed coin only sees its own
short post-rename history and is starved of its own past.

This module provides:
  - TICKER_LINEAGE: declarative map of current base -> [current, *predecessors].
    One line per future rename. Non-destructive: both tickers stay in the DB.
  - lineage_bases(base): the ordered list of bases to union for a given coin.
  - load_lineage_daily(db, base, columns): union `candles_daily` rows across the
    coin's lineage, dedup by timestamp (keep latest / newest ticker), sorted.

Scalable: O(1) per rename (one map entry). Preferred over physically re-keying
rows (destructive, one-off, loses provenance).
"""

import pandas as pd

# current_base -> [current_base, *predecessor_bases]  (newest first)
TICKER_LINEAGE = {
    "GRAM": ["GRAM", "TON"],   # Toncoin renamed to Gram, 2026-06-15
}


def lineage_bases(base):
    """Return the ordered lineage bases for a coin (current first).
    Coins without a rename return just [base]."""
    return TICKER_LINEAGE.get(base, [base])


def _symbols_for_bases(db, bases):
    """Resolve concrete candles_daily symbols for a list of bases, preserving
    lineage order (current-ticker symbols first). Within a base, prefer symbols
    that HAVE indicators, then widest date range."""
    ordered = []
    for b in bases:
        syms = [r[0] for r in db.execute(
            "SELECT DISTINCT symbol FROM candles_daily WHERE symbol LIKE ?",
            (f"{b}/%",)).fetchall()]
        if not syms:
            continue

        def _score(s):
            r = db.execute(
                "SELECT MAX(timestamp) - MIN(timestamp), "
                "SUM(CASE WHEN sma50 IS NOT NULL AND sma50 != 0 THEN 1 ELSE 0 END) "
                "FROM candles_daily "
                "WHERE symbol=? AND timestamp IS NOT NULL AND timestamp > 0", (s,)).fetchone()
            date_range = r[0] or 0
            has_indicators = 1 if (r[1] or 0) > 0 else 0
            return (has_indicators * 10**15) + date_range

        # best symbol per base; if multiple quote pairs, take the best-scored
        ordered.append(max(syms, key=_score))
    return ordered


def load_lineage_daily(db, base, columns="timestamp, open, high, low, close, volume"):
    """Union candles_daily across the coin's ticker lineage.

    Returns a DataFrame indexed by datetime (dt), deduped by timestamp keeping the
    LATEST row (so an overlapping boundary favors the newer ticker), sorted. Returns
    None if no rows exist for any lineage member.

    `columns` is the column list to SELECT (callers vary: OHLCV vs `*`).
    """
    bases = lineage_bases(base)
    syms = _symbols_for_bases(db, bases)
    if not syms:
        return None

    frames = []
    for s in syms:
        df = pd.read_sql(
            f"SELECT {columns} FROM candles_daily WHERE symbol=? ORDER BY timestamp",
            db, params=[s])
        if len(df):
            frames.append(df)
    if not frames:
        return None

    merged = pd.concat(frames, ignore_index=True)
    merged["dt"] = pd.to_datetime(merged["timestamp"], unit="ms")
    merged = merged.set_index("dt").sort_index()
    # dedup by timestamp: keep last (newer ticker wins at any overlap/collision)
    merged = merged[~merged.index.duplicated(keep="last")]
    merged.attrs["symbol"] = syms[0]
    merged.attrs["lineage"] = bases
    return merged
