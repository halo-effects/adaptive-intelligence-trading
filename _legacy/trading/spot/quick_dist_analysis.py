#!/usr/bin/env python3
"""Quick Distribution Score Analysis - Focus on Dec 2024 period."""

import sys, json, logging
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import numpy as np

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.run_v11_chained import get_candles
from trading.spot.distribution_scorer import DistributionScorer
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.WARNING)

def analyze_dec_2024_distribution_scores():
    """Quick analysis of distribution scores during Dec 2024 ETH top."""
    
    print("=" * 80)
    print("DISTRIBUTION SCORE ANALYSIS: Dec 2024 ETH Top")
    print("=" * 80)
    
    # Get ETH 1h data for Nov-Dec 2024 period
    print("Fetching ETH/USDT 1h data for Nov-Dec 2024...")
    df = get_candles("ETH/USDT", "1h", "2024-11-01", "2025-01-15", exchange="aster")
    
    if df.empty:
        print("ERROR: No data fetched!")
        return
        
    print(f"Got {len(df)} candles from {df.iloc[0]['timestamp']} to {df.iloc[-1]['timestamp']}")
    
    # Load Fear & Greed data
    fg = load_historical_fear_greed()
    print(f"Loaded {len(fg)} Fear & Greed entries")
    
    # Convert timestamps
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['price'] = df['close'].astype(float)
    
    # Initialize distribution scorer
    scorer = DistributionScorer()
    
    # Analyze scores for each candle in the dataset
    print(f"\nAnalyzing distribution scores...")
    scores = []
    
    for i in range(200, len(df)):  # Start after enough data for indicators
        row = df.iloc[i]
        dt = row['datetime']
        price = row['price']
        
        # Get F&G value for this timestamp (simplified)
        fg_value = 50  # Default neutral value for now
        
        # Get recent data window for scoring
        window_df = df.iloc[max(0, i-500):i+1]  # 500 candle lookback
        
        try:
            result = scorer.score_distribution_phase(
                window_df, fg_value, timeframe="1h", current_idx=min(500, i)
            )
            
            scores.append({
                'datetime': dt,
                'timestamp': row['timestamp'],
                'price': price,
                'score': result.score,
                'phase': result.phase.name,
                'fg_value': fg_value,
                'details': result.details
            })
            
            # Print high scores during Dec 2024
            if dt >= pd.Timestamp('2024-12-01') and dt <= pd.Timestamp('2024-12-31'):
                if result.score >= 15:  # Focus on potentially triggering scores
                    print(f"  {dt.strftime('%Y-%m-%d %H:%M')} | Score: {result.score:5.1f} | "
                          f"Phase: {result.phase.name:<12} | Price: ${price:>7.2f} | F&G: {fg_value:2.0f}")
                    
        except Exception as e:
            continue
    
    if not scores:
        print("ERROR: No scores calculated!")
        return
        
    scores_df = pd.DataFrame(scores)
    
    # Find December 2024 period
    dec_scores = scores_df[
        (scores_df['datetime'] >= '2024-12-01') & 
        (scores_df['datetime'] <= '2024-12-31')
    ]
    
    print(f"\n" + "=" * 80)
    print(f"DECEMBER 2024 SUMMARY ({len(dec_scores)} candles)")
    print("=" * 80)
    
    if not dec_scores.empty:
        print(f"Price range: ${dec_scores['price'].min():.2f} - ${dec_scores['price'].max():.2f}")
        print(f"Score range: {dec_scores['score'].min():.1f} - {dec_scores['score'].max():.1f}")
        print(f"Scores >= 30: {len(dec_scores[dec_scores['score'] >= 30])}")
        print(f"Scores >= 25: {len(dec_scores[dec_scores['score'] >= 25])}")
        print(f"Scores >= 20: {len(dec_scores[dec_scores['score'] >= 20])}")
        print(f"Scores >= 15: {len(dec_scores[dec_scores['score'] >= 15])}")
        
        # Find the highest scores
        top_scores = dec_scores.nlargest(10, 'score')
        print(f"\nTOP 10 DISTRIBUTION SCORES IN DECEMBER 2024:")
        print("-" * 80)
        for _, row in top_scores.iterrows():
            print(f"  {row['datetime'].strftime('%Y-%m-%d %H:%M')} | Score: {row['score']:5.1f} | "
                  f"Price: ${row['price']:>7.2f} | F&G: {row['fg_value']:2.0f}")
    
    # Also check mid-2023 period (should have low scores)
    mid_2023_scores = scores_df[
        (scores_df['datetime'] >= '2023-06-01') & 
        (scores_df['datetime'] <= '2023-09-01')
    ]
    
    if not mid_2023_scores.empty:
        print(f"\nMID-2023 COMPARISON (Jun-Aug 2023, {len(mid_2023_scores)} candles):")
        print("-" * 80)
        print(f"Price range: ${mid_2023_scores['price'].min():.2f} - ${mid_2023_scores['price'].max():.2f}")
        print(f"Score range: {mid_2023_scores['score'].min():.1f} - {mid_2023_scores['score'].max():.1f}")
        print(f"Max score: {mid_2023_scores['score'].max():.1f}")
        
        if mid_2023_scores['score'].max() >= 15:
            high_mid_scores = mid_2023_scores[mid_2023_scores['score'] >= 15].nlargest(5, 'score')
            print("Top scores in mid-2023 (should be low!):")
            for _, row in high_mid_scores.iterrows():
                print(f"  {row['datetime'].strftime('%Y-%m-%d %H:%M')} | Score: {row['score']:5.1f} | "
                      f"Price: ${row['price']:>7.2f}")
    
    print(f"\n" + "=" * 80)
    print("THRESHOLD RECOMMENDATIONS:")
    print("=" * 80)
    
    if not dec_scores.empty:
        dec_75th = np.percentile(dec_scores['score'], 75)
        dec_90th = np.percentile(dec_scores['score'], 90)
        dec_95th = np.percentile(dec_scores['score'], 95)
        dec_max = dec_scores['score'].max()
        
        print(f"Dec 2024 - 75th percentile: {dec_75th:.1f}")
        print(f"Dec 2024 - 90th percentile: {dec_90th:.1f}")
        print(f"Dec 2024 - 95th percentile: {dec_95th:.1f}")
        print(f"Dec 2024 - Maximum: {dec_max:.1f}")
        
        print(f"\nSuggested thresholds to catch Dec 2024 top:")
        print(f"  - Conservative (catch ~25% of Dec): {dec_75th:.0f}")
        print(f"  - Moderate (catch ~10% of Dec): {dec_90th:.0f}")  
        print(f"  - Aggressive (catch ~5% of Dec): {dec_95th:.0f}")
        
        if not mid_2023_scores.empty:
            mid_max = mid_2023_scores['score'].max()
            print(f"\nMid-2023 max score: {mid_max:.1f}")
            print(f"Safe threshold (above mid-2023): {max(mid_max + 2, 15):.0f}")
    
    # Save detailed scores to file
    output_file = Path(__file__).resolve().parent / "backtest_results" / "v11_hybrid" / "distribution_score_analysis.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        # Convert datetime to string for JSON serialization
        scores_for_json = []
        for score in scores:
            score_copy = score.copy()
            score_copy['datetime'] = score_copy['datetime'].strftime('%Y-%m-%d %H:%M:%S')
            scores_for_json.append(score_copy)
            
        json.dump(scores_for_json, f, indent=2, default=str)
    
    print(f"\nDetailed scores saved to: {output_file}")
    print("=" * 80)

if __name__ == "__main__":
    analyze_dec_2024_distribution_scores()