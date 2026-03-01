import sqlite3, pandas as pd, numpy as np

db = sqlite3.connect('trading/spot/data/candles.db')

def stoch_rsi(close, rsi_period=14, stoch_period=14, k_smooth=3, d_smooth=3):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/rsi_period, min_periods=rsi_period).mean()
    avg_loss = loss.ewm(alpha=1/rsi_period, min_periods=rsi_period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi_low = rsi.rolling(stoch_period).min()
    rsi_high = rsi.rolling(stoch_period).max()
    stoch_k = 100 * (rsi - rsi_low) / (rsi_high - rsi_low + 1e-10)
    stoch_k = stoch_k.rolling(k_smooth).mean()
    stoch_d = stoch_k.rolling(d_smooth).mean()
    return stoch_k, stoch_d

for coin in ['SOL', 'BTC', 'ETH', 'BNB', 'XRP']:
    sym = [r[0] for r in db.execute('SELECT DISTINCT symbol FROM candles_daily WHERE symbol LIKE ?', (f'{coin}%',)).fetchall()]
    if not sym:
        continue
    df = pd.read_sql('SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp', db, params=[sym[0]])
    df['dt'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('dt', inplace=True)

    # Resample to weekly
    wk = df['close'].resample('W').last().dropna()

    k, d = stoch_rsi(wk)

    combined = pd.DataFrame({'close': wk, 'K': k, 'D': d})
    combined = combined[combined.index >= '2024-09-01']

    prev_k = combined['K'].shift(1)
    ob_crosses = combined[(prev_k > 80) & (combined['K'] <= 80)]
    os_crosses = combined[(prev_k < 20) & (combined['K'] >= 20)]

    print(f'\n===== {coin} WEEKLY StochRSI =====')

    print('\nOverbought exits (K crosses below 80) - potential tops:')
    for dt, row in ob_crosses.iterrows():
        cl = row['close']
        kv = row['K']
        dv = row['D']
        print(f'  {dt.date()}: close={cl:.1f}, K={kv:.1f}, D={dv:.1f}')

    print('\nOversold exits (K crosses above 20) - potential bottoms:')
    for dt, row in os_crosses.iterrows():
        cl = row['close']
        kv = row['K']
        dv = row['D']
        print(f'  {dt.date()}: close={cl:.1f}, K={kv:.1f}, D={dv:.1f}')

    # Show every-2-week timeline
    print('\nWeekly StochRSI (every 2 weeks):')
    for i, (dt, row) in enumerate(combined.iterrows()):
        if i % 2 == 0:
            cl = row['close']
            kv = row['K']
            dv = row['D']
            zone = 'OB' if kv > 80 else 'OS' if kv < 20 else '  '
            print(f'  {dt.date()}: close={cl:>9.1f}  K={kv:5.1f}  D={dv:5.1f}  {zone}')

# Now check: how many of the >14% drops were preceded by weekly StochRSI overbought?
print('\n\n===== SIGNAL QUALITY: Weekly StochRSI OB before >14% drops =====')
for coin in ['SOL', 'BTC', 'ETH']:
    sym = [r[0] for r in db.execute('SELECT DISTINCT symbol FROM candles_daily WHERE symbol LIKE ?', (f'{coin}%',)).fetchall()]
    if not sym:
        continue
    df = pd.read_sql('SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp', db, params=[sym[0]])
    df['dt'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('dt', inplace=True)

    wk = df['close'].resample('W').last().dropna()
    k, d_line = stoch_rsi(wk)
    stoch_df = pd.DataFrame({'K': k, 'D': d_line})

    # Find drops >14%
    df2 = df[df.index >= '2024-09-01'].copy()
    df2['rh14'] = df2['high'].rolling(14).max()
    df2['dd'] = (df2['close'] - df2['rh14']) / df2['rh14'] * 100

    drop_starts = []
    in_drop = False
    for dt, row in df2.iterrows():
        if row['dd'] < -14 and not in_drop:
            drop_starts.append(dt)
            in_drop = True
        elif row['dd'] > -5:
            in_drop = False

    ob_before = 0
    for ds in drop_starts:
        # Was weekly StochRSI >80 in the 4 weeks before?
        four_weeks_ago = ds - pd.Timedelta(weeks=4)
        recent_stoch = stoch_df[(stoch_df.index >= four_weeks_ago) & (stoch_df.index <= ds)]
        was_ob = (recent_stoch['K'] > 80).any()
        if was_ob:
            ob_before += 1

    print(f'{coin}: {len(drop_starts)} drops, {ob_before} preceded by weekly StochRSI OB ({ob_before/max(len(drop_starts),1)*100:.0f}%)')
