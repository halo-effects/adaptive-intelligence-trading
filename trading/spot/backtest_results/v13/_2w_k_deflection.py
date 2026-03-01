"""
2W StochRSI K deflection analysis for top detection.
Pattern: K rises above threshold, then drops by X points = momentum topping.
Test across ETH, SOL, LINK, XRP with known ETF-era tops.
"""
import sqlite3, pandas as pd, numpy as np

db = sqlite3.connect('trading/spot/data/candles.db')

tops = {
    'ETH': ('2024-12-06', 3999),
    'SOL': ('2025-01-19', 252),
    'BTC': ('2025-01-20', 103707),
    'LINK': ('2024-12-08', 26.1),
    'XRP': ('2025-01-16', 3.2),
}

def compute_2w_stochrsi(coin):
    df = pd.read_sql(f"SELECT timestamp, open, high, low, close FROM candles_daily WHERE symbol LIKE '{coin}%' ORDER BY timestamp", db)
    if df.empty:
        return None
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('date').sort_index()
    
    # Resample to 2W
    w2 = df.resample('2W').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
    
    # RSI
    period = 14
    delta = w2['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # StochRSI
    stoch_period = 14
    rsi_min = rsi.rolling(stoch_period).min()
    rsi_max = rsi.rolling(stoch_period).max()
    k = ((rsi - rsi_min) / (rsi_max - rsi_min)) * 100
    d = k.rolling(3).mean()
    
    w2['k'] = k
    w2['d'] = d
    w2['rsi'] = rsi
    return w2

# Test multiple threshold/drop combos
thresholds = [70, 75, 80, 85]
drops = [5, 10, 15, 20]

print("=" * 80)
print("2W StochRSI K DEFLECTION ANALYSIS — TOP DETECTION")
print("=" * 80)

# First, show K values around each top
print("\n--- K VALUES AROUND EACH TOP ---\n")
for coin, (top_date, top_price) in tops.items():
    w2 = compute_2w_stochrsi(coin)
    if w2 is None:
        print(f"{coin}: no data")
        continue
    top_dt = pd.Timestamp(top_date)
    window = w2[(w2.index >= top_dt - pd.Timedelta(days=120)) & (w2.index <= top_dt + pd.Timedelta(days=120))]
    print(f"{coin} (top {top_date}, ~${top_price}):")
    for idx, row in window.iterrows():
        days_from_top = (idx - top_dt).days
        marker = " <-- TOP" if abs(days_from_top) <= 14 else ""
        k_val = f"{row['k']:.1f}" if pd.notna(row['k']) else "NaN"
        d_val = f"{row['d']:.1f}" if pd.notna(row['d']) else "NaN"
        print(f"  {idx.strftime('%Y-%m-%d')} ({days_from_top:+4d}d): K={k_val:>6} D={d_val:>6} close=${row['close']:.2f}{marker}")
    print()

# Now sweep deflection parameters
print("\n--- DEFLECTION PARAMETER SWEEP ---\n")
print(f"{'Thresh':>6} {'Drop':>5} | {'Caught':>6} | {'False':>5} | {'Avg Timing':>10} | Details")
print("-" * 80)

for thresh in thresholds:
    for drop in drops:
        all_signals = {}
        for coin, (top_date, top_price) in tops.items():
            if coin == 'BTC':
                continue  # Exclude BTC per Brett
            w2 = compute_2w_stochrsi(coin)
            if w2 is None:
                continue
            top_dt = pd.Timestamp(top_date)
            
            # Find deflections: K went above thresh, then dropped by 'drop' points from local peak
            # Only look at ETF era (2023+)
            etf_start = pd.Timestamp('2023-01-01')
            w2_etf = w2[w2.index >= etf_start]
            
            signals = []
            peak_k = 0
            armed = False
            
            for idx, row in w2_etf.iterrows():
                k_val = row['k']
                if pd.isna(k_val):
                    continue
                
                if k_val >= thresh:
                    armed = True
                    peak_k = max(peak_k, k_val)
                
                if armed and k_val <= peak_k - drop:
                    days_from_top = (idx - top_dt).days
                    pct_from_top = (row['close'] / top_price - 1) * 100
                    signals.append({
                        'date': idx,
                        'days': days_from_top,
                        'pct': pct_from_top,
                        'k': k_val,
                        'peak_k': peak_k,
                        'price': row['close']
                    })
                    # Reset after signal
                    armed = False
                    peak_k = 0
            
            all_signals[coin] = signals
        
        # Analyze: which signals are within -60 to +60 days of top?
        caught = 0
        false_pos = 0
        timings = []
        details = []
        
        for coin, signals in all_signals.items():
            top_date_str = tops[coin][0]
            top_dt = pd.Timestamp(top_date_str)
            
            # Find closest signal to top (within -60 to +60 days)
            best = None
            for s in signals:
                if -60 <= s['days'] <= 60:
                    if best is None or abs(s['days']) < abs(best['days']):
                        best = s
            
            if best:
                caught += 1
                timings.append(best['days'])
                details.append(f"{coin}:{best['days']:+d}d")
            
            # Count false positives (signals NOT near any top, >60d away)
            for s in signals:
                if abs(s['days']) > 60:
                    false_pos += 1
        
        total_signals = sum(len(s) for s in all_signals.values())
        avg_timing = f"{np.mean(timings):+.0f}d" if timings else "N/A"
        false_rate = f"{false_pos}/{total_signals}" if total_signals > 0 else "N/A"
        
        print(f"{thresh:>6} {drop:>5} | {caught:>4}/4 | {false_rate:>5} | {avg_timing:>10} | {', '.join(details)}")

# Best configs: show full signal list
print("\n\n--- DETAILED SIGNALS FOR PROMISING CONFIGS ---\n")
for thresh, drop in [(80, 10), (75, 10), (70, 10), (80, 15), (70, 15)]:
    print(f"\nThresh={thresh}, Drop={drop}:")
    print("-" * 60)
    for coin, (top_date, top_price) in tops.items():
        if coin == 'BTC':
            continue
        w2 = compute_2w_stochrsi(coin)
        if w2 is None:
            continue
        top_dt = pd.Timestamp(top_date)
        etf_start = pd.Timestamp('2023-01-01')
        w2_etf = w2[w2.index >= etf_start]
        
        peak_k = 0
        armed = False
        
        print(f"  {coin} (top {top_date}):")
        for idx, row in w2_etf.iterrows():
            k_val = row['k']
            if pd.isna(k_val):
                continue
            if k_val >= thresh:
                armed = True
                peak_k = max(peak_k, k_val)
            if armed and k_val <= peak_k - drop:
                days = (idx - top_dt).days
                pct = (row['close'] / top_price - 1) * 100
                label = "*** TOP ZONE ***" if -60 <= days <= 60 else ""
                print(f"    {idx.strftime('%Y-%m-%d')} ({days:+4d}d): K={k_val:.1f} (peak={peak_k:.1f}), ${row['close']:.2f} ({pct:+.1f}%) {label}")
                armed = False
                peak_k = 0
        print()
