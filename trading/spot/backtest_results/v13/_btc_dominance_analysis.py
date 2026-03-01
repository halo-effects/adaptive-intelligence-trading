"""BTC Dominance + CFGI Combo Signal Analysis

Tests the hypothesis: falling BTC dominance + rising alt CFGI = bullish for alts.

Signal: BTC.D ROC30 < -3% AND coin CFGI trending up (current > 30-day-ago)
"""

import sqlite3
import statistics
from collections import defaultdict
from datetime import datetime, timedelta

DB_PATH = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'
COINS = {
    'HBAR': {'candle': 'HBAR/USDT', 'cfgi': None},  # No CFGI data
    'ATOM': {'candle': 'ATOM/USDT', 'cfgi': 'ATOM'},
    'LINK': {'candle': 'LINK/USDT', 'cfgi': 'LINK'},
    'NEAR': {'candle': 'NEAR/USDT', 'cfgi': 'NEAR'},
}
FORWARD_WINDOWS = [7, 14, 30]
BTC_D_ROC_THRESHOLD = -3.0  # dominance falling >3% over 30 days


def load_data(conn):
    """Load all needed data from DB."""
    # BTC dominance
    btc_d = {}
    for row in conn.execute('SELECT date, dominance_pct, dominance_sma30, dominance_roc30 FROM btc_dominance ORDER BY date'):
        btc_d[row[0]] = {'dom': row[1], 'sma30': row[2], 'roc30': row[3]}
    
    # CFGI data
    cfgi = defaultdict(dict)
    for row in conn.execute('SELECT symbol, date, cfgi FROM cfgi_daily ORDER BY date'):
        cfgi[row[0]][row[1]] = row[2]
    
    # Coin prices (daily close)
    prices = defaultdict(dict)
    for coin, info in COINS.items():
        for row in conn.execute('SELECT date, close FROM candles_daily WHERE symbol = ? ORDER BY date', (info['candle'],)):
            prices[coin][row[0]] = row[1]
    
    return btc_d, cfgi, prices


def forward_return(prices_dict, date_str, days):
    """Calculate forward return from date over N days."""
    dates = sorted(prices_dict.keys())
    try:
        idx = dates.index(date_str)
    except ValueError:
        return None
    target_idx = idx + days
    if target_idx >= len(dates):
        return None
    start_price = prices_dict[dates[idx]]
    end_price = prices_dict[dates[target_idx]]
    if start_price <= 0:
        return None
    return ((end_price - start_price) / start_price) * 100


def analyze():
    conn = sqlite3.connect(DB_PATH)
    btc_d, cfgi, prices = load_data(conn)
    conn.close()
    
    print("=" * 80)
    print("BTC DOMINANCE + CFGI COMBO SIGNAL ANALYSIS")
    print("=" * 80)
    print(f"\nBTC.D data: {min(btc_d.keys())} to {max(btc_d.keys())} ({len(btc_d)} days)")
    
    # Show BTC.D trend summary
    dom_values = [v['dom'] for v in btc_d.values() if v['dom']]
    print(f"BTC.D range: {min(dom_values):.1f}% - {max(dom_values):.1f}% (avg {statistics.mean(dom_values):.1f}%)")
    
    roc_values = [v['roc30'] for v in btc_d.values() if v['roc30'] is not None]
    print(f"BTC.D ROC30 range: {min(roc_values):.2f}% to {max(roc_values):.2f}%")
    falling_days = sum(1 for r in roc_values if r < BTC_D_ROC_THRESHOLD)
    print(f"Days with ROC30 < {BTC_D_ROC_THRESHOLD}%: {falling_days}/{len(roc_values)}")
    
    # Per-coin analysis
    for coin, info in COINS.items():
        print(f"\n{'='*80}")
        print(f"  {coin}")
        print(f"{'='*80}")
        
        cfgi_sym = info['cfgi']
        if not cfgi_sym:
            print(f"  No CFGI data available for {coin} - skipping combo signal")
            print(f"  Price data: {len(prices[coin])} days")
            # Still show BTC.D-only correlation
            _analyze_btc_d_only(coin, btc_d, prices)
            continue
        
        coin_cfgi = cfgi.get(cfgi_sym, {})
        coin_prices = prices[coin]
        
        if not coin_prices:
            print(f"  No price data for {coin}")
            continue
        
        price_dates = sorted(coin_prices.keys())
        print(f"  Price data: {price_dates[0]} to {price_dates[-1]} ({len(price_dates)} days)")
        print(f"  CFGI data: {len(coin_cfgi)} days")
        
        # Find signal dates: BTC.D falling + CFGI rising
        signal_dates = []
        no_signal_dates = []
        
        for date in price_dates:
            if date not in btc_d or btc_d[date]['roc30'] is None:
                continue
            
            roc30 = btc_d[date]['roc30']
            
            # Check CFGI trend: current > 30 days ago
            cfgi_now = coin_cfgi.get(date)
            # Find CFGI ~30 days ago
            dt = datetime.strptime(date, '%Y-%m-%d')
            dt_30ago = (dt - timedelta(days=30)).strftime('%Y-%m-%d')
            cfgi_30ago = coin_cfgi.get(dt_30ago)
            
            btc_d_falling = roc30 < BTC_D_ROC_THRESHOLD
            cfgi_rising = cfgi_now is not None and cfgi_30ago is not None and cfgi_now > cfgi_30ago
            
            if btc_d_falling and cfgi_rising:
                signal_dates.append(date)
            else:
                no_signal_dates.append(date)
        
        print(f"\n  COMBO signal (BTC.D ROC30 < {BTC_D_ROC_THRESHOLD}% AND CFGI rising): {len(signal_dates)} days")
        print(f"  No signal: {len(no_signal_dates)} days")
        
        if signal_dates:
            print(f"\n  Signal date samples: {signal_dates[:5]}")
        
        # Calculate forward returns for signal vs no-signal
        print(f"\n  {'Window':>8} | {'Signal Avg':>12} | {'Signal Med':>12} | {'No-Sig Avg':>12} | {'No-Sig Med':>12} | {'Edge':>8} | {'Win%':>6}")
        print(f"  {'-'*8} | {'-'*12} | {'-'*12} | {'-'*12} | {'-'*12} | {'-'*8} | {'-'*6}")
        
        for window in FORWARD_WINDOWS:
            sig_returns = []
            for d in signal_dates:
                r = forward_return(coin_prices, d, window)
                if r is not None:
                    sig_returns.append(r)
            
            nosig_returns = []
            # Sample no-signal dates (take every 3rd to keep it manageable)
            for d in no_signal_dates[::3]:
                r = forward_return(coin_prices, d, window)
                if r is not None:
                    nosig_returns.append(r)
            
            if sig_returns and nosig_returns:
                sig_avg = statistics.mean(sig_returns)
                sig_med = statistics.median(sig_returns)
                nosig_avg = statistics.mean(nosig_returns)
                nosig_med = statistics.median(nosig_returns)
                edge = sig_avg - nosig_avg
                win_pct = sum(1 for r in sig_returns if r > 0) / len(sig_returns) * 100
                print(f"  {window:>6}d | {sig_avg:>+11.2f}% | {sig_med:>+11.2f}% | {nosig_avg:>+11.2f}% | {nosig_med:>+11.2f}% | {edge:>+7.2f}% | {win_pct:>5.1f}%")
            else:
                n_sig = len(sig_returns)
                n_nosig = len(nosig_returns)
                print(f"  {window:>6}d | insufficient data (sig={n_sig}, nosig={n_nosig})")
        
        # Also show BTC.D-only signal for comparison
        _analyze_btc_d_only(coin, btc_d, prices)


def _analyze_btc_d_only(coin, btc_d, prices):
    """Analyze using only BTC.D falling as signal (no CFGI)."""
    coin_prices = prices[coin]
    if not coin_prices:
        return
    
    price_dates = sorted(coin_prices.keys())
    
    sig_dates = []
    nosig_dates = []
    for date in price_dates:
        if date not in btc_d or btc_d[date]['roc30'] is None:
            continue
        if btc_d[date]['roc30'] < BTC_D_ROC_THRESHOLD:
            sig_dates.append(date)
        else:
            nosig_dates.append(date)
    
    print(f"\n  BTC.D-only signal (ROC30 < {BTC_D_ROC_THRESHOLD}%): {len(sig_dates)} days")
    
    if not sig_dates:
        print("  No signal dates found")
        return
    
    print(f"\n  {'Window':>8} | {'Falling Avg':>12} | {'Falling Med':>12} | {'Other Avg':>12} | {'Other Med':>12} | {'Edge':>8} | {'Win%':>6}")
    print(f"  {'-'*8} | {'-'*12} | {'-'*12} | {'-'*12} | {'-'*12} | {'-'*8} | {'-'*6}")
    
    for window in FORWARD_WINDOWS:
        sig_r = [r for d in sig_dates if (r := forward_return(coin_prices, d, window)) is not None]
        nos_r = [r for d in nosig_dates[::3] if (r := forward_return(coin_prices, d, window)) is not None]
        
        if sig_r and nos_r:
            sa, sm = statistics.mean(sig_r), statistics.median(sig_r)
            na, nm = statistics.mean(nos_r), statistics.median(nos_r)
            edge = sa - na
            wp = sum(1 for r in sig_r if r > 0) / len(sig_r) * 100
            print(f"  {window:>6}d | {sa:>+11.2f}% | {sm:>+11.2f}% | {na:>+11.2f}% | {nm:>+11.2f}% | {edge:>+7.2f}% | {wp:>5.1f}%")
        else:
            print(f"  {window:>6}d | insufficient data")


if __name__ == '__main__':
    analyze()
