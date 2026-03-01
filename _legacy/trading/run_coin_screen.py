"""Dual-tracking strategy fitness screener."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from trading.data_fetcher import fetch_multiple_symbols
from trading.regime_detector import classify_regime_v2
from trading import indicators

SYMBOLS = [
    "XRP/USDT", "LINK/USDT", "DOGE/USDT", "HYPE/USDT", "BTC/USDT",
    "ETH/USDT", "SOL/USDT", "AVAX/USDT", "ADA/USDT", "MATIC/USDT",
    "DOT/USDT", "NEAR/USDT", "SUI/USDT", "ARB/USDT", "OP/USDT",
    "ASTER/USDT",
]

def dual_track_metrics(df_1h, df_5m, symbol):
    """Compute dual-tracking specific metrics."""
    if df_1h is None or len(df_1h) < 50:
        return None

    # Price range % over last 14 days (use 1h data)
    tail = df_1h.tail(336)  # ~14 days of 1h
    price_high = tail["high"].max()
    price_low = tail["low"].min()
    price_avg = tail["close"].mean()
    range_pct = (price_high - price_low) / price_avg * 100

    # Trend strength: net change over 14 days
    trend_strength = abs((tail["close"].iloc[-1] - tail["close"].iloc[0]) / tail["close"].iloc[0] * 100)

    # ATR% from 1h data
    df_ind = indicators.compute_all(df_1h)
    atr_pct_val = df_ind["atr_pct"].dropna().tail(100).mean()

    # Volume score (normalized later)
    vol_usd = (tail["volume"] * tail["close"]).mean()

    # Mean reversion: SMA20 crosses on 1h data
    sma20 = indicators.sma(tail["close"], 20)
    above = tail["close"] > sma20
    crosses = (above != above.shift(1)).sum()
    cross_rate = crosses / len(tail) * 100  # crosses per bar as %

    # Regime distribution on 5m data (limit to last 1500 rows for speed)
    ranging_pct = 0.0
    if df_5m is not None and len(df_5m) > 100:
        df_5m_trimmed = df_5m.tail(1500).reset_index(drop=True)
        regimes = classify_regime_v2(df_5m_trimmed, timeframe="5m")
        total = len(regimes)
        friendly = regimes.isin(["RANGING", "CHOPPY", "ACCUMULATION"]).sum()
        ranging_pct = friendly / total * 100

    return {
        "symbol": symbol,
        "range_pct": round(range_pct, 2),
        "trend_str": round(trend_strength, 2),
        "atr_pct": round(atr_pct_val, 3) if not np.isnan(atr_pct_val) else 0,
        "sma_crosses": crosses,
        "cross_rate": round(cross_rate, 2),
        "ranging_pct": round(ranging_pct, 1),
        "vol_usd": round(vol_usd, 0),
    }


def compute_fitness(rows):
    """Compute dual-tracking fitness score with weighted components."""
    df = pd.DataFrame(rows)

    # Normalize each component to 0-1
    # Trend strength: lower is better → invert
    ts_max = df["trend_str"].max() or 1
    df["trend_score"] = 1 - (df["trend_str"] / ts_max)

    # Mean reversion (cross rate): higher is better
    cr_max = df["cross_rate"].max() or 1
    df["mr_score"] = df["cross_rate"] / cr_max

    # ATR%: moderate is best (target ~1-2%), penalize extremes
    def atr_fitness(v):
        if 0.5 <= v <= 2.5:
            return 1.0
        elif v < 0.5:
            return v / 0.5
        else:
            return max(0, 1.0 - (v - 2.5) / 5.0)
    df["atr_score"] = df["atr_pct"].apply(atr_fitness)

    # Volume: higher is better (log scale)
    log_vol = np.log1p(df["vol_usd"])
    lv_max = log_vol.max() or 1
    df["vol_score"] = log_vol / lv_max

    # Weighted fitness
    df["fitness"] = (
        0.40 * df["trend_score"] +
        0.30 * df["mr_score"] +
        0.20 * df["atr_score"] +
        0.10 * df["vol_score"]
    )

    df = df.sort_values("fitness", ascending=False).reset_index(drop=True)
    return df


def main():
    print("=" * 80)
    print("DUAL-TRACKING STRATEGY FITNESS SCREENER")
    print("=" * 80)

    # Fetch 1h data (14 days)
    print("\n--- Fetching 1h data (14 days) ---")
    data_1h = fetch_multiple_symbols(SYMBOLS, "1h", days_back=14)

    # Fetch 5m data (14 days)
    print("\n--- Fetching 5m data (14 days) ---")
    data_5m = fetch_multiple_symbols(SYMBOLS, "5m", days_back=14)

    # Compute metrics
    print("\n--- Computing dual-tracking metrics ---")
    rows = []
    for sym in SYMBOLS:
        if sym not in data_1h:
            print(f"  Skipping {sym} (no data)")
            continue
        df_5m = data_5m.get(sym)
        print(f"  Processing {sym}...")
        m = dual_track_metrics(data_1h[sym], df_5m, sym)
        if m:
            rows.append(m)

    if not rows:
        print("No data available!")
        return

    df = compute_fitness(rows)

    # Print results
    print("\n" + "=" * 120)
    print(f"{'Rank':<5} {'Symbol':<12} {'Fitness':<9} {'Trend%':<9} {'Range%':<9} {'ATR%':<8} {'SMA✕':<7} {'✕Rate%':<9} {'Ranging%':<10} {'Vol$':<15}")
    print("-" * 120)
    for i, r in df.iterrows():
        print(f"{i+1:<5} {r['symbol']:<12} {r['fitness']:.3f}     {r['trend_str']:<9} {r['range_pct']:<9} {r['atr_pct']:<8} {r['sma_crosses']:<7} {r['cross_rate']:<9} {r['ranging_pct']:<10} {r['vol_usd']:>12,.0f}")

    print("=" * 120)
    print("\nTop 5 coins for dual-tracking:")
    for i, r in df.head(5).iterrows():
        print(f"  {i+1}. {r['symbol']} (fitness={r['fitness']:.3f}) — trend={r['trend_str']}%, range={r['range_pct']}%, ranging={r['ranging_pct']}%")


if __name__ == "__main__":
    main()
