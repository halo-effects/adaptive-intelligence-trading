"""
2D Golden Cross → Top Timing Analysis

For each coin in ETF era (Jan 2023+):
- Find every 2D golden cross (SMA50 crosses above SMA200 on 2-day candles)
- Measure days from golden cross to the next engine top signal
- See if there's a consistent timing pattern we can use in the top signal stack
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'
COINS = ['ETH/USDT', 'SOL/USDT', 'BTC/USDT', 'LINK/USDT', 'XRP/USDT']
DISPLAY = {'ETH/USDT':'ETH', 'SOL/USDT':'SOL', 'BTC/USDT':'BTC', 'LINK/USDT':'LINK', 'XRP/USDT':'XRP'}

# ETF era start
ETF_START = pd.Timestamp('2023-01-01')

def load_daily(coin):
    conn = sqlite3.connect(DB)
    df = pd.read_sql(
        "SELECT timestamp, open, high, low, close, volume FROM candles_daily WHERE symbol=? ORDER BY timestamp",
        conn, params=[coin]
    )
    conn.close()
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('date').sort_index()
    return df

def resample_2d(daily):
    """Resample daily candles to 2-day candles."""
    df2 = daily.resample('2D').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    return df2

def find_golden_crosses(df2):
    """Find 2D golden crosses (SMA50 crosses above SMA200)."""
    df2 = df2.copy()
    df2['sma50'] = df2['close'].rolling(50).mean()
    df2['sma200'] = df2['close'].rolling(200).mean()
    df2 = df2.dropna(subset=['sma50', 'sma200'])
    
    crosses = []
    prev_above = None
    for i in range(len(df2)):
        above = df2['sma50'].iloc[i] > df2['sma200'].iloc[i]
        if prev_above is not None and not prev_above and above:
            crosses.append({
                'date': df2.index[i],
                'price': df2['close'].iloc[i],
                'sma50': df2['sma50'].iloc[i],
                'sma200': df2['sma200'].iloc[i],
            })
        prev_above = above
    return crosses

def find_engine_tops(daily, coin):
    """
    Find engine top signals using V13's logic:
    - 2W StochRSI OB93 (primary)
    - 1W OB85 (fallback)  
    - 1W K<50 (failsafe)
    
    Simplified: use weekly StochRSI thresholds on daily data resampled to weekly/biweekly.
    """
    from v13_signals import V13SignalPack
    
    base = coin.split('/')[0]
    try:
        pack = V13SignalPack(base + '/USDC')
    except Exception:
        pack = None
    
    # If signal pack works, use it to find top signals
    # Otherwise, use a simplified approach with weekly StochRSI
    tops = []
    
    # Resample to weekly
    weekly = daily.resample('1W').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    # Resample to biweekly (2W)
    biweekly = daily.resample('2W').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    
    def stochrsi(series, period=14, smooth_k=3, smooth_d=3):
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        min_rsi = rsi.rolling(period).min()
        max_rsi = rsi.rolling(period).max()
        stoch_rsi = (rsi - min_rsi) / (max_rsi - min_rsi) * 100
        k = stoch_rsi.rolling(smooth_k).mean()
        d = k.rolling(smooth_d).mean()
        return k, d
    
    # 2W StochRSI
    bw_k, bw_d = stochrsi(biweekly['close'])
    biweekly['stochrsi_k'] = bw_k
    
    # 1W StochRSI
    wk_k, wk_d = stochrsi(weekly['close'])
    weekly['stochrsi_k'] = wk_k
    
    # Find top signals: 2W K > 93 OR 1W K > 85 OR 1W K < 50 (failsafe after being > 85)
    # Track state: need to detect when K crosses thresholds
    
    # Primary: 2W StochRSI crosses above 93
    prev_k = None
    for date, row in biweekly.iterrows():
        k = row['stochrsi_k']
        if pd.notna(k) and pd.notna(prev_k):
            if prev_k <= 93 and k > 93:
                tops.append({'date': date, 'type': '2W_OB93', 'k': k})
        prev_k = k
    
    # Fallback: 1W StochRSI crosses above 85
    prev_k = None
    for date, row in weekly.iterrows():
        k = row['stochrsi_k']
        if pd.notna(k) and pd.notna(prev_k):
            if prev_k <= 85 and k > 85:
                tops.append({'date': date, 'type': '1W_OB85', 'k': k})
        prev_k = k
    
    # Sort and deduplicate (keep first within 30-day windows)
    tops.sort(key=lambda x: x['date'])
    deduped = []
    for t in tops:
        if not deduped or (t['date'] - deduped[-1]['date']).days > 30:
            deduped.append(t)
    
    return deduped

def analyze_coin(coin):
    name = DISPLAY[coin]
    print(f"\n{'='*60}")
    print(f"  {name} — 2D Golden Cross → Top Timing")
    print(f"{'='*60}")
    
    daily = load_daily(coin)
    df2 = resample_2d(daily)
    
    # Filter to ETF era for crosses
    crosses = find_golden_crosses(df2)
    crosses = [c for c in crosses if c['date'] >= ETF_START]
    
    # Find tops (need full history for warmup)
    tops = find_engine_tops(daily, coin)
    tops = [t for t in tops if t['date'] >= ETF_START]
    
    print(f"\n  2D Golden Crosses (ETF era): {len(crosses)}")
    for c in crosses:
        print(f"    {c['date'].strftime('%Y-%m-%d')} @ ${c['price']:.2f}  (SMA50=${c['sma50']:.2f}, SMA200=${c['sma200']:.2f})")
    
    print(f"\n  Engine Top Signals (ETF era): {len(tops)}")
    for t in tops:
        print(f"    {t['date'].strftime('%Y-%m-%d')} [{t['type']}] K={t['k']:.1f}")
    
    # For each golden cross, find next top signal
    results = []
    print(f"\n  Golden Cross → Next Top:")
    for gc in crosses:
        next_top = None
        for t in tops:
            if t['date'] > gc['date']:
                next_top = t
                break
        
        if next_top:
            days = (next_top['date'] - gc['date']).days
            # Find price at top
            closest_idx = daily.index.get_indexer([next_top['date']], method='nearest')[0]
            top_price = daily['close'].iloc[closest_idx]
            pct_gain = (top_price / gc['price'] - 1) * 100
            
            results.append({
                'gc_date': gc['date'],
                'gc_price': gc['price'],
                'top_date': next_top['date'],
                'top_type': next_top['type'],
                'days_to_top': days,
                'pct_gain': pct_gain,
            })
            print(f"    {gc['date'].strftime('%Y-%m-%d')} → {next_top['date'].strftime('%Y-%m-%d')} = {days}d  (+{pct_gain:.1f}% price gain)  [{next_top['type']}]")
        else:
            print(f"    {gc['date'].strftime('%Y-%m-%d')} → No top yet (still in uptrend or no signal)")
            results.append({
                'gc_date': gc['date'],
                'gc_price': gc['price'],
                'top_date': None,
                'top_type': None,
                'days_to_top': None,
                'pct_gain': None,
            })
    
    return results

def main():
    print("2D GOLDEN CROSS → TOP TIMING ANALYSIS")
    print("ETF Era (Jan 2023+)")
    print("="*60)
    
    all_results = {}
    for coin in COINS:
        try:
            results = analyze_coin(coin)
            all_results[DISPLAY[coin]] = results
        except Exception as e:
            print(f"\n  {DISPLAY[coin]}: ERROR — {e}")
            import traceback; traceback.print_exc()
    
    # Summary
    print(f"\n\n{'='*60}")
    print("  SUMMARY — Days from 2D Golden Cross to Top Signal")
    print(f"{'='*60}")
    
    all_days = []
    for name, results in all_results.items():
        days_list = [r['days_to_top'] for r in results if r['days_to_top'] is not None]
        if days_list:
            print(f"\n  {name}: {len(days_list)} samples")
            print(f"    Days: {days_list}")
            print(f"    Avg: {np.mean(days_list):.0f}d | Median: {np.median(days_list):.0f}d | Min: {min(days_list)}d | Max: {max(days_list)}d")
            all_days.extend(days_list)
    
    if all_days:
        print(f"\n  ALL COINS COMBINED: {len(all_days)} samples")
        print(f"    Avg: {np.mean(all_days):.0f}d | Median: {np.median(all_days):.0f}d | Min: {min(all_days)}d | Max: {max(all_days)}d")
        
        # Distribution
        print(f"\n  Distribution:")
        for bucket_label, lo, hi in [("0-30d", 0, 30), ("31-60d", 31, 60), ("61-90d", 61, 90), 
                                      ("91-120d", 91, 120), ("121-180d", 121, 180), ("180d+", 181, 9999)]:
            count = sum(1 for d in all_days if lo <= d <= hi)
            if count:
                print(f"    {bucket_label}: {count} ({count/len(all_days)*100:.0f}%)")

if __name__ == '__main__':
    main()
