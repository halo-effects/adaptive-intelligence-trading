"""Compute daily technical indicators for coins that only have raw OHLCV."""
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

DB = Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'

def compute_indicators(symbol):
    conn = sqlite3.connect(str(DB))
    df = pd.read_sql(
        "SELECT rowid, timestamp, open, high, low, close, volume FROM candles_daily WHERE symbol=? ORDER BY timestamp",
        conn, params=[symbol]
    )
    if len(df) == 0:
        print(f"No data for {symbol}")
        return

    # SMA
    df['sma20'] = df['close'].rolling(20).mean()
    df['sma50'] = df['close'].rolling(50).mean()
    df['sma200'] = df['close'].rolling(200).mean()

    # Bollinger Bands
    std20 = df['close'].rolling(20).std()
    df['bb_width'] = (std20 * 4) / df['sma20']
    df['bb_pct'] = (df['close'] - (df['sma20'] - 2 * std20)) / (4 * std20)

    # ATR
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift()).abs(),
        (df['low'] - df['close'].shift()).abs()
    ], axis=1).max(axis=1)
    df['atr14'] = tr.rolling(14).mean()
    df['atr_pct'] = df['atr14'] / df['close'] * 100

    # ADX
    plus_dm = df['high'].diff().clip(lower=0)
    minus_dm = (-df['low'].diff()).clip(lower=0)
    plus_dm[plus_dm < minus_dm] = 0
    minus_dm[minus_dm < plus_dm] = 0
    atr_smooth = tr.ewm(alpha=1/14, min_periods=14).mean()
    df['plus_di'] = 100 * plus_dm.ewm(alpha=1/14, min_periods=14).mean() / atr_smooth
    df['minus_di'] = 100 * minus_dm.ewm(alpha=1/14, min_periods=14).mean() / atr_smooth
    dx = 100 * (df['plus_di'] - df['minus_di']).abs() / (df['plus_di'] + df['minus_di'])
    df['adx'] = dx.ewm(alpha=1/14, min_periods=14).mean()

    # RSI(14)
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
    rs = avg_gain / avg_loss
    df['rsi14'] = 100 - (100 / (1 + rs))

    # Consecutive HH/HL and LH/LL
    hh = df['high'] > df['high'].shift()
    hl = df['low'] > df['low'].shift()
    lh = df['high'] < df['high'].shift()
    ll = df['low'] < df['low'].shift()

    consec_hh_hl = np.zeros(len(df))
    consec_lh_ll = np.zeros(len(df))
    for i in range(1, len(df)):
        if hh.iloc[i] and hl.iloc[i]:
            consec_hh_hl[i] = consec_hh_hl[i-1] + 1
        else:
            consec_hh_hl[i] = 0
        if lh.iloc[i] and ll.iloc[i]:
            consec_lh_ll[i] = consec_lh_ll[i-1] + 1
        else:
            consec_lh_ll[i] = 0
    df['consec_hh_hl'] = consec_hh_hl
    df['consec_lh_ll'] = consec_lh_ll

    # SMA slopes
    df['sma50_slope'] = df['sma50'].pct_change(5) * 100
    df['sma200_slope'] = df['sma200'].pct_change(5) * 100

    # Price vs SMA
    df['price_vs_sma50'] = (df['close'] - df['sma50']) / df['sma50'] * 100
    df['price_vs_sma200'] = (df['close'] - df['sma200']) / df['sma200'] * 100

    # Update DB
    cur = conn.cursor()
    cols = ['sma20','sma50','sma200','bb_width','bb_pct','atr14','atr_pct',
            'adx','plus_di','minus_di','rsi14','consec_hh_hl','consec_lh_ll',
            'sma50_slope','sma200_slope','price_vs_sma50','price_vs_sma200']
    for _, row in df.iterrows():
        sets = ', '.join(f'{c}=?' for c in cols)
        vals = [None if pd.isna(row[c]) else float(row[c]) for c in cols]
        vals.append(int(row['rowid']))
        cur.execute(f'UPDATE candles_daily SET {sets} WHERE rowid=?', vals)
    conn.commit()
    conn.close()
    print(f"{symbol}: {len(df)} rows updated with indicators")


if __name__ == '__main__':
    compute_indicators('HBAR/USDT')
