import sqlite3, pandas as pd, numpy as np

db = sqlite3.connect('trading/spot/data/candles.db')

tops = {'ETH': '2024-12-06', 'SOL': '2025-01-19', 'BTC': '2025-01-20', 'LINK': '2024-12-08', 'XRP': '2025-01-16'}

for coin, top_date in tops.items():
    df = pd.read_sql(f"SELECT timestamp, open, high, low, close FROM candles_daily WHERE symbol LIKE '{coin}%' ORDER BY timestamp", db)
    if df.empty:
        print(f'{coin}: no daily data'); continue
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('date').sort_index()
    d3 = df.resample('3D').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    
    period = 14
    delta = d3['close'].diff()
    gain = delta.where(delta>0, 0).rolling(period).mean()
    loss = (-delta.where(delta<0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    stoch_period = 14
    rsi_min = rsi.rolling(stoch_period).min()
    rsi_max = rsi.rolling(stoch_period).max()
    k = ((rsi - rsi_min) / (rsi_max - rsi_min)) * 100
    d_line = k.rolling(3).mean()
    
    top_dt = pd.Timestamp(top_date)
    top_price = d3['close'].loc[d3.index <= top_dt].iloc[-1]
    
    window = d3[(d3.index >= top_dt - pd.Timedelta(days=90)) & (d3.index <= top_dt + pd.Timedelta(days=90))]
    k_win = k.reindex(window.index)
    d_win = d_line.reindex(window.index)
    
    crosses = []
    for i in range(1, len(k_win)):
        if pd.notna(k_win.iloc[i-1]) and pd.notna(d_win.iloc[i-1]) and pd.notna(k_win.iloc[i]) and pd.notna(d_win.iloc[i]):
            if k_win.iloc[i-1] >= d_win.iloc[i-1] and k_win.iloc[i] < d_win.iloc[i]:
                cross_date = k_win.index[i]
                cross_price = d3['close'].loc[cross_date]
                days_from_top = (cross_date - top_dt).days
                pct = (cross_price / top_price - 1) * 100
                crosses.append((cross_date.strftime('%Y-%m-%d'), days_from_top, pct, k_win.iloc[i], d_win.iloc[i]))
    
    print(f'{coin} (top {top_date}, ~${top_price:.0f}):')
    if crosses:
        for dt, days, pct, kv, dv in crosses:
            print(f'  3D K<D: {dt}, {days:+d}d from top, {pct:+.1f}%, K={kv:.1f} D={dv:.1f}')
    else:
        print('  No 3D K<D bearish cross in window')
    print()
