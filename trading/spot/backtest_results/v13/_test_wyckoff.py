"""
Test Script for Wyckoff Pattern Detection Module

This script tests the WyckoffDetector on all paper bot universe coins 
and compares results against V13 phase transition signals.

Usage:
    python _test_wyckoff.py

Author: V13 Trading Engine  
Date: 2026-02-27
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from wyckoff_detector import WyckoffDetector, load_daily_data
from v13_signals import V13SignalPack

# Test configuration
TEST_COINS = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']
ETF_START = '2023-01-01'
ETF_END = '2026-02-25'


def test_wyckoff_detector():
    """Test Wyckoff detector on all coins and print results."""
    
    print("=" * 80)
    print("WYCKOFF PATTERN DETECTION TEST - V13 Trading Engine")
    print("=" * 80)
    print(f"Testing period: {ETF_START} to {ETF_END}")
    print(f"Coins: {', '.join(TEST_COINS)}")
    print()
    
    all_results = {}
    
    for coin in TEST_COINS:
        print(f"\n{'='*60}")
        print(f"TESTING {coin}")
        print(f"{'='*60}")
        
        try:
            # Load daily data
            daily_data = load_daily_data(coin)
            if daily_data is None:
                print(f"❌ No daily data found for {coin}")
                continue
                
            print(f"✅ Loaded {len(daily_data)} daily candles for {daily_data.attrs.get('symbol', coin)}")
            print(f"   Date range: {daily_data.index[0].date()} to {daily_data.index[-1].date()}")
            
            # Initialize Wyckoff detector
            detector = WyckoffDetector(daily_data, coin)
            
            # Get pattern summary
            summary = detector.get_phase_summary(ETF_START, ETF_END)
            all_results[coin] = summary
            
            print(f"\n📊 PATTERN SUMMARY:")
            print(f"   Total events detected: {summary['total_events']}")
            
            if summary['pattern_counts']:
                print(f"\n   Pattern breakdown:")
                for pattern, count in sorted(summary['pattern_counts'].items()):
                    print(f"     {pattern:6s}: {count:2d}")
            
            # Key signals
            print(f"\n🎯 KEY SIGNALS:")
            print(f"   Accumulation signals: {summary['key_accumulation_signals']} (Spring + SOS)")
            print(f"   Distribution signals: {summary['key_distribution_signals']} (UTAD + SOW)")
            
            # Show Springs (key accumulation signals)
            if summary['springs']:
                print(f"\n🌱 SPRING SIGNALS ({len(summary['springs'])}):")
                for spring in summary['springs']:
                    print(f"   {spring['date'].strftime('%Y-%m-%d')}: "
                          f"${spring['price']:.4f}, Vol: {spring['volume_ratio']:.1f}x, "
                          f"Conf: {spring['confidence']:.1f}")
            
            # Show SOS signals  
            if summary['sos_signals']:
                print(f"\n📈 SIGN OF STRENGTH SIGNALS ({len(summary['sos_signals'])}):")
                for sos in summary['sos_signals']:
                    print(f"   {sos['date'].strftime('%Y-%m-%d')}: "
                          f"${sos['price']:.4f}, Vol: {sos['volume_ratio']:.1f}x, "
                          f"Conf: {sos['confidence']:.1f}")
            
            # Show UTAD signals
            if summary['utads']:
                print(f"\n⚠️ UTAD SIGNALS ({len(summary['utads'])}):")
                for utad in summary['utads']:
                    print(f"   {utad['date'].strftime('%Y-%m-%d')}: "
                          f"${utad['price']:.4f}, Vol: {utad['volume_ratio']:.1f}x, "
                          f"Conf: {utad['confidence']:.1f}")
                          
            # Show SOW signals
            if summary['sows']:
                print(f"\n📉 SIGN OF WEAKNESS SIGNALS ({len(summary['sows'])}):")
                for sow in summary['sows']:
                    print(f"   {sow['date'].strftime('%Y-%m-%d')}: "
                          f"${sow['price']:.4f}, Vol: {sow['volume_ratio']:.1f}x, "
                          f"Conf: {sow['confidence']:.1f}")
            
            # Test phase classification on key dates
            test_dates = []
            
            # Add Spring and SOS dates for phase testing
            for spring in summary['springs']:
                test_dates.append((spring['date'], 'Spring'))
            for sos in summary['sos_signals']:
                test_dates.append((sos['date'], 'SOS'))
                
            if test_dates:
                print(f"\n📅 PHASE CLASSIFICATION TEST:")
                for date, signal_type in sorted(test_dates):
                    phase = detector.classify_phase(date)
                    print(f"   {date.strftime('%Y-%m-%d')} ({signal_type:6s}): Phase {phase}")
            
        except Exception as e:
            print(f"❌ Error testing {coin}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    # Cross-reference with V13 signals
    print(f"\n{'='*80}")
    print("CROSS-REFERENCE WITH V13 HH_HL SIGNALS")
    print(f"{'='*80}")
    
    try:
        compare_with_v13_signals(all_results)
    except Exception as e:
        print(f"❌ Error in V13 comparison: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Summary statistics
    print_summary_statistics(all_results)


def compare_with_v13_signals(wyckoff_results):
    """Compare Wyckoff signals with V13 HH_HL transitions."""
    
    for coin in TEST_COINS:
        if coin not in wyckoff_results:
            continue
            
        try:
            print(f"\n🔄 {coin} - V13 Signal Comparison:")
            
            # Load V13 signal pack
            v13_pack = V13SignalPack(coin)
            
            # Get HH_HL streak information (this indicates trend structure changes)
            daily = v13_pack.daily
            if 'consec_hh_hl' in daily.columns and 'consec_lh_ll' in daily.columns:
                
                # Find significant HH_HL streak starts (potential bottoms)
                hh_hl_starts = []
                for i in range(1, len(daily)):
                    prev_hh = daily.iloc[i-1]['consec_hh_hl'] if not pd.isna(daily.iloc[i-1]['consec_hh_hl']) else 0
                    curr_hh = daily.iloc[i]['consec_hh_hl'] if not pd.isna(daily.iloc[i]['consec_hh_hl']) else 0
                    
                    # HH_HL streak starting (transition from 0 or low to 2+)
                    if prev_hh <= 1 and curr_hh >= 2:
                        date = daily.index[i]
                        if ETF_START <= date.strftime('%Y-%m-%d') <= ETF_END:
                            hh_hl_starts.append(date)
                
                print(f"   HH_HL streak starts (potential bottoms): {len(hh_hl_starts)}")
                
                # Compare with Wyckoff Spring/SOS signals
                wyckoff_buy_signals = []
                wyckoff_buy_signals.extend(wyckoff_results[coin]['springs'])
                wyckoff_buy_signals.extend(wyckoff_results[coin]['sos_signals'])
                
                print(f"   Wyckoff buy signals (Spring + SOS): {len(wyckoff_buy_signals)}")
                
                # Check for correlation
                if wyckoff_buy_signals and hh_hl_starts:
                    correlations = []
                    
                    for wyckoff_signal in wyckoff_buy_signals:
                        wyckoff_date = wyckoff_signal['date']
                        
                        # Find closest HH_HL start within 10 days
                        closest_hh_hl = None
                        min_distance = float('inf')
                        
                        for hh_date in hh_hl_starts:
                            distance = abs((wyckoff_date - hh_date).days)
                            if distance <= 10 and distance < min_distance:
                                min_distance = distance
                                closest_hh_hl = hh_date
                                
                        if closest_hh_hl:
                            correlations.append({
                                'wyckoff_date': wyckoff_date,
                                'wyckoff_type': wyckoff_signal['pattern_type'],
                                'hh_hl_date': closest_hh_hl,
                                'days_diff': min_distance
                            })
                            
                    if correlations:
                        print(f"   📍 Found {len(correlations)} correlations within 10 days:")
                        for corr in correlations:
                            print(f"     {corr['wyckoff_date'].strftime('%Y-%m-%d')} ({corr['wyckoff_type']}) "
                                  f"↔ HH_HL start {corr['hh_hl_date'].strftime('%Y-%m-%d')} "
                                  f"({corr['days_diff']} days)")
                    else:
                        print("   ⚠️ No close correlations found")
                        
                    # Show potential misses
                    uncorrelated_wyckoff = [
                        s for s in wyckoff_buy_signals 
                        if not any(abs((s['date'] - hh_date).days) <= 10 for hh_date in hh_hl_starts)
                    ]
                    
                    uncorrelated_hh_hl = [
                        hh_date for hh_date in hh_hl_starts
                        if not any(abs((wyckoff_signal['date'] - hh_date).days) <= 10 
                                  for wyckoff_signal in wyckoff_buy_signals)
                    ]
                    
                    if uncorrelated_wyckoff:
                        print(f"   🎯 Wyckoff signals HH_HL missed ({len(uncorrelated_wyckoff)}):")
                        for signal in uncorrelated_wyckoff[:3]:  # Show first 3
                            print(f"     {signal['date'].strftime('%Y-%m-%d')} ({signal['pattern_type']})")
                            
                    if uncorrelated_hh_hl:
                        print(f"   ⚡ HH_HL starts Wyckoff missed ({len(uncorrelated_hh_hl)}):")
                        for hh_date in uncorrelated_hh_hl[:3]:  # Show first 3
                            print(f"     {hh_date.strftime('%Y-%m-%d')}")
            else:
                print("   ⚠️ No HH_HL data available in V13 signals")
                
        except Exception as e:
            print(f"   ❌ Error comparing {coin}: {str(e)}")
            continue


def print_summary_statistics(all_results):
    """Print overall summary statistics."""
    
    print(f"\n{'='*80}")
    print("SUMMARY STATISTICS")
    print(f"{'='*80}")
    
    total_events = sum(r['total_events'] for r in all_results.values())
    total_springs = sum(len(r['springs']) for r in all_results.values())
    total_sos = sum(len(r['sos_signals']) for r in all_results.values())
    total_utads = sum(len(r['utads']) for r in all_results.values())
    total_sows = sum(len(r['sows']) for r in all_results.values())
    
    print(f"📊 Across {len(all_results)} coins ({ETF_START} to {ETF_END}):")
    print(f"   Total Wyckoff events: {total_events}")
    print(f"   Key accumulation signals: {total_springs + total_sos}")
    print(f"     - Springs: {total_springs}")
    print(f"     - SOS: {total_sos}")
    print(f"   Key distribution signals: {total_utads + total_sows}")
    print(f"     - UTAD: {total_utads}")
    print(f"     - SOW: {total_sows}")
    
    # Pattern frequency
    all_patterns = {}
    for result in all_results.values():
        for pattern, count in result['pattern_counts'].items():
            all_patterns[pattern] = all_patterns.get(pattern, 0) + count
    
    if all_patterns:
        print(f"\n📈 Most frequent patterns:")
        sorted_patterns = sorted(all_patterns.items(), key=lambda x: x[1], reverse=True)
        for pattern, count in sorted_patterns[:5]:
            print(f"   {pattern:8s}: {count:3d} occurrences")
    
    # Best performers
    best_acc_coin = max(all_results.items(), 
                       key=lambda x: len(x[1]['springs']) + len(x[1]['sos_signals']))
    best_dist_coin = max(all_results.items(),
                        key=lambda x: len(x[1]['utads']) + len(x[1]['sows']))
    
    print(f"\n🏆 Top performers:")
    print(f"   Best accumulation signals: {best_acc_coin[0]} "
          f"({len(best_acc_coin[1]['springs']) + len(best_acc_coin[1]['sos_signals'])} signals)")
    print(f"   Best distribution signals: {best_dist_coin[0]} "
          f"({len(best_dist_coin[1]['utads']) + len(best_dist_coin[1]['sows'])} signals)")
    
    print(f"\n✅ Test completed successfully!")
    print(f"💡 Integration ready: Use WyckoffDetector.detect_patterns() in V13 ROUTER phase")
    

def analyze_specific_period(coin: str, start_date: str, end_date: str):
    """Analyze a specific period in detail for debugging."""
    
    print(f"\n{'='*60}")
    print(f"DETAILED ANALYSIS: {coin} ({start_date} to {end_date})")
    print(f"{'='*60}")
    
    try:
        daily_data = load_daily_data(coin)
        if daily_data is None:
            print(f"❌ No data for {coin}")
            return
            
        detector = WyckoffDetector(daily_data, coin)
        events = detector.detect_patterns(start_date, end_date)
        
        if events:
            print(f"📅 Chronological events:")
            for event in sorted(events, key=lambda x: x['date']):
                phase = detector.classify_phase(event['date'])
                print(f"   {event['date'].strftime('%Y-%m-%d')}: "
                      f"{event['pattern_type']:6s} (Phase {phase}) - "
                      f"${event['price']:.4f}, Vol: {event['volume_ratio']:.1f}x")
        else:
            print("   No events detected in this period")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == '__main__':
    # Run main test
    test_wyckoff_detector()
    
    # Optional: Detailed analysis of specific periods
    # Example: Analyze BTC during a known accumulation period
    # analyze_specific_period('BTC', '2023-10-01', '2023-12-31')