"""
Test: Weekly StochRSI Bullish/Bearish Divergence as phase signal

Bullish divergence: Price makes lower low, StochRSI makes higher low (bottom signal)
Bearish divergence: Price makes higher high, StochRSI makes lower high (top signal)

Tests on weekly timeframe for BTC, ETH, SOL since 2024-01-01
"""

import sqlite3, pandas as pd, numpy as np
from datetime import timedelta

DB_PATH = 'trading/spot/data/candles.db'

def stoch_rsi(close):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi_low = rsi.rolling(14).min()
    rsi_high = rsi.rolling(14).max()
    stoch_k = 100 * (rsi - rsi_low) / (rsi_high - rsi_low + 1e-10)
    stoch_k = stoch_k.rolling(3).mean()
    stoch_d = stoch_k.rolling(3).mean()
    return stoch_k, stoch_d, rsi


def find_local_extremes(series, order=3):
    """Find local minima and maxima using simple comparison"""
    mins = []
    maxs = []
    vals = series.values
    idx = series.index
    for i in range(order, len(vals) - order):
        if all(vals[i] <= vals[i-j] for j in range(1, order+1)) and \
           all(vals[i] <= vals[i+j] for j in range(1, order+1)):
            mins.append((idx[i], vals[i]))
        if all(vals[i] >= vals[i-j] for j in range(1, order+1)) and \
           all(vals[i] >= vals[i+j] for j in range(1, order+1)):
            maxs.append((idx[i], vals[i]))
    return mins, maxs


def find_divergences(price_series, stoch_k, lookback_weeks=20):
    """
    Find bullish and bearish divergences between price and StochRSI.
    
    Bullish: price lower low + StochRSI higher low (within lookback window)
    Bearish: price higher high + StochRSI lower high (within lookback window)
    """
    price_mins, price_maxs = find_local_extremes(price_series, order=2)
    stoch_mins, stoch_maxs = find_local_extremes(stoch_k, order=2)
    
    bullish_divs = []
    bearish_divs = []
    
    # Bullish: compare consecutive price lows vs StochRSI lows
    for i in range(1, len(price_mins)):
        p_date1, p_val1 = price_mins[i-1]
        p_date2, p_val2 = price_mins[i]
        
        # Price made lower low
        if p_val2 >= p_val1:
            continue
        
        # Within lookback?
        if (p_date2 - p_date1).days > lookback_weeks * 7:
            continue
        
        # Find StochRSI lows near these dates (within 2 weeks)
        s_val1 = None
        s_val2 = None
        for s_date, s_val in stoch_mins:
            if abs((s_date - p_date1).days) <= 14:
                s_val1 = s_val
            if abs((s_date - p_date2).days) <= 14:
                s_val2 = s_val
        
        # StochRSI made higher low (divergence)
        if s_val1 is not None and s_val2 is not None and s_val2 > s_val1:
            bullish_divs.append({
                'date': p_date2,
                'price_low1': p_val1, 'price_low2': p_val2,
                'stoch_low1': s_val1, 'stoch_low2': s_val2,
                'price_date1': p_date1, 'price_date2': p_date2,
            })
    
    # Bearish: compare consecutive price highs vs StochRSI highs
    for i in range(1, len(price_maxs)):
        p_date1, p_val1 = price_maxs[i-1]
        p_date2, p_val2 = price_maxs[i]
        
        # Price made higher high
        if p_val2 <= p_val1:
            continue
        
        # Within lookback?
        if (p_date2 - p_date1).days > lookback_weeks * 7:
            continue
        
        # Find StochRSI highs near these dates
        s_val1 = None
        s_val2 = None
        for s_date, s_val in stoch_maxs:
            if abs((s_date - p_date1).days) <= 14:
                s_val1 = s_val
            if abs((s_date - p_date2).days) <= 14:
                s_val2 = s_val
        
        # StochRSI made lower high (divergence)
        if s_val1 is not None and s_val2 is not None and s_val2 < s_val1:
            bearish_divs.append({
                'date': p_date2,
                'price_high1': p_val1, 'price_high2': p_val2,
                'stoch_high1': s_val1, 'stoch_high2': s_val2,
                'price_date1': p_date1, 'price_date2': p_date2,
            })
    
    return bullish_divs, bearish_divs


db = sqlite3.connect(DB_PATH)

print("WEEKLY STOCHRSI DIVERGENCE ANALYSIS")
print("=" * 90)
print()
print("Bullish divergence = Price lower low + StochRSI higher low (potential bottom)")
print("Bearish divergence = Price higher high + StochRSI lower high (potential top)")
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
    
    # Weekly OHLC
    wk_close = daily['close'].resample('W').last().dropna()
    wk_low = daily['low'].resample('W').min().dropna()
    wk_high = daily['high'].resample('W').max().dropna()
    
    k, d, rsi = stoch_rsi(wk_close)
    
    # Use weekly lows/highs for divergence (more accurate than close)
    bullish, bearish = find_divergences(wk_low, k, lookback_weeks=20)
    
    # Also check with weekly close for comparison
    bullish_close, bearish_close = find_divergences(wk_close, k, lookback_weeks=20)
    
    print(f"\n{'='*70}")
    print(f"  {coin} ({sym[0]})")
    print(f"{'='*70}")
    
    # Filter to recent period
    bullish = [b for b in bullish if b['date'] >= pd.Timestamp('2024-01-01')]
    bearish = [b for b in bearish if b['date'] >= pd.Timestamp('2024-01-01')]
    bullish_close = [b for b in bullish_close if b['date'] >= pd.Timestamp('2024-01-01')]
    bearish_close = [b for b in bearish_close if b['date'] >= pd.Timestamp('2024-01-01')]
    
    print(f"\n  BULLISH DIVERGENCES (weekly lows): {len(bullish)} found")
    for b in bullish:
        # Measure outcome: 60 days forward
        future = daily[daily.index >= b['date']].head(60)
        if len(future) > 0:
            entry = wk_close[wk_close.index >= b['date']].iloc[0] if len(wk_close[wk_close.index >= b['date']]) > 0 else 0
            max_up = ((future['high'].max() - entry) / entry * 100) if entry > 0 else 0
            max_down = ((future['low'].min() - entry) / entry * 100) if entry > 0 else 0
            correct = max_up > 15
        else:
            max_up = max_down = 0
            correct = False
        
        print(f"    {b['date'].date()}: Price lows {b['price_low1']:.1f} -> {b['price_low2']:.1f} (lower)")
        print(f"      StochRSI lows {b['stoch_low1']:.1f} -> {b['stoch_low2']:.1f} (higher = divergence)")
        print(f"      Span: {b['price_date1'].date()} -> {b['price_date2'].date()}")
        print(f"      60d outcome: up={max_up:.1f}%, down={max_down:.1f}% {'CORRECT' if correct else 'WRONG'}")
    
    print(f"\n  BEARISH DIVERGENCES (weekly highs): {len(bearish)} found")
    for b in bearish:
        future = daily[daily.index >= b['date']].head(60)
        if len(future) > 0:
            entry = wk_close[wk_close.index >= b['date']].iloc[0] if len(wk_close[wk_close.index >= b['date']]) > 0 else 0
            max_down = ((future['low'].min() - entry) / entry * 100) if entry > 0 else 0
            max_up = ((future['high'].max() - entry) / entry * 100) if entry > 0 else 0
            correct = max_down < -10
        else:
            max_up = max_down = 0
            correct = False
        
        print(f"    {b['date'].date()}: Price highs {b['price_high1']:.1f} -> {b['price_high2']:.1f} (higher)")
        print(f"      StochRSI highs {b['stoch_high1']:.1f} -> {b['stoch_high2']:.1f} (lower = divergence)")
        print(f"      Span: {b['price_date1'].date()} -> {b['price_date2'].date()}")
        print(f"      60d outcome: down={max_down:.1f}%, up={max_up:.1f}% {'CORRECT' if correct else 'WRONG'}")
    
    # Also test with close prices
    extra_bull = [b for b in bullish_close if b['date'] not in [x['date'] for x in bullish]]
    extra_bear = [b for b in bearish_close if b['date'] not in [x['date'] for x in bearish]]
    if extra_bull:
        print(f"\n  Additional bullish divs (close-based only): {len(extra_bull)}")
        for b in extra_bull:
            print(f"    {b['date'].date()}: Close lows {b['price_low1']:.1f} -> {b['price_low2']:.1f}")
    if extra_bear:
        print(f"\n  Additional bearish divs (close-based only): {len(extra_bear)}")
        for b in extra_bear:
            print(f"    {b['date'].date()}: Close highs {b['price_high1']:.1f} -> {b['price_high2']:.1f}")

# Summary
print("\n\n" + "=" * 90)
print("DIVERGENCE SUMMARY")
print("=" * 90)
print("""
Key question: Does weekly StochRSI divergence add value over simple OB/OS exits?

Prior testing on 1h RSI divergence (SPRING_DIVERGENCE_ANALYSIS.md) showed:
- RSI divergence was present at 83% of spring entries — ALL were BAD
- "The divergence forms too early in the capitulation"
- But that was 1h timeframe. Weekly should be more reliable.

Compare with weekly StochRSI OB/OS exit signals:
- OB exit + daily confirm: caught major tops with high accuracy
- OS exit + daily confirm: caught major bottoms  
- 15-25 day lag, missing 10-20% of moves

Divergence ADDS to OB/OS by:
1. Potentially earlier signal (divergence forms BEFORE the crossover)
2. Higher conviction when BOTH divergence AND OB/OS exit align
3. Distinguishing corrections (no divergence) from real tops (divergence present)
""")
