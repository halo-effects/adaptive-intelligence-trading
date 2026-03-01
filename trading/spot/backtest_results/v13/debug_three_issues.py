"""Debug Brett's three questions:
1. BTC: Should post-top go straight to markdown after cooldown?
2. XRP: What went wrong with markdown signals?
3. BNB: Did it cold start wrong?
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import pandas as pd, numpy as np
from v13_signals import V13SignalPack

# ── ISSUE 2: XRP Markdown Signal Check ──
print("=" * 80)
print("ISSUE 2: XRP Markdown — Did signals match matrix winners?")
print("=" * 80)

pack = V13SignalPack('XRP')
daily = pack.daily

# XRP markdown entries from results:
# 1. Feb 24, 2025: ADX=27+Fib_break (from DCA) — shorted at $2.28, lost -29%
# 2. Apr 7, 2025: ADX=22+Fib_break (from DCA) — shorted at $1.90, lost -34%
# 3. Oct 12, 2025: ADX=23+Fib_break (from DCA) — shorted, still open +42.8%

dates_to_check = [
    ('2025-02-24', 'Markdown #1 (lost -29%)'),
    ('2025-04-07', 'Markdown #2 (lost -34%)'),
    ('2025-10-12', 'Markdown #3 (won +42.8%)')
]

for date_str, label in dates_to_check:
    date = pd.Timestamp(date_str)
    idx = daily.index.get_indexer([date], method='pad')[0]
    price = daily['close'].iloc[idx]
    adx = pack.structure.adx_at(date)
    hh = pack.structure.hh_hl_streak(date, 2)
    
    # Check what happened AFTER this markdown entry
    future = daily.iloc[idx:idx+30]
    if len(future) > 1:
        max_price = future['close'].max()
        min_price = future['close'].min()
        end_price = future['close'].iloc[-1] if len(future) >= 30 else future['close'].iloc[-1]
        
    print(f"\n  {label}: {date_str}")
    print(f"    Entry price: ${price:.3f}")
    print(f"    ADX at entry: {adx:.1f}")
    print(f"    HH_HL (bullish structure?): {hh}")
    print(f"    Next 30d: high=${max_price:.3f}, low=${min_price:.3f}, end=${end_price:.3f}")
    print(f"    Direction after entry: {'UP (wrong!)' if end_price > price else 'DOWN (correct)'}")
    
    # Check if price was above 200-SMA (overextended)
    overext = pack.sma200.overextension_at(date)
    print(f"    200-SMA overextension: {overext*100:+.1f}%")
    
    # What was CFGI?
    cfgi = pack.cfgi.value_at(date)
    print(f"    CFGI: {cfgi:.0f}")

# ── ISSUE 3: BNB Cold Start ──
print("\n" + "=" * 80)
print("ISSUE 3: BNB — Did it cold start wrong?")
print("=" * 80)

pack_bnb = V13SignalPack('BNB')
daily_bnb = pack_bnb.daily

# BNB entered markup Oct 5 via HH_HL+Fib_support
date = pd.Timestamp('2024-10-05')
idx = daily_bnb.index.get_indexer([date], method='pad')[0]
price = daily_bnb['close'].iloc[idx]
adx = pack_bnb.structure.adx_at(date)
hh = pack_bnb.structure.hh_hl_streak(date, 2)
overext = pack_bnb.sma200.overextension_at(date)
cfgi = pack_bnb.cfgi.value_at(date)

print(f"\n  BNB Markup entry: Oct 5, 2024")
print(f"    Price: ${price:.0f}")
print(f"    ADX: {adx:.1f}")
print(f"    HH_HL: {hh}")
print(f"    200-SMA overextension: {overext*100:+.1f}%")
print(f"    CFGI: {cfgi:.0f}")

# What happened to BNB price after Oct 5?
future_bnb = daily_bnb.iloc[idx:idx+90]
print(f"    Next 90d: ${future_bnb['close'].iloc[0]:.0f} -> ${future_bnb['close'].iloc[-1]:.0f} (high=${future_bnb['close'].max():.0f})")

# ADX profile for BNB — is it naturally low?
all_adx = []
for d in daily_bnb.index:
    try:
        a = pack_bnb.structure.adx_at(d)
        if not np.isnan(a):
            all_adx.append(a)
    except:
        pass

print(f"\n  BNB ADX profile (entire history):")
print(f"    Min: {min(all_adx):.1f}, Max: {max(all_adx):.1f}, Avg: {np.mean(all_adx):.1f}, Median: {np.median(all_adx):.1f}")
print(f"    % below 20: {sum(1 for a in all_adx if a < 20)/len(all_adx)*100:.0f}%")
print(f"    % below 25: {sum(1 for a in all_adx if a < 25)/len(all_adx)*100:.0f}%")

# Compare with BTC/ETH/SOL
for coin in ['BTC', 'ETH', 'SOL', 'XRP']:
    p = V13SignalPack(coin)
    coin_adx = []
    for d in p.daily.index:
        try:
            a = p.structure.adx_at(d)
            if not np.isnan(a):
                coin_adx.append(a)
        except:
            pass
    print(f"    {coin} ADX: avg={np.mean(coin_adx):.1f}, median={np.median(coin_adx):.1f}, %<20={sum(1 for a in coin_adx if a < 20)/len(coin_adx)*100:.0f}%")

# ── ISSUE 1: BTC post-top behavior ──
print("\n" + "=" * 80)
print("ISSUE 1: BTC — Post-top, should we go straight to MARKDOWN?")
print("=" * 80)

pack_btc = V13SignalPack('BTC')
# After Jan 1 2025 top, what would have happened with a 14-day cooldown then markdown?
print("\n  BTC after Jan 1 2025 top ($94,592):")
btc_post = pack_btc.daily[pack_btc.daily.index >= pd.Timestamp('2025-01-01')]
for date, row in btc_post.head(60).iterrows():
    if date.weekday() == 0 or date == pd.Timestamp('2025-01-01'):
        adx = pack_btc.structure.adx_at(date)
        fib = None  # Can't easily compute here
        print(f"    {date.strftime('%Y-%m-%d')}: ${row['close']:>10,.0f}  ADX={adx:>5.1f}")
        
print("\n  BTC was RANGING at $92-106K after the top.")
print("  ADX only crossed >20 on Feb 10. Real crash started Feb 24.")
print("  A fixed cooldown (14d) then straight to MARKDOWN would have shorted at ~$102K")
print("  but BTC was actually going UP during Jan — shorts would have lost money.")
print("  The 42-day fallback to DCA -> MARKDOWN at Feb 24 was actually safer.")
