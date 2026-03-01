"""
Crypto Crew University (Steve) Framework Validation

Tests:
1. 2-week StochRSI with 97 threshold for tops, 20 for bottoms
2. 3-week StochRSI same thresholds
3. Pi Cycle Top Indicator (111-day MA crosses above 2x 350-day MA)
4. Bull Market Support Band (20-week SMA + 21-week EMA)
5. Compare 1W vs 2W vs 3W StochRSI accuracy
"""

import sqlite3, pandas as pd, numpy as np
from datetime import timedelta

DB_PATH = 'trading/spot/data/candles.db'

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


def resample_nweek(daily, n_weeks):
    """Resample daily data to n-week OHLCV"""
    # Use custom period resampling
    daily_copy = daily.copy()
    # Group by n-week periods from the start
    start = daily_copy.index[0]
    daily_copy['period'] = ((daily_copy.index - start).days // (n_weeks * 7))
    
    result = daily_copy.groupby('period').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })
    # Use last date in each period as index
    dates = daily_copy.groupby('period').apply(lambda x: x.index[-1])
    result.index = dates.values
    return result


db = sqlite3.connect(DB_PATH)

print("CRYPTO CREW UNIVERSITY FRAMEWORK VALIDATION")
print("=" * 90)
print()
print("Steve's methodology: 2W/3W StochRSI, 97 threshold tops, <20 bottoms")
print("Pi Cycle Top: 111-day MA crosses above 2x 350-day MA")
print("Bull Market Support Band: 20-week SMA + 21-week EMA")
print()

for coin in ['BTC', 'ETH', 'SOL']:
    sym = [r[0] for r in db.execute(
        'SELECT DISTINCT symbol FROM candles_daily WHERE symbol LIKE ?',
        (f'{coin}%',)).fetchall()]
    if not sym:
        continue

    daily = pd.read_sql(
        'SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp',
        db, params=[sym[0]])
    daily['dt'] = pd.to_datetime(daily['timestamp'], unit='ms')
    daily.set_index('dt', inplace=True)

    print(f"\n{'='*80}")
    print(f"  {coin} ({sym[0]}) — {len(daily)} daily candles")
    print(f"{'='*80}")

    # ==========================================
    # 1. Multi-timeframe StochRSI comparison
    # ==========================================
    print(f"\n  --- STOCHRSI COMPARISON: 1W vs 2W vs 3W ---")

    for label, n_weeks in [('1W', 1), ('2W', 2), ('3W', 3)]:
        if n_weeks == 1:
            resampled = daily[['open','high','low','close','volume']].resample('W').agg({
                'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
            }).dropna()
        else:
            resampled = resample_nweek(daily, n_weeks)

        k, d = stoch_rsi(resampled['close'])
        df = pd.DataFrame({'close': resampled['close'], 'K': k, 'D': d})
        df = df[df.index >= '2024-01-01']

        # Steve's signals:
        # Top: K crosses DOWN from 97
        # Bottom: K crosses UP from below 20
        prev_k = df['K'].shift(1)

        # 97 threshold (Steve's "leaving the road")
        top_97 = df[(prev_k >= 97) & (df['K'] < 97)]
        # 80 threshold (standard)
        top_80 = df[(prev_k >= 80) & (df['K'] < 80)]
        # Bottom: crosses above 20
        bot_20 = df[(prev_k < 20) & (df['K'] >= 20)]

        # "Leaving the road" — both K and D exit 75-100 range
        road_exit = df[(prev_k >= 75) & (df['K'] < 75)]

        print(f"\n    {label} StochRSI:")
        
        if len(top_97) > 0:
            print(f"      97 threshold crosses (Steve's cycle top):")
            for dt, row in top_97.iterrows():
                future = daily[daily.index >= dt].head(60)
                max_dd = ((future['low'].min() - row['close']) / row['close'] * 100) if len(future) > 0 else 0
                print(f"        {dt.date()}: close={row['close']:.1f}, K={row['K']:.1f} -> {max_dd:.1f}% in 60d")
        else:
            print(f"      97 threshold: no crosses found")

        if len(top_80) > 0:
            print(f"      80 threshold crosses (standard OB exit):")
            for dt, row in top_80.iterrows():
                future = daily[daily.index >= dt].head(60)
                max_dd = ((future['low'].min() - row['close']) / row['close'] * 100) if len(future) > 0 else 0
                print(f"        {dt.date()}: close={row['close']:.1f}, K={row['K']:.1f} -> {max_dd:.1f}% in 60d")
        
        if len(road_exit) > 0:
            print(f"      'Leaving the road' (K exits 75-100):")
            for dt, row in road_exit.iterrows():
                future = daily[daily.index >= dt].head(60)
                max_dd = ((future['low'].min() - row['close']) / row['close'] * 100) if len(future) > 0 else 0
                print(f"        {dt.date()}: close={row['close']:.1f}, K={row['K']:.1f} -> {max_dd:.1f}% in 60d")

        if len(bot_20) > 0:
            print(f"      Bottom signals (K crosses above 20):")
            for dt, row in bot_20.iterrows():
                future = daily[daily.index >= dt].head(90)
                max_up = ((future['high'].max() - row['close']) / row['close'] * 100) if len(future) > 0 else 0
                print(f"        {dt.date()}: close={row['close']:.1f}, K={row['K']:.1f} -> +{max_up:.1f}% in 90d")

        # Show timeline (sparse)
        print(f"      Timeline (key points):")
        for dt, row in df.iterrows():
            kv = row['K']
            if pd.isna(kv):
                continue
            # Show OB/OS zones and zone transitions
            if kv > 90 or kv < 15:
                zone = 'OB!!!' if kv > 97 else 'OB' if kv > 80 else 'OS' if kv < 20 else ''
                if zone:
                    print(f"        {dt.date()}: close={row['close']:>10.1f}  K={kv:5.1f}  D={row['D']:5.1f}  {zone}")

    # ==========================================
    # 2. Pi Cycle Top Indicator
    # ==========================================
    print(f"\n  --- PI CYCLE TOP INDICATOR ---")
    daily['ma111'] = daily['close'].rolling(111).mean()
    daily['ma350x2'] = daily['close'].rolling(350).mean() * 2

    pi_valid = daily.dropna(subset=['ma111', 'ma350x2'])
    if len(pi_valid) > 1:
        # Cross: 111-MA crosses ABOVE 2x350-MA
        prev_diff = (pi_valid['ma111'].shift(1) - pi_valid['ma350x2'].shift(1))
        curr_diff = (pi_valid['ma111'] - pi_valid['ma350x2'])
        pi_crosses = pi_valid[(prev_diff <= 0) & (curr_diff > 0)]
        pi_crosses = pi_crosses[pi_crosses.index >= '2024-01-01']

        if len(pi_crosses) > 0:
            print(f"    Pi Cycle Top signals (111-MA crosses above 2x350-MA):")
            for dt, row in pi_crosses.iterrows():
                future = daily[daily.index >= dt].head(60)
                max_dd = ((future['low'].min() - row['close']) / row['close'] * 100) if len(future) > 0 else 0
                print(f"      {dt.date()}: close={row['close']:.1f}, 111MA={row['ma111']:.1f}, 2x350MA={row['ma350x2']:.1f} -> {max_dd:.1f}% in 60d")
        else:
            print(f"    No Pi Cycle crosses since 2024")
            # Show current distance
            last = pi_valid.iloc[-1]
            gap = (last['ma111'] - last['ma350x2']) / last['ma350x2'] * 100
            print(f"    Current: 111MA={last['ma111']:.1f}, 2x350MA={last['ma350x2']:.1f}, gap={gap:.1f}%")
    else:
        print(f"    Insufficient data for Pi Cycle (need 350 days)")

    # ==========================================
    # 3. Bull Market Support Band
    # ==========================================
    print(f"\n  --- BULL MARKET SUPPORT BAND ---")
    # 20-week SMA + 21-week EMA on daily data (140 days / 147 days)
    daily['sma_20w'] = daily['close'].rolling(140).mean()
    daily['ema_21w'] = daily['close'].ewm(span=147).mean()
    
    bmsb = daily.dropna(subset=['sma_20w', 'ema_21w'])
    bmsb = bmsb[bmsb.index >= '2024-01-01']
    
    if len(bmsb) > 0:
        # Price above band = bull, below = bear
        bmsb['above_band'] = bmsb['close'] > bmsb[['sma_20w', 'ema_21w']].max(axis=1)
        bmsb['below_band'] = bmsb['close'] < bmsb[['sma_20w', 'ema_21w']].min(axis=1)
        
        # Find transitions
        prev_above = bmsb['above_band'].shift(1)
        prev_below = bmsb['below_band'].shift(1)
        
        lost_support = bmsb[(prev_above == True) & (bmsb['above_band'] == False)]
        regained = bmsb[(prev_below == True) & (bmsb['below_band'] == False)]
        
        print(f"    Lost Bull Market Support Band:")
        for dt, row in lost_support.iterrows():
            future = daily[daily.index >= dt].head(30)
            max_dd = ((future['low'].min() - row['close']) / row['close'] * 100) if len(future) > 0 else 0
            recovered = ((future['high'].max() - row['close']) / row['close'] * 100) if len(future) > 0 else 0
            band_top = max(row['sma_20w'], row['ema_21w'])
            print(f"      {dt.date()}: close={row['close']:.1f}, band={band_top:.1f} -> 30d: dd={max_dd:.1f}%, bounce={recovered:.1f}%")
        
        # Current status
        last = bmsb.iloc[-1]
        band_top = max(last['sma_20w'], last['ema_21w'])
        band_bot = min(last['sma_20w'], last['ema_21w'])
        status = "ABOVE" if last['above_band'] else "BELOW" if last['below_band'] else "IN BAND"
        print(f"    Current: close={last['close']:.1f}, band=[{band_bot:.1f}-{band_top:.1f}], status={status}")


print("\n\n" + "=" * 90)
print("SUMMARY: STEVE'S FRAMEWORK APPLICABILITY")
print("=" * 90)
print("""
Key questions:
1. Does 2W/3W StochRSI with 97 threshold work better than 1W with 80?
2. Does Pi Cycle Top add value for our timeframe?
3. Does Bull Market Support Band help distinguish corrections from bears?

Note: Steve's framework is designed for BTC MACRO cycles (multi-year).
Our V13 needs signals for INTERMEDIATE phases (weeks to months).
The 2W/3W timeframe may be too slow for our use case, but the 97 threshold
and "leaving the road" concept could improve our 1W signals.
""")
