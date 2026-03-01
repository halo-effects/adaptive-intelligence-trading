"""Test 2W StochRSI bottom signal: K pinned below 5, then K crosses above D."""
import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'

def compute_2w_stochrsi(coin, conn):
    sym = coin + '/USDT'
    df = pd.read_sql(
        'SELECT timestamp, open, high, low, close, volume FROM candles_daily WHERE symbol=? ORDER BY timestamp',
        conn, params=[sym])
    df['dt'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('dt').sort_index()
    df = df[~df.index.duplicated(keep='last')]

    w2 = df.resample('2W').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()

    # RSI(14)
    delta = w2['close'].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
    rs = avg_gain / avg_loss
    w2['rsi14'] = 100 - (100 / (1 + rs))

    # StochRSI(3,3,14,14)
    rsi = w2['rsi14']
    rsi_low = rsi.rolling(14).min()
    rsi_high = rsi.rolling(14).max()
    denom = rsi_high - rsi_low
    stoch_raw = ((rsi - rsi_low) / denom.replace(0, np.nan)) * 100
    w2['k'] = stoch_raw.rolling(3).mean()
    w2['d'] = w2['k'].rolling(3).mean()
    return w2


def analyze(coin, conn):
    w2 = compute_2w_stochrsi(coin, conn)
    
    # Find K cross above D
    w2['k_above_d'] = w2['k'] > w2['d']
    w2['cross_up'] = w2['k_above_d'] & ~w2['k_above_d'].shift(1).fillna(False)
    
    # Find oversold periods (K < 5)
    oversold = w2[w2['k'] < 5]
    
    print(f"\n{'='*60}")
    print(f"  {coin} -- 2W StochRSI Bottom Analysis")
    print(f"  Total 2W candles: {len(w2)}, Date range: {w2.index[0].date()} to {w2.index[-1].date()}")
    print(f"{'='*60}")
    
    if len(oversold) == 0:
        print("  No oversold periods found (K < 5)")
        return
    
    # Group consecutive oversold candles (within 20 days)
    groups = []
    current = []
    for dt in oversold.index:
        if not current or (dt - current[-1]).days <= 20:
            current.append(dt)
        else:
            groups.append(current)
            current = [dt]
    if current:
        groups.append(current)
    
    print(f"  Oversold periods: {len(groups)}")
    
    for g in groups:
        start = g[0]
        end = g[-1]
        duration = len(g)
        price_start = w2.loc[start, 'close']
        price_end = w2.loc[end, 'close']
        k_vals = [w2.loc[d, 'k'] for d in g]
        
        # Find next K cross above D after oversold
        future = w2[w2.index > end]
        crosses = future[future['cross_up']]
        
        print(f"\n  Period: {start.date()} to {end.date()} ({duration} candles, K range: {min(k_vals):.1f}-{max(k_vals):.1f})")
        print(f"    Price at start: ${price_start:,.2f}, at end: ${price_end:,.2f}")
        
        if len(crosses):
            cross_date = crosses.index[0]
            cross_price = crosses.iloc[0]['close']
            cross_k = crosses.iloc[0]['k']
            cross_d = crosses.iloc[0]['d']
            days_to_cross = (cross_date - end).days
            
            # Find actual bottom between start and cross
            window = w2[(w2.index >= start) & (w2.index <= cross_date)]
            bottom_idx = window['close'].idxmin()
            bottom_price = window['close'].min()
            days_late = (cross_date - bottom_idx).days
            pct_from_bottom = (cross_price - bottom_price) / bottom_price * 100
            
            print(f"    K cross above D: {cross_date.date()} (K={cross_k:.1f}, D={cross_d:.1f})")
            print(f"    Days after oversold ended: {days_to_cross}")
            print(f"    Actual bottom: {bottom_idx.date()} at ${bottom_price:,.2f}")
            print(f"    Cross price: ${cross_price:,.2f} ({pct_from_bottom:+.1f}% above bottom, {days_late}d late)")
        else:
            print(f"    ** STILL OVERSOLD / NO CROSS YET **")
            # Show current K and D
            last = w2.iloc[-1]
            print(f"    Current: K={last['k']:.2f}, D={last['d']:.2f}, price=${last['close']:,.2f}")


if __name__ == '__main__':
    conn = sqlite3.connect(str(DB))
    for coin in ['ETH', 'SOL', 'LINK', 'XRP', 'BTC', 'AAVE', 'BNB', 'HBAR']:
        try:
            analyze(coin, conn)
        except Exception as e:
            print(f"\n  {coin}: ERROR - {e}")
    conn.close()
