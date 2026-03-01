"""
Check conviction stack indicator values on 2D chart at known bottoms.
Are our thresholds (RSI<26, StochRSI K&D<20, CFGI<35) correct for 2D?
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import timedelta

DB = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
conn = sqlite3.connect(DB)

COINS = ["ETH/USDT", "SOL/USDT", "LINK/USDT", "XRP/USDT", "BTC/USDT"]

BOTTOMS = {
    "ETH": [("2025-04-09", 1385.05), ("2025-11-21", 2623.57)],
    "SOL": [("2025-04-07", 95.26), ("2025-12-18", 116.88)],
    "LINK": [("2024-08-05", 8.08), ("2025-10-10", 7.90)],
    "XRP": [("2024-07-05", 0.38), ("2025-12-19", 1.77)],
    "BTC": [("2024-09-06", 52550.00), ("2025-04-07", 74508.00)],
}


def compute_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_stochrsi(close, rsi_period=14, stoch_period=14, k_smooth=3, d_smooth=3):
    rsi = compute_rsi(close, rsi_period)
    rsi_low = rsi.rolling(stoch_period).min()
    rsi_high = rsi.rolling(stoch_period).max()
    stoch = ((rsi - rsi_low) / (rsi_high - rsi_low).replace(0, np.nan)) * 100
    k = stoch.rolling(k_smooth).mean()
    d = k.rolling(d_smooth).mean()
    return rsi, k, d


print("2D INDICATOR VALUES AT KNOWN BOTTOMS")
print("=" * 95)
print("Current thresholds: RSI<26, StochRSI K&D<20, CFGI<35, Below SMA200")
print()

# Also load CFGI
cfgi_all = {}
for sym in COINS:
    base = sym.split("/")[0]
    try:
        cdf = pd.read_sql("SELECT * FROM cfgi_daily WHERE symbol=? ORDER BY date", conn, params=[base])
        cdf["dt"] = pd.to_datetime(cdf["date"], format="mixed").dt.normalize()
        cdf = cdf.set_index("dt")
        cdf = cdf[~cdf.index.duplicated(keep="last")]
        cfgi_all[base] = cdf
    except:
        pass

for sym in COINS:
    base = sym.split("/")[0]
    if base not in BOTTOMS:
        continue

    df = pd.read_sql_query(
        "SELECT timestamp, close FROM candles_daily WHERE symbol=? ORDER BY timestamp",
        conn, params=[sym]
    )
    df["dt"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("dt").sort_index()
    df = df[~df.index.duplicated(keep="last")]

    # 2D resample
    d2 = df["close"].resample("2D").last().dropna()
    d2_rsi, d2_k, d2_d = compute_stochrsi(d2)
    d2_sma200 = d2.rolling(200).mean()

    # Daily for comparison
    d1_rsi, d1_k, d1_d = compute_stochrsi(df["close"])
    d1_sma200 = df["close"].rolling(200).mean()

    print(f"\n{'='*95}")
    print(f"  {base}")
    print(f"{'='*95}")

    for bdate_s, bprice in BOTTOMS[base]:
        bdate = pd.Timestamp(bdate_s)
        print(f"\n  Bottom: {bdate_s} @ ${bprice:,.2f}")

        # Get values in a window around the bottom
        window = pd.date_range(bdate - timedelta(days=10), bdate + timedelta(days=20), freq="D")

        print(f"\n  {'Date':12} {'Price':>10} | {'2D_RSI':>7} {'2D_K':>6} {'2D_D':>6} {'<SMA200':>8} | {'1D_RSI':>7} {'1D_K':>6} {'1D_D':>6} {'<SMA200':>8} | {'CFGI':>5}")
        print(f"  {'-'*98}")

        for dt in window:
            # Daily values
            price = df["close"].loc[dt] if dt in df["close"].index else None
            if price is None:
                continue

            rsi_1d = d1_rsi.loc[dt] if dt in d1_rsi.index else np.nan
            k_1d = d1_k.loc[dt] if dt in d1_k.index else np.nan
            d_1d = d1_d.loc[dt] if dt in d1_d.index else np.nan
            sma_1d = d1_sma200.loc[dt] if dt in d1_sma200.index else np.nan
            below_1d = "YES" if (not np.isnan(sma_1d) and price < sma_1d) else ""

            # 2D values (find nearest)
            d2_dates = d2.index[d2.index <= dt]
            if len(d2_dates) == 0:
                continue
            d2_dt = d2_dates[-1]
            rsi_2d = d2_rsi.loc[d2_dt] if d2_dt in d2_rsi.index else np.nan
            k_2d = d2_k.loc[d2_dt] if d2_dt in d2_k.index else np.nan
            d_2d = d2_d.loc[d2_dt] if d2_dt in d2_d.index else np.nan
            sma_2d = d2_sma200.loc[d2_dt] if d2_dt in d2_sma200.index else np.nan
            below_2d = "YES" if (not np.isnan(sma_2d) and d2.loc[d2_dt] < sma_2d) else ""

            # CFGI
            cfgi_val = ""
            if base in cfgi_all:
                c_dates = cfgi_all[base].index[cfgi_all[base].index <= dt]
                if len(c_dates):
                    cfgi_val = f"{cfgi_all[base].loc[c_dates[-1], 'cfgi']:.0f}"

            # Highlight if meets threshold
            rsi_2d_s = f"{rsi_2d:>6.1f}{'*' if rsi_2d < 26 else ' '}" if not np.isnan(rsi_2d) else "    nan"
            k_2d_s = f"{k_2d:>5.1f}{'*' if k_2d < 20 else ' '}" if not np.isnan(k_2d) else "   nan"
            d_2d_s = f"{d_2d:>5.1f}{'*' if d_2d < 20 else ' '}" if not np.isnan(d_2d) else "   nan"
            rsi_1d_s = f"{rsi_1d:>6.1f}{'*' if rsi_1d < 26 else ' '}" if not np.isnan(rsi_1d) else "    nan"
            k_1d_s = f"{k_1d:>5.1f}{'*' if k_1d < 20 else ' '}" if not np.isnan(k_1d) else "   nan"
            d_1d_s = f"{d_1d:>5.1f}{'*' if d_1d < 20 else ' '}" if not np.isnan(d_1d) else "   nan"

            print(f"  {dt.strftime('%Y-%m-%d'):12} ${price:>9.2f} | {rsi_2d_s} {k_2d_s} {d_2d_s} {below_2d:>8} | {rsi_1d_s} {k_1d_s} {d_1d_s} {below_1d:>8} | {cfgi_val:>5}")

conn.close()
