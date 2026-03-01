#!/usr/bin/env python3
"""Fast diagnostic test for TA Top Scorer on ETH chunk 8 data.

Optimized version that pre-calculates indicators once, then scores key periods.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime


def convert_timestamp_to_date(ts):
    """Convert timestamp to readable date."""
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d %H:%M')
    else:
        return str(ts)


def calculate_rsi(close_series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI for entire series."""
    delta = close_series.diff()
    gains = delta.where(delta > 0, 0.0)
    losses = -delta.where(delta < 0, 0.0)
    
    avg_gains = gains.rolling(window=period, min_periods=period).mean()
    avg_losses = losses.rolling(window=period, min_periods=period).mean()
    
    rs = avg_gains / avg_losses
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(close_series: pd.Series) -> dict:
    """Calculate MACD for entire series."""
    ema_fast = close_series.ewm(span=12).mean()
    ema_slow = close_series.ewm(span=26).mean()
    
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=9).mean()
    macd_histogram = macd_line - macd_signal
    
    return {
        'line': macd_line,
        'signal': macd_signal,
        'histogram': macd_histogram
    }


def find_swing_highs(df: pd.DataFrame, lookback: int = 24) -> pd.Series:
    """Find swing highs for entire series."""
    swing_flags = pd.Series(False, index=df.index)
    
    for i in range(lookback, len(df) - lookback):
        price = df.iloc[i]['high']
        
        # Check if it's a local maximum
        is_high = True
        for k in range(i - lookback, i + lookback + 1):
            if k != i and df.iloc[k]['high'] >= price:
                is_high = False
                break
        
        if is_high:
            swing_flags.iloc[i] = True
    
    return swing_flags


def score_rsi_divergence(df: pd.DataFrame, rsi: pd.Series, swing_flags: pd.Series, i: int) -> float:
    """Score RSI bearish divergence at index i."""
    current_price = df.iloc[i]['high']
    current_rsi = rsi.iloc[i]
    
    if pd.isna(current_rsi):
        return 0.0
    
    # Find most recent swing high before current index
    prev_swings = swing_flags.iloc[max(0, i-168):i][swing_flags.iloc[max(0, i-168):i]]
    
    if len(prev_swings) == 0:
        return 0.0
    
    prev_idx = prev_swings.index[-1]
    prev_price = df.iloc[prev_idx]['high']
    prev_rsi = rsi.iloc[prev_idx]
    
    if pd.isna(prev_rsi):
        return 0.0
    
    # Check for bearish divergence
    if current_price > prev_price and current_rsi < prev_rsi:
        # Confirm current price is near recent high
        recent_high = df.iloc[max(0, i-48):i+1]['high'].max()
        if current_price >= recent_high * 0.95:
            return 25.0
    
    return 0.0


def score_volume_divergence(df: pd.DataFrame, swing_flags: pd.Series, i: int) -> float:
    """Score volume divergence at index i."""
    current_price = df.iloc[i]['high']
    current_vol_avg = df.iloc[max(0, i-23):i+1]['volume'].mean()
    
    # Find most recent swing high
    prev_swings = swing_flags.iloc[max(0, i-168):i][swing_flags.iloc[max(0, i-168):i]]
    
    if len(prev_swings) == 0:
        return 0.0
    
    prev_idx = prev_swings.index[-1]
    prev_price = df.iloc[prev_idx]['high']
    prev_vol_avg = df.iloc[max(0, prev_idx-23):prev_idx+1]['volume'].mean()
    
    # Check for volume divergence
    if current_price > prev_price and current_vol_avg < prev_vol_avg:
        ratio = 1 - (current_vol_avg / prev_vol_avg)
        return min(25.0, max(0.0, 25 * ratio))
    
    return 0.0


def score_upper_wick_rejection(df: pd.DataFrame, i: int) -> float:
    """Score upper wick rejection at index i."""
    rejection_count = 0
    
    lookback = min(48, i)
    start_idx = max(0, i - lookback)
    
    for j in range(start_idx, i + 1):
        row = df.iloc[j]
        open_price = row['open']
        high_price = row['high']
        close_price = row['close']
        
        body_size = abs(close_price - open_price)
        upper_wick = high_price - max(open_price, close_price)
        
        is_bearish = close_price < open_price
        has_large_wick = upper_wick > 2 * body_size if body_size > 0 else upper_wick > 0
        
        if is_bearish and has_large_wick:
            rejection_count += 1
    
    return min(25.0, rejection_count * 5.0)


def score_momentum_stall(df: pd.DataFrame, macd: dict, i: int) -> float:
    """Score momentum stall at index i."""
    if i < 30:
        return 0.0
    
    current_price = df.iloc[i]['close']
    
    # Check if near recent high
    recent_high = df.iloc[max(0, i-24):i+1]['high'].max()
    if current_price < recent_high * 0.97:
        return 0.0
    
    # Count declining MACD histogram
    histogram = macd['histogram']
    consecutive_declining = 0
    
    for j in range(i, max(i-10, 0), -1):
        if j < 1:
            break
        
        current_hist = histogram.iloc[j]
        prev_hist = histogram.iloc[j-1]
        
        if pd.isna(current_hist) or pd.isna(prev_hist):
            break
        
        if current_hist < prev_hist:
            consecutive_declining += 1
        else:
            break
    
    if consecutive_declining >= 3:
        return min(25.0, consecutive_declining * 5.0)
    
    return 0.0


def determine_phase(score: float) -> str:
    """Determine phase from score."""
    if score >= 70:
        return "EXIT"
    elif score >= 50:
        return "WIND_DOWN"
    elif score >= 30:
        return "TIGHTEN"
    else:
        return "NORMAL"


def run_fast_diagnostic():
    """Run optimized diagnostic on key periods."""
    data_file = "trading/spot/data/dwell_cache/ETH_USDT_1h_2024-09-10_2025-01-16.csv"
    print(f"Loading data from {data_file}")
    
    df = pd.read_csv(data_file)
    print(f"Loaded {len(df)} candles from {convert_timestamp_to_date(df.iloc[0]['timestamp'])} to {convert_timestamp_to_date(df.iloc[-1]['timestamp'])}")
    
    # Pre-calculate indicators
    print("\nPre-calculating technical indicators...")
    rsi = calculate_rsi(df['close'])
    macd = calculate_macd(df['close'])
    swing_flags = find_swing_highs(df)
    
    print(f"Found {swing_flags.sum()} swing highs")
    
    # Score key periods and sample points
    print("\nScoring selected candles...")
    
    scores = []
    
    # Sample every 10th candle after sufficient lookback
    sample_indices = list(range(200, len(df), 10))  # Start after 200 candles for indicator stability
    
    print(f"Scoring {len(sample_indices)} sample points...")
    
    for i in sample_indices:
        # Calculate component scores
        rsi_div = score_rsi_divergence(df, rsi, swing_flags, i)
        vol_div = score_volume_divergence(df, swing_flags, i)
        wick_rej = score_upper_wick_rejection(df, i)
        momentum = score_momentum_stall(df, macd, i)
        
        total_score = rsi_div + vol_div + wick_rej + momentum
        phase = determine_phase(total_score)
        
        scores.append({
            'index': i,
            'timestamp': df.iloc[i]['timestamp'],
            'date': convert_timestamp_to_date(df.iloc[i]['timestamp']),
            'price': df.iloc[i]['close'],
            'high': df.iloc[i]['high'],
            'score': total_score,
            'phase': phase,
            'rsi_div': rsi_div,
            'vol_div': vol_div,
            'wick_rej': wick_rej,
            'momentum': momentum,
        })
    
    scores_df = pd.DataFrame(scores)
    
    # Print summary statistics
    print(f"\nSCORE STATISTICS (from {len(scores)} sample points):")
    print(f"  Max score: {scores_df['score'].max():.1f}")
    print(f"  Mean score: {scores_df['score'].mean():.1f}")
    print(f"  Std dev: {scores_df['score'].std():.1f}")
    print(f"  Scores >= 50: {(scores_df['score'] >= 50).sum()} points")
    print(f"  Scores >= 70: {(scores_df['score'] >= 70).sum()} points")
    
    # Phase distribution
    phase_counts = scores_df['phase'].value_counts()
    print(f"\nPHASE DISTRIBUTION:")
    for phase, count in phase_counts.items():
        pct = count / len(scores_df) * 100
        print(f"  {phase}: {count} points ({pct:.1f}%)")
    
    # Print top 20 scores
    top_scores = scores_df.nlargest(20, 'score')
    print(f"\nTOP 20 SCORES:")
    print(f"{'Date':<17} {'Price':<8} {'Score':<6} {'Phase':<10} {'RSI':<4} {'Vol':<4} {'Wick':<4} {'Mom':<4}")
    print("-" * 80)
    
    for _, row in top_scores.iterrows():
        print(f"{row['date']:<17} ${row['price']:<7.0f} {row['score']:<5.0f} "
              f"{row['phase']:<10} {row['rsi_div']:<3.0f} {row['vol_div']:<3.0f} "
              f"{row['wick_rej']:<3.0f} {row['momentum']:<3.0f}")
    
    # Key dates analysis
    key_dates = [
        ('2024-12-16', 'ETH Dec 2024 peak ($4,087)'),
        ('2024-12-15', 'Day before peak'),
        ('2024-12-17', 'Day after peak'),
        ('2024-10-15', 'Mid-Oct recovery (~$2,500)'),
        ('2024-11-01', 'Early Nov (~$2,800)'),
        ('2024-12-01', 'Early Dec run-up'),
    ]
    
    print(f"\nKEY DATE ANALYSIS:")
    for date_str, description in key_dates:
        target_ts = pd.Timestamp(date_str).timestamp() * 1000
        
        # Find closest scored point
        closest_idx = (scores_df['timestamp'] - target_ts).abs().idxmin()
        row = scores_df.loc[closest_idx]
        
        print(f"{description}:")
        print(f"  Date: {row['date']}, Price: ${row['price']:.0f}")
        print(f"  Score: {row['score']:.0f}, Phase: {row['phase']}")
        print(f"  Components: RSI={row['rsi_div']:.0f}, Vol={row['vol_div']:.0f}, "
              f"Wick={row['wick_rej']:.0f}, Mom={row['momentum']:.0f}")
        print()
    
    # Price level analysis
    print(f"PRICE LEVEL ANALYSIS:")
    high_price_mask = scores_df['price'] >= 4000
    mid_price_mask = (scores_df['price'] >= 2400) & (scores_df['price'] <= 2800)
    
    if high_price_mask.any():
        print(f"  At high prices (>$4000): avg_score={scores_df[high_price_mask]['score'].mean():.1f}")
    if mid_price_mask.any():
        print(f"  At mid prices ($2400-2800): avg_score={scores_df[mid_price_mask]['score'].mean():.1f}")
    
    # EXIT phase analysis
    exit_entries = scores_df[scores_df['phase'] == 'EXIT']
    print(f"\nEXIT PHASE ANALYSIS:")
    if len(exit_entries) > 0:
        print(f"  Found {len(exit_entries)} EXIT phase points:")
        for _, row in exit_entries.iterrows():
            print(f"    {row['date']}: ${row['price']:.0f}, score={row['score']:.0f}")
    else:
        print(f"  No EXIT phase detected in sampled points")
    
    return scores_df


if __name__ == "__main__":
    scores_df = run_fast_diagnostic()
    print("\nFast diagnostic complete!")