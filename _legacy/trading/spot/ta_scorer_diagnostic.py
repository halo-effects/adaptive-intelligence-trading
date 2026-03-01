#!/usr/bin/env python3
"""Diagnostic test for TA Top Scorer on ETH chunk 8 data (Sep 2024 - Jan 2025).

Loads ETH 1h data and scores every candle with the new TA scorer.
Prints top 20 scores and when they occur to verify high scores near Dec 2024 peak.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime
from trading.spot.ta_top_scorer import TATopScorer


def load_chunk_data():
    """Load ETH chunk 8 data (Sep 2024 - Jan 2025)."""
    data_file = "trading/spot/data/dwell_cache/ETH_USDT_1h_2024-09-10_2025-01-16.csv"
    print(f"Loading data from {data_file}")
    
    df = pd.read_csv(data_file)
    print(f"Loaded {len(df)} candles")
    print(f"Date range: {df.iloc[0]['timestamp']} to {df.iloc[-1]['timestamp']}")
    
    return df


def convert_timestamp_to_date(ts):
    """Convert timestamp to readable date."""
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d %H:%M')
    else:
        return str(ts)


def run_diagnostic():
    """Run diagnostic scoring on ETH data."""
    df = load_chunk_data()
    
    # Initialize TA scorer
    scorer = TATopScorer()
    print("\nInitialized TATopScorer")
    print(f"Phase thresholds: TIGHTEN >= {scorer.tighten_threshold}, "
          f"WIND_DOWN >= {scorer.winddown_threshold}, EXIT >= {scorer.exit_threshold}")
    
    # Score every candle
    scores = []
    print("\nScoring candles...")
    
    for i in range(len(df)):
        if i % 500 == 0:
            print(f"  Progress: {i}/{len(df)} ({i/len(df)*100:.1f}%)")
            
        result = scorer.score(df, i, "SIDEWAYS", None, None)
        
        scores.append({
            'index': i,
            'timestamp': df.iloc[i]['timestamp'],
            'date': convert_timestamp_to_date(df.iloc[i]['timestamp']),
            'price': float(df.iloc[i]['close']),
            'high': float(df.iloc[i]['high']),
            'score': result.score,
            'phase': result.phase,
            'rsi_div': result.rsi_divergence_score,
            'vol_div': result.volume_divergence_score,
            'wick_rej': result.upper_wick_rejection_score,
            'momentum': result.momentum_stall_score,
        })
    
    print(f"\nCompleted scoring {len(scores)} candles")
    
    # Convert to DataFrame for analysis
    scores_df = pd.DataFrame(scores)
    
    # Print summary stats
    print(f"\nSCORE STATISTICS:")
    print(f"  Max score: {scores_df['score'].max():.1f}")
    print(f"  Mean score: {scores_df['score'].mean():.1f}")
    print(f"  Std dev: {scores_df['score'].std():.1f}")
    print(f"  Scores >= 50: {(scores_df['score'] >= 50).sum()} candles")
    print(f"  Scores >= 70: {(scores_df['score'] >= 70).sum()} candles")
    
    # Phase distribution
    phase_counts = scores_df['phase'].value_counts()
    print(f"\nPHASE DISTRIBUTION:")
    for phase, count in phase_counts.items():
        pct = count / len(scores_df) * 100
        print(f"  {phase}: {count} candles ({pct:.1f}%)")
    
    # Print top 20 scores
    top_scores = scores_df.nlargest(20, 'score')
    print(f"\nTOP 20 SCORES:")
    print(f"{'Date':<17} {'Price':<8} {'Score':<6} {'Phase':<10} {'RSI':<4} {'Vol':<4} {'Wick':<4} {'Mom':<4}")
    print("-" * 80)
    
    for _, row in top_scores.iterrows():
        print(f"{row['date']:<17} ${row['price']:<7.0f} {row['score']:<5.0f} "
              f"{row['phase']:<10} {row['rsi_div']:<3.0f} {row['vol_div']:<3.0f} "
              f"{row['wick_rej']:<3.0f} {row['momentum']:<3.0f}")
    
    # Key dates to check
    key_dates = [
        ('2024-12-16', 'ETH Dec 2024 peak ($4,087)'),
        ('2024-10-15', 'Mid-Oct recovery (~$2,500)'),
        ('2024-11-01', 'Early Nov (~$2,800)'),
        ('2024-12-01', 'Early Dec run-up'),
    ]
    
    print(f"\nKEY DATE ANALYSIS:")
    for date_str, description in key_dates:
        # Find closest candle to this date
        target_ts = pd.Timestamp(date_str).timestamp() * 1000
        closest_idx = scores_df.iloc[(scores_df['timestamp'] - target_ts).abs().argsort()[:1]].index[0]
        row = scores_df.iloc[closest_idx]
        
        print(f"{description}:")
        print(f"  Date: {row['date']}, Price: ${row['price']:.0f}")
        print(f"  Score: {row['score']:.0f}, Phase: {row['phase']}")
        print(f"  Components: RSI={row['rsi_div']:.0f}, Vol={row['vol_div']:.0f}, "
              f"Wick={row['wick_rej']:.0f}, Mom={row['momentum']:.0f}")
        print()
    
    # Price level analysis
    print(f"PRICE LEVEL ANALYSIS:")
    high_price_mask = scores_df['price'] >= 4000  # Near ATH
    mid_price_mask = (scores_df['price'] >= 2400) & (scores_df['price'] <= 2800)  # Mid-cycle
    
    print(f"  At high prices (>$4000): avg_score={scores_df[high_price_mask]['score'].mean():.1f}")
    print(f"  At mid prices ($2400-2800): avg_score={scores_df[mid_price_mask]['score'].mean():.1f}")
    
    # Look for EXIT phase entries
    exit_entries = scores_df[scores_df['phase'] == 'EXIT']
    if len(exit_entries) > 0:
        print(f"\nEXIT PHASE PERIODS ({len(exit_entries)} candles):")
        # Group consecutive EXIT periods
        exit_groups = []
        current_group = []
        
        for _, row in exit_entries.iterrows():
            if not current_group or row['index'] == current_group[-1]['index'] + 1:
                current_group.append(row)
            else:
                exit_groups.append(current_group)
                current_group = [row]
        if current_group:
            exit_groups.append(current_group)
        
        for i, group in enumerate(exit_groups):
            start_row = group[0]
            end_row = group[-1]
            max_score_row = max(group, key=lambda x: x['score'])
            
            print(f"  Period {i+1}: {start_row['date']} to {end_row['date']}")
            print(f"    Duration: {len(group)} candles")
            print(f"    Price range: ${min(r['price'] for r in group):.0f} - ${max(r['price'] for r in group):.0f}")
            print(f"    Max score: {max_score_row['score']:.0f} on {max_score_row['date']}")
            print()
    else:
        print(f"\nNo EXIT phase detected (scores < 70)")
    
    return scores_df


if __name__ == "__main__":
    scores_df = run_diagnostic()
    print("\nDiagnostic complete!")