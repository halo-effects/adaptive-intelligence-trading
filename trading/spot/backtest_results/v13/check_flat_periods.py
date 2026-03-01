"""Check ADX during long FLAT periods — is the sustained requirement too strict?"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import pandas as pd, numpy as np
from v13_signals import V13SignalPack

for coin in ['BTC', 'ETH', 'SOL', 'BNB', 'XRP']:
    pack = V13SignalPack(coin)
    daily = pack.daily
    
    # Known long FLAT periods from results
    flat_periods = {
        'BTC': [('2025-01-01', '2025-01-29'), ('2025-06-15', '2025-09-01')],
        'ETH': [('2024-12-22', '2025-06-25')],
        'SOL': [('2024-12-15', '2025-04-29')],
        'BNB': [('2024-12-22', '2025-01-16'), ('2025-08-03', '2025-12-02')],
        'XRP': [('2025-01-09', '2025-03-25')],
    }
    
    if coin not in flat_periods:
        continue
    
    print(f"\n{'='*70}")
    print(f"  {coin} FLAT PERIODS — ADX Analysis")
    print(f"{'='*70}")
    
    for start_str, end_str in flat_periods[coin]:
        start = pd.Timestamp(start_str)
        end = pd.Timestamp(end_str)
        days = (end - start).days
        
        mask = (daily.index >= start) & (daily.index <= end)
        data = daily[mask]
        
        print(f"\n  {start_str} - {end_str} ({days}d)")
        
        # Get ADX values
        adx_vals = []
        streak = 0
        max_streak = 0
        for date in data.index:
            try:
                adx = pack.structure.adx_at(date)
                adx_vals.append((date, adx))
                if adx < 20:
                    streak += 1
                    max_streak = max(max_streak, streak)
                else:
                    streak = 0
            except:
                pass
        
        if adx_vals:
            vals = [v for _, v in adx_vals]
            below_20 = sum(1 for v in vals if v < 20)
            print(f"  ADX: min={min(vals):.1f}, max={max(vals):.1f}, avg={np.mean(vals):.1f}")
            print(f"  Days below 20: {below_20}/{len(vals)} ({below_20/len(vals)*100:.0f}%)")
            print(f"  Max consecutive days below 20: {max_streak}")
            
            # What about ADX < 25?
            below_25 = sum(1 for v in vals if v < 25)
            streak25 = 0
            max_streak25 = 0
            for _, v in adx_vals:
                if v < 25:
                    streak25 += 1
                    max_streak25 = max(max_streak25, streak25)
                else:
                    streak25 = 0
            print(f"  Days below 25: {below_25}/{len(vals)} ({below_25/len(vals)*100:.0f}%), max streak: {max_streak25}")
            
            # Price movement during FLAT
            p_start = data['close'].iloc[0]
            p_end = data['close'].iloc[-1]
            print(f"  Price: ${p_start:,.0f} -> ${p_end:,.0f} ({(p_end/p_start-1)*100:+.1f}%)")
            print(f"  ** Opportunity cost of sitting in cash: {(p_end/p_start-1)*100:+.1f}% price move missed")
