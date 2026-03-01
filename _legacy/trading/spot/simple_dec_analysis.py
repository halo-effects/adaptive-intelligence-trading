#!/usr/bin/env python3
"""Simple December 2024 Price Analysis."""

import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from trading.spot.run_v11_chained import get_candles

def analyze_dec_2024_price_action():
    """Simple analysis of December 2024 ETH price action."""
    
    print("=" * 80)
    print("DECEMBER 2024 ETH PRICE ANALYSIS")
    print("=" * 80)
    
    # Get ETH 1h data for Nov 2024 - Jan 2025
    print("Fetching ETH/USDT 1h data...")
    df = get_candles("ETH/USDT", "1h", "2024-11-01", "2025-01-15", exchange="aster")
    
    if df.empty:
        print("ERROR: No data!")
        return
        
    print(f"Got {len(df)} candles")
    
    # Convert timestamps and add indicators
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['price'] = df['close'].astype(float)
    
    # Calculate simple moving averages
    df['sma_50'] = df['price'].rolling(50).mean()
    df['sma_200'] = df['price'].rolling(200).mean()
    
    # Focus on December 2024
    dec_df = df[(df['datetime'] >= '2024-12-01') & (df['datetime'] <= '2024-12-31')].copy()
    
    if dec_df.empty:
        print("No December 2024 data found!")
        return
    
    print(f"\nDECEMBER 2024 ({len(dec_df)} candles):")
    print("-" * 50)
    print(f"Price range: ${dec_df['price'].min():.2f} - ${dec_df['price'].max():.2f}")
    print(f"Start price: ${dec_df.iloc[0]['price']:.2f}")
    print(f"End price: ${dec_df.iloc[-1]['price']:.2f}")
    print(f"Peak price: ${dec_df['price'].max():.2f}")
    
    # Find the peak
    peak_idx = dec_df['price'].idxmax()
    peak_row = dec_df.loc[peak_idx]
    print(f"Peak date: {peak_row['datetime'].strftime('%Y-%m-%d %H:%M')}")
    print(f"Peak price: ${peak_row['price']:.2f}")
    
    # Check if peak was near $4000 as mentioned
    peak_price = peak_row['price']
    if 3800 <= peak_price <= 4200:
        print(f"Peak is near $4000 target - GOOD!")
    else:
        print(f"Peak is NOT near $4000 - may affect short timing")
    
    # Calculate decline from peak
    post_peak_df = dec_df[dec_df.index >= peak_idx]
    if len(post_peak_df) > 1:
        min_after_peak = post_peak_df['price'].min()
        decline_pct = (peak_price - min_after_peak) / peak_price * 100
        print(f"Max decline from peak: {decline_pct:.1f}%")
        
        # Look for significant declines (>10%) that could trigger distribution
        big_declines = []
        for i, row in post_peak_df.iterrows():
            decline = (peak_price - row['price']) / peak_price * 100
            if decline >= 10:
                big_declines.append({
                    'date': row['datetime'],
                    'price': row['price'],
                    'decline_pct': decline
                })
        
        if big_declines:
            print(f"\nSIGNIFICANT DECLINES (>10% from peak):")
            for decline in big_declines[:5]:  # Show first 5
                print(f"  {decline['date'].strftime('%Y-%m-%d %H:%M')} | "
                      f"${decline['price']:.2f} | -{decline['decline_pct']:.1f}%")
        else:
            print("\nNo significant declines >10% from peak in December")
    
    # Death cross analysis
    dec_df['death_cross'] = dec_df['sma_50'] < dec_df['sma_200']
    death_cross_periods = dec_df[dec_df['death_cross'] == True]
    
    if not death_cross_periods.empty:
        print(f"\nDEATH CROSS periods: {len(death_cross_periods)} candles")
        first_death = death_cross_periods.iloc[0]
        print(f"First death cross: {first_death['datetime'].strftime('%Y-%m-%d %H:%M')}")
    else:
        print("\nNo death cross in December 2024")
    
    # Check for rapid price movements that might trigger distribution
    print(f"\nRAPID PRICE MOVEMENTS:")
    dec_df['price_change_1h'] = dec_df['price'].pct_change() * 100
    dec_df['price_change_24h'] = dec_df['price'].pct_change(periods=24) * 100
    
    # Find big moves
    big_hourly_moves = dec_df[abs(dec_df['price_change_1h']) >= 3]
    big_daily_moves = dec_df[abs(dec_df['price_change_24h']) >= 10]
    
    print(f"1h moves >= 3%: {len(big_hourly_moves)}")
    print(f"24h moves >= 10%: {len(big_daily_moves)}")
    
    if not big_daily_moves.empty:
        print("Top 24h moves:")
        for _, row in big_daily_moves.nlargest(3, 'price_change_24h').iterrows():
            print(f"  {row['datetime'].strftime('%Y-%m-%d')} | "
                  f"${row['price']:.2f} | {row['price_change_24h']:+.1f}%")
    
    # Compare to mid-2023 (should be much lower prices)
    mid_2023_df = df[(df['datetime'] >= '2023-06-01') & (df['datetime'] <= '2023-09-01')]
    
    if not mid_2023_df.empty:
        print(f"\nMID-2023 COMPARISON (Jun-Aug 2023):")
        print("-" * 50)
        print(f"Price range: ${mid_2023_df['price'].min():.2f} - ${mid_2023_df['price'].max():.2f}")
        print(f"Peak price: ${mid_2023_df['price'].max():.2f}")
        
        mid_peak = mid_2023_df['price'].max()
        dec_peak = dec_df['price'].max()
        ratio = dec_peak / mid_peak
        print(f"Dec 2024 peak is {ratio:.1f}x higher than mid-2023")
    
    print(f"\n" + "=" * 80)
    print("SUMMARY FOR SHORT ENTRY OPTIMIZATION:")
    print("=" * 80)
    
    if 3800 <= peak_price <= 4200:
        print("1. Peak price ~$4000: CONFIRMED")
        
        # Suggest thresholds based on when significant moves happened
        significant_moves = dec_df[abs(dec_df['price_change_24h']) >= 8].copy()
        if not significant_moves.empty:
            print("2. Significant price movements detected")
            print("3. RECOMMENDED APPROACH:")
            print("   - Try lower distribution thresholds: 15, 20, 25")
            print("   - Enable structural exit for 1h timeframe")
            print("   - Consider disabling mcap gating temporarily to test pure distribution")
            
        else:
            print("2. No major distribution-like moves detected")
            print("3. May need VERY low thresholds or different approach")
    
    else:
        print(f"1. Peak price ${peak_price:.2f} not near expected $4000")
        print("2. May need to adjust target period or approach")
    
    print("=" * 80)

if __name__ == "__main__":
    analyze_dec_2024_price_action()