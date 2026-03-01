#!/usr/bin/env python3
"""Direct test of the TA scorer on chunk 8 data."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime
from trading.spot.ta_top_scorer import TATopScorer

def convert_timestamp_to_date(ts):
    """Convert timestamp to readable date."""
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d %H:%M')
    else:
        return str(ts)

def test_ta_scorer_direct():
    """Test the optimized TA scorer directly."""
    # Load test data
    data_file = "trading/spot/data/dwell_cache/ETH_USDT_1h_2024-09-10_2025-01-16.csv"
    print(f"Loading test data: {data_file}")
    
    df = pd.read_csv(data_file)
    print(f"Loaded {len(df)} candles from {convert_timestamp_to_date(df.iloc[0]['timestamp'])} to {convert_timestamp_to_date(df.iloc[-1]['timestamp'])}")
    
    # Initialize TA scorer
    scorer = TATopScorer()
    print("Initialized TATopScorer")
    
    # Test scoring on key dates around Dec 2024 peak
    key_dates = [
        ('2024-12-15', 'Day before peak'),
        ('2024-12-16', 'Peak day ($4,087)'),
        ('2024-12-17', 'Day after peak'),
        ('2024-11-01', 'Early Nov (~$2,800)'),
        ('2024-10-15', 'Mid-Oct recovery (~$2,500)'),
    ]
    
    print(f"\nTesting TA scorer on key dates...")
    
    for date_str, description in key_dates:
        # Find the closest candle to target date
        target_ts = pd.Timestamp(date_str).timestamp() * 1000
        time_diffs = abs(df['timestamp'] - target_ts)
        closest_idx = time_diffs.idxmin()
        
        if closest_idx < 200:  # Skip if too early (not enough data for indicators)
            print(f"{description}: Skipped (not enough data)")
            continue
            
        # Score this candle
        result = scorer.score(df, closest_idx, "SIDEWAYS", None, None)
        
        price = df.iloc[closest_idx]['close']
        actual_date = convert_timestamp_to_date(df.iloc[closest_idx]['timestamp'])
        
        print(f"{description}:")
        print(f"  Date: {actual_date}, Price: ${price:.0f}")
        print(f"  Score: {result.score:.0f}, Phase: {result.phase}")
        print(f"  Components: RSI={result.rsi_divergence_score:.0f}, Vol={result.volume_divergence_score:.0f}, "
              f"Wick={result.upper_wick_rejection_score:.0f}, Mom={result.momentum_stall_score:.0f}")
        print()
    
    # Find peak score in the dataset
    print("Finding highest scoring periods...")
    sample_indices = range(200, len(df), 50)  # Sample every 50th candle after lookback
    scores = []
    
    for i in sample_indices:
        result = scorer.score(df, i, "SIDEWAYS", None, None)
        scores.append((i, result.score, result.phase))
    
    # Sort by score and show top 10
    scores.sort(key=lambda x: x[1], reverse=True)
    top_scores = scores[:10]
    
    print(f"TOP 10 SCORING PERIODS:")
    print(f"{'Date':<17} {'Price':<8} {'Score':<6} {'Phase':<10}")
    print("-" * 50)
    
    for idx, score, phase in top_scores:
        price = df.iloc[idx]['close']
        date = convert_timestamp_to_date(df.iloc[idx]['timestamp'])
        print(f"{date:<17} ${price:<7.0f} {score:<5.0f} {phase}")
    
    # Check if any scores exceed the threshold
    exit_scores = [s for _, s, p in scores if p == "EXIT"]
    print(f"\nEXIT phase detection:")
    print(f"  Scores >= 70: {len(exit_scores)} periods")
    print(f"  Max score: {max(s for _, s, _ in scores):.0f}")
    
    if exit_scores:
        print(f"  EXIT scores: {exit_scores}")
    else:
        print("  No EXIT phase detected in sampled periods")
    
    return len(exit_scores) > 0

if __name__ == "__main__":
    success = test_ta_scorer_direct()
    print(f"\n{'TA scorer test completed!' if success else 'TA scorer needs tuning'}")