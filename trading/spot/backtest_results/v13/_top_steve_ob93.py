"""
Steve Top Stack + OB93 Combo Test

Variants:
1. Current OB93 alone (baseline)
2. Steve 3/4 alone (baseline)
3. Steve 3 + OB93 active (2W K>93 within 28 days of Steve cluster)
4. Steve 4 + OB93 active
5. Steve 3 fires DURING 2W OB93 period (same 2W candle window)
6. Steve 3 + OB93 → then K×D crossover confirms
7. Steve 4 + OB93 → then K×D crossover confirms

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


def build_signals(coin):
    df = load_daily(coin)
    
    # 2D
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
    
    # 2W
    w2 = resample(df, "2W")
    w2["k"], w2["d"] = compute_stochrsi(w2["close"], 14, 14, 3, 3)
    
    return d2, w2


def get_peak(d2):
    d2_etf = d2[d2["date"] >= ETF_START]
    idx = d2_etf["close"].idxmax()
    return d2_etf.loc[idx, "date"], d2_etf.loc[idx, "close"]


def steve_clusters(d2, min_score):
    d2_etf = d2[d2["date"] >= ETF_START].copy()
    hits = d2_etf[d2_etf["score"] >= min_score].copy()
    if len(hits) == 0:
        return []
    hits["group"] = (hits["date"].diff() > timedelta(days=30)).cumsum()
    clusters = []
    for _, gdf in hits.groupby("group"):
        clusters.append({
            "start": gdf["date"].iloc[0],
            "end": gdf["date"].iloc[-1],
            "max_score": gdf["score"].max(),
            "peak_close": gdf["close"].max(),
        })
    return clusters


def ob93_periods(w2):
    """Return list of (start_date, end_date) where K>93."""
    w2_etf = w2[w2["date"] >= ETF_START].copy()
    periods = []
    in_ob = False
    start = None
    for i, row in w2_etf.iterrows():
        if row["k"] > 93 and not in_ob:
            in_ob = True
            start = row["date"]
        elif row["k"] <= 93 and in_ob:
            in_ob = False
            periods.append({"start": start, "end": row["date"], "cross_date": row["date"],
                           "cross_k": row["k"], "cross_d": row["d"]})
    if in_ob:
        periods.append({"start": start, "end": w2_etf.iloc[-1]["date"], "cross_date": None,
                        "cross_k": None, "cross_d": None})
    return periods


def ob93_first_touches(w2):
    """First candle K>93 in each new OB period."""
    w2_etf = w2[w2["date"] >= ETF_START].copy()
    signals = []
    prev_ob = False
    for _, row in w2_etf.iterrows():
        if row["k"] > 93 and not prev_ob:
            signals.append({"date": row["date"], "k": row["k"], "price": row["close"]})
        prev_ob = row["k"] > 93
    return signals


def k_cross_below_d(w2):
    """All K cross below D events."""
    w2_etf = w2[w2["date"] >= ETF_START].copy()
    crosses = []
    for i in range(1, len(w2_etf)):
        if w2_etf.iloc[i]["k"] < w2_etf.iloc[i]["d"] and w2_etf.iloc[i-1]["k"] >= w2_etf.iloc[i-1]["d"]:
            crosses.append({"date": w2_etf.iloc[i]["date"], "k": w2_etf.iloc[i]["k"], 
                           "d": w2_etf.iloc[i]["d"], "price": w2_etf.iloc[i]["close"]})
    return crosses


def false_rate(signals, d2, peak_date):
    """Count signals where price rose >20% in 90d after."""
    d2_etf = d2[d2["date"] >= ETF_START]
    false_count = 0
    for s in signals:
        sig_date = s["date"]
        future = d2_etf[(d2_etf["date"] > sig_date) & (d2_etf["date"] <= sig_date + timedelta(days=90))]
        if len(future) > 0:
            price_at = d2_etf[d2_etf["date"] <= sig_date]["close"].iloc[-1] if len(d2_etf[d2_etf["date"] <= sig_date]) > 0 else s.get("price", 0)
            if price_at > 0 and (future["close"].max() / price_at - 1) > 0.20:
                false_count += 1
    return false_count


print("STEVE TOP STACK + OB93 COMBO TEST")
print("=" * 70)

summary = []

for coin in COINS:
    base = coin.split("/")[0]
    d2, w2 = build_signals(coin)
    peak_date, peak_price = get_peak(d2)
    
    print(f"\n{'='*70}")
    print(f"  {base} — Peak: {peak_date.strftime('%Y-%m-%d')} ${peak_price:.2f}")
    print(f"{'='*70}")
    
    ob_periods = ob93_periods(w2)
    ob_touches = ob93_first_touches(w2)
    crosses = k_cross_below_d(w2)
    
    # Show OB93 periods
    print(f"\n  2W OB93 periods (K>93):")
    for p in ob_periods:
        end_str = p["end"].strftime("%Y-%m-%d") if p["end"] else "ongoing"
        print(f"    {p['start'].strftime('%Y-%m-%d')} to {end_str}")
    
    for score_thresh in [3, 4]:
        clusters = steve_clusters(d2, score_thresh)
        
        # --- Method: Steve fires within 28d of 2W K being >93 ---
        label = f"Steve{score_thresh} + OB93 nearby (28d)"
        signals = []
        for cl in clusters:
            for p in ob_periods:
                # Steve cluster overlaps or is within 28d of OB93 period
                if (cl["start"] <= p["end"] + timedelta(days=28) and 
                    cl["end"] >= p["start"] - timedelta(days=28)):
                    signals.append({
                        "date": cl["start"],
                        "price": cl["peak_close"],
                        "score": cl["max_score"],
                        "ob_start": p["start"],
                    })
                    break
        
        n_false = false_rate(signals, d2, peak_date)
        last_days = (peak_date - signals[-1]["date"]).days if signals else None
        
        print(f"\n  {label}: {len(signals)} signals, {n_false} false")
        for s in signals:
            days = (peak_date - s["date"]).days
            print(f"    {s['date'].strftime('%Y-%m-%d')} score={s['score']} "
                  f"(OB93 from {s['ob_start'].strftime('%Y-%m-%d')})  ({days:+d}d)")
        
        summary.append({"method": label, "coin": base, "signals": len(signals), 
                        "false": n_false, "last_days": last_days})
        
        # --- Method: Steve + OB93 → then K×D crossover ---
        label2 = f"Steve{score_thresh} + OB93 → K×D"
        signals2 = []
        for cl in clusters:
            for p in ob_periods:
                if (cl["start"] <= p["end"] + timedelta(days=28) and 
                    cl["end"] >= p["start"] - timedelta(days=28)):
                    # Found overlap. Now find next K×D cross after the later of Steve/OB93
                    trigger_date = max(cl["start"], p["start"])
                    for cx in crosses:
                        if cx["date"] > trigger_date:
                            signals2.append({
                                "date": cx["date"],
                                "price": cx["price"],
                                "steve_date": cl["start"],
                                "score": cl["max_score"],
                                "ob_start": p["start"],
                            })
                            break
                    break
        
        n_false2 = false_rate(signals2, d2, peak_date)
        last_days2 = (peak_date - signals2[-1]["date"]).days if signals2 else None
        
        print(f"\n  {label2}: {len(signals2)} signals, {n_false2} false")
        for s in signals2:
            days = (peak_date - s["date"]).days
            print(f"    {s['date'].strftime('%Y-%m-%d')} ${s['price']:.2f} "
                  f"(Steve {s['steve_date'].strftime('%Y-%m-%d')}, OB93 {s['ob_start'].strftime('%Y-%m-%d')})  ({days:+d}d)")
        
        summary.append({"method": label2, "coin": base, "signals": len(signals2),
                        "false": n_false2, "last_days": last_days2})

    # --- Baseline: OB93 alone ---
    label_b = "OB93 alone (first touch)"
    n_false_b = false_rate(ob_touches, d2, peak_date)
    last_b = (peak_date - ob_touches[-1]["date"]).days if ob_touches else None
    print(f"\n  {label_b}: {len(ob_touches)} signals, {n_false_b} false")
    for s in ob_touches:
        days = (peak_date - s["date"]).days
        print(f"    {s['date'].strftime('%Y-%m-%d')} K={s['k']:.1f}  ({days:+d}d)")
    summary.append({"method": label_b, "coin": base, "signals": len(ob_touches),
                    "false": n_false_b, "last_days": last_b})


# ─── Grand Summary ───
print(f"\n\n{'='*70}")
print("GRAND SUMMARY")
print(f"{'='*70}")

methods_order = [
    "OB93 alone (first touch)",
    "Steve3 + OB93 nearby (28d)",
    "Steve4 + OB93 nearby (28d)",
    "Steve3 + OB93 → K×D",
    "Steve4 + OB93 → K×D",
]

for method in methods_order:
    entries = [s for s in summary if s["method"] == method]
    total_sig = sum(e["signals"] for e in entries)
    total_false = sum(e["false"] for e in entries)
    false_pct = total_false / max(total_sig, 1) * 100
    
    print(f"\n  {method}:")
    for e in entries:
        last_str = f"{e['last_days']:+d}d" if e["last_days"] is not None else "none"
        print(f"    {e['coin']:6} {e['signals']} sig, {e['false']} false, last: {last_str}")
    print(f"    TOTAL: {total_sig} sig, {total_false} false ({false_pct:.0f}%)")
