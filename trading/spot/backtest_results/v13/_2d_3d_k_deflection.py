"""
2D and 3D StochRSI K deflection analysis for top detection.
"""
import sqlite3, pandas as pd, numpy as np

db = sqlite3.connect('trading/spot/data/candles.db')

tops = {
    'ETH': ('2024-12-06', 3999),
    'SOL': ('2025-01-19', 252),
    'LINK': ('2024-12-08', 26.1),
    'XRP': ('2025-01-16', 3.2),
}

def compute_stochrsi(coin, timeframe='2D'):
    df = pd.read_sql(f"SELECT timestamp, open, high, low, close FROM candles_daily WHERE symbol LIKE '{coin}%' ORDER BY timestamp", db)
    if df.empty:
        return None
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('date').sort_index()
    
    if timeframe != '1D':
        resampled = df.resample(timeframe).agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    else:
        resampled = df
    
    period = 14
    delta = resampled['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    stoch_period = 14
    rsi_min = rsi.rolling(stoch_period).min()
    rsi_max = rsi.rolling(stoch_period).max()
    k = ((rsi - rsi_min) / (rsi_max - rsi_min)) * 100
    d = k.rolling(3).mean()
    
    resampled['k'] = k
    resampled['d'] = d
    return resampled

for tf in ['2D', '3D']:
    print("=" * 80)
    print(f"{tf} StochRSI K DEFLECTION ANALYSIS")
    print("=" * 80)
    
    # Show K values around tops
    print(f"\n--- K VALUES AROUND TOPS ({tf}) ---\n")
    for coin, (top_date, top_price) in tops.items():
        data = compute_stochrsi(coin, tf)
        if data is None:
            continue
        top_dt = pd.Timestamp(top_date)
        window = data[(data.index >= top_dt - pd.Timedelta(days=60)) & (data.index <= top_dt + pd.Timedelta(days=60))]
        print(f"{coin} (top {top_date}):")
        for idx, row in window.iterrows():
            days = (idx - top_dt).days
            k_val = f"{row['k']:.1f}" if pd.notna(row['k']) else "NaN"
            marker = " <--" if abs(days) <= 3 else ""
            print(f"  {idx.strftime('%Y-%m-%d')} ({days:+4d}d): K={k_val:>6} ${row['close']:.2f}{marker}")
        print()
    
    # Sweep
    print(f"\n--- PARAMETER SWEEP ({tf}) ---\n")
    print(f"{'Thresh':>6} {'Drop':>5} | {'Caught':>6} | {'Total':>5} {'False':>5} | {'Avg Timing':>10} | Details")
    print("-" * 90)
    
    for thresh in [70, 75, 80, 85, 90]:
        for drop in [5, 10, 15, 20]:
            all_signals = {}
            for coin, (top_date, top_price) in tops.items():
                data = compute_stochrsi(coin, tf)
                if data is None:
                    continue
                top_dt = pd.Timestamp(top_date)
                etf_start = pd.Timestamp('2023-01-01')
                data_etf = data[data.index >= etf_start]
                
                signals = []
                peak_k = 0
                armed = False
                
                for idx, row in data_etf.iterrows():
                    k_val = row['k']
                    if pd.isna(k_val):
                        continue
                    if k_val >= thresh:
                        armed = True
                        peak_k = max(peak_k, k_val)
                    if armed and k_val <= peak_k - drop:
                        days = (idx - top_dt).days
                        pct = (row['close'] / top_price - 1) * 100
                        signals.append({'date': idx, 'days': days, 'pct': pct, 'k': k_val, 'peak_k': peak_k})
                        armed = False
                        peak_k = 0
                
                all_signals[coin] = signals
            
            caught = 0
            timings = []
            details = []
            total = sum(len(s) for s in all_signals.values())
            false_count = 0
            
            for coin, signals in all_signals.items():
                best = None
                for s in signals:
                    if -60 <= s['days'] <= 60:
                        if best is None or abs(s['days']) < abs(best['days']):
                            best = s
                if best:
                    caught += 1
                    timings.append(best['days'])
                    details.append(f"{coin}:{best['days']:+d}d")
                for s in signals:
                    if abs(s['days']) > 60:
                        false_count += 1
            
            avg_t = f"{np.mean(timings):+.0f}d" if timings else "N/A"
            print(f"{thresh:>6} {drop:>5} | {caught:>4}/4 | {total:>5} {false_count:>5} | {avg_t:>10} | {', '.join(details)}")

    # Best configs detail
    print(f"\n--- BEST CONFIG DETAILS ({tf}) ---\n")
    # Find configs that caught 4/4
    for thresh in [70, 75, 80, 85, 90]:
        for drop in [5, 10, 15, 20]:
            all_signals = {}
            for coin, (top_date, top_price) in tops.items():
                data = compute_stochrsi(coin, tf)
                if data is None:
                    continue
                top_dt = pd.Timestamp(top_date)
                etf_start = pd.Timestamp('2023-01-01')
                data_etf = data[data.index >= etf_start]
                
                signals = []
                peak_k = 0
                armed = False
                
                for idx, row in data_etf.iterrows():
                    k_val = row['k']
                    if pd.isna(k_val):
                        continue
                    if k_val >= thresh:
                        armed = True
                        peak_k = max(peak_k, k_val)
                    if armed and k_val <= peak_k - drop:
                        days = (idx - top_dt).days
                        pct = (row['close'] / top_price - 1) * 100
                        signals.append({'date': idx, 'days': days, 'pct': pct, 'k': k_val, 'peak_k': peak_k})
                        armed = False
                        peak_k = 0
                
                all_signals[coin] = signals
            
            caught = sum(1 for coin in all_signals if any(-60 <= s['days'] <= 60 for s in all_signals[coin]))
            if caught == 4:
                total = sum(len(s) for s in all_signals.values())
                false_count = sum(1 for coin in all_signals for s in all_signals[coin] if abs(s['days']) > 60)
                print(f"\n*** {tf} Thresh={thresh}, Drop={drop} (4/4, {false_count} false out of {total}) ***")
                for coin in ['ETH', 'SOL', 'LINK', 'XRP']:
                    top_dt = pd.Timestamp(tops[coin][0])
                    print(f"  {coin}:")
                    for s in all_signals[coin]:
                        label = "TOP ZONE" if -60 <= s['days'] <= 60 else ""
                        print(f"    {s['date'].strftime('%Y-%m-%d')} ({s['days']:+4d}d): K={s['k']:.1f} (peak={s['peak_k']:.1f}) {s['pct']:+.1f}% {label}")
