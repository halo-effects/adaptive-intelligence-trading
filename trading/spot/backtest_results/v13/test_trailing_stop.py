"""Test trailing stops on markup positions.

Current: MARKUP_FAIL fires at 25% DD + ADX > 25. That's a lot of damage.

Trailing stop variants:
  A) Simple trailing: after +X% profit, set stop at Y% below peak
  B) Breakeven stop: after +X% profit, move stop to entry price
  C) Tiered trailing: tighter stop as profit grows

We simulate by walking the markup equity curve and checking when
the trailing stop would have fired vs the actual exit.
"""
from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack
from run_new_coins_profiles import make_config
import pandas as pd
import numpy as np


def simulate_trailing_stops(bt, r, activation_pct=10, trail_pct=10):
    """Simulate trailing stops on all markup phases.
    
    activation_pct: minimum profit % before trailing stop activates
    trail_pct: stop trails at this % below peak equity during markup
    
    Returns list of markup entries with original vs trailing stop outcomes.
    """
    results = []
    
    # Get daily equity curve
    equity_curve = bt.equity_curve  # list of (date, equity) tuples
    
    # Find markup phases from phase log
    markup_phases = []
    for i, t in enumerate(bt.phase_log):
        if str(t.get('to', '')) == 'MARKUP':
            start_date = t['date']
            start_equity = t['equity']
            
            # Find end of this markup
            end_date = None
            end_equity = None
            end_reason = None
            for j in range(i+1, len(bt.phase_log)):
                next_t = bt.phase_log[j]
                if str(next_t.get('to', '')) != 'MARKUP':
                    end_date = next_t['date']
                    end_equity = next_t['equity']
                    end_reason = next_t.get('reason', '')
                    break
            
            if end_date is None:
                end_equity = r['final_equity']
                end_date = equity_curve[-1][0] if equity_curve else start_date
                end_reason = 'END_OF_DATA'
            
            markup_phases.append({
                'start_date': start_date,
                'start_equity': start_equity,
                'end_date': end_date,
                'end_equity': end_equity,
                'end_reason': end_reason,
            })
    
    for phase in markup_phases:
        start_eq = phase['start_equity']
        peak_eq = start_eq
        trail_stop_active = False
        trail_stop_price = 0
        trail_exit_date = None
        trail_exit_eq = None
        
        # Walk equity curve during this markup
        for point in equity_curve:
            date, eq = point['date'], point['equity']
            if date < phase['start_date']:
                continue
            if date > phase['end_date']:
                break
            
            profit_pct = (eq / start_eq - 1) * 100
            
            # Track peak
            if eq > peak_eq:
                peak_eq = eq
            
            # Activate trailing stop when profit reaches threshold
            if profit_pct >= activation_pct:
                trail_stop_active = True
            
            if trail_stop_active:
                trail_stop_price = peak_eq * (1 - trail_pct / 100)
                
                if eq <= trail_stop_price and trail_exit_date is None:
                    trail_exit_date = date
                    trail_exit_eq = eq
        
        actual_pnl = phase['end_equity'] - start_eq
        actual_pct = (phase['end_equity'] / start_eq - 1) * 100
        peak_pct = (peak_eq / start_eq - 1) * 100
        
        if trail_exit_date:
            trail_pnl = trail_exit_eq - start_eq
            trail_pct_result = (trail_exit_eq / start_eq - 1) * 100
        else:
            trail_pnl = actual_pnl
            trail_pct_result = actual_pct
        
        improvement = trail_pnl - actual_pnl
        
        results.append({
            'start_date': phase['start_date'],
            'start_eq': start_eq,
            'peak_pct': peak_pct,
            'actual_pct': actual_pct,
            'actual_pnl': actual_pnl,
            'trail_pct': trail_pct_result,
            'trail_pnl': trail_pnl,
            'trail_exit': trail_exit_date,
            'improvement': improvement,
            'end_reason': phase['end_reason'],
        })
    
    return results


if __name__ == '__main__':
    print("TRAILING STOP TEST ON MARKUP POSITIONS")
    print("="*80)
    
    # Test multiple trailing stop configs
    configs = [
        (5, 8, "Aggressive: activate +5%, trail 8%"),
        (10, 10, "Moderate: activate +10%, trail 10%"),
        (10, 15, "Standard: activate +10%, trail 15%"),
        (15, 10, "Late activate: +15%, trail 10%"),
        (5, 5, "Tight: activate +5%, trail 5%"),
    ]
    
    for coin in ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']:
        pack = V13SignalPack(coin)
        cfg = make_config('high')
        bt = V13BacktestV8(pack, cfg)
        r = bt.run()
        
        print(f"\n{'='*80}")
        print(f"{coin} (high) -- ROI: {r['roi']:+.1f}%")
        print(f"{'='*80}")
        
        for act, trail, label in configs:
            results = simulate_trailing_stops(bt, r, act, trail)
            
            total_improvement = sum(x['improvement'] for x in results)
            stops_fired = sum(1 for x in results if x['trail_exit'] is not None)
            
            print(f"\n  {label}")
            for res in results:
                fired = f"TRAIL@{str(res['trail_exit'])[:10]}" if res['trail_exit'] else "no stop"
                imp = res['improvement']
                imp_str = f"{'+'if imp>=0 else ''}{imp:.0f}"
                print(f"    {str(res['start_date'])[:10]}: peak={res['peak_pct']:>+5.1f}%, "
                      f"actual={res['actual_pct']:>+6.1f}%, trail={res['trail_pct']:>+6.1f}%, "
                      f"delta=${imp_str:>7s}  [{fired}]")
            
            print(f"    >> Total improvement: ${total_improvement:>+9.0f}  Stops fired: {stops_fired}/{len(results)}")
