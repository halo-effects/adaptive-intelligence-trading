"""Compare 1D, 2D, 3D death cross status for all coins."""
import sqlite3, pandas as pd, numpy as np
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'

def load_daily(coin):
    conn = sqlite3.connect(str(DB_PATH))
    base = coin.split('/')[0].upper()
    df = pd.read_sql_query(f"SELECT * FROM candles_daily WHERE symbol LIKE '{base}%' ORDER BY timestamp", conn)
    conn.close()
    if df.empty:
        return pd.DataFrame()
    if df['timestamp'].dtype in ['int64', 'float64']:
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    else:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp').sort_index()
    df = df[~df.index.duplicated(keep='last')]
    df = df[df.index.notna()]
    return df

coins = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']

for tf_days, label in [(1, '1D'), (2, '2D'), (3, '3D')]:
    print(f"\n{'='*100}")
    print(f"  {label} DEATH CROSS STATUS (SMA50/SMA200 on {label} candles)")
    print(f"{'='*100}")
    print(f"  {'Coin':<6} {'Status':<20} {'Gap%':>7} {'Price vs SMA200':>16} {'Last DX Date':>14} {'Days Ago':>9} {'Converging?':>14}")
    print(f"  {'-'*6} {'-'*20} {'-'*7} {'-'*16} {'-'*14} {'-'*9} {'-'*14}")
    
    for coin in coins:
        df = load_daily(coin)
        if df.empty:
            continue
        
        if tf_days > 1:
            dfr = df.resample(f'{tf_days}D').agg({
                'open': 'first', 'high': 'max', 'low': 'min',
                'close': 'last', 'volume': 'sum'
            }).dropna()
        else:
            dfr = df.copy()
        
        dfr['sma50'] = dfr['close'].rolling(50).mean()
        dfr['sma200'] = dfr['close'].rolling(200).mean()
        
        latest = dfr.iloc[-1]
        sma50 = latest['sma50']
        sma200 = latest['sma200']
        price = latest['close']
        
        if pd.isna(sma50) or pd.isna(sma200):
            print(f"  {coin:<6} {'INSUFFICIENT DATA':<20}")
            continue
        
        status = "GOLDEN (bullish)" if sma50 > sma200 else "DEATH (bearish)"
        gap_pct = (sma50 - sma200) / sma200 * 100
        price_vs_200 = (price - sma200) / sma200 * 100
        
        # Find last death cross
        prev_above = None
        last_death = None
        for i in range(len(dfr)):
            s50 = dfr['sma50'].iloc[i]
            s200 = dfr['sma200'].iloc[i]
            if pd.isna(s50) or pd.isna(s200):
                continue
            currently_above = s50 > s200
            if prev_above is not None and prev_above and not currently_above:
                last_death = dfr.index[i]
            prev_above = currently_above
        
        days_ago = (dfr.index[-1] - last_death).days if last_death else None
        dx_str = last_death.strftime('%Y-%m-%d') if last_death else "Never"
        days_str = f"{days_ago}" if days_ago else "-"
        
        # Convergence
        if len(dfr) >= 6:
            rate = (dfr['sma50'].iloc[-1] - dfr['sma50'].iloc[-5]) / 5 - (dfr['sma200'].iloc[-1] - dfr['sma200'].iloc[-5]) / 5
            if sma50 > sma200 and rate < 0:
                bars = abs(sma50 - sma200) / abs(rate)
                conv = f"~{bars*tf_days:.0f}d to DX"
            elif sma50 < sma200 and rate > 0:
                bars = abs(sma50 - sma200) / abs(rate)
                conv = f"~{bars*tf_days:.0f}d to GX"
            elif sma50 > sma200:
                conv = "Diverging"
            else:
                conv = "Widening"
        else:
            conv = "N/A"
        
        print(f"  {coin:<6} {status:<20} {gap_pct:>+6.1f}% {price_vs_200:>+14.1f}% {dx_str:>14} {days_str:>9} {conv:>14}")
