"""Fetch OHLCV data from Binance via ccxt with local CSV caching."""
import os
import time
import ccxt
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

_exchange = None

def _get_exchange():
    global _exchange
    if _exchange is None:
        # Try multiple exchanges in case of geo-restrictions
        for ExCls in [ccxt.okx, ccxt.bybit, ccxt.binanceus, ccxt.kucoin]:
            try:
                ex = ExCls({"enableRateLimit": True})
                ex.load_markets()
                _exchange = ex
                print(f"  Using exchange: {ex.id}")
                return _exchange
            except Exception:
                continue
        raise RuntimeError("No accessible exchange found")
    return _exchange


def _cache_path(symbol: str, timeframe: str) -> Path:
    safe = symbol.replace("/", "_")
    return DATA_DIR / f"{safe}_{timeframe}.csv"


def fetch_ohlcv(symbol: str, timeframe: str, since: int = None, limit: int = 1000) -> pd.DataFrame:
    """Fetch OHLCV candles. `since` is ms timestamp."""
    ex = _get_exchange()
    all_rows = []
    current_since = since
    while True:
        batch = ex.fetch_ohlcv(symbol, timeframe, since=current_since, limit=min(limit - len(all_rows), 1000))
        if not batch:
            break
        all_rows.extend(batch)
        if len(all_rows) >= limit:
            break
        current_since = batch[-1][0] + 1
        time.sleep(ex.rateLimit / 1000)
    df = pd.DataFrame(all_rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.drop_duplicates(subset="timestamp").sort_values("timestamp").reset_index(drop=True)
    return df


def fetch_multiple_symbols(symbols: list, timeframe: str, days_back: int = 90) -> dict:
    """Fetch and cache OHLCV for multiple symbols. Returns {symbol: DataFrame}."""
    since_ms = int((datetime.now(timezone.utc) - timedelta(days=days_back)).timestamp() * 1000)
    result = {}
    for sym in symbols:
        cache = _cache_path(sym, timeframe)
        if cache.exists():
            df = pd.read_csv(cache, parse_dates=["timestamp"])
            last_ts = pd.Timestamp(df["timestamp"].max(), unit="ms" if isinstance(df["timestamp"].max(), (int, float)) else None)
            if last_ts.tzinfo is None:
                last_ts = last_ts.tz_localize("UTC")
            if pd.Timestamp.now(tz="UTC") - last_ts < timedelta(hours=1):
                result[sym] = df
                print(f"  [cache] {sym} {timeframe} — {len(df)} candles")
                continue
        try:
            # calculate rough limit
            tf_minutes = _tf_to_minutes(timeframe)
            limit = (days_back * 24 * 60) // tf_minutes + 10
            df = fetch_ohlcv(sym, timeframe, since=since_ms, limit=limit)
            df.to_csv(cache, index=False)
            result[sym] = df
            print(f"  [fetch] {sym} {timeframe} — {len(df)} candles")
        except Exception as e:
            print(f"  [error] {sym}: {e}")
    return result


def get_top_pairs(n: int = 20) -> list:
    """Get top N USDT pairs by 24h volume from Binance."""
    ex = _get_exchange()
    tickers = ex.fetch_tickers()
    usdt_pairs = []
    for sym, t in tickers.items():
        if sym.endswith("/USDT") and t.get("quoteVolume"):
            usdt_pairs.append((sym, t["quoteVolume"]))
    usdt_pairs.sort(key=lambda x: x[1], reverse=True)
    return [p[0] for p in usdt_pairs[:n]]


def _tf_to_minutes(tf: str) -> int:
    unit = tf[-1]
    val = int(tf[:-1])
    return val * {"m": 1, "h": 60, "d": 1440, "w": 10080}[unit]


if __name__ == "__main__":
    print("Testing fetch BTC/USDT 1h last 7 days...")
    since = int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp() * 1000)
    df = fetch_ohlcv("BTC/USDT", "1h", since=since, limit=200)
    print(f"Got {len(df)} candles")
    print(df.head())
    print(df.tail())
