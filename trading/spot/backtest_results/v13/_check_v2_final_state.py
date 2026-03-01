"""Check final state of v2_full: open positions, cash, realized PnL, unrealized."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

import sqlite3, pandas as pd, numpy as np
from v13_router_engine_v2 import V13RouterV2, V13Config, Phase, V13SignalPack
from _backtest_full_v2_final import V13RouterV2Final, compute_2d_divergence_dates

coins = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
capital = 10000
per_coin = capital / len(coins)

total_equity = 0
total_cash = 0
total_invested = 0
total_unrealized = 0

for coin in coins:
    base = coin.split('/')[0]
    div_dates = compute_2d_divergence_dates(coin)
    
    pack = V13SignalPack(base)
    eng = V13RouterV2Final(pack, V13Config(), conviction_enabled=True,
                          min_score=3, exhaustion_tf='2W', exhaustion_mode='k_lift',
                          div_dates=div_dates, top_timing_enabled=True, max_wait_days=35)
    eng.cfg.CAPITAL = per_coin
    r = eng.run()
    
    # Get final state
    phase = eng.phase.name if hasattr(eng.phase, 'name') else str(eng.phase)
    cash = eng.cash
    spot_coins = eng.coins
    short_coins = eng.short_coins
    last_price = eng.last_price if hasattr(eng, 'last_price') else 0
    
    # Try to get last price from trades
    last_trade = eng.trades[-1] if eng.trades else None
    if last_trade:
        last_price = last_trade['price']
    
    spot_value = spot_coins * last_price if spot_coins > 0 else 0
    short_value = short_coins * last_price if short_coins > 0 else 0
    
    equity = r['final_equity']
    invested = equity - cash
    
    print(f"{coin}:")
    print(f"  Phase: {phase}")
    print(f"  Equity: ${equity:,.2f}")
    print(f"  Cash: ${cash:,.2f}")
    print(f"  Spot coins: {spot_coins:.6f} (value ~${spot_value:,.2f})")
    print(f"  Short coins: {short_coins:.6f} (value ~${short_value:,.2f})")
    print(f"  Last price: ${last_price:,.2f}")
    
    # Check for open shorts
    if short_coins > 0:
        print(f"  ** OPEN SHORT: {short_coins:.4f} coins")
        # Find short entry
        short_entries = [t for t in eng.trades if 'SHORT' in str(t.get('action', '')) and 'CLOSE' not in str(t.get('action', ''))]
        if short_entries:
            for se in short_entries[-3:]:
                print(f"     Entry: {se['date']} @ ${se['price']:.2f}")
    
    if spot_coins > 0:
        print(f"  ** OPEN LONG: {spot_coins:.4f} coins")
        buy_entries = [t for t in eng.trades if 'BUY' in str(t.get('action', '')) or 'MARKUP' in str(t.get('action', ''))]
        if buy_entries:
            for be in buy_entries[-3:]:
                print(f"     Entry: {be['date']} @ ${be['price']:.2f}")
    
    # Last few trades
    print(f"  Last 5 trades:")
    for t in eng.trades[-5:]:
        a = str(t.get('action', ''))
        amt = t.get('amount', 0)
        if amt != 0:
            print(f"    {t['date']} - {a} @ ${t['price']:.2f} (${amt:.2f})")
    
    total_equity += equity
    total_cash += cash
    print()

print(f"PORTFOLIO:")
print(f"  Total equity: ${total_equity:,.2f}")
print(f"  Total PnL: ${total_equity - capital:+,.2f} ({(total_equity - capital)/capital*100:+.1f}%)")
