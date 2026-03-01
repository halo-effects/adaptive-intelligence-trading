"""
V13 Gate Test: Weekly StochRSI as phase confirmation signal

Tests:
1. Weekly StochRSI OB exit (K crosses below 80) + daily structure break = MARKDOWN confirmation
2. Weekly StochRSI OS exit (K crosses above 20) + daily structure = MARKUP confirmation
3. Drop WITHOUT weekly OB = correction (stay in markup)
4. Composite signal quality: how many phases caught, how much of moves captured

Uses daily candles resampled to weekly, plus daily indicators for structure.
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DB_PATH = 'trading/spot/data/candles.db'

def stoch_rsi(close, rsi_period=14, stoch_period=14, k_smooth=3, d_smooth=3):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/rsi_period, min_periods=rsi_period).mean()
    avg_loss = loss.ewm(alpha=1/rsi_period, min_periods=rsi_period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi_low = rsi.rolling(stoch_period).min()
    rsi_high = rsi.rolling(stoch_period).max()
    stoch_k = 100 * (rsi - rsi_low) / (rsi_high - rsi_low + 1e-10)
    stoch_k = stoch_k.rolling(k_smooth).mean()
    stoch_d = stoch_k.rolling(d_smooth).mean()
    return stoch_k, stoch_d, rsi


def load_coin(coin):
    db = sqlite3.connect(DB_PATH)
    sym = [r[0] for r in db.execute(
        'SELECT DISTINCT symbol FROM candles_daily WHERE symbol LIKE ?', 
        (f'{coin}%',)).fetchall()]
    if not sym:
        return None, None, None
    
    daily = pd.read_sql(
        'SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp', 
        db, params=[sym[0]])
    daily['dt'] = pd.to_datetime(daily['timestamp'], unit='ms')
    daily.set_index('dt', inplace=True)
    
    # Build weekly
    wk_close = daily['close'].resample('W').last().dropna()
    wk_high = daily['high'].resample('W').max().dropna()
    wk_low = daily['low'].resample('W').min().dropna()
    
    k, d, rsi = stoch_rsi(wk_close)
    weekly = pd.DataFrame({
        'close': wk_close, 'high': wk_high, 'low': wk_low,
        'K': k, 'D': d, 'rsi': rsi
    })
    
    db.close()
    return daily, weekly, sym[0]


def find_weekly_signals(weekly):
    """Find OB exits and OS exits on weekly StochRSI"""
    signals = []
    prev_k = weekly['K'].shift(1)
    
    # OB exit: K was >80, now <=80
    ob_mask = (prev_k > 80) & (weekly['K'] <= 80)
    for dt in weekly[ob_mask].index:
        signals.append({'date': dt, 'type': 'OB_EXIT', 'K': weekly.loc[dt, 'K'], 
                        'D': weekly.loc[dt, 'D'], 'close': weekly.loc[dt, 'close']})
    
    # OS exit: K was <20, now >=20
    os_mask = (prev_k < 20) & (weekly['K'] >= 20)
    for dt in weekly[os_mask].index:
        signals.append({'date': dt, 'type': 'OS_EXIT', 'K': weekly.loc[dt, 'K'],
                        'D': weekly.loc[dt, 'D'], 'close': weekly.loc[dt, 'close']})
    
    return sorted(signals, key=lambda x: x['date'])


def check_daily_structure_at(daily, date, lookback=10):
    """Check daily structure around a date"""
    end = date + timedelta(days=3)  # small forward buffer
    start = date - timedelta(days=lookback)
    window = daily[(daily.index >= start) & (daily.index <= end)]
    
    if len(window) < 5:
        return {}
    
    last = window.iloc[-1]
    
    result = {
        'adx': last.get('adx', np.nan),
        'rsi14': last.get('rsi14', np.nan),
        'price_vs_sma50': last.get('price_vs_sma50', np.nan),
        'price_vs_sma200': last.get('price_vs_sma200', np.nan),
        'sma50_slope': last.get('sma50_slope', np.nan),
        'consec_lh_ll': last.get('consec_lh_ll', 0),
        'consec_hh_hl': last.get('consec_hh_hl', 0),
        'bb_width': last.get('bb_width', np.nan),
    }
    
    # Check if SMA50 crossed below SMA200 recently
    sma50 = window.get('sma50', pd.Series())
    sma200 = window.get('sma200', pd.Series())
    if len(sma50) > 1 and len(sma200) > 1:
        result['death_cross'] = (sma50.iloc[-1] < sma200.iloc[-1]) and (sma50.iloc[0] >= sma200.iloc[0])
        result['golden_cross'] = (sma50.iloc[-1] > sma200.iloc[-1]) and (sma50.iloc[0] <= sma200.iloc[0])
    
    return result


def measure_move_after(daily, signal_date, days=60):
    """Measure price move after a signal"""
    start = daily[daily.index >= signal_date]
    if len(start) < 2:
        return {}
    
    entry_price = start.iloc[0]['close']
    window = start.head(days)
    
    max_price = window['high'].max()
    min_price = window['low'].min()
    end_price = window.iloc[-1]['close']
    
    return {
        'entry': entry_price,
        'max_up': (max_price - entry_price) / entry_price * 100,
        'max_down': (min_price - entry_price) / entry_price * 100,
        'end_pct': (end_price - entry_price) / entry_price * 100,
        'end_price': end_price,
    }


def test_composite_gates():
    """
    Test: Weekly StochRSI signal + daily structure = phase confirmation
    
    MARKUP gate: Weekly StochRSI OS exit + daily price > SMA50 + SMA50 slope positive
    MARKDOWN gate: Weekly StochRSI OB exit + daily price < SMA50 OR daily structure break (LH/LL)
    CORRECTION filter: Drop >10% but weekly StochRSI NOT overbought = stay in markup
    """
    
    print("=" * 80)
    print("V13 COMPOSITE GATE TEST: Weekly StochRSI + Daily Structure")
    print("=" * 80)
    
    for coin in ['BTC', 'ETH', 'SOL']:
        daily, weekly, sym = load_coin(coin)
        if daily is None:
            continue
        
        daily = daily[daily.index >= '2024-09-01']
        weekly = weekly[weekly.index >= '2024-09-01']
        
        signals = find_weekly_signals(weekly)
        
        print(f"\n{'='*70}")
        print(f"  {coin} ({sym})")
        print(f"{'='*70}")
        
        # === TEST 1: OB exits as markdown signals ===
        print(f"\n--- MARKDOWN SIGNALS (Weekly StochRSI OB Exit) ---")
        ob_signals = [s for s in signals if s['type'] == 'OB_EXIT']
        
        for sig in ob_signals:
            ds = check_daily_structure_at(daily, sig['date'])
            move = measure_move_after(daily, sig['date'], days=60)
            
            # Daily confirmation checks
            below_sma50 = ds.get('price_vs_sma50', 0) < 0
            sma50_declining = ds.get('sma50_slope', 0) < 0
            has_lh_ll = ds.get('consec_lh_ll', 0) >= 2
            
            daily_confirms = below_sma50 or has_lh_ll
            
            print(f"\n  {sig['date'].date()}: K={sig['K']:.0f} D={sig['D']:.0f} close={sig['close']:.1f}")
            print(f"    Daily: ADX={ds.get('adx', 0):.1f}, RSI={ds.get('rsi14', 0):.1f}, "
                  f"vs_SMA50={ds.get('price_vs_sma50', 0):.1f}%, "
                  f"SMA50_slope={ds.get('sma50_slope', 0):.4f}, LH/LL={ds.get('consec_lh_ll', 0)}")
            print(f"    Daily confirms markdown: {daily_confirms} "
                  f"(below_sma50={below_sma50}, lh_ll={has_lh_ll})")
            if move:
                was_correct = move['max_down'] < -10  # At least 10% further drop
                print(f"    60d outcome: max_down={move['max_down']:.1f}%, max_up={move['max_up']:.1f}%, "
                      f"end={move['end_pct']:.1f}%")
                print(f"    Signal correct (>10% further drop): {'YES ✅' if was_correct else 'NO ❌'}")
        
        # === TEST 2: OS exits as markup signals ===
        print(f"\n--- MARKUP SIGNALS (Weekly StochRSI OS Exit) ---")
        os_signals = [s for s in signals if s['type'] == 'OS_EXIT']
        
        for sig in os_signals:
            ds = check_daily_structure_at(daily, sig['date'])
            move = measure_move_after(daily, sig['date'], days=90)
            
            above_sma50 = ds.get('price_vs_sma50', 0) > 0
            sma50_rising = ds.get('sma50_slope', 0) > 0
            has_hh_hl = ds.get('consec_hh_hl', 0) >= 2
            
            daily_confirms = above_sma50 or has_hh_hl
            
            print(f"\n  {sig['date'].date()}: K={sig['K']:.0f} D={sig['D']:.0f} close={sig['close']:.1f}")
            print(f"    Daily: ADX={ds.get('adx', 0):.1f}, RSI={ds.get('rsi14', 0):.1f}, "
                  f"vs_SMA50={ds.get('price_vs_sma50', 0):.1f}%, "
                  f"SMA50_slope={ds.get('sma50_slope', 0):.4f}, HH/HL={ds.get('consec_hh_hl', 0)}")
            print(f"    Daily confirms markup: {daily_confirms} "
                  f"(above_sma50={above_sma50}, hh_hl={has_hh_hl})")
            if move:
                was_correct = move['max_up'] > 15  # At least 15% upside
                print(f"    90d outcome: max_up={move['max_up']:.1f}%, max_down={move['max_down']:.1f}%, "
                      f"end={move['end_pct']:.1f}%")
                print(f"    Signal correct (>15% upside): {'YES ✅' if was_correct else 'NO ❌'}")
        
        # === TEST 3: Correction filter — drops without OB ===
        print(f"\n--- CORRECTION FILTER (>10% drops WITHOUT weekly OB) ---")
        
        # Find drops
        daily['rh14'] = daily['high'].rolling(14).max()
        daily['dd'] = (daily['close'] - daily['rh14']) / daily['rh14'] * 100
        
        drop_starts = []
        in_drop = False
        for dt, row in daily.iterrows():
            if row['dd'] < -10 and not in_drop:
                drop_starts.append(dt)
                in_drop = True
            elif row['dd'] > -5:
                in_drop = False
        
        for ds_date in drop_starts:
            # Was weekly StochRSI OB in prior 4 weeks?
            four_weeks_ago = ds_date - timedelta(weeks=4)
            recent_wk = weekly[(weekly.index >= four_weeks_ago) & (weekly.index <= ds_date)]
            was_ob = (recent_wk['K'] > 80).any() if len(recent_wk) > 0 else False
            
            if not was_ob:
                # This is a correction — should we have stayed in markup?
                move = measure_move_after(daily, ds_date, days=30)
                if move:
                    recovered = move['max_up'] > 5  # Bounced >5% from drop
                    close_val = daily.loc[ds_date, 'close']
                    dd_val = daily.loc[ds_date, 'dd']
                    
                    # Get weekly StochRSI at this point
                    nearest_wk = weekly[weekly.index <= ds_date].tail(1)
                    wk_k = nearest_wk['K'].values[0] if len(nearest_wk) > 0 else np.nan
                    
                    print(f"  {ds_date.date()}: close={close_val:.1f}, DD={dd_val:.1f}%, "
                          f"wk_K={wk_k:.0f} (not OB)")
                    print(f"    30d after: max_up={move['max_up']:.1f}%, end={move['end_pct']:.1f}% | "
                          f"Recovered >5%: {'YES ✅ (correction)' if recovered else 'NO ❌ (real markdown)'}")


def test_timing_quality():
    """How early/late are the weekly StochRSI signals vs actual tops/bottoms?"""
    
    print("\n\n" + "=" * 80)
    print("TIMING ANALYSIS: How early/late are weekly StochRSI signals?")
    print("=" * 80)
    
    for coin in ['BTC', 'ETH', 'SOL']:
        daily, weekly, sym = load_coin(coin)
        if daily is None:
            continue
        
        daily = daily[daily.index >= '2024-09-01']
        weekly = weekly[weekly.index >= '2024-09-01']
        
        signals = find_weekly_signals(weekly)
        
        print(f"\n--- {coin} ---")
        
        for sig in signals:
            sig_date = sig['date']
            
            if sig['type'] == 'OB_EXIT':
                # Find the actual top (highest close) in 30 days before signal
                window = daily[(daily.index >= sig_date - timedelta(days=45)) & 
                              (daily.index <= sig_date)]
                if len(window) > 0:
                    top_date = window['high'].idxmax()
                    top_price = window['high'].max()
                    sig_price = sig['close']
                    lag_days = (sig_date - top_date).days
                    missed_pct = (top_price - sig_price) / top_price * 100
                    print(f"  OB_EXIT {sig_date.date()}: actual top={top_date.date()} "
                          f"({lag_days}d lag, missed {missed_pct:.1f}% from top)")
            
            elif sig['type'] == 'OS_EXIT':
                # Find the actual bottom in 30 days before signal
                window = daily[(daily.index >= sig_date - timedelta(days=45)) & 
                              (daily.index <= sig_date)]
                if len(window) > 0:
                    bot_date = window['low'].idxmin()
                    bot_price = window['low'].min()
                    sig_price = sig['close']
                    lag_days = (sig_date - bot_date).days
                    missed_pct = (sig_price - bot_price) / bot_price * 100
                    print(f"  OS_EXIT {sig_date.date()}: actual bottom={bot_date.date()} "
                          f"({lag_days}d lag, missed {missed_pct:.1f}% from bottom)")


if __name__ == '__main__':
    test_composite_gates()
    test_timing_quality()
