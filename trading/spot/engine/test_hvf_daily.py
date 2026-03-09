import os
"""
Test Francis Hunt's HVF (Harmonic Volume Factor) / Vuvuzela pattern on daily candles
at known DCA transition points.

Goal: Can HVF detect energy building before markup/markdown breakouts?
Specifically: does it fire before BNB/XRP transitions that our 2W StochRSI misses?
"""
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

DB_PATH = Path(os.environ.get('AIT_CANDLES_DB', str(Path(__file__).resolve().parent.parent / "data" / "candles.db")))

# ── HVF Detection (upgraded for daily) ──────────────────────────────────────

def detect_swing_points(df, lookback=5):
    """Identify swing highs and lows using fractal method."""
    swings = []
    highs = df['high'].values
    lows = df['low'].values
    dates = df.index
    
    for i in range(lookback, len(df) - lookback):
        # Swing high: highest high in window
        if highs[i] == max(highs[i-lookback:i+lookback+1]):
            swings.append({'date': dates[i], 'type': 'high', 'price': highs[i], 'idx': i})
        # Swing low: lowest low in window
        if lows[i] == min(lows[i-lookback:i+lookback+1]):
            swings.append({'date': dates[i], 'type': 'low', 'price': lows[i], 'idx': i})
    
    return sorted(swings, key=lambda x: x['date'])


def hvf_vuvuzela_daily(df, lookback=30):
    """Detect vuvuzela pattern (volume funnel) on daily candles.
    Returns Series of scores 0-1 where higher = stronger vuvuzela."""
    vol = df['volume'].values
    result = pd.Series(0.0, index=df.index)
    
    for i in range(lookback, len(df)):
        window = vol[i-lookback:i]
        half = lookback // 2
        first_half = window[:half]
        second_half = window[half:]
        
        first_spread = np.max(first_half) - np.min(first_half)
        second_spread = np.max(second_half) - np.min(second_half)
        
        if first_spread > 0:
            contraction = max(0, min(1, 1.0 - second_spread / first_spread))
            first_avg = np.mean(first_half)
            second_avg = np.mean(second_half)
            vol_decline = max(0, min(1, 1.0 - second_avg / first_avg)) if first_avg > 0 else 0
            result.iloc[i] = contraction * 0.6 + vol_decline * 0.4
    
    return result


def hvf_harmonic_pattern(df, swings, tolerance=0.05):
    """Detect ABCD harmonic patterns at swing points.
    Checks if retracements match Fibonacci ratios."""
    patterns = []
    
    for i in range(3, len(swings)):
        A, B, C, D = swings[i-3], swings[i-2], swings[i-1], swings[i]
        
        # Need alternating high/low
        if A['type'] == B['type']:
            continue
            
        AB = abs(B['price'] - A['price'])
        if AB == 0:
            continue
        BC = abs(C['price'] - B['price'])
        CD = abs(D['price'] - C['price'])
        
        # BC retracement of AB
        bc_ratio = BC / AB
        # CD extension of BC
        cd_ratio = CD / BC if BC > 0 else 0
        
        # Check Fibonacci ratios (±tolerance)
        fib_retrace = [0.382, 0.5, 0.618, 0.786]
        fib_extend = [1.0, 1.272, 1.618, 2.0, 2.618]
        
        bc_match = any(abs(bc_ratio - f) < tolerance for f in fib_retrace)
        cd_match = any(abs(cd_ratio - f) < tolerance * 2 for f in fib_extend)
        
        if bc_match or cd_match:
            # Determine direction
            if D['type'] == 'low':
                direction = 'BULLISH'  # Pattern completes at a low → expect markup
            else:
                direction = 'BEARISH'  # Pattern completes at a high → expect markdown
            
            # Score based on ratio precision
            bc_precision = min(abs(bc_ratio - f) for f in fib_retrace) / tolerance
            score = max(0, 1.0 - bc_precision) * 0.5
            if cd_match:
                cd_precision = min(abs(cd_ratio - f) for f in fib_extend) / (tolerance * 2)
                score += max(0, 1.0 - cd_precision) * 0.5
            
            patterns.append({
                'date': D['date'],
                'direction': direction,
                'A': A['price'], 'B': B['price'], 'C': C['price'], 'D': D['price'],
                'bc_ratio': bc_ratio,
                'cd_ratio': cd_ratio,
                'score': score,
                'A_date': A['date'], 'D_date': D['date'],
            })
    
    return patterns


def volume_compression_score(df, window=20):
    """Measure volume compression (declining volume into a point).
    High score = volume is squeezing, energy building."""
    vol = df['volume'].values
    result = pd.Series(0.0, index=df.index)
    
    for i in range(window, len(df)):
        w = vol[i-window:i]
        # Linear regression slope of volume
        x = np.arange(window)
        slope = np.polyfit(x, w, 1)[0]
        avg_vol = np.mean(w)
        if avg_vol > 0:
            norm_slope = slope / avg_vol  # Normalized slope
            # Negative slope = declining volume = compression
            if norm_slope < 0:
                result.iloc[i] = min(1.0, abs(norm_slope) * 50)  # Scale
    
    return result


def price_range_compression(df, window=20):
    """Measure price range compression (tightening candles).
    High score = price is squeezing."""
    result = pd.Series(0.0, index=df.index)
    
    for i in range(window, len(df)):
        ranges = (df['high'].iloc[i-window:i] - df['low'].iloc[i-window:i]).values
        first_half = ranges[:window//2]
        second_half = ranges[window//2:]
        
        avg_first = np.mean(first_half)
        avg_second = np.mean(second_half)
        
        if avg_first > 0:
            compression = max(0, 1.0 - avg_second / avg_first)
            result.iloc[i] = min(1.0, compression)
    
    return result


def composite_hvf_score(df, lookback=30):
    """Composite HVF score combining vuvuzela, volume compression, and price compression."""
    vuvu = hvf_vuvuzela_daily(df, lookback)
    vol_comp = volume_compression_score(df, lookback)
    price_comp = price_range_compression(df, lookback)
    
    # Composite: vuvuzela (40%) + volume compression (30%) + price compression (30%)
    composite = vuvu * 0.4 + vol_comp * 0.3 + price_comp * 0.3
    return composite, vuvu, vol_comp, price_comp


# ── Known transition points ────────────────────────────────────────────────

# Ground truth: dates where DCA should have transitioned to MARKUP or MARKDOWN
TRANSITIONS = {
    'BTC/USDC': [
        {'date': '2024-10-15', 'to': 'MARKUP', 'note': 'BTC rally from 60K to 100K+'},
        {'date': '2025-01-20', 'to': 'MARKDOWN', 'note': 'BTC distribution → decline'},
    ],
    'ETH/USDC': [
        {'date': '2024-11-05', 'to': 'MARKUP', 'note': 'ETH rally from 2500 to 4000+'},
        {'date': '2025-01-10', 'to': 'MARKDOWN', 'note': 'ETH distribution → decline'},
    ],
    'SOL/USDC': [
        {'date': '2024-10-15', 'to': 'MARKUP', 'note': 'SOL rally from 150 to 260+'},
        {'date': '2025-01-20', 'to': 'MARKDOWN', 'note': 'SOL distribution → decline'},
    ],
    'BNB/USDT': [
        {'date': '2024-11-10', 'to': 'MARKUP', 'note': 'BNB breakout from 600 channel'},
        {'date': '2025-02-01', 'to': 'MARKDOWN', 'note': 'BNB breakdown from 700 range'},
    ],
    'XRP/USDT': [
        {'date': '2024-11-10', 'to': 'MARKUP', 'note': 'XRP breakout from 0.50 channel'},
        {'date': '2025-01-20', 'to': 'MARKDOWN', 'note': 'XRP topped at 3.40, declined'},
    ],
}


def test_coin(symbol):
    """Test HVF signals around known transition points for a coin."""
    db = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql(
        'SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp',
        db, params=(symbol,))
    db.close()
    
    if len(df) == 0:
        print(f"  No data for {symbol}")
        return
    
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('date', inplace=True)
    
    print(f"\n{'='*70}")
    print(f"  {symbol} ({len(df)} daily candles)")
    print(f"{'='*70}")
    
    # Compute HVF signals
    composite, vuvu, vol_comp, price_comp = composite_hvf_score(df, lookback=30)
    
    # Detect swing points and harmonic patterns
    swings = detect_swing_points(df, lookback=5)
    patterns = hvf_harmonic_pattern(df, swings)
    
    transitions = TRANSITIONS.get(symbol, [])
    
    for t in transitions:
        t_date = pd.Timestamp(t['date'])
        print(f"\n  Transition: DCA → {t['to']} around {t['date']} ({t['note']})")
        print(f"  {'─'*60}")
        
        # Look at HVF scores in the 30 days before transition
        window_start = t_date - pd.Timedelta(days=45)
        window_end = t_date + pd.Timedelta(days=5)
        
        mask = (df.index >= window_start) & (df.index <= window_end)
        window = df[mask]
        
        if len(window) == 0:
            print(f"  No data in window")
            continue
        
        # Print composite scores leading up to transition
        print(f"  {'Date':>12} {'Close':>10} {'Composite':>10} {'Vuvuzela':>10} {'VolComp':>10} {'PriceComp':>10} {'Volume':>12}")
        
        for d, row in window.iterrows():
            c = composite.get(d, 0)
            v = vuvu.get(d, 0)
            vc = vol_comp.get(d, 0)
            pc = price_comp.get(d, 0)
            marker = " ◄◄◄" if d.date() == t_date.date() else ""
            # Only print weekly to keep output manageable
            if d.day % 7 <= 1 or d.date() == t_date.date() or c > 0.3:
                print(f"  {d.date()} {row['close']:>10.2f} {c:>10.3f} {v:>10.3f} {vc:>10.3f} {pc:>10.3f} {row['volume']:>12.0f}{marker}")
        
        # Peak HVF score in the 30 days before transition
        pre_mask = (composite.index >= window_start) & (composite.index < t_date)
        pre_scores = composite[pre_mask]
        if len(pre_scores) > 0:
            peak_score = pre_scores.max()
            peak_date = pre_scores.idxmax()
            days_before = (t_date - peak_date).days
            print(f"\n  Peak composite score: {peak_score:.3f} on {peak_date.date()} ({days_before}d before transition)")
        
        # Check for harmonic patterns near transition
        nearby_patterns = [p for p in patterns 
                          if abs((p['date'] - t_date).days) < 30]
        if nearby_patterns:
            print(f"\n  Harmonic patterns near transition:")
            for p in nearby_patterns:
                print(f"    {p['D_date'].date()} {p['direction']} "
                      f"BC={p['bc_ratio']:.3f} CD={p['cd_ratio']:.3f} "
                      f"score={p['score']:.2f}")
        else:
            print(f"\n  No harmonic patterns detected near transition")


def main():
    print("HVF / Vuvuzela Analysis on Daily Candles")
    print("Testing at known DCA transition points")
    
    for symbol in ['BTC/USDC', 'ETH/USDC', 'SOL/USDC', 'BNB/USDT', 'XRP/USDT']:
        test_coin(symbol)
    
    # Summary: what threshold works?
    print(f"\n{'='*70}")
    print(f"  SIGNAL QUALITY SUMMARY")
    print(f"{'='*70}")
    print("""
  Questions to answer:
  1. Does HVF composite score spike before known transitions?
  2. What threshold separates real transitions from noise?
  3. Does HVF fire for BNB/XRP where 2W StochRSI doesn't?
  4. How many days of lead time does HVF give?
  5. Are there false positives (high HVF but no transition)?
    """)


if __name__ == '__main__':
    main()
