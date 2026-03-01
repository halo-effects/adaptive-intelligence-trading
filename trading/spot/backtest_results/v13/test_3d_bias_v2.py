"""Test 3D bias V2: Asymmetric — bear filter only.

Rules:
  BEAR (death cross active):
    - MARKUP entry: BLOCKED (no longs against confirmed bear)
    - MARKDOWN entry: allowed (shorts are fine in bear)
  
  BULL or NEUTRAL:
    - Everything allowed (let LH_LL gate handle bad shorts)

This avoids the lag problem on bull entries — we never block markups
during golden cross, and we never block markdowns at all.
We ONLY block markups during confirmed bear markets.
"""
from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack
from build_3d_signals import build_3d_signals
from run_new_coins_profiles import make_config
import pandas as pd


def get_bias_at_date(df_3d, date):
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


def analyze(coin, profile='high'):
    pack = V13SignalPack(coin)
    cfg = make_config(profile)
    bt = V13BacktestV8(pack, cfg)
    r = bt.run()
    df_3d = build_3d_signals(coin)
    
    print(f"\n{'='*70}")
    print(f"{coin} ({profile}) -- Current ROI: {r['roi']:+.1f}%")
    print(f"{'='*70}")
    
    blocked_good = []
    blocked_bad = []
    
    for i, t in enumerate(bt.phase_log):
        date = t.get('date')
        to_phase = str(t.get('to', ''))
        reason = t.get('reason', '')
        equity = t.get('equity', 0)
        
        if not date:
            continue
        
        bias = get_bias_at_date(df_3d, date)
        
        # Only check MARKUP entries — only block during bear bias
        if to_phase == 'MARKUP':
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
            
            marker = " ** BLOCKED" if would_block else ""
            quality = "GOOD" if good else "BAD"
            print(f"  MARKUP  {str(date)[:10]}: bias={bias:>7}, pnl={pnl:>+8.0f} ({pnl_pct:>+5.1f}%) [{quality}]{marker}")
            
            if would_block:
                if good:
                    blocked_good.append((date, pnl, pnl_pct))
                else:
                    blocked_bad.append((date, pnl, pnl_pct))
        
        elif to_phase == 'MARKDOWN':
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
            quality = "GOOD" if good else "BAD"
            # Never blocked in V2
            print(f"  MARKDOWN {str(date)[:10]}: bias={bias:>7}, pnl={pnl:>+8.0f} ({pnl_pct:>+5.1f}%) [{quality}]")
    
    saved = sum(p for _,p,_ in blocked_bad)
    missed = sum(p for _,p,_ in blocked_good)
    
    print(f"\n  Bear-only filter results:")
    print(f"    Blocked bad markups:  {len(blocked_bad):>2} trades, ${saved:>+9.0f} saved")
    print(f"    Blocked good markups: {len(blocked_good):>2} trades, ${missed:>+9.0f} missed")
    print(f"    Net impact: ${-saved + missed:>+9.0f} ({'HELPS' if saved > missed else 'HURTS'})")


if __name__ == '__main__':
    print("3D BIAS V2: BEAR-ONLY FILTER")
    print("Only blocks MARKUP entries during 3D death cross. Everything else allowed.")
    print()
    
    for coin in ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']:
        analyze(coin, 'high')
    
    print("\n\n--- Also check Medium and Low for best coin ---")
    for profile in ['medium', 'low']:
        for coin in ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']:
            pack = V13SignalPack(coin)
            cfg = make_config(profile)
            bt = V13BacktestV8(pack, cfg)
            r = bt.run()
            df_3d = build_3d_signals(coin)
            
            blocked_bad_total = 0
            blocked_good_total = 0
            
            for i, t in enumerate(bt.phase_log):
                date = t.get('date')
                to_phase = str(t.get('to', ''))
                equity = t.get('equity', 0)
                if to_phase != 'MARKUP' or not date:
                    continue
                bias = get_bias_at_date(df_3d, date)
                if bias != 'bear':
                    continue
                next_eq = None
                for j in range(i+1, len(bt.phase_log)):
                    if bt.phase_log[j].get('to') != 'MARKUP':
                        next_eq = bt.phase_log[j].get('equity', equity)
                        break
                if next_eq is None:
                    next_eq = r['final_equity']
                pnl = next_eq - equity
                if pnl > 0:
                    blocked_good_total += pnl
                else:
                    blocked_bad_total += pnl
            
            net = -blocked_bad_total + blocked_good_total
            label = "HELPS" if blocked_bad_total < 0 and abs(blocked_bad_total) > blocked_good_total else "HURTS" if blocked_good_total > abs(blocked_bad_total) else "NEUTRAL"
            print(f"  {coin} {profile:>6}: ROI={r['roi']:>+7.1f}%  Saved=${blocked_bad_total:>+8.0f}  Missed=${blocked_good_total:>+8.0f}  Net=${net:>+8.0f} {label}")
