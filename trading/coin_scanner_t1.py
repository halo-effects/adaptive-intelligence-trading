"""Tier 1: Quick coin filter for Aster DEX futures pairs.

Runs cheap signals on 1h data (7 days) to produce a shortlist.
Standalone: python trading/coin_scanner_t1.py
"""
import sys, os, json, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

from trading import indicators
from trading.data_fetcher import fetch_ohlcv

LIVE_DIR = Path(__file__).parent / "live"
LIVE_DIR.mkdir(exist_ok=True)
OUTPUT_PATH = LIVE_DIR / "scanner_t1.json"

# Cache for 1h klines (reuse within 1 hour)
_kline_cache = {}  # symbol -> (timestamp, df)
CACHE_TTL = 3600  # seconds

# Maturity filter thresholds
MIN_AGE_CANDLES = 60        # need ≥60 daily candles (~2 months on Aster)
VOLUME_SPIKE_RATIO = 4.0    # 7d avg vol / 30d avg vol (crypto is spiky)
PRICE_SWING_PCT = 120.0     # (max-min)/min * 100 over 30 days (crypto routinely swings 80-100%)
MIN_VOLUME_24H = 1_000_000  # $1M floor

# Cache for daily klines used by maturity filters
_daily_cache = {}  # symbol -> (timestamp, df)


# ── Aster pair discovery ──────────────────────────────────────────────

def get_aster_usdt_pairs() -> list[str]:
    """Fetch all USDT perpetual pairs from Aster DEX."""
    url = "https://fapi.asterdex.com/fapi/v1/exchangeInfo"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[ERROR] Failed to fetch Aster exchangeInfo: {e}")
        return []

    pairs = []
    for sym in data.get("symbols", []):
        if (sym.get("quoteAsset") == "USDT"
                and sym.get("status", "").upper() == "TRADING"
                and sym.get("contractType", "").upper() == "PERPETUAL"):
            pairs.append(sym["symbol"])  # e.g. "BTCUSDT"
    return pairs


def aster_symbol_to_ccxt(symbol: str) -> str:
    """Convert BTCUSDT -> BTC/USDT for ccxt fetching."""
    if symbol.endswith("USDT"):
        return symbol[:-4] + "/USDT"
    return symbol


# ── Data fetching ─────────────────────────────────────────────────────

def fetch_1h_cached(ccxt_symbol: str, days: int = 7) -> pd.DataFrame | None:
    """Fetch 1h klines with simple in-memory cache."""
    now = time.time()
    if ccxt_symbol in _kline_cache:
        cached_time, cached_df = _kline_cache[ccxt_symbol]
        if now - cached_time < CACHE_TTL:
            return cached_df

    from datetime import timedelta
    since_ms = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    try:
        df = fetch_ohlcv(ccxt_symbol, "1h", since=since_ms, limit=days * 24 + 10)
        if df is not None and len(df) > 0:
            _kline_cache[ccxt_symbol] = (now, df)
            return df
    except Exception as e:
        print(f"  [skip] {ccxt_symbol}: {e}")
    return None


# ── Maturity filters ──────────────────────────────────────────────────

def fetch_daily_aster(aster_symbol: str, days: int = 90) -> pd.DataFrame | None:
    """Fetch daily klines directly from Aster DEX API (Binance-compatible)."""
    now = time.time()
    cache_key = f"aster_{aster_symbol}_1d"
    if cache_key in _daily_cache:
        cached_time, cached_df = _daily_cache[cache_key]
        if now - cached_time < CACHE_TTL:
            return cached_df

    from datetime import timedelta
    start_ms = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    url = "https://fapi.asterdex.com/fapi/v1/klines"
    try:
        r = requests.get(url, params={
            "symbol": aster_symbol,
            "interval": "1d",
            "startTime": start_ms,
            "limit": days + 5,
        }, timeout=5)
        r.raise_for_status()
        data = r.json()
        if not data:
            return None
        rows = [[c[0], float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])] for c in data]
        df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
        _daily_cache[cache_key] = (now, df)
        return df
    except Exception:
        return None


def maturity_check(aster_symbol: str) -> tuple[bool, str]:
    """Run maturity/pump-and-dump filters. Returns (passed, reason)."""
    # Fetch 90 days of daily klines directly from Aster
    df_90 = fetch_daily_aster(aster_symbol, days=90)

    # 1. Age filter: need ≥80 daily candles
    if df_90 is None or len(df_90) < MIN_AGE_CANDLES:
        candles = 0 if df_90 is None else len(df_90)
        return False, f"too_new ({candles} daily candles, need {MIN_AGE_CANDLES})"

    # Use last 30 days for volume/price stability
    df_30 = df_90.tail(30)
    if len(df_30) < 25:
        return False, f"insufficient_30d_data ({len(df_30)} candles)"

    # 2. Volume stability: 7d avg vs 30d avg
    daily_vol_usd = df_30["volume"] * df_30["close"]
    vol_30d_avg = daily_vol_usd.mean()
    vol_7d_avg = daily_vol_usd.tail(7).mean()

    if vol_30d_avg > 0:
        vol_ratio = vol_7d_avg / vol_30d_avg
        if vol_ratio > VOLUME_SPIKE_RATIO:
            return False, f"volume_spike (7d/30d ratio={vol_ratio:.1f}, max={VOLUME_SPIKE_RATIO})"

    # 3. Price stability: max swing over 30 days
    price_min = df_30["low"].min()
    price_max = df_30["high"].max()
    if price_min > 0:
        swing_pct = (price_max - price_min) / price_min * 100
        if swing_pct > PRICE_SWING_PCT:
            return False, f"price_swing ({swing_pct:.0f}%, max={PRICE_SWING_PCT:.0f}%)"

    # 4. Volume floor (24h)
    last_day_vol = daily_vol_usd.iloc[-1] if len(daily_vol_usd) > 0 else 0
    if last_day_vol < MIN_VOLUME_24H:
        return False, f"low_volume (${last_day_vol:,.0f} < ${MIN_VOLUME_24H:,.0f})"

    return True, "passed"


# ── Tier 1 signals ───────────────────────────────────────────────────

def hurst_quick(closes: np.ndarray, min_chunk: int = 8, max_chunk: int = 64) -> float:
    """Quick single-value Hurst exponent via R/S analysis on log-returns.

    For each chunk size n, split the returns into non-overlapping chunks,
    compute rescaled range R/S for each, average, then regress
    log(mean R/S) on log(n) to get the Hurst exponent.
    """
    segment = closes[-168:]  # use up to 168 candles (7 days of 1h)
    # Work on log-returns (stationary series)
    returns = np.diff(np.log(segment))
    if len(returns) < min_chunk * 2:
        return 0.5

    eff_max = min(max_chunk, len(returns) // 2)
    if eff_max < min_chunk + 4:
        return 0.5

    chunk_sizes = np.unique(np.geomspace(min_chunk, eff_max, num=15).astype(int))
    log_n = []
    log_rs = []

    for n in chunk_sizes:
        num_chunks = len(returns) // n
        if num_chunks < 1:
            continue
        rs_vals = []
        for k in range(num_chunks):
            chunk = returns[k * n:(k + 1) * n]
            m = chunk.mean()
            deviate = np.cumsum(chunk - m)
            r = deviate.max() - deviate.min()
            s_std = chunk.std(ddof=1)
            if s_std > 0:
                rs_vals.append(r / s_std)
        if rs_vals:
            log_n.append(np.log(n))
            log_rs.append(np.log(np.mean(rs_vals)))

    if len(log_n) < 4:
        return 0.5

    slope = np.polyfit(log_n, log_rs, 1)[0]
    return float(np.clip(slope, 0.01, 0.99))


def sma_cross_count(closes: pd.Series, period: int = 20) -> int:
    """Count SMA crosses over the series."""
    sma_val = indicators.sma(closes, period)
    above = closes > sma_val
    crosses = (above != above.shift(1)).sum()
    return int(crosses)


def score_coin_t1(df: pd.DataFrame, volume_24h: float = None) -> dict | None:
    """Score a coin on Tier 1 cheap signals. Returns dict or None if filtered out."""
    if len(df) < 100:
        return None

    closes = df["close"].values
    close_s = df["close"]

    # 1. ADX (14-period)
    adx_val = indicators.adx(df, 14).dropna().tail(20).mean()
    if np.isnan(adx_val):
        adx_val = 30.0

    # 2. ATR%
    atr_pct_val = indicators.atr_pct(df, 14).dropna().tail(20).mean()
    if np.isnan(atr_pct_val):
        return None

    # 3. Hurst exponent
    hurst_val = hurst_quick(closes)

    # 4. SMA20 cross rate
    crosses = sma_cross_count(close_s, 20)
    cross_rate = crosses / len(df)  # per bar

    # 5. 24h volume estimate from data
    if volume_24h is None:
        # Estimate from last 24 1h candles
        tail24 = df.tail(24)
        volume_24h = (tail24["volume"] * tail24["close"]).sum()

    # ── Filtering thresholds ──
    if volume_24h < 1_000_000:
        return None  # too illiquid
    if atr_pct_val < 0.3 or atr_pct_val > 4.0:
        return None  # volatility outside usable range

    # ── Scoring (0-100) ──
    # ADX: lower is better for DCA (want < 25)
    if adx_val < 20:
        adx_score = 30.0
    elif adx_val < 25:
        adx_score = 25.0
    elif adx_val < 30:
        adx_score = 15.0
    else:
        adx_score = max(0, 10 - (adx_val - 30))

    # ATR%: sweet spot 0.5-2.5%
    if 0.5 <= atr_pct_val <= 2.5:
        atr_score = 25.0
    elif atr_pct_val < 0.5:
        atr_score = atr_pct_val / 0.5 * 15
    else:
        atr_score = max(0, 25 - (atr_pct_val - 2.5) * 10)

    # Hurst: want < 0.5 (mean-reverting)
    if hurst_val < 0.4:
        hurst_score = 25.0
    elif hurst_val < 0.5:
        hurst_score = 20.0
    elif hurst_val < 0.55:
        hurst_score = 10.0
    else:
        hurst_score = max(0, 5 - (hurst_val - 0.55) * 20)

    # Cross rate: more crosses = more mean reversion
    cross_score = min(cross_rate * 500, 20.0)  # normalize

    total = adx_score + atr_score + hurst_score + cross_score

    return {
        "adx": round(adx_val, 2),
        "atr_pct": round(atr_pct_val, 3),
        "hurst": round(hurst_val, 3),
        "sma_crosses": crosses,
        "cross_rate": round(cross_rate, 4),
        "volume_24h": round(volume_24h, 0),
        "adx_score": round(adx_score, 1),
        "atr_score": round(atr_score, 1),
        "hurst_score": round(hurst_score, 1),
        "cross_score": round(cross_score, 1),
        "total_score": round(total, 1),
    }


# ── Main runner ──────────────────────────────────────────────────────

def run_tier1(top_n: int = 15) -> list[dict]:
    """Run Tier 1 scan on all Aster USDT perps. Returns sorted shortlist."""
    print("=" * 70)
    print("TIER 1: QUICK COIN SCANNER")
    print("=" * 70)

    # Get Aster pairs
    print("\n[1] Fetching Aster futures pairs...")
    aster_pairs = get_aster_usdt_pairs()
    print(f"    Found {len(aster_pairs)} USDT perpetuals")

    if not aster_pairs:
        print("    No pairs found! Check Aster API.")
        return []

    # ── Maturity pre-filters ──
    print(f"\n[2] Running maturity filters ({len(aster_pairs)} pairs)...")
    mature_pairs = []
    rejected = []
    filter_counts = {"too_new": 0, "volume_spike": 0, "price_swing": 0, "low_volume": 0, "insufficient_30d_data": 0}

    for i, aster_sym in enumerate(aster_pairs):
        ccxt_sym = aster_symbol_to_ccxt(aster_sym)
        if (i + 1) % 10 == 0 or i == 0:
            print(f"  maturity check ({i+1}/{len(aster_pairs)})...", flush=True)

        passed, reason = maturity_check(aster_sym)
        time.sleep(0.1)  # rate limit Aster API
        if passed:
            mature_pairs.append(aster_sym)
        else:
            rejected.append({"symbol": ccxt_sym, "aster_symbol": aster_sym, "filter_reason": reason})
            # Increment category counter
            for key in filter_counts:
                if reason.startswith(key):
                    filter_counts[key] += 1
                    break

    print(f"\n    Maturity filter results:")
    print(f"      {len(aster_pairs)} total -> {len(mature_pairs)} passed maturity filters")
    print(f"      Rejected: {len(rejected)} — too_new={filter_counts['too_new']}, "
          f"volume_spike={filter_counts['volume_spike']}, price_swing={filter_counts['price_swing']}, "
          f"low_volume={filter_counts['low_volume']}, insufficient_data={filter_counts['insufficient_30d_data']}")

    # ── Technical scoring on mature coins only ──
    print(f"\n[3] Fetching 1h data & scoring ({len(mature_pairs)} mature pairs)...")
    results = []
    for i, aster_sym in enumerate(mature_pairs):
        ccxt_sym = aster_symbol_to_ccxt(aster_sym)
        print(f"  ({i+1}/{len(mature_pairs)}) {ccxt_sym}...", end=" ", flush=True)

        df = fetch_1h_cached(ccxt_sym, days=7)
        if df is None or len(df) < 50:
            print("skip (no data)")
            continue

        score = score_coin_t1(df)
        if score is None:
            print("filtered out")
            continue

        score["symbol"] = ccxt_sym
        score["aster_symbol"] = aster_sym
        results.append(score)
        print(f"score={score['total_score']}")

    # Sort by total score
    results.sort(key=lambda x: x["total_score"], reverse=True)

    # Take top N
    shortlist = results[:top_n]

    print(f"\n    Pipeline: {len(aster_pairs)} total -> {len(mature_pairs)} after maturity -> "
          f"{len(results)} after technical -> {len(shortlist)} shortlist")

    # Save
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_pairs_scanned": len(aster_pairs),
        "passed_maturity": len(mature_pairs),
        "passed_technical": len(results),
        "shortlist_size": len(shortlist),
        "maturity_filter_counts": filter_counts,
        "rejected_by_maturity": rejected,
        "candidates": shortlist,
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"\n[4] Results saved to {OUTPUT_PATH}")

    # Print summary
    print(f"\n{'Rank':<5} {'Symbol':<14} {'Score':<7} {'ADX':<7} {'ATR%':<7} {'Hurst':<7} {'Crosses':<8} {'Vol24h':<14}")
    print("-" * 75)
    for i, c in enumerate(shortlist):
        print(f"{i+1:<5} {c['symbol']:<14} {c['total_score']:<7} {c['adx']:<7} {c['atr_pct']:<7} {c['hurst']:<7} {c['sma_crosses']:<8} {c['volume_24h']:>12,.0f}")

    return shortlist


if __name__ == "__main__":
    run_tier1()
