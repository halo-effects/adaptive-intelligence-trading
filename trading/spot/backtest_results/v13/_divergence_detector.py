"""
Bearish Divergence Detector & Backtest

Detects: Price makes Higher High while RSI makes Lower High (classic bearish divergence)

Approach:
1. Find swing highs in price (local max over N bars each side)
2. At each swing high, record the RSI value
3. If current swing high > previous swing high in PRICE but < previous in RSI → bearish divergence
4. Test with MFI as secondary confirmation

Sweep parameters:
- Swing lookback: 5, 10, 15, 20 bars
- RSI drop threshold: 3, 5, 8, 10 points
- Max distance between swing highs: 20, 40, 60 days
- Require MFI divergence too? yes/no

Evaluate: timing vs actual top, false positive rate, coverage
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"

# ETF-era tops
TOPS = {
    "ETH": {"date": "2024-12-06", "price": 4107},
    "SOL": {"date": "2025-01-19", "price": 294},
    "BTC": {"date": "2025-01-20", "price": 109350},
    "LINK": {"date": "2024-12-08", "price": 30.8},
    "XRP": {"date": "2025-01-16", "price": 3.39},
}


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


def compute_mfi(high, low, close, volume, period=14):
    tp = (high + low + close) / 3
    rmf = tp * volume
    delta = tp.diff()
    pos_flow = rmf.where(delta > 0, 0.0)
    neg_flow = rmf.where(delta < 0, 0.0)
    pos_sum = pos_flow.rolling(period).sum()
    neg_sum = neg_flow.rolling(period).sum()
    mfi = 100 - (100 / (1 + pos_sum / neg_sum.replace(0, 1e-10)))
    return mfi


def find_swing_highs(series, lookback):
    """Find indices where value is highest within lookback bars on each side."""
    highs = []
    values = series if isinstance(series, np.ndarray) else series.values
    for i in range(lookback, len(values) - lookback):
        window = values[i - lookback:i + lookback + 1]
        if values[i] == np.max(window):
            highs.append(i)
    return highs


def detect_bearish_divergence(df, swing_lb, rsi_drop, max_dist, require_mfi=False):
    """
    Detect bearish divergence signals.
    Returns list of (date, price, rsi, prev_price, prev_rsi, mfi_div) tuples.
    """
    df = df.copy()
    df["rsi"] = compute_rsi(df["close"], 14)
    df["mfi"] = compute_mfi(df["high"], df["low"], df["close"], df["volume"], 14)
    
    # Find swing highs in price
    swing_idxs = find_swing_highs(df["high"].values, swing_lb)
    
    signals = []
    for i in range(1, len(swing_idxs)):
        curr_idx = swing_idxs[i]
        prev_idx = swing_idxs[i - 1]
        
        # Distance check
        days_apart = (df.iloc[curr_idx]["date"] - df.iloc[prev_idx]["date"]).days
        if days_apart > max_dist or days_apart < 5:
            continue
        
        curr_price = df.iloc[curr_idx]["high"]
        prev_price = df.iloc[prev_idx]["high"]
        curr_rsi = df.iloc[curr_idx]["rsi"]
        prev_rsi = df.iloc[prev_idx]["rsi"]
        curr_mfi = df.iloc[curr_idx]["mfi"]
        prev_mfi = df.iloc[prev_idx]["mfi"]
        
        # Price HH + RSI LH
        if curr_price > prev_price and (prev_rsi - curr_rsi) >= rsi_drop:
            mfi_div = curr_mfi < prev_mfi - 3  # MFI also diverging
            if require_mfi and not mfi_div:
                continue
            signals.append({
                "date": df.iloc[curr_idx]["date"],
                "price": curr_price,
                "rsi": curr_rsi,
                "prev_date": df.iloc[prev_idx]["date"],
                "prev_price": prev_price,
                "prev_rsi": prev_rsi,
                "rsi_drop": prev_rsi - curr_rsi,
                "mfi_div": mfi_div,
                "days_apart": days_apart,
            })
    
    return signals


def classify_signal(sig_date, top_date, top_price, price_at_signal):
    """Classify a divergence signal relative to the actual top."""
    days_to_top = (top_date - sig_date).days
    if -7 <= days_to_top <= 60:
        # Signal fired within 60 days before top or 7 days after
        return "TRUE", days_to_top
    elif days_to_top < -7:
        # Signal fired after the top (too late)
        return "LATE", days_to_top
    else:
        # Signal fired way too early
        return "FALSE", days_to_top


# ============================================================
# PARAMETER SWEEP
# ============================================================
print("=" * 90)
print("BEARISH DIVERGENCE DETECTOR — Parameter Sweep")
print("=" * 90)

# ETF era filter: Jan 2023+
ETF_START = pd.Timestamp("2023-01-01")

configs = [
    # swing_lb, rsi_drop, max_dist, require_mfi
    (5,  5,  40, False),
    (5,  5,  60, False),
    (10, 5,  40, False),
    (10, 5,  60, False),
    (10, 8,  40, False),
    (10, 8,  60, False),
    (15, 5,  60, False),
    (15, 8,  60, False),
    (20, 5,  60, False),
    (10, 5,  60, True),   # with MFI requirement
    (15, 5,  60, True),
]

best_config = None
best_score = -999

for swing_lb, rsi_drop, max_dist, req_mfi in configs:
    total_true = 0
    total_false = 0
    total_late = 0
    coins_caught = 0
    total_signals = 0
    timing_sum = 0
    
    for coin, top_info in TOPS.items():
        symbol = f"{coin}/USDT"
        df = load_daily(symbol)
        df = df[df["date"] >= ETF_START].reset_index(drop=True)
        top_date = pd.Timestamp(top_info["date"])
        
        signals = detect_bearish_divergence(df, swing_lb, rsi_drop, max_dist, req_mfi)
        total_signals += len(signals)
        
        caught = False
        for sig in signals:
            cls, days = classify_signal(sig["date"], top_date, top_info["price"], sig["price"])
            if cls == "TRUE":
                total_true += 1
                timing_sum += days
                caught = True
            elif cls == "FALSE":
                total_false += 1
            elif cls == "LATE":
                total_late += 1
        
        if caught:
            coins_caught += 1
    
    false_rate = total_false / total_signals * 100 if total_signals > 0 else 0
    avg_timing = timing_sum / total_true if total_true > 0 else 0
    
    # Score: coverage (coins caught) - false rate penalty
    score = coins_caught * 20 - false_rate
    
    mfi_str = "+MFI" if req_mfi else "    "
    print(f"  swing={swing_lb:2d} rsi_drop={rsi_drop} dist={max_dist:2d} {mfi_str} | "
          f"caught={coins_caught}/5 true={total_true} false={total_false} late={total_late} "
          f"total={total_signals} false_rate={false_rate:.0f}% avg_timing={avg_timing:.0f}d | score={score:.0f}")
    
    if score > best_score:
        best_score = score
        best_config = (swing_lb, rsi_drop, max_dist, req_mfi)

print(f"\nBest config: swing={best_config[0]}, rsi_drop={best_config[1]}, "
      f"max_dist={best_config[2]}, require_mfi={best_config[3]}")

# ============================================================
# DETAILED OUTPUT FOR BEST CONFIG
# ============================================================
swing_lb, rsi_drop, max_dist, req_mfi = best_config
print(f"\n{'='*90}")
print(f"DETAILED SIGNALS — swing={swing_lb}, rsi_drop>={rsi_drop}, max_dist={max_dist}, mfi={req_mfi}")
print(f"{'='*90}")

for coin, top_info in TOPS.items():
    symbol = f"{coin}/USDT"
    df = load_daily(symbol)
    df = df[df["date"] >= ETF_START].reset_index(drop=True)
    top_date = pd.Timestamp(top_info["date"])
    
    signals = detect_bearish_divergence(df, swing_lb, rsi_drop, max_dist, req_mfi)
    
    print(f"\n  {coin} (top: {top_info['date']} @ ${top_info['price']:,})")
    print(f"  {'─'*70}")
    
    if not signals:
        print(f"    No signals detected")
        continue
    
    for sig in signals:
        cls, days = classify_signal(sig["date"], top_date, top_info["price"], sig["price"])
        marker = ">>TRUE<<" if cls == "TRUE" else f"  {cls}  "
        print(f"    {marker} {sig['date'].strftime('%Y-%m-%d')} "
              f"price=${sig['price']:,.1f} RSI={sig['rsi']:.1f} "
              f"(prev: {sig['prev_date'].strftime('%Y-%m-%d')} "
              f"${sig['prev_price']:,.1f} RSI={sig['prev_rsi']:.1f}) "
              f"drop={sig['rsi_drop']:.1f} MFI_div={sig['mfi_div']} "
              f"gap={sig['days_apart']}d  [{days:+d}d to top]")
