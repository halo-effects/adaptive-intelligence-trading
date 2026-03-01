"""Debug: Why doesn't ETH enter MARKUP during Oct 2020 - May 2021 bull run?
Trace HH_HL and Fib_support signals day by day while in DCA phase."""
import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
from v13_phase_backtest_v8 import compute_fib_levels, price_near_fib_support, FIB_RATIOS, FIB_TOLERANCE

DB = str(Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db')

def main():
    for coin in ['ETH', 'BTC']:
        pack = V13SignalPack(coin, DB)
        daily = pack.daily
        
        print(f"\n{'='*80}")
        print(f"  {coin}: DCA->MARKUP signal trace (Oct 2020 - May 2021)")
        print(f"{'='*80}")
        
        start = '2020-10-01'
        end = '2021-05-22'
        
        mask = (daily.index >= start) & (daily.index <= end)
        subset = daily[mask]
        
        hh_count = 0
        fib_count = 0
        both_count = 0
        
        for i, (date, row) in enumerate(subset.iterrows()):
            price = row['close']
            
            # Check HH_HL
            hh = pack.structure.hh_hl_streak(date, min_streak=2)
            hh_val = row.get('consec_hh_hl', 0)
            
            # Check Fib support
            fib = compute_fib_levels(daily, date)
            near_fib = price_near_fib_support(price, fib)
            
            # Check SMA200 overextension
            overext = pack.sma200.overextension_at(date)
            overext_blocked = not np.isnan(overext) and overext > 0.20
            
            if hh:
                hh_count += 1
            if near_fib:
                fib_count += 1
            if hh and near_fib:
                both_count += 1
                blocked = " ** BLOCKED (SMA200 overext)" if overext_blocked else " >>> WOULD ENTER MARKUP"
                
                # Show fib details
                fib_detail = ""
                if fib:
                    for ratio in FIB_RATIOS:
                        level = fib.get(ratio, 0)
                        if level > 0:
                            dist = abs(price - level) / level
                            if dist < FIB_TOLERANCE:
                                fib_detail = f" near {ratio:.3f}={level:.0f}"
                                break
                
                print(f"  {date.strftime('%Y-%m-%d')}: ${price:,.0f} HH_HL={hh_val:.0f} "
                      f"fib_near=True{fib_detail} overext={overext*100:+.0f}%{blocked}")
            
            # Sample every 14 days to show status even when no signal
            elif i % 14 == 0:
                fib_detail = ""
                if fib:
                    nearest = None
                    nearest_dist = 999
                    for ratio in FIB_RATIOS:
                        level = fib.get(ratio, 0)
                        if level > 0:
                            dist = abs(price - level) / level
                            if dist < nearest_dist:
                                nearest_dist = dist
                                nearest = (ratio, level)
                    if nearest:
                        fib_detail = f" nearest_fib={nearest[0]:.3f}@{nearest[1]:.0f} dist={nearest_dist*100:.1f}%"
                
                oe = f" overext={overext*100:+.0f}%" if not np.isnan(overext) else " overext=NaN"
                print(f"  {date.strftime('%Y-%m-%d')}: ${price:,.0f} HH_HL={hh_val:.0f} "
                      f"fib_near={near_fib}{fib_detail}{oe}")
        
        print(f"\n  Summary: HH_HL fired {hh_count} days, Fib_near fired {fib_count} days, "
              f"BOTH fired {both_count} days")
        
        # Also check: how is consec_hh_hl computed?
        print(f"\n  consec_hh_hl distribution during this period:")
        vals = subset['consec_hh_hl'].dropna()
        if len(vals) > 0:
            print(f"    max={vals.max():.0f}, mean={vals.mean():.1f}")
            for v in [0, 1, 2, 3, 4, 5]:
                c = (vals >= v).sum()
                print(f"    >= {v}: {c} days ({c/len(vals)*100:.0f}%)")

if __name__ == '__main__':
    main()
