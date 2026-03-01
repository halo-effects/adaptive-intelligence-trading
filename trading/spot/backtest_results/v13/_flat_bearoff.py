"""
Win #1: Bear-OFF fast exit for post-top FLAT windows.
If Weekly CFGI RSI(7) < 40 fires during a post-top FLAT, go to DCA immediately
instead of waiting for the 42-day timeout.
"""
import sys, datetime as dt, numpy as np, pandas as pd
sys.path.insert(0, r'C:\Users\Never\.openclaw\workspace')
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'
COINS = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']
START = dt.date(2023, 1, 1)
END = dt.date(2026, 2, 27)


def calc_weekly_cfgi_rsi7_series(pack):
    """Pre-calculate entire Weekly CFGI RSI(7) series for a coin."""
    cfgi_df = pack.cfgi.cfgi
    if cfgi_df is None or cfgi_df.empty:
        return pd.Series(dtype=float)
    
    daily = cfgi_df['value'].copy()
    daily.index = pd.to_datetime(daily.index)
    
    # Resample to weekly (Friday close)
    weekly = daily.resample('W-FRI').last().dropna()
    if len(weekly) < 8:
        return pd.Series(dtype=float)
    
    # Wilder's RSI(7)
    delta = weekly.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    
    # Use EWM (Wilder's smoothing = span=2*period-1)
    avg_gain = gain.ewm(span=13, adjust=False).mean()
    avg_loss = loss.ewm(span=13, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def run_with_bearoff(coin, threshold=40):
    """Run V13 with bear-OFF fast exit patched in."""
    pack = V13SignalPack(coin, DB)
    cfg = V13Config()
    cfg.START_DATE = START
    cfg.END_DATE = END
    cfg.CAPITAL = 2500
    
    # Pre-calculate weekly CFGI RSI(7)
    rsi_series = calc_weekly_cfgi_rsi7_series(pack)
    
    eng = V13BacktestV8(pack, cfg)
    
    # Save original _check_flat
    orig_check_flat = eng._check_flat
    
    def patched_check_flat(date, price):
        """Inject bear-OFF check before the 42d timeout."""
        if eng.flat_from_top:
            days_flat = (date - eng.phase_start_date).days if eng.phase_start_date else 0
            if days_flat >= eng.cfg.FLAT_MIN_EVAL_DAYS:
                # Check Weekly CFGI RSI(7) < threshold
                ts = pd.Timestamp(date)
                # Find most recent RSI value on or before this date
                mask = rsi_series.index <= ts
                if mask.any():
                    val = rsi_series[mask].iloc[-1]
                    if not np.isnan(val) and val < threshold:
                        eng._change_phase(date, Phase.DCA,
                            f'FLAT->DCA: Bear-OFF (CFGI RSI7w={val:.0f}<{threshold}, flat {days_flat}d)')
                        return
        orig_check_flat(date, price)
    
    eng._check_flat = patched_check_flat
    eng.run()
    return eng


def run_baseline(coin):
    pack = V13SignalPack(coin, DB)
    cfg = V13Config()
    cfg.START_DATE = START
    cfg.END_DATE = END
    cfg.CAPITAL = 2500
    eng = V13BacktestV8(pack, cfg)
    eng.run()
    return eng


def flat_stats(eng):
    """Extract FLAT window stats from engine."""
    total_flat = 0
    windows = []
    log = eng.phase_log
    for i, p in enumerate(log):
        if p.get('to') == 'FLAT':
            enter_date = p['date']
            if i + 1 < len(log):
                exit_p = log[i + 1]
                exit_date = exit_p['date']
                days = (exit_date - enter_date).days
                total_flat += days
                windows.append({
                    'enter': str(enter_date.date()) if hasattr(enter_date, 'date') else str(enter_date),
                    'days': days,
                    'to': exit_p.get('to', '?'),
                    'reason': exit_p.get('reason', '')
                })
    equity = eng.equity_curve[-1]['equity'] if eng.equity_curve else 2500
    return total_flat, equity, windows


def main():
    print("=" * 90)
    print("FLAT BEAR-OFF FAST EXIT TEST")
    print("If post-top FLAT sees Weekly CFGI RSI(7) < threshold -> skip to DCA immediately")
    print("ETF Era: Jan 2023 - Feb 2026")
    print("=" * 90)
    
    for threshold in [40, 35, 45, 30]:
        print(f"\n{'='*90}")
        print(f"THRESHOLD: Weekly CFGI RSI(7) < {threshold}")
        print(f"{'='*90}")
        
        total_base_flat = 0
        total_base_eq = 0
        total_bo_flat = 0
        total_bo_eq = 0
        
        for coin in COINS:
            try:
                base_eng = run_baseline(coin)
                bo_eng = run_with_bearoff(coin, threshold)
                
                bf, be, bw = flat_stats(base_eng)
                of, oe, ow = flat_stats(bo_eng)
                
                total_base_flat += bf
                total_base_eq += be
                total_bo_flat += of
                total_bo_eq += oe
                
                saved = bf - of
                delta_eq = oe - be
                
                print(f"\n  {coin}: {bf}d -> {of}d (saved {saved:+d}d), ${be:,.0f} -> ${oe:,.0f} ({delta_eq:+,.0f})")
                
                # Show changed windows
                for w in ow:
                    if 'Bear-OFF' in w['reason']:
                        print(f"    NEW: {w['enter']}: {w['days']}d -> {w['to']} | {w['reason'][:70]}")
                
            except Exception as e:
                print(f"  {coin}: ERROR {e}")
        
        saved_total = total_base_flat - total_bo_flat
        delta_total = total_bo_eq - total_base_eq
        print(f"\n  PORTFOLIO: {total_base_flat}d -> {total_bo_flat}d (saved {saved_total}d)")
        print(f"  EQUITY: ${total_base_eq:,.0f} -> ${total_bo_eq:,.0f} ({delta_total:+,.0f})")


if __name__ == '__main__':
    main()
