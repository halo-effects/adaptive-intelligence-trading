"""Show full V13 phase timeline for each coin — all phases, durations, transitions."""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack
from run_new_coins_profiles import make_config

COINS = ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']

for coin in COINS:
    print(f"\n{'='*90}")
    print(f"  {coin} — Full Phase Timeline (High profile)")
    print(f"{'='*90}")
    
    pack = V13SignalPack(coin)
    cfg = make_config('high')
    bt = V13BacktestV8(pack, cfg)
    bt.run()
    
    # Phase duration stats
    phase_stats = {}  # phase -> [(start, end, duration_days, exit_to)]
    
    for i, t in enumerate(bt.phase_log):
        phase_from = str(t.get('from', ''))
        phase_to = str(t.get('to', ''))
        date = t.get('date')
        reason = t.get('reason', '')
        
        if not date:
            continue
        
        # Calculate duration (time until next transition)
        if i + 1 < len(bt.phase_log):
            next_date = bt.phase_log[i + 1].get('date')
            if next_date:
                days = (next_date - date).days
            else:
                days = 0
        else:
            days = 0  # last transition
        
        date_str = str(date)[:10]
        print(f"  {date_str}  {phase_from:>10} -> {phase_to:<10}  {days:>4}d  {reason[:60]}")
        
        phase_stats.setdefault(phase_to, []).append({
            'start': date_str, 'days': days,
            'exit_to': bt.phase_log[i+1]['to'] if i+1 < len(bt.phase_log) else 'END'
        })
    
    # Summary
    print(f"\n  --- Phase Summary ---")
    for phase in ['DCA', 'MARKUP', 'FLAT', 'MARKDOWN']:
        entries = phase_stats.get(phase, [])
        if not entries:
            continue
        total_days = sum(e['days'] for e in entries)
        avg_days = total_days / len(entries) if entries else 0
        exits = {}
        for e in entries:
            ex = str(e['exit_to'])
            exits[ex] = exits.get(ex, 0) + 1
        exit_str = ', '.join(f"{k}:{v}" for k, v in sorted(exits.items()))
        print(f"  {phase:>10}: {len(entries)} periods, {total_days}d total, {avg_days:.0f}d avg  exits: {exit_str}")
    
    # DCA windows by year
    dca_entries = phase_stats.get('DCA', [])
    if dca_entries:
        print(f"\n  --- DCA Windows by Year ---")
        by_year = {}
        for e in dca_entries:
            yr = e['start'][:4]
            by_year.setdefault(yr, []).append(e)
        for yr in sorted(by_year.keys()):
            entries = by_year[yr]
            markup = sum(1 for e in entries if str(e['exit_to']) == 'MARKUP')
            markdown = sum(1 for e in entries if str(e['exit_to']) == 'MARKDOWN')
            other = len(entries) - markup - markdown
            print(f"    {yr}: {len(entries)} windows -> MARKUP:{markup} MARKDOWN:{markdown} OTHER:{other}")

print()
