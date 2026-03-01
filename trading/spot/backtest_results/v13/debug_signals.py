"""Debug: check how often HH_HL+Fib fired but was blocked by SMA200 overextension."""
import sys
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13Config, price_near_fib_support
from v13_signals import V13SignalPack

coins = ['ETH', 'SOL', 'BTC']
cfg = V13Config()
cfg.START_DATE = '2020-10-01'
cfg.END_DATE = '2026-02-26'

for coin in coins:
    pack = V13SignalPack(coin)
    daily = pack.daily
    data = daily[(daily.index >= cfg.START_DATE) & (daily.index <= cfg.END_DATE)]
    
    print(f"\n{'='*60}")
    print(f"  {coin} — Blocked markup entries (SMA200 > {cfg.SMA200_OVEREXTENSION:.0%})")
    print(f"{'='*60}")
    
    blocked = 0
    allowed = 0
    for date, row in data.iterrows():
        price = row['close']
        hh = pack.structure.hh_hl_streak(date, min_streak=cfg.HH_HL_LOOKBACK)
        if not hh:
            continue
        
        # Check fib support
        fib_data = pack.structure.daily[pack.structure.daily.index <= date].tail(60)
        if len(fib_data) < 10:
            continue
        high = fib_data['high'].max()
        low = fib_data['low'].min()
        diff = high - low
        if diff == 0:
            continue
        fibs = [low + diff * r for r in [0.236, 0.382, 0.5, 0.618, 0.786]]
        near_fib = any(abs(price - f) / price < 0.03 for f in fibs)
        if not near_fib:
            continue
        
        overext = pack.sma200.overextension_at(date)
        if not np.isnan(overext) and overext > cfg.SMA200_OVEREXTENSION:
            blocked += 1
            if blocked <= 20:  # Show first 20
                print(f"  BLOCKED {date.date()}: HH_HL+Fib @ ${price:,.2f}, SMA200 overext={overext*100:+.1f}%")
        else:
            allowed += 1
            if allowed <= 10:
                print(f"  ALLOWED {date.date()}: HH_HL+Fib @ ${price:,.2f}, SMA200 overext={overext*100:+.1f}% {'(NaN)' if np.isnan(overext) else ''}")
    
    print(f"\n  Total: {blocked} blocked, {allowed} allowed")
