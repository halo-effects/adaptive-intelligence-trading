"""Analyze DCA window context — what precedes each window and how price behaves."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, Phase
from v13_signals import V13SignalPack
from run_new_coins_profiles import make_config
from dca_long_sweep import load_candles
from datetime import datetime

COINS = ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']

for coin in COINS:
    print(f"\n{'='*100}")
    print(f"  {coin} — DCA Window Context Analysis")
    print(f"{'='*100}")
    
    pack = V13SignalPack(coin)
    cfg = make_config('high')
    bt = V13BacktestV8(pack, cfg)
    bt.run()
    
    # Build phase timeline with from/to context
    dca_windows = []
    for i, t in enumerate(bt.phase_log):
        to_phase = str(t.get('to', ''))
        from_phase = str(t.get('from', ''))
        date = t.get('date')
        reason = t.get('reason', '')
        
        if to_phase == 'DCA':
            # Find what DCA exits to
            exit_to = 'END'
            exit_date = '2026-02-27'
            for j in range(i+1, len(bt.phase_log)):
                if str(bt.phase_log[j].get('to', '')) != 'DCA':
                    exit_to = str(bt.phase_log[j].get('to', ''))
                    exit_date = str(bt.phase_log[j].get('date', ''))[:10]
                    break
            
            # Find what preceded FLAT (if DCA came from FLAT)
            pre_flat = ''
            pre_flat_reason = ''
            if from_phase == 'FLAT':
                for k in range(i-1, -1, -1):
                    if str(bt.phase_log[k].get('to', '')) == 'FLAT':
                        pre_flat = str(bt.phase_log[k].get('from', ''))
                        pre_flat_reason = bt.phase_log[k].get('reason', '')[:50]
                        break
            
            dca_windows.append({
                'start': str(date)[:10],
                'end': exit_date,
                'from': from_phase,
                'exit_to': exit_to,
                'reason': reason[:60],
                'pre_flat': pre_flat,
                'pre_flat_reason': pre_flat_reason,
            })
    
    print(f"  {'Start':>12} {'End':>12} {'From':>10} {'Exit':>10} {'Pre-FLAT':>10} {'Price%':>8}  Context")
    print(f"  {'-'*12} {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*8}  {'-'*40}")
    
    for w in dca_windows:
        # Get price change during window
        df = load_candles(coin, '1h', w['start'], w['end'])
        if not df.empty:
            price_chg = (df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close'] * 100
        else:
            price_chg = float('nan')
        
        # Classification guess
        if w['pre_flat'] in ('MARKUP',):
            context = 'POST-TOP (distribution?)'
        elif w['pre_flat'] in ('MARKDOWN',):
            context = 'POST-BOTTOM (accumulation?)'
        elif w['from'] == 'None' or w['from'] == 'START':
            context = 'INITIAL'
        else:
            context = f"from {w['from']}: {w['reason'][:30]}"
        
        marker = 'LONG OK' if w['exit_to'] == 'MARKUP' else 'SHORT OK' if w['exit_to'] == 'MARKDOWN' else '?'
        
        print(f"  {w['start']:>12} {w['end']:>12} {w['from']:>10} {w['exit_to']:>10} {w['pre_flat']:>10} {price_chg:>+7.1f}%  {context}  [{marker}]")

    # Summary stats
    post_top = [w for w in dca_windows if w['pre_flat'] == 'MARKUP']
    post_bottom = [w for w in dca_windows if w['pre_flat'] == 'MARKDOWN']
    print(f"\n  Summary:")
    print(f"    Post-top (distribution?):    {len(post_top)} windows -> exits: {', '.join(w['exit_to'] for w in post_top)}")
    print(f"    Post-bottom (accumulation?): {len(post_bottom)} windows -> exits: {', '.join(w['exit_to'] for w in post_bottom)}")
