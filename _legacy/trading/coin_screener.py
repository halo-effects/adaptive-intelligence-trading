"""Rank coins by Martingale friendliness."""
import pandas as pd
import numpy as np
from . import indicators
from .data_fetcher import fetch_multiple_symbols, get_top_pairs


def score_coin(df: pd.DataFrame) -> dict:
    """Score a single coin's DataFrame. Returns dict with component scores and total."""
    if len(df) < 100:
        return {"total": 0, "volume": 0, "atr_pct": 0, "hurst": 0, "reason": "insufficient data"}

    df = indicators.compute_all(df)
    tail = df.tail(100)

    # Volume score (0-25): higher daily volume = better liquidity
    vol_mean = tail["volume"].mean()
    vol_score = min(vol_mean / (tail["volume"].quantile(0.9) + 1) * 25, 25)

    # ATR% score (0-30): moderate is best, too high is risky
    atr_mean = tail["atr_pct"].dropna().mean()
    if 0.5 <= atr_mean <= 2.0:
        atr_score = 30
    elif atr_mean < 0.5:
        atr_score = 15
    elif atr_mean <= 4.0:
        atr_score = 20 - (atr_mean - 2.0) * 5
    else:
        atr_score = max(0, 10 - (atr_mean - 4.0) * 3)

    # Hurst score (0-30): lower = more mean-reverting = better
    hurst_vals = tail["hurst"].dropna()
    if len(hurst_vals) > 10:
        h_mean = hurst_vals.mean()
        if h_mean < 0.4:
            hurst_score = 30
        elif h_mean < 0.5:
            hurst_score = 20
        elif h_mean < 0.55:
            hurst_score = 10
        else:
            hurst_score = max(0, 5 - (h_mean - 0.55) * 20)
    else:
        hurst_score = 15  # default if not enough data

    # BBW tightness (0-15): tighter = choppier = better
    bbw_vals = tail["bbw"].dropna()
    if len(bbw_vals) > 10:
        bbw_mean = bbw_vals.mean()
        bbw_score = max(0, 15 - bbw_mean * 1.5)
    else:
        bbw_score = 7.5

    total = vol_score + atr_score + hurst_score + bbw_score

    return {
        "total": round(total, 1),
        "volume": round(vol_score, 1),
        "atr_pct": round(atr_score, 1),
        "hurst": round(hurst_score, 1),
        "bbw": round(bbw_score, 1),
        "atr_pct_raw": round(atr_mean, 3) if not np.isnan(atr_mean) else None,
    }


def screen_coins(symbols: list = None, timeframe: str = "1h", days_back: int = 30) -> pd.DataFrame:
    """Fetch data and score/rank coins. Returns sorted DataFrame."""
    if symbols is None:
        print("Fetching top pairs...")
        symbols = get_top_pairs(20)

    print(f"Fetching data for {len(symbols)} symbols...")
    data = fetch_multiple_symbols(symbols, timeframe, days_back)

    rows = []
    for sym, df in data.items():
        scores = score_coin(df)
        scores["symbol"] = sym
        rows.append(scores)

    result = pd.DataFrame(rows).sort_values("total", ascending=False).reset_index(drop=True)
    return result
