"""Compact summary: 2D and 3D K deflection sweep + K values at tops."""
import sqlite3, pandas as pd, numpy as np

db = sqlite3.connect('trading/spot/data/candles.db')

tops = {
    'ETH': ('2024-12-06', 3999),
    'SOL': ('2025-01-19', 252),
    'LINK': ('2024-12-08', 26.1),
    'XRP': ('2025-01-16', 3.2),
}

def compute_stochrsi(coin, timeframe):
    df = pd.read_sql(f"SELECT timestamp, open, high, low, close FROM candles_daily WHERE symbol LIKE '{coin}%' ORDER BY timestamp", db)
    if df.empty: return None
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('date').sort_index()
    r = df.resample(timeframe).agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    period = 14
    delta = r['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi_min = rsi.rolling(14).min()
    rsi_max = rsi.rolling(14).max()
    r['k'] = ((rsi - rsi_min) / (rsi_max - rsi_min)) * 100
    r['d'] = r['k'].rolling(3).mean()
    return r

for tf in ['2D', '3D']:
    print(f"\n{'='*60}")
    print(f"{tf} StochRSI K — PEAK VALUES NEAR TOPS")
    print(f"{'='*60}")
    for coin, (top_date, top_price) in tops.items():
        data = compute_stochrsi(coin, tf)
        if data is None: continue
        top_dt = pd.Timestamp(top_date)
        near = data[(data.index >= top_dt - pd.Timedelta(days=30)) & (data.index <= top_dt + pd.Timedelta(days=30))]
        k_vals = near['k'].dropna()
        peak_k = k_vals.max()
        peak_date = k_vals.idxmax()
        days = (peak_date - top_dt).days
        print(f"  {coin}: peak K={peak_k:.1f} on {peak_date.strftime('%Y-%m-%d')} ({days:+d}d from top)")

    print(f"\n{tf} PARAMETER SWEEP (ETF era 2023+, 4 coins excl BTC)")
    print(f"{'Thresh':>6} {'Drop':>5} | {'Hit':>4} | {'Total':>5} {'FP':>4} {'FP%':>5} | {'Timing':>8} | Details")
    print("-" * 80)
    
    for thresh in [70, 75, 80, 85, 90]:
        for drop in [5, 10, 15, 20]:
            all_sigs = {}
            for coin, (top_date, top_price) in tops.items():
                data = compute_stochrsi(coin, tf)
                if data is None: continue
                top_dt = pd.Timestamp(top_date)
                d_etf = data[data.index >= pd.Timestamp('2023-01-01')]
                sigs = []
                peak_k = 0; armed = False
                for idx, row in d_etf.iterrows():
                    kv = row['k']
                    if pd.isna(kv): continue
                    if kv >= thresh: armed = True; peak_k = max(peak_k, kv)
                    if armed and kv <= peak_k - drop:
                        sigs.append({'days': (idx - top_dt).days, 'k': kv, 'pk': peak_k})
                        armed = False; peak_k = 0
                all_sigs[coin] = sigs
            
            caught = 0; timings = []; details = []
            total = sum(len(s) for s in all_sigs.values())
            fp = sum(1 for c in all_sigs for s in all_sigs[c] if abs(s['days']) > 60)
            
            for coin, sigs in all_sigs.items():
                best = None
                for s in sigs:
                    if -60 <= s['days'] <= 60:
                        if best is None or abs(s['days']) < abs(best['days']):
                            best = s
                if best:
                    caught += 1; timings.append(best['days'])
                    details.append(f"{coin}:{best['days']:+d}d")
            
            avg_t = f"{np.mean(timings):+.0f}d" if timings else "N/A"
            fp_pct = f"{fp/total*100:.0f}%" if total > 0 else "N/A"
            marker = " ***" if caught == 4 else ""
            print(f"{thresh:>6} {drop:>5} | {caught:>2}/4 | {total:>5} {fp:>4} {fp_pct:>5} | {avg_t:>8} | {', '.join(details)}{marker}")
