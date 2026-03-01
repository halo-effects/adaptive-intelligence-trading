"""Check current 3D death cross status for all coins."""
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

print("=" * 100)
print("  CURRENT 3D DEATH CROSS STATUS")
print("=" * 100)

for coin in coins:
    df = load_daily(coin)
    if df.empty:
        print(f"\n  {coin}: No data")
        continue
    
    # Resample to 3D
    df_3d = df.resample('3D').agg({
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'volume': 'sum'
    }).dropna()
    
    df_3d['sma50'] = df_3d['close'].rolling(50).mean()
    df_3d['sma200'] = df_3d['close'].rolling(200).mean()
    
    # Current status
    latest = df_3d.iloc[-1]
    prev = df_3d.iloc[-2]
    
    sma50 = latest['sma50']
    sma200 = latest['sma200']
    price = latest['close']
    
    cross_status = "GOLDEN (bullish)" if sma50 > sma200 else "DEATH (bearish)"
    gap_pct = (sma50 - sma200) / sma200 * 100
    price_vs_200 = (price - sma200) / sma200 * 100
    
    # Find most recent cross
    prev_above = None
    last_death = None
    last_golden = None
    for i in range(len(df_3d)):
        s50 = df_3d['sma50'].iloc[i]
        s200 = df_3d['sma200'].iloc[i]
        if pd.isna(s50) or pd.isna(s200):
            continue
        currently_above = s50 > s200
        if prev_above is not None:
            if prev_above and not currently_above:
                last_death = df_3d.index[i]
            elif not prev_above and currently_above:
                last_golden = df_3d.index[i]
        prev_above = currently_above
    
    days_since_death = (df_3d.index[-1] - last_death).days if last_death else None
    days_since_golden = (df_3d.index[-1] - last_golden).days if last_golden else None
    
    # Also check daily SMA status
    df['sma50_d'] = df['close'].rolling(50).mean()
    df['sma200_d'] = df['close'].rolling(200).mean()
    d_latest = df.iloc[-1]
    daily_status = "GOLDEN" if d_latest['sma50_d'] > d_latest['sma200_d'] else "DEATH"
    daily_gap = (d_latest['sma50_d'] - d_latest['sma200_d']) / d_latest['sma200_d'] * 100
    
    # CFGI from status.json
    cfgi_str = "N/A"
    try:
        import json
        status = json.loads(open(Path(__file__).resolve().parent.parent.parent.parent / 'paper' / 'v13' / 'status.json').read())
        for sym, data in status.get('coins', {}).items():
            if coin in sym:
                cfgi_str = f"{data.get('cfgi', 'N/A')}"
    except:
        pass
    
    print(f"\n  {coin}:")
    print(f"    Price: ${price:,.2f}")
    print(f"    3D SMA50: ${sma50:,.2f}  |  3D SMA200: ${sma200:,.2f}")
    print(f"    3D Status: {cross_status} (gap: {gap_pct:+.1f}%)")
    print(f"    Daily Status: {daily_status} (gap: {daily_gap:+.1f}%)")
    print(f"    Price vs 3D SMA200: {price_vs_200:+.1f}%")
    if last_death:
        print(f"    Last 3D Death Cross: {last_death.strftime('%Y-%m-%d')} ({days_since_death} days ago)")
    if last_golden:
        print(f"    Last 3D Golden Cross: {last_golden.strftime('%Y-%m-%d')} ({days_since_golden} days ago)")
    print(f"    CFGI: {cfgi_str}")
    
    # How close to crossing?
    if sma50 > sma200:
        converge_rate = (df_3d['sma50'].iloc[-1] - df_3d['sma50'].iloc[-5]) / 5 - (df_3d['sma200'].iloc[-1] - df_3d['sma200'].iloc[-5]) / 5
        if converge_rate < 0:
            bars_to_cross = abs(sma50 - sma200) / abs(converge_rate)
            print(f"    CONVERGING: ~{bars_to_cross:.0f} 3D bars ({bars_to_cross*3:.0f} days) to potential death cross")
        else:
            print(f"    DIVERGING (moving apart)")
    else:
        converge_rate = (df_3d['sma50'].iloc[-1] - df_3d['sma50'].iloc[-5]) / 5 - (df_3d['sma200'].iloc[-1] - df_3d['sma200'].iloc[-5]) / 5
        if converge_rate > 0:
            bars_to_cross = abs(sma50 - sma200) / abs(converge_rate)
            print(f"    RECOVERING: ~{bars_to_cross:.0f} 3D bars ({bars_to_cross*3:.0f} days) to potential golden cross")
        else:
            print(f"    WIDENING (death cross deepening)")
