"""
Analyze every T2/T3 tier add in V13 backtest.
For each tier add: was the subsequent trade profitable or a loss?
Did signal conditions (HH_HL, ADX, OB proximity) predict success?
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack


def analyze_coin(coin, start='2023-01-01', end='2026-02-25', capital=2500):
    pack = V13SignalPack(coin)
    cfg = V13Config()
    cfg.START_DATE = start
    cfg.END_DATE = end
    cfg.CAPITAL = capital

    bt = V13BacktestV8(pack, cfg)
    result = bt.run()
    if result is None:
        print(f"  {coin}: No data")
        return []

    # Find all tier add trades
    tier_adds = []
    for i, t in enumerate(bt.trades):
        action = t.get('action', '')
        if 'BUY_T2' in action or 'BUY_T3' in action or 'SHORT_T2' in action or 'SHORT_T3' in action:
            tier = 2 if 'T2' in action else 3
            side = 'short' if 'SHORT' in action else 'long'
            phase = t.get('phase', '')

            # Find the closing trade for this position
            close_trade = None
            for j in range(i+1, len(bt.trades)):
                ct = bt.trades[j]
                ca = ct.get('action', '')
                if side == 'long' and 'SELL_ALL' in ca:
                    close_trade = ct
                    break
                elif side == 'short' and 'SHORT_CLOSE' in ca:
                    close_trade = ct
                    break

            # Get signal conditions at time of tier add
            date = t['date']
            price = t['price']

            hh_hl = bt.pack.structure.hh_hl_streak(date, cfg.HH_HL_LOOKBACK) if hasattr(bt.pack, 'structure') else 0
            try:
                adx_val = pack.daily.loc[:date, 'adx'].iloc[-1] if 'adx' in pack.daily.columns else np.nan
            except:
                adx_val = np.nan

            # Days since phase start
            days_in = (date - bt.phase_start_date).days if bt.phase_start_date else 0

            # Check if OB signal was near (within 14 days)
            ob_near = False
            for ob_date in bt.ob_exits_2w:
                if 0 <= (ob_date - date).days <= 14:
                    ob_near = True
                    break
            for ob_date in bt.ob85_1w:
                if 0 <= (ob_date - date).days <= 14:
                    ob_near = True
                    break

            tier_adds.append({
                'coin': coin,
                'date': str(date.date()) if hasattr(date, 'date') else str(date)[:10],
                'tier': f'T{tier}',
                'side': side,
                'phase': phase,
                'price': price,
                'amount': t.get('amount', 0),
                'days_in_phase': days_in,
                'close_pnl_pct': close_trade.get('pnl_pct', 0) if close_trade else None,
                'close_action': close_trade.get('action', 'OPEN') if close_trade else 'STILL_OPEN',
                'ob_within_14d': ob_near,
                'outcome': 'WIN' if close_trade and close_trade.get('pnl_pct', 0) > 0 else ('OPEN' if not close_trade else 'LOSS'),
            })

    return tier_adds


def main():
    coins = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']
    all_adds = []

    print("=" * 80)
    print("  V13 TIER ADD ANALYSIS — Which T2/T3 adds helped vs hurt?")
    print("=" * 80)

    for coin in coins:
        adds = analyze_coin(coin)
        all_adds.extend(adds)

    if not all_adds:
        print("No tier adds found!")
        return

    # Summary
    print(f"\n{'='*80}")
    print(f"  TOTAL TIER ADDS: {len(all_adds)}")
    print(f"{'='*80}\n")

    # Group by tier + side
    for tier in ['T2', 'T3']:
        for side in ['long', 'short']:
            subset = [a for a in all_adds if a['tier'] == tier and a['side'] == side]
            if not subset:
                continue
            wins = [a for a in subset if a['outcome'] == 'WIN']
            losses = [a for a in subset if a['outcome'] == 'LOSS']
            opens = [a for a in subset if a['outcome'] == 'OPEN']

            print(f"\n--- {tier} {side.upper()} ({len(subset)} total) ---")
            print(f"  Wins: {len(wins)}, Losses: {len(losses)}, Still Open: {len(opens)}")
            if wins:
                avg_win = np.mean([a['close_pnl_pct'] for a in wins])
                print(f"  Avg win return: {avg_win:+.1f}%")
            if losses:
                avg_loss = np.mean([a['close_pnl_pct'] for a in losses])
                print(f"  Avg loss return: {avg_loss:+.1f}%")

            # OB proximity analysis
            ob_adds = [a for a in subset if a['ob_within_14d']]
            if ob_adds:
                ob_losses = [a for a in ob_adds if a['outcome'] == 'LOSS']
                print(f"  WARNING: {len(ob_adds)} adds within 14d of OB signal -- {len(ob_losses)} were losses")

    # Detailed per-trade
    print(f"\n{'='*80}")
    print(f"  DETAILED TIER ADDS")
    print(f"{'='*80}")
    print(f"{'Coin':<6} {'Date':<12} {'Tier':<4} {'Side':<6} {'$Amt':>8} {'Days':>5} {'Close%':>8} {'OB14d':>6} {'Result':<8}")
    print("-" * 75)
    for a in sorted(all_adds, key=lambda x: x['date']):
        close_pct = f"{a['close_pnl_pct']:+.1f}%" if a['close_pnl_pct'] is not None else "OPEN"
        ob = "YES" if a['ob_within_14d'] else "no"
        print(f"{a['coin']:<6} {a['date']:<12} {a['tier']:<4} {a['side']:<6} "
              f"${a['amount']:>7.0f} {a['days_in_phase']:>5d} {close_pct:>8} {ob:>6} {a['outcome']:<8}")

    # Key question: would signal gates have prevented any losses?
    print(f"\n{'='*80}")
    print(f"  LOSS ANALYSIS — Could signal gates have prevented these?")
    print(f"{'='*80}")
    losses = [a for a in all_adds if a['outcome'] == 'LOSS']
    for a in losses:
        print(f"  {a['coin']} {a['date']} {a['tier']} {a['side']}: {a['close_pnl_pct']:+.1f}% "
              f"(${a['amount']:.0f} invested, {a['days_in_phase']}d in phase, OB_near={a['ob_within_14d']})")


if __name__ == '__main__':
    main()
