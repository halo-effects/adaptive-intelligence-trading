import sqlite3, pandas as pd, numpy as np
from datetime import timedelta

db = sqlite3.connect('trading/spot/data/candles.db')

def stoch_rsi(close):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi_low = rsi.rolling(14).min()
    rsi_high = rsi.rolling(14).max()
    stoch_k = 100 * (rsi - rsi_low) / (rsi_high - rsi_low + 1e-10)
    stoch_k = stoch_k.rolling(3).mean()
    stoch_d = stoch_k.rolling(3).mean()
    return stoch_k, stoch_d

print("SMA50 vs SMA200 as daily confirmation for weekly StochRSI signals")
print("=" * 90)

# Track scores
sma50_md_score = 0
sma50_md_total = 0
sma200_md_score = 0
sma200_md_total = 0
sma50_mu_score = 0
sma50_mu_total = 0
sma200_mu_score = 0
sma200_mu_total = 0

for coin in ['BTC', 'ETH', 'SOL']:
    sym = [r[0] for r in db.execute('SELECT DISTINCT symbol FROM candles_daily WHERE symbol LIKE ?', (f'{coin}%',)).fetchall()]
    if not sym: continue
    daily = pd.read_sql('SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp', db, params=[sym[0]])
    daily['dt'] = pd.to_datetime(daily['timestamp'], unit='ms')
    daily.set_index('dt', inplace=True)
    daily = daily[daily.index >= '2024-09-01']

    wk = daily['close'].resample('W').last().dropna()
    k, d = stoch_rsi(wk)
    weekly = pd.DataFrame({'close': wk, 'K': k, 'D': d})
    weekly = weekly[weekly.index >= '2024-09-01']

    prev_k = weekly['K'].shift(1)
    ob_exits = weekly[(prev_k > 80) & (weekly['K'] <= 80)]
    os_exits = weekly[(prev_k < 20) & (weekly['K'] >= 20)]

    print(f"\n{'='*70}")
    print(f"  {coin}")
    print(f"{'='*70}")

    print("\n  MARKDOWN signals (weekly StochRSI OB exit):")
    for dt, row in ob_exits.iterrows():
        nearest = daily[daily.index <= dt].tail(1)
        if len(nearest) == 0: continue
        nd = nearest.iloc[0]
        vs50 = nd.get('price_vs_sma50', np.nan)
        vs200 = nd.get('price_vs_sma200', np.nan)

        future = daily[daily.index >= dt].head(60)
        max_dd = ((future['low'].min() - row['close']) / row['close'] * 100) if len(future) > 0 else 0
        real_md = max_dd < -10

        b50 = vs50 < 0
        b200 = vs200 < 0

        # Score: did the filter agree with reality?
        if b50:
            sma50_md_total += 1
            if real_md: sma50_md_score += 1
        if b200:
            sma200_md_total += 1
            if real_md: sma200_md_score += 1

        c50 = "CONFIRM" if b50 else "reject"
        c200 = "CONFIRM" if b200 else "reject"
        outcome = "DROPPED" if real_md else "bounced"

        print(f"    {dt.date()}: vs_SMA50={vs50:+.1f}% ({c50})  vs_SMA200={vs200:+.1f}% ({c200})  60d={max_dd:.1f}% [{outcome}]")

    print("\n  MARKUP signals (weekly StochRSI OS exit):")
    for dt, row in os_exits.iterrows():
        nearest = daily[daily.index <= dt].tail(1)
        if len(nearest) == 0: continue
        nd = nearest.iloc[0]
        vs50 = nd.get('price_vs_sma50', np.nan)
        vs200 = nd.get('price_vs_sma200', np.nan)

        future = daily[daily.index >= dt].head(90)
        max_up = ((future['high'].max() - row['close']) / row['close'] * 100) if len(future) > 0 else 0
        real_mu = max_up > 15

        a50 = vs50 > 0
        a200 = vs200 > 0

        if a50:
            sma50_mu_total += 1
            if real_mu: sma50_mu_score += 1
        if a200:
            sma200_mu_total += 1
            if real_mu: sma200_mu_score += 1

        c50 = "CONFIRM" if a50 else "reject"
        c200 = "CONFIRM" if a200 else "reject"
        outcome = "RALLIED" if real_mu else "failed"

        print(f"    {dt.date()}: vs_SMA50={vs50:+.1f}% ({c50})  vs_SMA200={vs200:+.1f}% ({c200})  90d_up={max_up:.1f}% [{outcome}]")

print("\n" + "=" * 90)
print("SCORECARD")
print("=" * 90)
print(f"\nMARKDOWN confirmation (below SMA = confirm markdown):")
print(f"  SMA50:  {sma50_md_score}/{sma50_md_total} correct ({100*sma50_md_score/max(sma50_md_total,1):.0f}%)")
print(f"  SMA200: {sma200_md_score}/{sma200_md_total} correct ({100*sma200_md_score/max(sma200_md_total,1):.0f}%)")
print(f"\nMARKUP confirmation (above SMA = confirm markup):")
print(f"  SMA50:  {sma50_mu_score}/{sma50_mu_total} correct ({100*sma50_mu_score/max(sma50_mu_total,1):.0f}%)")
print(f"  SMA200: {sma200_mu_score}/{sma200_mu_total} correct ({100*sma200_mu_score/max(sma200_mu_total,1):.0f}%)")

# Also check: how often is price below each SMA at each signal?
print(f"\nSIGNAL AVAILABILITY (how often does the filter trigger?):")
total_ob = 0
total_os = 0
b50_count = 0
b200_count = 0
a50_count = 0
a200_count = 0

for coin in ['BTC', 'ETH', 'SOL']:
    sym = [r[0] for r in db.execute('SELECT DISTINCT symbol FROM candles_daily WHERE symbol LIKE ?', (f'{coin}%',)).fetchall()]
    if not sym: continue
    daily = pd.read_sql('SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp', db, params=[sym[0]])
    daily['dt'] = pd.to_datetime(daily['timestamp'], unit='ms')
    daily.set_index('dt', inplace=True)
    daily = daily[daily.index >= '2024-09-01']

    wk = daily['close'].resample('W').last().dropna()
    k, d = stoch_rsi(wk)
    weekly = pd.DataFrame({'close': wk, 'K': k, 'D': d})
    weekly = weekly[weekly.index >= '2024-09-01']
    prev_k = weekly['K'].shift(1)

    for dt in weekly[(prev_k > 80) & (weekly['K'] <= 80)].index:
        nearest = daily[daily.index <= dt].tail(1)
        if len(nearest) == 0: continue
        total_ob += 1
        if nearest.iloc[0].get('price_vs_sma50', 0) < 0: b50_count += 1
        if nearest.iloc[0].get('price_vs_sma200', 0) < 0: b200_count += 1

    for dt in weekly[(prev_k < 20) & (weekly['K'] >= 20)].index:
        nearest = daily[daily.index <= dt].tail(1)
        if len(nearest) == 0: continue
        total_os += 1
        if nearest.iloc[0].get('price_vs_sma50', 0) > 0: a50_count += 1
        if nearest.iloc[0].get('price_vs_sma200', 0) > 0: a200_count += 1

print(f"\n  OB exits where price below SMA50: {b50_count}/{total_ob}")
print(f"  OB exits where price below SMA200: {b200_count}/{total_ob}")
print(f"  OS exits where price above SMA50: {a50_count}/{total_os}")
print(f"  OS exits where price above SMA200: {a200_count}/{total_os}")
