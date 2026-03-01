"""
Death Cross -> Bottom Timing Analysis
For each coin, find all SMA50/SMA200 death crosses and measure days to actual bottom.
Brett's hypothesis: BTC bottoms ~33 days after death cross. Test all coins.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'

def load_daily(coin):
    """Load daily candles for a coin."""
    conn = sqlite3.connect(str(DB_PATH))
    base = coin.split('/')[0].upper()
    
    # Try candles_daily first
    df = pd.read_sql_query(
        f"SELECT * FROM candles_daily WHERE symbol LIKE '{base}%' ORDER BY timestamp",
        conn
    )
    
    if df.empty:
        # Fallback: resample from 1h candles
        df_1h = pd.read_sql_query(
            f"SELECT * FROM candles WHERE symbol LIKE '{base}%' AND timeframe='1h' ORDER BY timestamp",
            conn
        )
        if df_1h.empty:
            conn.close()
            return pd.DataFrame()
        
        df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
        df_1h = df_1h.set_index('timestamp')
        df = df_1h.resample('1D').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 
            'close': 'last', 'volume': 'sum'
        }).dropna()
        df = df.reset_index()
    
    conn.close()
    
    # Handle epoch ms timestamps
    if df['timestamp'].dtype in ['int64', 'float64']:
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    else:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp').sort_index()
    df = df[~df.index.duplicated(keep='last')]  # Remove duplicate timestamps
    df = df[df.index.notna()]  # Remove NaT timestamps
    
    return df


def resample_3d(df):
    """Resample daily candles to 3-day candles and compute SMAs."""
    df_3d = df.resample('3D').agg({
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'volume': 'sum'
    }).dropna()
    df_3d['sma50'] = df_3d['close'].rolling(50).mean()
    df_3d['sma200'] = df_3d['close'].rolling(200).mean()
    return df_3d


def find_death_crosses(df, compute_sma=False):
    """Find all death cross events (SMA50 crosses below SMA200).
    If compute_sma=True, compute SMAs on this df. Otherwise assume they exist."""
    if compute_sma or 'sma50' not in df.columns:
        df = df.copy()
        df['sma50'] = df['close'].rolling(50).mean()
        df['sma200'] = df['close'].rolling(200).mean()
    
    crosses = []
    prev_above = None
    
    for i in range(len(df)):
        if pd.isna(df['sma50'].iloc[i]) or pd.isna(df['sma200'].iloc[i]):
            continue
        
        currently_above = df['sma50'].iloc[i] > df['sma200'].iloc[i]
        
        if prev_above is not None and prev_above and not currently_above:
            # Death cross: SMA50 just crossed below SMA200
            crosses.append({
                'date': df.index[i],
                'price': df['close'].iloc[i],
                'sma50': df['sma50'].iloc[i],
                'sma200': df['sma200'].iloc[i],
            })
        
        prev_above = currently_above
    
    return crosses


def find_bottom_after(df, cross_date, max_days=120):
    """Find the lowest price within max_days after a death cross."""
    end_date = cross_date + pd.Timedelta(days=max_days)
    window = df.loc[cross_date:end_date]
    
    if window.empty:
        return None
    
    bottom_idx = window['low'].idxmin()
    bottom_price = window['low'].min()
    days_to_bottom = (bottom_idx - cross_date).days
    
    # Also find the price 60 days after bottom (to see recovery)
    recovery_date = bottom_idx + pd.Timedelta(days=60)
    recovery_window = df.loc[bottom_idx:recovery_date]
    recovery_price = recovery_window['close'].iloc[-1] if len(recovery_window) > 0 else None
    recovery_pct = ((recovery_price - bottom_price) / bottom_price * 100) if recovery_price else None
    
    return {
        'bottom_date': bottom_idx,
        'bottom_price': bottom_price,
        'days_to_bottom': days_to_bottom,
        'cross_price': float(df.loc[cross_date, 'close'].iloc[0]) if hasattr(df.loc[cross_date, 'close'], 'iloc') else float(df.loc[cross_date, 'close']),
        'drawdown_pct': float((bottom_price - (df.loc[cross_date, 'close'].iloc[0] if hasattr(df.loc[cross_date, 'close'], 'iloc') else df.loc[cross_date, 'close'])) / (df.loc[cross_date, 'close'].iloc[0] if hasattr(df.loc[cross_date, 'close'], 'iloc') else df.loc[cross_date, 'close']) * 100),
        'recovery_60d_pct': recovery_pct,
    }


def find_golden_crosses(df):
    """Find all golden cross events (SMA50 crosses above SMA200)."""
    crosses = []
    prev_above = None
    
    for i in range(len(df)):
        if pd.isna(df['sma50'].iloc[i]) or pd.isna(df['sma200'].iloc[i]):
            continue
        
        currently_above = df['sma50'].iloc[i] > df['sma200'].iloc[i]
        
        if prev_above is not None and not prev_above and currently_above:
            crosses.append(df.index[i])
        
        prev_above = currently_above
    
    return crosses


def main():
    coins = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']
    
    print("=" * 120)
    print("  DEATH CROSS -> BOTTOM TIMING ANALYSIS (3-DAY CANDLES)")
    print("  Hypothesis: BTC bottoms ~33 days after death cross. Using 3D resampled candles.")
    print("=" * 120)
    
    all_results = {}
    
    for coin in coins:
        print(f"\n{'='*80}")
        print(f"  {coin}")
        print(f"{'='*80}")
        
        df = load_daily(coin)
        if df.empty:
            print(f"  No data for {coin}")
            continue
        
        # Resample to 3-day candles
        df_3d = resample_3d(df)
        
        print(f"  Daily data: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')} ({len(df)} candles)")
        print(f"  3D resampled: {len(df_3d)} candles")
        
        # Find death crosses on 3-day candles
        death_crosses = find_death_crosses(df_3d)
        golden_crosses = find_golden_crosses(df_3d)
        
        print(f"  Death crosses found: {len(death_crosses)}")
        print(f"  Golden crosses found: {len(golden_crosses)}")
        
        if not death_crosses:
            continue
        
        results = []
        
        print(f"\n  {'Date':<14} {'Price':>10} {'Bottom Date':<14} {'Bottom$':>10} {'Days':>6} {'DD%':>8} {'Recovery 60d':>12}")
        print(f"  {'-'*14} {'-'*10} {'-'*14} {'-'*10} {'-'*6} {'-'*8} {'-'*12}")
        
        for cross in death_crosses:
            bottom = find_bottom_after(df, cross['date'], max_days=120)  # Use daily df for bottom precision
            if bottom:
                rec_str = f"{bottom['recovery_60d_pct']:+.1f}%" if bottom['recovery_60d_pct'] is not None else "N/A"
                print(f"  {cross['date'].strftime('%Y-%m-%d'):<14} ${cross['price']:>9,.0f} "
                      f"{bottom['bottom_date'].strftime('%Y-%m-%d'):<14} ${bottom['bottom_price']:>9,.0f} "
                      f"{bottom['days_to_bottom']:>6} {bottom['drawdown_pct']:>+7.1f}% {rec_str:>12}")
                results.append({**cross, **bottom})
        
        if results:
            days = [r['days_to_bottom'] for r in results]
            dds = [r['drawdown_pct'] for r in results]
            print(f"\n  Summary:")
            print(f"    Avg days to bottom: {np.mean(days):.1f}")
            print(f"    Median days to bottom: {np.median(days):.1f}")
            print(f"    Range: {min(days)} - {max(days)} days")
            print(f"    Avg drawdown from cross: {np.mean(dds):.1f}%")
            
            # ETF era only (2023+)
            etf_results = [r for r in results if r['date'] >= pd.Timestamp('2023-01-01')]
            if etf_results:
                etf_days = [r['days_to_bottom'] for r in etf_results]
                print(f"\n  ETF Era (2023+):")
                print(f"    Death crosses: {len(etf_results)}")
                print(f"    Avg days to bottom: {np.mean(etf_days):.1f}")
                print(f"    Median: {np.median(etf_days):.1f}")
                print(f"    Range: {min(etf_days)} - {max(etf_days)} days")
        
        all_results[coin] = results
    
    # Cross-coin summary
    print(f"\n{'='*120}")
    print(f"  CROSS-COIN SUMMARY")
    print(f"{'='*120}")
    
    print(f"\n  {'Coin':<8} {'Total DX':>10} {'ETF DX':>10} {'Avg Days':>10} {'Med Days':>10} {'Avg DD%':>10}")
    print(f"  {'-'*8} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
    
    for coin, results in all_results.items():
        if not results:
            continue
        etf = [r for r in results if r['date'] >= pd.Timestamp('2023-01-01')]
        target = etf if etf else results
        days = [r['days_to_bottom'] for r in target]
        dds = [r['drawdown_pct'] for r in target]
        era = "ETF" if etf else "ALL"
        print(f"  {coin:<8} {len(results):>10} {len(etf):>10} {np.mean(days):>10.1f} {np.median(days):>10.1f} {np.mean(dds):>+9.1f}%")
    
    # Brett's 33-day hypothesis
    print(f"\n  Brett's Hypothesis: BTC bottoms ~33 days after death cross")
    if 'BTC' in all_results and all_results['BTC']:
        btc_days = [r['days_to_bottom'] for r in all_results['BTC']]
        print(f"  BTC actual: avg {np.mean(btc_days):.1f} days, median {np.median(btc_days):.1f} days")
        within_window = sum(1 for d in btc_days if 25 <= d <= 45)
        print(f"  Within 25-45 day window: {within_window}/{len(btc_days)} ({within_window/len(btc_days)*100:.0f}%)")


if __name__ == '__main__':
    main()
