"""
Top Stack Combo Test: Steve Score + 2W StochRSI K cross below D

Variants:
A) Steve 3/4 fires, then 2W K crosses below D within N days = TOP
B) Steve 4/4 fires, then 2W K crosses below D within N days = TOP  
C) Steve 3/4 fires WHILE 2W K > 80, then 2W K crosses below D = TOP
D) Steve 3/4 fires, then 2W K crosses below D (any time after, no window limit)
E) 2W K > 90 at any point + Steve 3/4 at any point, then 2W K crosses below D = TOP

For each: measure timing vs actual peak, false positive rate.
ETF era, 4 paper bot coins.
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
COINS = ["ETH/USDT", "SOL/USDT", "LINK/USDT", "XRP/USDT"]
ETF_START = "2023-01-01"


def load_daily(coin):
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(
        f"SELECT * FROM candles_daily WHERE symbol='{coin}' ORDER BY timestamp", conn)
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
    typical_price = (high + low + close) / 3
    money_flow = typical_price * volume
    delta = typical_price.diff()
    pos_flow = money_flow.where(delta > 0, 0.0)
    neg_flow = money_flow.where(delta < 0, 0.0)
    pos_sum = pos_flow.rolling(period).sum()
    neg_sum = neg_flow.rolling(period).sum()
    mfi = 100 - (100 / (1 + pos_sum / neg_sum.replace(0, 1e-10)))
    return mfi


def compute_sma(series, period):
    return series.rolling(period).mean()


def resample(df, rule):
    df2 = df.set_index("date")
    ohlcv = df2[["open", "high", "low", "close", "volume"]].resample(rule).agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna()
    return ohlcv.reset_index()


def build_all_signals(coin):
    df = load_daily(coin)
    
    # 2D signals
    d2 = resample(df, "2D")
    d2["sma200"] = compute_sma(d2["close"], 200)
    d2["rsi"] = compute_rsi(d2["close"], 14)
    d2["stoch_k"], d2["stoch_d"] = compute_stochrsi(d2["close"], 14, 14, 3, 3)
    d2["mfi"] = compute_mfi(d2["high"], d2["low"], d2["close"], d2["volume"], 14)
    d2["score"] = (
        (d2["close"] > d2["sma200"]).astype(int) +
        (d2["rsi"] > 80).astype(int) +
        ((d2["stoch_k"] > 80) & (d2["stoch_d"] > 80)).astype(int) +
        (d2["mfi"] > 80).astype(int)
    )
    
    # 2W signals
    w2 = resample(df, "2W")
    w2["k"], w2["d"] = compute_stochrsi(w2["close"], 14, 14, 3, 3)
    
    # Find all 2W K cross below D events
    w2["k_cross_below_d"] = False
    for i in range(1, len(w2)):
        if w2.iloc[i]["k"] < w2.iloc[i]["d"] and w2.iloc[i-1]["k"] >= w2.iloc[i-1]["d"]:
            w2.iloc[i, w2.columns.get_loc("k_cross_below_d")] = True
    
    return d2, w2


def get_steve_clusters(d2, min_score, etf_start=ETF_START):
    d2_etf = d2[d2["date"] >= etf_start].copy()
    hits = d2_etf[d2_etf["score"] >= min_score].copy()
    if len(hits) == 0:
        return []
    hits["group"] = (hits["date"].diff() > timedelta(days=30)).cumsum()
    clusters = []
    for grp, gdf in hits.groupby("group"):
        clusters.append({
            "start": gdf["date"].iloc[0],
            "end": gdf["date"].iloc[-1],
            "max_score": gdf["score"].max(),
            "peak_close": gdf["close"].max(),
            "n_candles": len(gdf),
        })
    return clusters


def get_2w_crosses(w2, etf_start=ETF_START):
    w2_etf = w2[w2["date"] >= etf_start].copy()
    crosses = w2_etf[w2_etf["k_cross_below_d"]].copy()
    return crosses


def get_peak(d2, etf_start=ETF_START):
    d2_etf = d2[d2["date"] >= etf_start]
    peak_idx = d2_etf["close"].idxmax()
    return d2_etf.loc[peak_idx, "date"], d2_etf.loc[peak_idx, "close"]


print("TOP STACK COMBO TEST: Steve Score + 2W K Cross Below D")
print("=" * 70)
print()

all_results = {}

for coin in COINS:
    base = coin.split("/")[0]
    print(f"\n{'='*70}")
    print(f"  {base}")
    print(f"{'='*70}")
    
    d2, w2 = build_all_signals(coin)
    peak_date, peak_price = get_peak(d2)
    print(f"  Peak: {peak_date.strftime('%Y-%m-%d')} at ${peak_price:.2f}")
    
    crosses = get_2w_crosses(w2)
    w2_etf = w2[w2["date"] >= ETF_START]
    
    print(f"\n  2W K cross below D events:")
    for _, cx in crosses.iterrows():
        days = (peak_date - cx["date"]).days
        print(f"    {cx['date'].strftime('%Y-%m-%d')} K={cx['k']:.1f} D={cx['d']:.1f}  ({days:+d}d from peak)")
    
    results = {}
    
    for score_thresh in [3, 4]:
        clusters = get_steve_clusters(d2, score_thresh)
        
        # --- Variant A/B: Steve fires, then next K cross within 90 days ---
        label = f"Steve{score_thresh} then K×D (90d)"
        signals = []
        for cl in clusters:
            # Find next K cross below D after cluster end
            future_crosses = crosses[
                (crosses["date"] > cl["start"]) & 
                (crosses["date"] <= cl["end"] + timedelta(days=90))
            ]
            if len(future_crosses) > 0:
                cx = future_crosses.iloc[0]
                signals.append({
                    "date": cx["date"],
                    "steve_date": cl["start"],
                    "steve_score": cl["max_score"],
                    "price": cx["close"],
                })
        
        results[label] = signals
        print(f"\n  {label}:")
        if signals:
            for s in signals:
                days = (peak_date - s["date"]).days
                print(f"    TOP: {s['date'].strftime('%Y-%m-%d')} ${s['price']:.2f} "
                      f"(Steve {s['steve_date'].strftime('%Y-%m-%d')} score={s['steve_score']})  "
                      f"({days:+d}d from peak)")
        else:
            print(f"    No signals")
        
        # --- Variant C: Steve fires WHILE 2W K > 80, then K cross ---
        label2 = f"Steve{score_thresh} + 2W K>80, then K×D"
        signals2 = []
        for cl in clusters:
            # Check if 2W K was > 80 during the cluster
            w2_during = w2_etf[
                (w2_etf["date"] >= cl["start"] - timedelta(days=14)) & 
                (w2_etf["date"] <= cl["end"] + timedelta(days=14))
            ]
            if len(w2_during) > 0 and w2_during["k"].max() > 80:
                # Find next K cross below D
                future_crosses = crosses[crosses["date"] > cl["start"]]
                if len(future_crosses) > 0:
                    cx = future_crosses.iloc[0]
                    signals2.append({
                        "date": cx["date"],
                        "steve_date": cl["start"],
                        "steve_score": cl["max_score"],
                        "price": cx["close"],
                        "w2_k_max": w2_during["k"].max(),
                    })
        
        results[label2] = signals2
        print(f"\n  {label2}:")
        if signals2:
            for s in signals2:
                days = (peak_date - s["date"]).days
                print(f"    TOP: {s['date'].strftime('%Y-%m-%d')} ${s['price']:.2f} "
                      f"(Steve {s['steve_date'].strftime('%Y-%m-%d')} score={s['steve_score']}, 2W K max={s['w2_k_max']:.1f})  "
                      f"({days:+d}d from peak)")
        else:
            print(f"    No signals")

        # --- Variant D: Steve fires, then NEXT K cross (no time limit) ---
        label3 = f"Steve{score_thresh} then next K×D (unlimited)"
        signals3 = []
        for cl in clusters:
            future_crosses = crosses[crosses["date"] > cl["start"]]
            if len(future_crosses) > 0:
                cx = future_crosses.iloc[0]
                gap_days = (cx["date"] - cl["start"]).days
                signals3.append({
                    "date": cx["date"],
                    "steve_date": cl["start"],
                    "steve_score": cl["max_score"],
                    "price": cx["close"],
                    "gap_days": gap_days,
                })
        
        results[label3] = signals3
        print(f"\n  {label3}:")
        if signals3:
            for s in signals3:
                days = (peak_date - s["date"]).days
                print(f"    TOP: {s['date'].strftime('%Y-%m-%d')} ${s['price']:.2f} "
                      f"(Steve {s['steve_date'].strftime('%Y-%m-%d')}, gap={s['gap_days']}d)  "
                      f"({days:+d}d from peak)")
        else:
            print(f"    No signals")
    
    # --- Variant E: 2W ever hit K>90 + Steve 3 ever hit, use K cross ---
    # This is "armed" mode: once both conditions met in cycle, next K cross = top
    label_e = "Armed: 2W K>90 + Steve3 seen, then K×D"
    w2_etf_copy = w2_etf.copy()
    steve3_clusters = get_steve_clusters(d2, 3)
    
    armed = False
    armed_date = None
    saw_k90 = False
    saw_steve3 = False
    k90_first = None
    steve3_first = None
    signals_e = []
    
    for _, row in w2_etf_copy.iterrows():
        if row["k"] > 90 and not saw_k90:
            saw_k90 = True
            k90_first = row["date"]
        
        # Check if any steve3 cluster started before or on this date
        for cl in steve3_clusters:
            if cl["start"] <= row["date"] and not saw_steve3:
                saw_steve3 = True
                steve3_first = cl["start"]
        
        if saw_k90 and saw_steve3 and not armed:
            armed = True
            armed_date = max(k90_first, steve3_first)
        
        if armed and row["k_cross_below_d"]:
            signals_e.append({
                "date": row["date"],
                "price": row["close"],
                "armed_date": armed_date,
                "k90_date": k90_first,
                "steve3_date": steve3_first,
            })
            # Reset for next cycle
            armed = False
            saw_k90 = False
            saw_steve3 = False
            k90_first = None
            steve3_first = None
    
    results[label_e] = signals_e
    print(f"\n  {label_e}:")
    if signals_e:
        for s in signals_e:
            days = (peak_date - s["date"]).days
            print(f"    TOP: {s['date'].strftime('%Y-%m-%d')} ${s['price']:.2f} "
                  f"(armed {s['armed_date'].strftime('%Y-%m-%d')}, "
                  f"K>90: {s['k90_date'].strftime('%Y-%m-%d')}, "
                  f"Steve3: {s['steve3_date'].strftime('%Y-%m-%d')})  "
                  f"({days:+d}d from peak)")
    else:
        print(f"    No signals")
    
    all_results[base] = results


# ─── Summary ───
print(f"\n\n{'='*70}")
print("SUMMARY: Last signal timing vs peak + False signals")
print(f"{'='*70}")

methods = [
    "Steve3 then K×D (90d)",
    "Steve4 then K×D (90d)", 
    "Steve3 + 2W K>80, then K×D",
    "Steve4 + 2W K>80, then K×D",
    "Steve3 then next K×D (unlimited)",
    "Steve4 then next K×D (unlimited)",
    "Armed: 2W K>90 + Steve3 seen, then K×D",
]

for method in methods:
    print(f"\n  {method}:")
    total_signals = 0
    total_false = 0
    for coin in COINS:
        base = coin.split("/")[0]
        d2, w2 = build_all_signals(coin)
        peak_date, peak_price = get_peak(d2)
        d2_etf = d2[d2["date"] >= ETF_START]
        
        signals = all_results.get(base, {}).get(method, [])
        total_signals += len(signals)
        
        # Last signal
        if signals:
            last = signals[-1]
            days = (peak_date - last["date"]).days
            
            # False signal check: price rises >20% in 90d after
            false_count = 0
            for s in signals:
                future = d2_etf[(d2_etf["date"] > s["date"]) & (d2_etf["date"] <= s["date"] + timedelta(days=90))]
                if len(future) > 0:
                    price_at = d2_etf[d2_etf["date"] <= s["date"]]["close"].iloc[-1] if len(d2_etf[d2_etf["date"] <= s["date"]]) > 0 else s["price"]
                    if (future["close"].max() / price_at - 1) > 0.20:
                        false_count += 1
            total_false += false_count
            print(f"    {base:6} {len(signals)} signals, {false_count} false, last: {days:+d}d from peak")
        else:
            print(f"    {base:6} 0 signals")
    
    print(f"    TOTAL: {total_signals} signals, {total_false} false ({total_false/max(total_signals,1)*100:.0f}%)")
