"""
Bottom Signal Stack Analysis
At each actual bottom (from death cross analysis), what did the signals look like?
- Days from death cross
- CFGI (coin-specific)
- Weekly RSI
- Price vs SMA200
- Was there a Spring pattern (break below support + recovery)?
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'


def load_daily(coin):
    conn = sqlite3.connect(str(DB_PATH))
    base = coin.split('/')[0].upper()
    df = pd.read_sql_query(
        f"SELECT * FROM candles_daily WHERE symbol LIKE '{base}%' ORDER BY timestamp", conn)
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


def load_cfgi(coin):
    """Load CFGI data for a coin."""
    conn = sqlite3.connect(str(DB_PATH))
    base = coin.split('/')[0].upper()
    df = pd.read_sql_query(
        f"SELECT * FROM cfgi_daily WHERE symbol LIKE '{base}%' ORDER BY date", conn)
    if df.empty:
        # Try without symbol filter (market average)
        df = pd.read_sql_query("SELECT * FROM cfgi_daily WHERE symbol='market' ORDER BY date", conn)
    conn.close()
    if df.empty:
        return pd.Series(dtype=float)
    df['date'] = pd.to_datetime(df['date'], format='mixed')
    df = df.set_index('date').sort_index()
    df = df[~df.index.duplicated(keep='last')]
    return df.get('value', df.iloc[:, -1])  # Get the value column


def compute_weekly_rsi(daily_close, period=7):
    """Compute RSI on weekly resampled data."""
    weekly = daily_close.resample('W').last().dropna()
    delta = weekly.diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def detect_spring_at_bottom(df, bottom_date, lookback=10, forward=5):
    """Check if there's a spring-like pattern around the bottom date.
    Spring = price breaks below recent support, then quickly recovers above it."""
    try:
        bot_idx = df.index.get_loc(bottom_date)
    except KeyError:
        # Find nearest date
        nearest = df.index[df.index.get_indexer([bottom_date], method='nearest')[0]]
        bot_idx = df.index.get_loc(nearest)
    
    if bot_idx < lookback or bot_idx + forward >= len(df):
        return None
    
    # Support = lowest close in lookback period BEFORE the bottom
    pre_window = df.iloc[bot_idx - lookback:bot_idx]
    support = pre_window['low'].min()
    
    # Did price break below support at bottom?
    bottom_low = df.iloc[bot_idx]['low']
    broke_support = bottom_low < support
    
    # Did price recover above support within forward days?
    post_window = df.iloc[bot_idx:bot_idx + forward + 1]
    recovered = any(post_window['close'] > support)
    
    # Volume spike at bottom?
    vol_avg = pre_window['volume'].mean()
    bot_vol = df.iloc[bot_idx]['volume']
    vol_ratio = bot_vol / vol_avg if vol_avg > 0 else 0
    
    return {
        'broke_support': broke_support,
        'recovered': recovered,
        'is_spring': broke_support and recovered,
        'support_level': support,
        'bottom_low': bottom_low,
        'break_pct': (support - bottom_low) / support * 100 if support > 0 else 0,
        'vol_ratio': vol_ratio,
        'recovery_days': None
    }


def find_death_crosses(df):
    df['sma50'] = df['close'].rolling(50).mean()
    df['sma200'] = df['close'].rolling(200).mean()
    
    crosses = []
    prev_above = None
    for i in range(len(df)):
        if pd.isna(df['sma50'].iloc[i]) or pd.isna(df['sma200'].iloc[i]):
            continue
        currently_above = df['sma50'].iloc[i] > df['sma200'].iloc[i]
        if prev_above is not None and prev_above and not currently_above:
            crosses.append(df.index[i])
        prev_above = currently_above
    return crosses


def find_bottom_after(df, cross_date, max_days=120):
    end_date = cross_date + pd.Timedelta(days=max_days)
    window = df.loc[cross_date:end_date]
    if window.empty:
        return None, None
    bottom_idx = window['low'].idxmin()
    return bottom_idx, float(window['low'].min())


def main():
    coins = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']
    
    print("=" * 140)
    print("  BOTTOM SIGNAL STACK ANALYSIS")
    print("  At each actual bottom: what did death cross timing + CFGI + weekly RSI + Spring look like?")
    print("=" * 140)
    
    for coin in coins:
        print(f"\n{'='*100}")
        print(f"  {coin}")
        print(f"{'='*100}")
        
        df = load_daily(coin)
        if df.empty:
            print(f"  No daily data")
            continue
        
        cfgi = load_cfgi(coin)
        weekly_rsi = compute_weekly_rsi(df['close'], period=7)
        
        # SMA200 overextension
        df['sma200'] = df['close'].rolling(200).mean()
        df['sma200_pct'] = (df['close'] - df['sma200']) / df['sma200'] * 100
        
        death_crosses = find_death_crosses(df)
        
        # Focus on ETF era
        death_crosses = [dc for dc in death_crosses if dc >= pd.Timestamp('2023-01-01')]
        
        if not death_crosses:
            print(f"  No ETF-era death crosses")
            continue
        
        print(f"  ETF-era death crosses: {len(death_crosses)}")
        print(f"  CFGI data: {len(cfgi)} days" if len(cfgi) > 0 else "  CFGI: No data")
        print(f"  Weekly RSI data: {len(weekly_rsi)} weeks")
        
        print(f"\n  {'DC Date':<12} {'Days':>5} {'Bottom':<12} {'Price':>8} {'CFGI':>6} {'W-RSI':>6} {'SMA200%':>8} {'Spring':>8} {'Break%':>7} {'VolRat':>7}")
        print(f"  {'-'*12} {'-'*5} {'-'*12} {'-'*8} {'-'*6} {'-'*6} {'-'*8} {'-'*8} {'-'*7} {'-'*7}")
        
        for dc in death_crosses:
            bottom_date, bottom_price = find_bottom_after(df, dc)
            if bottom_date is None:
                continue
            
            days = (bottom_date - dc).days
            
            # CFGI at bottom
            cfgi_val = None
            if len(cfgi) > 0:
                # Find nearest CFGI value
                nearby = cfgi.index[cfgi.index.get_indexer([bottom_date], method='nearest')]
                if len(nearby) > 0 and abs((nearby[0] - bottom_date).days) <= 7:
                    cfgi_val = float(cfgi.loc[nearby[0]])
            
            # Weekly RSI at bottom
            wrsi_val = None
            nearby_rsi = weekly_rsi.index[weekly_rsi.index.get_indexer([bottom_date], method='nearest')]
            if len(nearby_rsi) > 0 and abs((nearby_rsi[0] - bottom_date).days) <= 7:
                wrsi_val = float(weekly_rsi.loc[nearby_rsi[0]])
            
            # SMA200 overextension at bottom
            sma200_pct = None
            if bottom_date in df.index:
                sma200_pct = df.loc[bottom_date, 'sma200_pct']
                if hasattr(sma200_pct, 'iloc'):
                    sma200_pct = float(sma200_pct.iloc[0])
                else:
                    sma200_pct = float(sma200_pct)
            
            # Spring detection
            spring = detect_spring_at_bottom(df, bottom_date)
            
            cfgi_str = f"{cfgi_val:.0f}" if cfgi_val is not None else "N/A"
            wrsi_str = f"{wrsi_val:.1f}" if wrsi_val is not None else "N/A"
            sma_str = f"{sma200_pct:+.0f}%" if sma200_pct is not None and not np.isnan(sma200_pct) else "N/A"
            spring_str = "YES" if spring and spring['is_spring'] else "no"
            break_str = f"{spring['break_pct']:.1f}%" if spring and spring['broke_support'] else "-"
            vol_str = f"{spring['vol_ratio']:.1f}x" if spring else "-"
            
            print(f"  {dc.strftime('%Y-%m-%d'):<12} {days:>5} {bottom_date.strftime('%Y-%m-%d'):<12} ${bottom_price:>7,.0f} {cfgi_str:>6} {wrsi_str:>6} {sma_str:>8} {spring_str:>8} {break_str:>7} {vol_str:>7}")
    
    # Signal convergence summary
    print(f"\n{'='*140}")
    print(f"  SIGNAL CONVERGENCE AT BOTTOMS")
    print(f"{'='*140}")
    print(f"\n  The ideal bottom signal stack:")
    print(f"  1. Death cross fired 25-90 days ago (timing context)")
    print(f"  2. CFGI < 25 (extreme fear)")  
    print(f"  3. Weekly RSI(7) < 30 (oversold)")
    print(f"  4. Price below SMA200 (deep value)")
    print(f"  5. Spring pattern detected (structural confirmation)")


if __name__ == '__main__':
    main()
