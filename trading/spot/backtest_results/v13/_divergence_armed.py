"""
Armed Divergence Detector — OB93 arms, divergence confirms

Tests:
1. 2W StochRSI OB93 arms the system (must have been >93 at some point)
2. Daily RSI divergence fires the top signal
3. Also test 2D RSI divergence (Brett wants to see what's on 2W/2D charts)
4. Combine: armed + 2D divergence

The arm resets when 2W StochRSI drops below a threshold (e.g., <50 = no longer overbought cycle)
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"

TOPS = {
    "ETH": {"date": "2024-12-06", "price": 4107},
    "SOL": {"date": "2025-01-19", "price": 294},
    "BTC": {"date": "2025-01-20", "price": 109350},
    "LINK": {"date": "2024-12-08", "price": 30.8},
    "XRP": {"date": "2025-01-16", "price": 3.39},
}
ETF_START = pd.Timestamp("2023-01-01")


def load_daily(symbol):
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(
        f"SELECT * FROM candles_daily WHERE symbol='{symbol}' ORDER BY timestamp", conn)
    conn.close()
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_stochrsi(close, rsi_period=14, stoch_period=14, k_smooth=3, d_smooth=3):
    rsi = compute_rsi(close, rsi_period)
    min_rsi = rsi.rolling(stoch_period).min()
    max_rsi = rsi.rolling(stoch_period).max()
    stoch_rsi = (rsi - min_rsi) / (max_rsi - min_rsi) * 100
    k = stoch_rsi.rolling(k_smooth).mean()
    d = k.rolling(d_smooth).mean()
    return k, d


def compute_mfi(high, low, close, volume, period=14):
    tp = (high + low + close) / 3
    rmf = tp * volume
    delta = tp.diff()
    pos_flow = rmf.where(delta > 0, 0.0)
    neg_flow = rmf.where(delta < 0, 0.0)
    pos_sum = pos_flow.rolling(period).sum()
    neg_sum = neg_flow.rolling(period).sum()
    return 100 - (100 / (1 + pos_sum / neg_sum.replace(0, 1e-10)))


def resample(df, rule):
    df2 = df.set_index("date")
    ohlcv = df2[["open", "high", "low", "close", "volume"]].resample(rule).agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna()
    return ohlcv.reset_index()


def get_2w_armed_dates(df_daily, ob_threshold=93, disarm_threshold=50):
    """
    Returns a set of dates where the system is "armed" by 2W StochRSI having been > ob_threshold.
    Armed = True once 2W K > ob_threshold, stays True until 2W K < disarm_threshold.
    Maps 2W candle dates back to daily dates.
    """
    df_2w = resample(df_daily.set_index("date").reset_index(), "2W")
    k_2w, d_2w = compute_stochrsi(df_2w["close"])
    df_2w["k"] = k_2w
    
    armed = False
    armed_periods = []  # (start_date, end_date) tuples
    arm_start = None
    
    for i, row in df_2w.iterrows():
        if pd.isna(row["k"]):
            continue
        if not armed and row["k"] > ob_threshold:
            armed = True
            arm_start = row["date"]
        elif armed and row["k"] < disarm_threshold:
            armed = False
            armed_periods.append((arm_start, row["date"]))
            arm_start = None
    
    # If still armed at end
    if armed and arm_start is not None:
        armed_periods.append((arm_start, df_2w["date"].max() + timedelta(days=30)))
    
    # Convert to set of daily dates that fall within armed periods
    armed_dates = set()
    for start, end in armed_periods:
        mask = (df_daily["date"] >= start) & (df_daily["date"] <= end)
        armed_dates.update(df_daily[mask]["date"].tolist())
    
    return armed_dates, armed_periods


def detect_divergence_daily(df, lookback=60, rsi_gap=8, price_pct=2.0, min_rsi=60):
    """Daily RSI divergence detection (best config from v2/v3)."""
    df = df.copy()
    df["rsi"] = compute_rsi(df["close"], 14)
    df["price_high_N"] = df["high"].rolling(lookback).max()
    df["rsi_high_N"] = df["rsi"].rolling(lookback).max()
    
    df["signal"] = (
        (df["high"] >= df["price_high_N"] * (1 - price_pct / 100)) &
        ((df["rsi_high_N"] - df["rsi"]) >= rsi_gap) &
        (df["rsi"] >= min_rsi) &
        (df["rsi_high_N"] > 75)  # RSI peak > 75 gate
    )
    return df


def detect_divergence_2d(df_daily, lookback=30, rsi_gap=8, price_pct=3.0, min_rsi=60):
    """2D RSI divergence detection."""
    df_2d = resample(df_daily, "2D")
    df_2d["rsi"] = compute_rsi(df_2d["close"], 14)
    df_2d["mfi"] = compute_mfi(df_2d["high"], df_2d["low"], df_2d["close"], df_2d["volume"], 14)
    df_2d["price_high_N"] = df_2d["high"].rolling(lookback).max()
    df_2d["rsi_high_N"] = df_2d["rsi"].rolling(lookback).max()
    df_2d["mfi_high_N"] = df_2d["mfi"].rolling(lookback).max()
    
    df_2d["signal"] = (
        (df_2d["high"] >= df_2d["price_high_N"] * (1 - price_pct / 100)) &
        ((df_2d["rsi_high_N"] - df_2d["rsi"]) >= rsi_gap) &
        (df_2d["rsi"] >= min_rsi) &
        (df_2d["rsi_high_N"] > 75)
    )
    return df_2d


def cluster_signals(dates, min_gap=10):
    """Take a list of dates and cluster them, returning first in each cluster."""
    if not dates:
        return []
    dates = sorted(dates)
    clusters = [dates[0]]
    for d in dates[1:]:
        if (d - clusters[-1]).days >= min_gap:
            clusters.append(d)
    return clusters


def classify(sig_date, top_date):
    days = (top_date - sig_date).days
    if -14 <= days <= 60:
        return "TRUE", days
    elif days < -14:
        return "LATE", days
    else:
        return "FALSE", days


def run_test(name, get_signal_dates_fn):
    """Run a test across all coins and return results."""
    total_true = 0
    total_false = 0
    total_late = 0
    coins_caught = set()
    timing_list = []
    details = {}
    
    for coin, top_info in TOPS.items():
        symbol = f"{coin}/USDT"
        df = load_daily(symbol)
        top_date = pd.Timestamp(top_info["date"])
        
        signal_dates = get_signal_dates_fn(df, coin)
        clustered = cluster_signals(signal_dates)
        
        # Filter to ETF era
        clustered = [d for d in clustered if d >= ETF_START]
        
        coin_results = []
        for sig_date in clustered:
            cls, days = classify(sig_date, top_date)
            coin_results.append((sig_date, cls, days))
            if cls == "TRUE":
                total_true += 1
                coins_caught.add(coin)
                timing_list.append(days)
            elif cls == "FALSE":
                total_false += 1
            else:
                total_late += 1
        
        details[coin] = coin_results
    
    total = total_true + total_false + total_late
    false_rate = total_false / total * 100 if total > 0 else 0
    avg_timing = sum(timing_list) / len(timing_list) if timing_list else 0
    
    return {
        "name": name,
        "caught": len(coins_caught),
        "coins": coins_caught,
        "true": total_true, "false": total_false, "late": total_late,
        "total": total, "false_rate": false_rate, "avg_timing": avg_timing,
        "details": details,
    }


# ============================================================
# Define test variants
# ============================================================

def make_daily_div(df, coin):
    """Daily divergence only (baseline)."""
    result = detect_divergence_daily(df)
    return list(result[result["signal"]]["date"])

def make_daily_armed(df, coin):
    """Daily divergence + OB93 armed."""
    armed_dates, _ = get_2w_armed_dates(df)
    result = detect_divergence_daily(df)
    dates = result[result["signal"]]["date"]
    return [d for d in dates if d in armed_dates]

def make_2d_div(df, coin):
    """2D divergence only."""
    result = detect_divergence_2d(df)
    return list(result[result["signal"]]["date"])

def make_2d_armed(df, coin):
    """2D divergence + OB93 armed."""
    armed_dates, _ = get_2w_armed_dates(df)
    result = detect_divergence_2d(df)
    dates = result[result["signal"]]["date"]
    return [d for d in dates if d in armed_dates]

def make_daily_or_2d_armed(df, coin):
    """Either daily OR 2D divergence, both requiring OB93 armed."""
    armed_dates, _ = get_2w_armed_dates(df)
    d1 = detect_divergence_daily(df)
    d2 = detect_divergence_2d(df)
    daily_dates = set(d1[d1["signal"]]["date"])
    two_d_dates = set(d2[d2["signal"]]["date"])
    all_dates = daily_dates | two_d_dates
    return [d for d in all_dates if d in armed_dates]

def make_daily_armed_lower(df, coin):
    """Daily divergence + OB80 armed (lower threshold)."""
    armed_dates, _ = get_2w_armed_dates(df, ob_threshold=80, disarm_threshold=40)
    result = detect_divergence_daily(df)
    dates = result[result["signal"]]["date"]
    return [d for d in dates if d in armed_dates]

def make_2d_armed_lower(df, coin):
    """2D divergence + OB80 armed."""
    armed_dates, _ = get_2w_armed_dates(df, ob_threshold=80, disarm_threshold=40)
    result = detect_divergence_2d(df)
    dates = result[result["signal"]]["date"]
    return [d for d in dates if d in armed_dates]


# ============================================================
# Run all tests
# ============================================================
print("=" * 100)
print("ARMED DIVERGENCE DETECTOR — Combo Tests")
print("=" * 100)

tests = [
    ("Daily div (baseline)", make_daily_div),
    ("Daily div + OB93 armed", make_daily_armed),
    ("Daily div + OB80 armed", make_daily_armed_lower),
    ("2D div only", make_2d_div),
    ("2D div + OB93 armed", make_2d_armed),
    ("2D div + OB80 armed", make_2d_armed_lower),
    ("Daily|2D + OB93 armed", make_daily_or_2d_armed),
]

print(f"\n{'Test':>30s} | caught | true | false | late | total | false% | timing")
print("-" * 100)

all_results = []
for name, fn in tests:
    r = run_test(name, fn)
    all_results.append(r)
    missing = set(TOPS.keys()) - r["coins"]
    miss_str = f"  MISS: {','.join(sorted(missing))}" if missing else ""
    print(f"  {name:>28s} | {r['caught']}/5  | {r['true']:3d}  | {r['false']:3d}   | {r['late']:3d}  | "
          f"{r['total']:3d}   | {r['false_rate']:4.0f}%  | {r['avg_timing']:4.0f}d{miss_str}")

# ============================================================
# Detail for best options
# ============================================================
for r in all_results:
    if r["caught"] >= 4:
        print(f"\n{'='*80}")
        print(f"DETAIL: {r['name']} — {r['caught']}/5 caught, {r['false_rate']:.0f}% false, {r['avg_timing']:.0f}d timing")
        print(f"{'='*80}")
        for coin, sigs in r["details"].items():
            top_info = TOPS[coin]
            caught_str = " [CAUGHT]" if coin in r["coins"] else " [MISSED]"
            print(f"\n  {coin} (top: {top_info['date']}){caught_str}")
            if not sigs:
                print(f"    No signals")
            for sig_date, cls, days in sigs:
                marker = ">>TRUE<<" if cls == "TRUE" else f"  {cls:6s}"
                print(f"    {marker} {sig_date.strftime('%Y-%m-%d')} [{days:+d}d to top]")

# ============================================================
# Show 2W armed periods for context
# ============================================================
print(f"\n{'='*80}")
print("2W StochRSI ARMED PERIODS (OB93)")
print(f"{'='*80}")
for coin in TOPS:
    symbol = f"{coin}/USDT"
    df = load_daily(symbol)
    _, periods = get_2w_armed_dates(df, ob_threshold=93)
    print(f"\n  {coin}:")
    if not periods:
        print(f"    No OB93 periods found")
    for start, end in periods:
        print(f"    Armed: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")

print(f"\n{'='*80}")
print("2W StochRSI ARMED PERIODS (OB80)")
print(f"{'='*80}")
for coin in TOPS:
    symbol = f"{coin}/USDT"
    df = load_daily(symbol)
    _, periods = get_2w_armed_dates(df, ob_threshold=80, disarm_threshold=40)
    print(f"\n  {coin}:")
    if not periods:
        print(f"    No OB80 periods found")
    for start, end in periods:
        print(f"    Armed: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
