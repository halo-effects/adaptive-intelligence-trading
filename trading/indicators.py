"""Technical indicators for regime detection. All operate on OHLCV DataFrames."""
import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"].shift(1)
    tr = pd.concat([h - l, (h - c).abs(), (l - c).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def atr_pct(df: pd.DataFrame, period: int = 14) -> pd.Series:
    return atr(df, period) / df["close"] * 100


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    plus_dm = (h - h.shift(1)).clip(lower=0)
    minus_dm = (l.shift(1) - l).clip(lower=0)
    # Zero out when the other is larger
    plus_dm[plus_dm < minus_dm] = 0
    minus_dm[minus_dm < plus_dm] = 0

    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    atr_ = tr.rolling(period).mean()
    plus_di = 100 * plus_dm.rolling(period).mean() / atr_
    minus_di = 100 * minus_dm.rolling(period).mean() / atr_
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.rolling(period).mean()


def bollinger_band_width(series: pd.Series, period: int = 20, std_mult: float = 2.0) -> pd.Series:
    mid = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    return (upper - lower) / mid * 100  # as percentage


def volume_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return df["volume"].rolling(period).mean()


def hurst_exponent(series: pd.Series, min_chunk: int = 8, max_chunk: int = 64) -> pd.Series:
    """Rolling Hurst exponent via R/S analysis. Returns Series aligned to input.

    For each window position, uses chunk sizes from min_chunk to max_chunk,
    splits window into non-overlapping chunks of size n, computes R/S per chunk,
    then regresses log(mean R/S) on log(n).
    """
    window = max(max_chunk * 2, 60)
    result = pd.Series(np.nan, index=series.index)

    vals = series.values
    n = len(vals)

    # For large datasets, subsample for speed
    step = 5 if n > 3000 else (3 if n > 1000 else 1)

    chunk_sizes = np.unique(np.geomspace(min_chunk, max_chunk, num=15).astype(int))

    for i in range(window, n, step):
        segment = vals[i - window: i]
        if np.isnan(segment).any():
            continue
        # Use log-returns for stationarity
        returns = np.diff(np.log(segment))
        if len(returns) < min_chunk * 2:
            continue
        log_n = []
        log_rs = []
        for cs in chunk_sizes:
            num_chunks = len(returns) // cs
            if num_chunks < 1:
                continue
            rs_vals = []
            for k in range(num_chunks):
                chunk = returns[k * cs:(k + 1) * cs]
                m = chunk.mean()
                deviate = np.cumsum(chunk - m)
                r = deviate.max() - deviate.min()
                s_std = chunk.std(ddof=1)
                if s_std > 0:
                    rs_vals.append(r / s_std)
            if rs_vals:
                log_n.append(np.log(cs))
                log_rs.append(np.log(np.mean(rs_vals)))

        if len(log_n) >= 4:
            slope = np.polyfit(log_n, log_rs, 1)[0]
            result.iloc[i] = float(np.clip(slope, 0.01, 0.99))

    # Forward fill gaps from subsampling
    if step > 1:
        result = result.ffill()

    return result


# ---------------------------------------------------------------------------
# Wyckoff Detection Indicators
# ---------------------------------------------------------------------------

def volume_climax(df: pd.DataFrame, lookback: int = 20) -> pd.Series:
    """Detect selling/buying climax. Returns Series: 'selling_climax', 'buying_climax', or None."""
    vol = df["volume"]
    rng = df["high"] - df["low"]
    vol_avg = vol.rolling(lookback).mean()
    rng_avg = rng.rolling(lookback).mean()

    # Relaxed: 1.5x volume (was 2.0) and 1.2x range (was 1.5) for broader detection
    high_vol = vol > vol_avg * 1.5
    wide_range = rng > rng_avg * 1.2

    body = df["close"] - df["open"]
    bar_range = rng.replace(0, np.nan)
    close_position = (df["close"] - df["low"]) / bar_range  # 0=close at low, 1=close at high

    selling = high_vol & wide_range & (close_position < 0.35)
    buying = high_vol & wide_range & (close_position > 0.65)

    result = pd.Series(None, index=df.index, dtype=object)
    result[selling] = "selling_climax"
    result[buying] = "buying_climax"
    return result


def spring_detection(df: pd.DataFrame, lookback: int = 30) -> pd.Series:
    """Detect Wyckoff spring: price dips below support then closes back above."""
    support = df["low"].rolling(lookback).min()
    # Spring: low goes below support of previous bars, but close stays above
    prev_support = support.shift(1)
    spring = (df["low"] < prev_support) & (df["close"] > prev_support)
    return spring.fillna(False)


def volume_trend(df: pd.DataFrame, period: int = 10) -> pd.Series:
    """Returns 'increasing', 'decreasing', or 'flat' based on volume slope."""
    vol_ma = df["volume"].rolling(period).mean()
    vol_ma_prev = vol_ma.shift(period)
    ratio = vol_ma / vol_ma_prev.replace(0, np.nan)

    result = pd.Series("flat", index=df.index, dtype=object)
    result[ratio > 1.1] = "increasing"
    result[ratio < 0.9] = "decreasing"
    result[vol_ma.isna() | vol_ma_prev.isna()] = "flat"
    return result


def range_tightening(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Ratio of current bar range to average range. <1 = tightening."""
    rng = df["high"] - df["low"]
    avg_rng = rng.rolling(period).mean()
    return rng / avg_rng.replace(0, np.nan)


# ---------------------------------------------------------------------------
# HVF (Harmonic Volume Factor) Indicators
# ---------------------------------------------------------------------------

def hvf_vuvuzela(df: pd.DataFrame, lookback: int = 30) -> pd.Series:
    """Detect Francis Hunt's vuvuzela pattern. Returns score 0-1."""
    vol = df["volume"]
    result = pd.Series(0.0, index=df.index)

    for i in range(lookback, len(df)):
        window = vol.iloc[i - lookback:i].values
        if len(window) < lookback:
            continue
        half = lookback // 2
        first_half = window[:half]
        second_half = window[half:]

        # Vuvuzela: volume expands in first half, contracts in second
        first_max = np.max(first_half) if len(first_half) > 0 else 0
        first_min = np.min(first_half) if len(first_half) > 0 else 0
        second_max = np.max(second_half) if len(second_half) > 0 else 0
        second_min = np.min(second_half) if len(second_half) > 0 else 0

        first_spread = first_max - first_min
        second_spread = second_max - second_min

        if first_spread > 0:
            contraction = 1.0 - (second_spread / first_spread)
            contraction = max(0.0, min(1.0, contraction))
            # Also check volume is declining overall
            first_avg = np.mean(first_half)
            second_avg = np.mean(second_half)
            vol_decline = max(0.0, min(1.0, 1.0 - second_avg / first_avg)) if first_avg > 0 else 0
            result.iloc[i] = contraction * 0.6 + vol_decline * 0.4

    return result


def volume_wedge(df: pd.DataFrame, lookback: int = 20) -> pd.Series:
    """Measures volume high/low convergence. Lower = more converged."""
    vol = df["volume"]
    vol_high = vol.rolling(lookback).max()
    vol_low = vol.rolling(lookback).min()
    vol_mid = vol.rolling(lookback).mean()
    spread = (vol_high - vol_low) / vol_mid.replace(0, np.nan)
    return spread.fillna(1.0)


# ---------------------------------------------------------------------------
# Price Channel Indicators
# ---------------------------------------------------------------------------

def donchian_channel(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Returns DataFrame with 'dc_upper', 'dc_lower', 'dc_mid'."""
    upper = df["high"].rolling(period).max()
    lower = df["low"].rolling(period).min()
    mid = (upper + lower) / 2
    return pd.DataFrame({"dc_upper": upper, "dc_lower": lower, "dc_mid": mid}, index=df.index)


def keltner_channel(df: pd.DataFrame, period: int = 20, atr_mult: float = 1.5) -> pd.DataFrame:
    """Returns DataFrame with 'kc_upper', 'kc_lower', 'kc_mid'."""
    mid = ema(df["close"], period)
    atr_ = atr(df, period)
    upper = mid + atr_mult * atr_
    lower = mid - atr_mult * atr_
    return pd.DataFrame({"kc_upper": upper, "kc_lower": lower, "kc_mid": mid}, index=df.index)


def channel_width_pct(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Donchian channel width as % of price."""
    dc = donchian_channel(df, period)
    return (dc["dc_upper"] - dc["dc_lower"]) / dc["dc_mid"] * 100


def channel_breakout(df: pd.DataFrame, period: int = 20, confirmation_candles: int = 3) -> pd.Series:
    """Detect confirmed channel breakouts. Returns 'breakout_up', 'breakout_down', or None."""
    dc = donchian_channel(df, period)
    vol = df["volume"]
    vol_avg = vol.rolling(period).mean()

    # Require 2x volume (was 1x) for breakout confirmation
    above = (df["close"] > dc["dc_upper"].shift(1)) & (vol > vol_avg * 2.0)
    below = (df["close"] < dc["dc_lower"].shift(1)) & (vol > vol_avg * 2.0)

    # Confirm: need N consecutive candles
    above_count = above.astype(int).rolling(confirmation_candles).sum()
    below_count = below.astype(int).rolling(confirmation_candles).sum()

    result = pd.Series(None, index=df.index, dtype=object)
    result[above_count >= confirmation_candles] = "breakout_up"
    result[below_count >= confirmation_candles] = "breakout_down"
    return result


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """Add all indicator columns to a copy of df."""
    df = df.copy()
    df["ema_9"] = ema(df["close"], 9)
    df["ema_21"] = ema(df["close"], 21)
    df["ema_50"] = ema(df["close"], 50)
    df["rsi_14"] = rsi(df["close"], 14)
    df["adx_14"] = adx(df, 14)
    df["atr_14"] = atr(df, 14)
    df["atr_pct"] = atr_pct(df, 14)
    df["bbw"] = bollinger_band_width(df["close"], 20)
    df["vol_sma_20"] = volume_sma(df, 20)
    df["hurst"] = hurst_exponent(df["close"])
    return df
