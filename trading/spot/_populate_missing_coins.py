"""
Fetch LINK/USDC and XRP/USDC candles from Hyperliquid and populate candles.db.
Fetches hourly candles, builds daily candles, stores both.
"""
import sqlite3
import time
from datetime import datetime, timezone
import ccxt

DB_PATH = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
COINS = {
    "LINK/USDC:USDC": "LINK/USDC",   # Hyperliquid symbol -> DB symbol
    "XRP/USDC:USDC": "XRP/USDC",
}
TIMEFRAME = "1h"
# Fetch from Oct 2024 (matches V13 backtest start)
START_TS = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)


def fetch_all_candles(exchange, hl_symbol, since_ms):
    """Fetch all hourly candles from since_ms to now."""
    all_candles = []
    current = since_ms
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(hl_symbol, TIMEFRAME, since=current, limit=1000)
        except Exception as e:
            print(f"  Error fetching {hl_symbol} from {current}: {e}")
            break
        if not ohlcv:
            break
        all_candles.extend(ohlcv)
        print(f"  Fetched {len(ohlcv)} candles, total: {len(all_candles)}, last: {datetime.fromtimestamp(ohlcv[-1][0]/1000, tz=timezone.utc)}")
        if len(ohlcv) < 1000:
            break
        current = ohlcv[-1][0] + 3600_000  # Next hour
        time.sleep(0.5)  # Rate limit
    return all_candles


def build_daily_from_hourly(hourly_candles):
    """Aggregate hourly candles into daily candles."""
    from collections import defaultdict
    daily = defaultdict(list)
    for ts, o, h, l, c, v in hourly_candles:
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
        day_key = dt.strftime("%Y-%m-%d")
        day_ts = int(datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc).timestamp() * 1000)
        daily[day_ts].append((o, h, l, c, v))

    result = []
    for day_ts in sorted(daily.keys()):
        bars = daily[day_ts]
        if len(bars) < 20:  # Skip incomplete days (need at least 20 of 24 hours)
            continue
        d_open = bars[0][0]
        d_high = max(b[1] for b in bars)
        d_low = min(b[2] for b in bars)
        d_close = bars[-1][3]
        d_vol = sum(b[4] for b in bars)
        result.append((day_ts, d_open, d_high, d_low, d_close, d_vol))
    return result


def main():
    print("Connecting to Hyperliquid...")
    exchange = ccxt.hyperliquid()
    exchange.load_markets()

    db = sqlite3.connect(DB_PATH)

    # Tables already exist with schema:
    # candles: symbol, timeframe, timestamp, open, high, low, close, volume  UNIQUE(symbol, timeframe, timestamp)
    # candles_daily: symbol, timestamp, open, high, low, close, volume  UNIQUE(symbol, timestamp)

    for hl_sym, db_sym in COINS.items():
        print(f"\n{'='*60}")
        print(f"Fetching {hl_sym} -> {db_sym}")

        # Check existing count
        existing = db.execute("SELECT COUNT(*) FROM candles WHERE symbol=?", (db_sym,)).fetchone()[0]
        print(f"  Existing hourly candles: {existing}")

        if existing > 0:
            last_ts = db.execute("SELECT MAX(timestamp) FROM candles WHERE symbol=?", (db_sym,)).fetchone()[0]
            since = last_ts + 3600_000
            print(f"  Fetching from last candle: {datetime.fromtimestamp(last_ts/1000, tz=timezone.utc)}")
        else:
            since = START_TS
            print(f"  Fetching from {datetime.fromtimestamp(since/1000, tz=timezone.utc)}")

        candles = fetch_all_candles(exchange, hl_sym, since)
        if not candles:
            print(f"  No new candles fetched")
            continue

        print(f"  Inserting {len(candles)} hourly candles...")
        db.executemany(
            "INSERT OR IGNORE INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?,?)",
            [(db_sym, "1h", int(c[0]), float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])) for c in candles]
        )
        db.commit()

        # Build and insert daily candles
        all_hourly = db.execute(
            "SELECT timestamp, open, high, low, close, volume FROM candles WHERE symbol=? AND timeframe='1h' ORDER BY timestamp",
            (db_sym,)
        ).fetchall()
        daily = build_daily_from_hourly(all_hourly)
        print(f"  Built {len(daily)} daily candles from {len(all_hourly)} hourly")

        db.executemany(
            "INSERT OR IGNORE INTO candles_daily (symbol, timestamp, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
            [(db_sym, d[0], d[1], d[2], d[3], d[4], d[5]) for d in daily]
        )
        db.commit()

        # Verify
        h_count = db.execute("SELECT COUNT(*) FROM candles WHERE symbol=?", (db_sym,)).fetchone()[0]
        d_count = db.execute("SELECT COUNT(*) FROM candles_daily WHERE symbol=?", (db_sym,)).fetchone()[0]
        print(f"  Final: {h_count} hourly, {d_count} daily candles")

    db.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
