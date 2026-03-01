"""Test Top+Bottom bias system.

TOP (bear trigger) = Engine's own top signals:
  - 2W StochRSI > 93 (primary)
  - 1W StochRSI > 85 (fallback)
  - 1W StochRSI K < 50 (failsafe)

BOTTOM (bull trigger) = Steve Courtney style on 3D candles:
  - Price below 3D SMA200
  - 3D RSI < 26
  - 3D StochRSI K < 20 AND D < 20

Bias state machine:
  START -> NEUTRAL (both directions allowed)
  TOP fires -> BEAR (block markups, allow shorts)
  BOTTOM fires -> BULL (block shorts... actually no, allow markups, block nothing?)
  
Actually simpler: 
  BEAR bias: active after top signal, cleared by bottom signal
  Default: no bias (everything allowed)
  
So BEAR only activates between TOP and BOTTOM. This means:
  - During bull runs: no bias (top hasn't fired) -> all markups allowed
  - After top: bear bias -> markups blocked until bottom confirmed
  - After bottom: bias cleared -> markups allowed again
  
This avoids the golden cross lag problem because the bottom signal fires
at the ACTUAL bottom (extreme oversold), not after a lagging MA cross.
"""
from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack
from build_3d_signals import build_3d_signals
from run_new_coins_profiles import make_config
import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'candles.db'


def compute_3d_stochrsi(df_3d, rsi_period=14, stoch_period=14, smooth_k=3, smooth_d=3):
    """Compute StochRSI on 3D candles."""
    # RSI
    delta = df_3d['close'].diff()
    gain = delta.where(delta > 0, 0.0).ewm(alpha=1/rsi_period, min_periods=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/rsi_period, min_periods=rsi_period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    
    # StochRSI
    rsi_min = rsi.rolling(stoch_period).min()
    rsi_max = rsi.rolling(stoch_period).max()
    stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan) * 100
    
    k = stoch_rsi.rolling(smooth_k).mean()
    d = k.rolling(smooth_d).mean()
    
    return rsi, k, d


def find_top_signals(pack):
    """Extract top signal dates from the signal pack (engine's own detection)."""
    # We need to find when 2W StochRSI > 93 or 1W OB85 fires
    # These are stored in the weekly indicators
    tops = []
    
    # Get weekly stochrsi data
    if hasattr(pack, 'weekly_stoch'):
        ws = pack.weekly_stoch
    else:
        # Load from DB directly
        conn = sqlite3.connect(DB_PATH)
        # Check what tables exist for weekly data
        tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
    
    # Actually, let's just use the phase log from a backtest run
    # The engine itself detects tops — we can extract them from phase transitions
    return tops


def build_bias_timeline(coin, pack, cfg):
    """Build a timeline of bias states using engine top signals + 3D bottom signals."""
    # Run backtest to get top signal dates from phase log
    bt = V13BacktestV8(pack, cfg)
    r = bt.run()
    
    # Extract TOP dates (when engine exits markup due to top signal)
    top_dates = []
    for t in bt.phase_log:
        reason = t.get('reason', '')
        to_phase = str(t.get('to', ''))
        if to_phase == 'FLAT' and ('OB' in reason or 'failsafe' in reason.lower()):
            top_dates.append(t['date'])
    
    # Build 3D bottom signals
    df_3d = build_3d_signals(coin)
    rsi, stoch_k, stoch_d = compute_3d_stochrsi(df_3d)
    df_3d['rsi'] = rsi  # overwrites the simple one
    df_3d['stoch_k'] = stoch_k
    df_3d['stoch_d'] = stoch_d
    
    # Find bottom signals: price < SMA200 AND RSI < 26 AND StochRSI K < 20 AND D < 20
    bottom_mask = (
        (df_3d['close'] < df_3d['sma200']) &
        (df_3d['rsi'] < 26) &
        (df_3d['stoch_k'] < 20) &
        (df_3d['stoch_d'] < 20)
    )
    bottom_dates = df_3d[bottom_mask].index.tolist()
    
    # Also try relaxed bottom: RSI < 30 AND StochRSI K < 25
    bottom_relaxed = (
        (df_3d['close'] < df_3d['sma200']) &
        (df_3d['rsi'] < 30) &
        (df_3d['stoch_k'] < 25) &
        (df_3d['stoch_d'] < 25)
    )
    bottom_dates_relaxed = df_3d[bottom_relaxed].index.tolist()
    
    return bt, r, top_dates, bottom_dates, bottom_dates_relaxed, df_3d


def get_bias(date, top_dates, bottom_dates):
    """Get bias at date. BEAR after top until bottom clears it."""
    ts = pd.Timestamp(date)
    bias = 'neutral'
    
    # Walk through events chronologically
    events = [(d, 'top') for d in top_dates] + [(d, 'bottom') for d in bottom_dates]
    events.sort(key=lambda x: x[0])
    
    for event_date, event_type in events:
        if pd.Timestamp(event_date) > ts:
            break
        if event_type == 'top':
            bias = 'bear'
        elif event_type == 'bottom':
            bias = 'neutral'  # Clear bear bias
    
    return bias


def analyze(coin, profile='high'):
    pack = V13SignalPack(coin)
    cfg = make_config(profile)
    
    bt, r, top_dates, bottom_dates, bottom_relaxed, df_3d = build_bias_timeline(coin, pack, cfg)
    
    print(f"\n{'='*70}")
    print(f"{coin} ({profile}) -- ROI: {r['roi']:+.1f}%, B&H: {r['buy_hold_return']:+.0f}%")
    print(f"{'='*70}")
    
    print(f"\n  Top signals (engine): {len(top_dates)}")
    for d in top_dates:
        print(f"    {str(d)[:10]}")
    
    print(f"\n  Bottom signals (strict RSI<26 + StochRSI<20): {len(bottom_dates)}")
    for d in bottom_dates:
        rsi_val = df_3d.loc[d, 'rsi'] if d in df_3d.index else '?'
        sk = df_3d.loc[d, 'stoch_k'] if d in df_3d.index else '?'
        price = df_3d.loc[d, 'close'] if d in df_3d.index else '?'
        sma = df_3d.loc[d, 'sma200'] if d in df_3d.index else '?'
        print(f"    {str(d)[:10]}: RSI={rsi_val:.1f}, StochK={sk:.1f}, price=${price:,.0f}, SMA200=${sma:,.0f}")
    
    print(f"\n  Bottom signals (relaxed RSI<30 + StochRSI<25): {len(bottom_relaxed)}")
    for d in bottom_relaxed[:10]:  # limit output
        rsi_val = df_3d.loc[d, 'rsi'] if d in df_3d.index else '?'
        print(f"    {str(d)[:10]}: RSI={rsi_val:.1f}")
    if len(bottom_relaxed) > 10:
        print(f"    ... and {len(bottom_relaxed)-10} more")
    
    # Test with strict bottom signals
    for label, bdates in [("STRICT (RSI<26)", bottom_dates), ("RELAXED (RSI<30)", bottom_relaxed)]:
        print(f"\n  --- {label} ---")
        
        blocked_good = []
        blocked_bad = []
        
        for i, t in enumerate(bt.phase_log):
            date = t.get('date')
            to_phase = str(t.get('to', ''))
            equity = t.get('equity', 0)
            
            if not date or to_phase not in ('MARKUP', 'MARKDOWN'):
                continue
            
            bias = get_bias(date, top_dates, bdates)
            
            # Get trade PnL
            next_eq = None
            for j in range(i+1, len(bt.phase_log)):
                if bt.phase_log[j].get('to') != to_phase:
                    next_eq = bt.phase_log[j].get('equity', equity)
                    break
            if next_eq is None:
                next_eq = r['final_equity']
            pnl = next_eq - equity
            good = pnl > 0
            
            # Bear bias blocks MARKUP only
            would_block = (bias == 'bear' and to_phase == 'MARKUP')
            
            if to_phase == 'MARKUP':
                marker = " ** BLOCKED" if would_block else ""
                quality = "GOOD" if good else "BAD"
                print(f"    MARKUP  {str(date)[:10]}: bias={bias:>7}, pnl={pnl:>+8.0f} [{quality}]{marker}")
            
            if would_block:
                if good:
                    blocked_good.append((date, pnl))
                else:
                    blocked_bad.append((date, pnl))
        
        saved = sum(p for _,p in blocked_bad)
        missed = sum(p for _,p in blocked_good)
        net = abs(saved) - missed
        label2 = "HELPS" if net > 0 else "HURTS"
        print(f"\n    Blocked bad:  {len(blocked_bad)} trades, ${saved:>+9.0f} saved")
        print(f"    Blocked good: {len(blocked_good)} trades, ${missed:>+9.0f} missed")
        print(f"    Net: ${net:>+9.0f} ({label2})")


if __name__ == '__main__':
    print("TOP+BOTTOM BIAS SYSTEM TEST")
    print("Bear bias activates on engine top signal, clears on 3D bottom signal.")
    print("Only blocks MARKUP during bear bias. Everything else allowed.")
    
    for coin in ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']:
        analyze(coin, 'high')
