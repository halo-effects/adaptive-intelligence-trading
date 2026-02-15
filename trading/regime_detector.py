"""Market regime classifier using multi-indicator weighted scoring."""
import pandas as pd
import numpy as np
from . import indicators

# Regimes ranked by Martingale friendliness (best to worst)
REGIMES = ["CHOPPY", "RANGING", "MILD_TREND", "TRENDING", "EXTREME"]

# Timeframe noise adjustment: shorter = noisier, so relax thresholds
_TF_ADJ = {"1m": 1.5, "5m": 1.3, "15m": 1.15, "1h": 1.0, "4h": 0.85}


def classify_regime(df: pd.DataFrame, timeframe: str = "1h") -> pd.Series:
    """Classify each row into a market regime. df must have OHLCV columns.
    Returns a Series of regime strings aligned to df index."""
    df = indicators.compute_all(df)
    adj = _TF_ADJ.get(timeframe, 1.0)

    regimes = pd.Series("RANGING", index=df.index)

    adx_ = df["adx_14"]
    hurst_ = df["hurst"]
    bbw_ = df["bbw"]
    atr_pct_ = df["atr_pct"]
    vol_ = df["volume"]
    vol_sma_ = df["vol_sma_20"]

    # Median BBW for "tight" / "wide" reference
    bbw_med = bbw_.rolling(100, min_periods=20).median()

    for i in range(len(df)):
        a = adx_.iloc[i] if not pd.isna(adx_.iloc[i]) else 25
        h = hurst_.iloc[i] if not pd.isna(hurst_.iloc[i]) else 0.5
        b = bbw_.iloc[i] if not pd.isna(bbw_.iloc[i]) else 3.0
        bm = bbw_med.iloc[i] if not pd.isna(bbw_med.iloc[i]) else 3.0
        ap = atr_pct_.iloc[i] if not pd.isna(atr_pct_.iloc[i]) else 1.0
        v = vol_.iloc[i] if not pd.isna(vol_.iloc[i]) else 0
        vs = vol_sma_.iloc[i] if (not pd.isna(vol_sma_.iloc[i]) and vol_sma_.iloc[i] > 0) else 1

        # Adjusted ADX thresholds
        adx_low = 20 * adj
        adx_mid = 30 * adj
        adx_high = 40 * adj

        # Score: lower = choppier, higher = trendier
        score = 0.0
        # ADX contribution (weight 0.35)
        score += 0.35 * min(a / adx_high, 1.5)
        # Hurst contribution (weight 0.25) — H>0.5 = trending
        score += 0.25 * (h / 0.5) if h > 0 else 0.25
        # BBW contribution (weight 0.2) — wide bands = trending
        bbw_ratio = b / bm if bm > 0 else 1.0
        score += 0.2 * min(bbw_ratio, 2.0)
        # Volume spike (weight 0.2)
        vol_ratio = v / vs
        score += 0.2 * min(vol_ratio / 2.0, 1.5)

        # Extreme detection: massive volume + ATR spike
        if vol_ratio > 3.0 and ap > 3.0 * adj:
            regimes.iloc[i] = "EXTREME"
        elif a > adx_high or score > 1.1:
            regimes.iloc[i] = "TRENDING"
        elif a > adx_mid or score > 0.85:
            regimes.iloc[i] = "MILD_TREND"
        elif a < adx_low and h < 0.45 and bbw_ratio < 0.9:
            regimes.iloc[i] = "CHOPPY"
        else:
            regimes.iloc[i] = "RANGING"

    return regimes


def is_martingale_friendly(regime: str) -> bool:
    return regime in ("CHOPPY", "RANGING")


# ---------------------------------------------------------------------------
# V2: Enhanced regime detection with Wyckoff, HVF, and Channel analysis
# ---------------------------------------------------------------------------

REGIMES_V2 = [
    "ACCUMULATION", "CHOPPY", "RANGING", "DISTRIBUTION",
    "BREAKOUT_WARNING", "MILD_TREND", "TRENDING", "EXTREME",
]


def classify_regime_v2(df: pd.DataFrame, timeframe: str = "1h") -> pd.Series:
    """Enhanced regime classifier with Wyckoff, HVF, and channel analysis."""
    df = indicators.compute_all(df)
    adj = _TF_ADJ.get(timeframe, 1.0)

    # Base regime from v1 logic
    base = classify_regime(df, timeframe)

    # Compute new indicators
    vc = indicators.volume_climax(df)
    spring = indicators.spring_detection(df)
    vt = indicators.volume_trend(df)
    rt = indicators.range_tightening(df)
    vuvu = indicators.hvf_vuvuzela(df)
    cb = indicators.channel_breakout(df)
    cwp = indicators.channel_width_pct(df)
    cwp_ma = cwp.rolling(50, min_periods=10).mean()

    vol = df["volume"]
    vol_sma = indicators.volume_sma(df, 20)

    # Timeframe-adjusted lookback: wider on shorter timeframes
    tf_lookback_mult = {
        "5m": 2, "15m": 1.5, "1h": 1, "4h": 1,
    }
    lb_mult = tf_lookback_mult.get(timeframe, 1)

    # HVF threshold: higher on shorter timeframes to avoid noise
    hvf_threshold = 0.8 if timeframe in ("5m", "15m") else 0.75

    regimes = base.copy()

    for i in range(len(df)):
        # --- HVF Breakout Warning (highest priority override) ---
        # Only trigger on very high scores (was 0.7)
        if vuvu.iloc[i] > hvf_threshold:
            regimes.iloc[i] = "BREAKOUT_WARNING"
            continue

        # --- Spring detection → ACCUMULATION ---
        if spring.iloc[i]:
            regimes.iloc[i] = "ACCUMULATION"
            continue

        # --- Wyckoff: selling climax + tightening + decreasing volume ---
        # Wider lookback window (scaled by timeframe)
        lookback_window = int(min(20 * lb_mult, i))
        recent_vc = vc.iloc[max(0, i - lookback_window):i + 1]

        if "selling_climax" in recent_vc.values:
            # Relaxed: range tightening < 1.0 (was 0.8) AND (declining or flat volume)
            rt_val = rt.iloc[i] if not pd.isna(rt.iloc[i]) else 999
            vt_val = vt.iloc[i]
            if rt_val < 1.0 and vt_val in ("decreasing", "flat"):
                regimes.iloc[i] = "ACCUMULATION"
                continue

        if "buying_climax" in recent_vc.values:
            rt_val = rt.iloc[i] if not pd.isna(rt.iloc[i]) else 999
            vt_val = vt.iloc[i]
            if rt_val < 1.0 and vt_val in ("decreasing", "flat"):
                regimes.iloc[i] = "DISTRIBUTION"
                continue

        # --- Broad accumulation: consolidation with declining volume ---
        # Only when base is RANGING (not MILD_TREND/TRENDING) with declining volume
        # and price is near recent lows (lower 30%)
        if base.iloc[i] == "RANGING" and vt.iloc[i] == "decreasing":
            lookback_price = int(min(60 * lb_mult, i))
            if lookback_price > 20:
                recent_high = df["high"].iloc[max(0, i - lookback_price):i + 1].max()
                recent_low = df["low"].iloc[max(0, i - lookback_price):i + 1].min()
                price_range = recent_high - recent_low
                if price_range > 0:
                    position = (df["close"].iloc[i] - recent_low) / price_range
                    if position < 0.3:
                        regimes.iloc[i] = "ACCUMULATION"
                        continue

        # --- Channel breakout: much stricter ---
        cb_val = cb.iloc[i]
        if cb_val is not None:
            v = vol.iloc[i] if not pd.isna(vol.iloc[i]) else 0
            vs = vol_sma.iloc[i] if (not pd.isna(vol_sma.iloc[i]) and vol_sma.iloc[i] > 0) else 1
            vol_ratio = v / vs
            # Only override on very strong breakouts (3x volume for EXTREME, keep TRENDING for 2x+)
            if vol_ratio > 3.0:
                regimes.iloc[i] = "EXTREME"
            elif vol_ratio > 2.0:
                regimes.iloc[i] = "TRENDING"
            # Otherwise don't override base — weak breakouts stay as base classification
            continue

        # --- Channel narrowing → CHOPPY/RANGING ---
        if not pd.isna(cwp.iloc[i]) and not pd.isna(cwp_ma.iloc[i]) and cwp_ma.iloc[i] > 0:
            if cwp.iloc[i] < cwp_ma.iloc[i] * 0.8:
                # Narrowing channels — downgrade trending to ranging
                if regimes.iloc[i] == "TRENDING":
                    regimes.iloc[i] = "MILD_TREND"
                elif regimes.iloc[i] == "MILD_TREND":
                    regimes.iloc[i] = "RANGING"

    return regimes


def is_martingale_friendly_v2(regime: str):
    """Returns True, 'cautious', or False based on v2 regime."""
    if regime in ("ACCUMULATION", "CHOPPY", "RANGING"):
        return True
    if regime == "DISTRIBUTION":
        return "cautious"
    return False
