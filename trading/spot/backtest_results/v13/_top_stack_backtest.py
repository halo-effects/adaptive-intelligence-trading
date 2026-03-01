"""
Steve Top Conviction Stack Backtest
Compare current 2W OB93 top detection vs Steve convergence stack.

Top stack (2D chart):
  1. Above SMA200
  2. RSI(14) > 80
  3. StochRSI(14,14,3,3) K&D > 80
  4. MFI(14) > 80
  5. 2W StochRSI exhaustion (K>93 for 2+ candles, then K crosses below D)

Test: use each method as bear-ON signal in V13 engine, measure portfolio impact.
ETF era only (Jan 2023+), 4 paper bot coins (ETH, SOL, LINK, XRP).
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


# ─── Build signals for each coin ───

def build_2d_signals(coin):
    """Build 2D Steve top stack signals."""
    df = load_daily(coin)
    d2 = resample(df, "2D")
    d2["sma200"] = compute_sma(d2["close"], 200)
    d2["rsi"] = compute_rsi(d2["close"], 14)
    d2["stoch_k"], d2["stoch_d"] = compute_stochrsi(d2["close"], 14, 14, 3, 3)
    d2["mfi"] = compute_mfi(d2["high"], d2["low"], d2["close"], d2["volume"], 14)

    d2["above_sma200"] = (d2["close"] > d2["sma200"]).astype(int)
    d2["rsi_ob"] = (d2["rsi"] > 80).astype(int)
    d2["stoch_ob"] = ((d2["stoch_k"] > 80) & (d2["stoch_d"] > 80)).astype(int)
    d2["mfi_ob"] = (d2["mfi"] > 80).astype(int)
    d2["score"] = d2["above_sma200"] + d2["rsi_ob"] + d2["stoch_ob"] + d2["mfi_ob"]
    return d2


def build_2w_signals(coin):
    """Build 2W StochRSI exhaustion signals."""
    df = load_daily(coin)
    w2 = resample(df, "2W")
    w2["k"], w2["d"] = compute_stochrsi(w2["close"], 14, 14, 3, 3)
    return w2


def find_2w_exhaustion_tops(w2, ob_thresh=93, min_candles=2):
    """Find dates where 2W StochRSI was pinned above threshold for min_candles,
    then K crossed below D."""
    signals = []
    ob = w2["k"] > ob_thresh
    groups = []
    in_group = False
    start_idx = None
    for i in range(len(w2)):
        if ob.iloc[i] and not in_group:
            in_group = True
            start_idx = i
        elif not ob.iloc[i] and in_group:
            in_group = False
            groups.append((start_idx, i - 1))
    if in_group:
        groups.append((start_idx, len(w2) - 1))

    for start_i, end_i in groups:
        n_candles = end_i - start_i + 1
        if n_candles < min_candles:
            continue
        # Find K cross below D after
        for j in range(end_i + 1, min(end_i + 20, len(w2))):
            if w2.iloc[j]["k"] < w2.iloc[j]["d"]:
                if j == 0 or w2.iloc[j-1]["k"] >= w2.iloc[j-1]["d"]:
                    signals.append({
                        "date": w2.iloc[j]["date"],
                        "ob_start": w2.iloc[start_i]["date"],
                        "ob_candles": n_candles,
                        "peak_price": w2.iloc[start_i:end_i+1]["close"].max(),
                    })
                    break
    return signals


def find_current_ob93_tops(w2):
    """Our current method: first candle K > 93."""
    signals = []
    for i in range(len(w2)):
        if w2.iloc[i]["k"] > 93:
            # Only if previous wasn't also >93 (first touch)
            if i == 0 or w2.iloc[i-1]["k"] <= 93:
                signals.append({"date": w2.iloc[i]["date"], "k": w2.iloc[i]["k"]})
    return signals


# ─── Main analysis ───

print("TOP CONVICTION STACK BACKTEST")
print("=" * 70)
print("ETF era (Jan 2023+), 4 paper bot coins")
print()

# Method 1: Current 2W OB93 (first touch)
# Method 2: 2W OB93 exhaustion (2+ candles pinned, then K x D)
# Method 3: Steve 2D score >= 3 (first candle hitting 3)
# Method 4: Steve 2D score >= 4 (first candle hitting 4)
# Method 5: Steve 2D score >= 3 + 2W exhaustion (both must fire)
# Method 6: Steve 2D score >= 3 OR 2W exhaustion

for coin in COINS:
    base = coin.split("/")[0]
    print(f"\n{'='*70}")
    print(f"  {base}")
    print(f"{'='*70}")

    d2 = build_2d_signals(coin)
    w2 = build_2w_signals(coin)

    # Filter to ETF era
    d2_etf = d2[d2["date"] >= ETF_START].copy()
    w2_etf = w2[w2["date"] >= ETF_START].copy()

    # Find the actual price peak in ETF era
    peak_idx = d2_etf["close"].idxmax()
    peak_date = d2_etf.loc[peak_idx, "date"]
    peak_price = d2_etf.loc[peak_idx, "close"]
    print(f"  Actual ETF-era peak: {peak_date.strftime('%Y-%m-%d')} at ${peak_price:.2f}")
    print()

    # Method 1: Current 2W OB93 first touch
    ob93_signals = find_current_ob93_tops(w2_etf)
    print(f"  Method 1: Current 2W OB93 (first K>93)")
    if ob93_signals:
        for s in ob93_signals:
            days_to_peak = (peak_date - s["date"]).days
            print(f"    {s['date'].strftime('%Y-%m-%d')} K={s['k']:.1f}  ({days_to_peak:+d}d from peak)")
    else:
        print(f"    No signals")

    # Method 2: 2W exhaustion (2+ candles >93, then K x D)
    exh_signals = find_2w_exhaustion_tops(w2_etf, ob_thresh=93, min_candles=2)
    print(f"\n  Method 2: 2W Exhaustion (K>93 for 2+ candles, then K cross D)")
    if exh_signals:
        for s in exh_signals:
            days_to_peak = (peak_date - s["date"]).days
            print(f"    {s['date'].strftime('%Y-%m-%d')} (OB {s['ob_candles']} candles from {s['ob_start'].strftime('%Y-%m-%d')})  ({days_to_peak:+d}d from peak)")
    else:
        print(f"    No signals")

    # Also test 1+ candle exhaustion for comparison
    exh1_signals = find_2w_exhaustion_tops(w2_etf, ob_thresh=93, min_candles=1)
    print(f"\n  Method 2b: 2W Exhaustion (K>93 for 1+ candle, then K cross D)")
    if exh1_signals:
        for s in exh1_signals:
            days_to_peak = (peak_date - s["date"]).days
            print(f"    {s['date'].strftime('%Y-%m-%d')} (OB {s['ob_candles']} candles from {s['ob_start'].strftime('%Y-%m-%d')})  ({days_to_peak:+d}d from peak)")
    else:
        print(f"    No signals")

    # Method 3: Steve 2D score >= 3 (first candle)
    print(f"\n  Method 3: Steve 2D Score >= 3 (first candle in each cluster)")
    score3 = d2_etf[d2_etf["score"] >= 3].copy()
    if len(score3) > 0:
        score3["group"] = (score3["date"].diff() > timedelta(days=30)).cumsum()
        for grp, gdf in score3.groupby("group"):
            first = gdf.iloc[0]
            days_to_peak = (peak_date - first["date"]).days
            max_score = gdf["score"].max()
            print(f"    {first['date'].strftime('%Y-%m-%d')} Score={first['score']:.0f} (max {max_score:.0f} over {len(gdf)} candles)  ({days_to_peak:+d}d from peak)")
    else:
        print(f"    No signals")

    # Method 4: Steve 2D score >= 4
    print(f"\n  Method 4: Steve 2D Score >= 4 (first candle in each cluster)")
    score4 = d2_etf[d2_etf["score"] >= 4].copy()
    if len(score4) > 0:
        score4["group"] = (score4["date"].diff() > timedelta(days=30)).cumsum()
        for grp, gdf in score4.groupby("group"):
            first = gdf.iloc[0]
            days_to_peak = (peak_date - first["date"]).days
            max_score = gdf["score"].max()
            print(f"    {first['date'].strftime('%Y-%m-%d')} Score={first['score']:.0f} (max {max_score:.0f} over {len(gdf)} candles)  ({days_to_peak:+d}d from peak)")
    else:
        print(f"    No signals")

    # Method 5: Steve score >= 3 within 60 days of 2W exhaustion cross
    print(f"\n  Method 5: Steve 2D >= 3 + 2W Exhaustion (both within 60 days)")
    if exh1_signals and len(score3) > 0:
        for exh in exh1_signals:
            # Find any score >= 3 within 60 days before the exhaustion cross
            nearby = score3[(score3["date"] >= exh["date"] - timedelta(days=90)) &
                           (score3["date"] <= exh["date"] + timedelta(days=30))]
            if len(nearby) > 0:
                first_score = nearby.iloc[0]
                days_to_peak = (peak_date - exh["date"]).days
                print(f"    Exhaustion: {exh['date'].strftime('%Y-%m-%d')}, "
                      f"Score3: {first_score['date'].strftime('%Y-%m-%d')} (score={first_score['score']:.0f})  "
                      f"({days_to_peak:+d}d from peak)")
            else:
                print(f"    Exhaustion: {exh['date'].strftime('%Y-%m-%d')} — no score>=3 nearby")
    else:
        print(f"    Insufficient signals")


# ─── Timing comparison summary ───

print(f"\n\n{'='*70}")
print("TIMING SUMMARY: Days before/after actual peak")
print("(Negative = before peak = early, Positive = after peak = late)")
print(f"{'='*70}")
print(f"\n  {'Coin':6} {'Peak Date':12} {'Peak$':>10} | {'OB93 1st':>10} {'Exh 2+':>10} {'Steve3':>10} {'Steve4':>10}")
print(f"  {'-'*72}")

for coin in COINS:
    base = coin.split("/")[0]
    d2 = build_2d_signals(coin)
    w2 = build_2w_signals(coin)
    d2_etf = d2[d2["date"] >= ETF_START].copy()
    w2_etf = w2[w2["date"] >= ETF_START].copy()

    peak_idx = d2_etf["close"].idxmax()
    peak_date = d2_etf.loc[peak_idx, "date"]
    peak_price = d2_etf.loc[peak_idx, "close"]

    # Find LAST signal before peak for each method (most relevant top call)
    # OB93 first touches
    ob93 = find_current_ob93_tops(w2_etf)
    ob93_before = [s for s in ob93 if s["date"] <= peak_date + timedelta(days=60)]
    ob93_str = f"{(peak_date - ob93_before[-1]['date']).days:+d}d" if ob93_before else "none"

    # Exhaustion
    exh = find_2w_exhaustion_tops(w2_etf, 93, 2)
    exh_before = [s for s in exh if s["date"] <= peak_date + timedelta(days=90)]
    exh_str = f"{(peak_date - exh_before[-1]['date']).days:+d}d" if exh_before else "none"

    # Steve 3
    score3 = d2_etf[d2_etf["score"] >= 3].copy()
    s3_before = score3[score3["date"] <= peak_date + timedelta(days=60)]
    if len(s3_before) > 0:
        # Last cluster's first candle
        s3_before_g = s3_before.copy()
        s3_before_g["group"] = (s3_before_g["date"].diff() > timedelta(days=30)).cumsum()
        last_grp = s3_before_g.groupby("group").first().iloc[-1]
        s3_str = f"{(peak_date - last_grp['date']).days:+d}d"
    else:
        s3_str = "none"

    # Steve 4
    score4 = d2_etf[d2_etf["score"] >= 4].copy()
    s4_before = score4[score4["date"] <= peak_date + timedelta(days=60)]
    if len(s4_before) > 0:
        s4_before_g = s4_before.copy()
        s4_before_g["group"] = (s4_before_g["date"].diff() > timedelta(days=30)).cumsum()
        last_grp = s4_before_g.groupby("group").first().iloc[-1]
        s4_str = f"{(peak_date - last_grp['date']).days:+d}d"
    else:
        s4_str = "none"

    print(f"  {base:6} {peak_date.strftime('%Y-%m-%d'):12} {peak_price:10.2f} | {ob93_str:>10} {exh_str:>10} {s3_str:>10} {s4_str:>10}")


# ─── False signal analysis ───

print(f"\n\n{'='*70}")
print("FALSE SIGNAL ANALYSIS")
print("Signal fires but price keeps rising >20% after")
print(f"{'='*70}")

for coin in COINS:
    base = coin.split("/")[0]
    d2 = build_2d_signals(coin)
    w2 = build_2w_signals(coin)
    d2_etf = d2[d2["date"] >= ETF_START].copy()
    w2_etf = w2[w2["date"] >= ETF_START].copy()

    print(f"\n  {base}:")

    # OB93 false signals
    ob93 = find_current_ob93_tops(w2_etf)
    false_ob93 = 0
    for s in ob93:
        # Check if price rose >20% in next 90 days
        future = d2_etf[(d2_etf["date"] > s["date"]) & (d2_etf["date"] <= s["date"] + timedelta(days=90))]
        if len(future) > 0:
            price_at_signal = d2_etf[d2_etf["date"] <= s["date"]]["close"].iloc[-1] if len(d2_etf[d2_etf["date"] <= s["date"]]) > 0 else 0
            max_future = future["close"].max()
            if price_at_signal > 0 and (max_future / price_at_signal - 1) > 0.20:
                false_ob93 += 1
    print(f"    OB93:     {len(ob93)} signals, {false_ob93} false (price rose >20% after)")

    # Exhaustion false signals
    exh = find_2w_exhaustion_tops(w2_etf, 93, 1)
    false_exh = 0
    for s in exh:
        future = d2_etf[(d2_etf["date"] > s["date"]) & (d2_etf["date"] <= s["date"] + timedelta(days=90))]
        if len(future) > 0:
            price_at_signal = d2_etf[d2_etf["date"] <= s["date"]]["close"].iloc[-1] if len(d2_etf[d2_etf["date"] <= s["date"]]) > 0 else 0
            max_future = future["close"].max()
            if price_at_signal > 0 and (max_future / price_at_signal - 1) > 0.20:
                false_exh += 1
    print(f"    Exh 1+:   {len(exh)} signals, {false_exh} false")

    exh2 = find_2w_exhaustion_tops(w2_etf, 93, 2)
    false_exh2 = 0
    for s in exh2:
        future = d2_etf[(d2_etf["date"] > s["date"]) & (d2_etf["date"] <= s["date"] + timedelta(days=90))]
        if len(future) > 0:
            price_at_signal = d2_etf[d2_etf["date"] <= s["date"]]["close"].iloc[-1] if len(d2_etf[d2_etf["date"] <= s["date"]]) > 0 else 0
            max_future = future["close"].max()
            if price_at_signal > 0 and (max_future / price_at_signal - 1) > 0.20:
                false_exh2 += 1
    print(f"    Exh 2+:   {len(exh2)} signals, {false_exh2} false")

    # Steve score 3 false
    score3 = d2_etf[d2_etf["score"] >= 3].copy()
    if len(score3) > 0:
        score3["group"] = (score3["date"].diff() > timedelta(days=30)).cumsum()
        clusters = score3.groupby("group").first()
        false_s3 = 0
        for _, cl in clusters.iterrows():
            future = d2_etf[(d2_etf["date"] > cl["date"]) & (d2_etf["date"] <= cl["date"] + timedelta(days=90))]
            if len(future) > 0:
                max_future = future["close"].max()
                if (max_future / cl["close"] - 1) > 0.20:
                    false_s3 += 1
        print(f"    Steve 3:  {len(clusters)} clusters, {false_s3} false")
    else:
        print(f"    Steve 3:  0 clusters")

    score4 = d2_etf[d2_etf["score"] >= 4].copy()
    if len(score4) > 0:
        score4["group"] = (score4["date"].diff() > timedelta(days=30)).cumsum()
        clusters = score4.groupby("group").first()
        false_s4 = 0
        for _, cl in clusters.iterrows():
            future = d2_etf[(d2_etf["date"] > cl["date"]) & (d2_etf["date"] <= cl["date"] + timedelta(days=90))]
            if len(future) > 0:
                max_future = future["close"].max()
                if (max_future / cl["close"] - 1) > 0.20:
                    false_s4 += 1
        print(f"    Steve 4:  {len(clusters)} clusters, {false_s4} false")
    else:
        print(f"    Steve 4:  0 clusters")
