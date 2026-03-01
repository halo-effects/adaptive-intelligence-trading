"""Test 3D death cross / golden cross as bias system for V13.

Bias rules:
  BULL (golden cross active):
    - MARKUP entry: standard gates (HH_HL >= 2 + Fib) 
    - MARKDOWN entry: BLOCKED (no shorts against bull bias)
    - FLAT->MARKUP: direct path enabled
  
  BEAR (death cross active):
    - MARKDOWN entry: standard gates (LH_LL >= 2 + ADX + Fib)
    - MARKUP entry: BLOCKED (no longs against bear bias)
    - FLAT->MARKDOWN: already exists
  
  NEUTRAL (before first cross for new coins):
    - Both directions allowed (current behavior)

We simulate this by post-processing the phase log — checking what the 3D bias
was at each phase transition and filtering accordingly.
"""
from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack
from build_3d_signals import build_3d_signals
from run_new_coins_profiles import make_config
import pandas as pd
import numpy as np


def get_bias_at_date(df_3d, date):
    """Get bull/bear bias at a given date from 3D signals.
    Returns: 'bull', 'bear', or 'neutral'
    """
    # Find most recent 3D candle on or before this date
    ts = pd.Timestamp(date)
    mask = df_3d.index <= ts
    if not mask.any():
        return 'neutral'
    row = df_3d.loc[mask].iloc[-1]
    if row['death_cross'] == 1:
        return 'bear'
    elif row['golden_cross'] == 1:
        return 'bull'
    return 'neutral'


def analyze_with_bias(coin, profile='high'):
    """Run backtest and analyze how 3D bias would have changed results."""
    pack = V13SignalPack(coin)
    cfg = make_config(profile)
    bt = V13BacktestV8(pack, cfg)
    r = bt.run()
    
    df_3d = build_3d_signals(coin)
    
    print(f"\n{'='*70}")
    print(f"{coin} ({profile}) — ROI: {r['roi']:+.1f}%, B&H: {r['buy_hold_return']:+.0f}%")
    print(f"{'='*70}")
    
    blocked_good = []
    blocked_bad = []
    allowed_good = []
    allowed_bad = []
    
    for i, t in enumerate(bt.phase_log):
        date = t.get('date')
        to_phase = str(t.get('to', ''))
        reason = t.get('reason', '')
        equity = t.get('equity', 0)
        
        if not date:
            continue
            
        bias = get_bias_at_date(df_3d, date)
        
        # Check markup entries
        if to_phase == 'MARKUP':
            # Was this markup profitable? Check next transition
            next_eq = None
            for j in range(i+1, len(bt.phase_log)):
                if bt.phase_log[j].get('to') != 'MARKUP':
                    next_eq = bt.phase_log[j].get('equity', equity)
                    break
            if next_eq is None:
                next_eq = r['final_equity']
            
            pnl = next_eq - equity
            pnl_pct = (next_eq / equity - 1) * 100 if equity > 0 else 0
            good = pnl > 0
            
            would_block = (bias == 'bear')
            marker = " ** BLOCKED by bear bias" if would_block else ""
            quality = "GOOD" if good else "BAD"
            
            print(f"  MARKUP {str(date)[:10]}: bias={bias:>7}, eq=${equity:>8.0f}, "
                  f"pnl={pnl:>+8.0f} ({pnl_pct:>+5.1f}%) [{quality}]{marker}")
            
            if would_block:
                if good:
                    blocked_good.append((date, pnl))
                else:
                    blocked_bad.append((date, pnl))
            else:
                if good:
                    allowed_good.append((date, pnl))
                else:
                    allowed_bad.append((date, pnl))
        
        # Check markdown entries
        elif to_phase == 'MARKDOWN':
            # Was this markdown profitable?
            next_eq = None
            for j in range(i+1, len(bt.phase_log)):
                if bt.phase_log[j].get('to') != 'MARKDOWN':
                    next_eq = bt.phase_log[j].get('equity', equity)
                    break
            if next_eq is None:
                next_eq = r['final_equity']
            
            pnl = next_eq - equity
            pnl_pct = (next_eq / equity - 1) * 100 if equity > 0 else 0
            good = pnl > 0
            
            would_block = (bias == 'bull')
            marker = " ** BLOCKED by bull bias" if would_block else ""
            quality = "GOOD" if good else "BAD"
            
            print(f"  MARKDOWN {str(date)[:10]}: bias={bias:>7}, eq=${equity:>8.0f}, "
                  f"pnl={pnl:>+8.0f} ({pnl_pct:>+5.1f}%) [{quality}]{marker}")
            
            if would_block:
                if good:
                    blocked_good.append((date, pnl))
                else:
                    blocked_bad.append((date, pnl))
            else:
                if good:
                    allowed_good.append((date, pnl))
                else:
                    allowed_bad.append((date, pnl))
    
    # Summary
    print(f"\n  SUMMARY:")
    print(f"    Allowed good:  {len(allowed_good):>2} trades, ${sum(p for _,p in allowed_good):>+9.0f}")
    print(f"    Allowed bad:   {len(allowed_bad):>2} trades, ${sum(p for _,p in allowed_bad):>+9.0f}")
    print(f"    Blocked bad:   {len(blocked_bad):>2} trades, ${sum(p for _,p in blocked_bad):>+9.0f} (saved)")
    print(f"    Blocked good:  {len(blocked_good):>2} trades, ${sum(p for _,p in blocked_good):>+9.0f} (missed)")
    
    net = sum(p for _,p in blocked_bad) - sum(p for _,p in blocked_good)
    print(f"    Net impact:    ${-net:>+9.0f} (positive = bias helps)")
    
    return {
        'coin': coin, 'profile': profile,
        'roi': r['roi'],
        'allowed_good': allowed_good, 'allowed_bad': allowed_bad,
        'blocked_good': blocked_good, 'blocked_bad': blocked_bad,
    }


if __name__ == '__main__':
    print("3D DEATH CROSS / GOLDEN CROSS BIAS TEST")
    print("Bull bias: block MARKDOWN entries. Bear bias: block MARKUP entries.")
    print()
    
    for coin in ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']:
        analyze_with_bias(coin, 'high')
