"""
Quick wins for FLAT dwell time reduction.
Win #1: Bear-OFF fast exit (Weekly CFGI RSI(7) < 40 clears post-top to DCA)
Win #2: Reduce ADX sustained days from 14 → 7
Win #3: Both combined
"""
import sys, datetime as dt, numpy as np, copy
sys.path.insert(0, r'C:\Users\Never\.openclaw\workspace')
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'
COINS = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']
START = dt.date(2023, 1, 1)
END = dt.date(2026, 2, 27)

def run_variant(label, cfg_mods=None, engine_mods=None):
    """Run all coins with given config modifications, return stats."""
    results = {}
    for coin in COINS:
        try:
            pack = V13SignalPack(coin, DB)
            cfg = V13Config()
            cfg.START_DATE = START
            cfg.END_DATE = END
            cfg.CAPITAL = 2500
            if cfg_mods:
                for k, v in cfg_mods.items():
                    setattr(cfg, k, v)
            eng = V13BacktestV8(pack, cfg)
            
            # Apply engine-level mods (monkey-patch for bear-OFF)
            if engine_mods and 'bear_off_fast_exit' in engine_mods:
                _patch_bear_off(eng, pack)
            
            eng.run()
            
            # Collect FLAT stats
            total_flat = 0
            flat_windows = []
            log = eng.phase_log
            for i, p in enumerate(log):
                if p.get('to') == 'FLAT':
                    enter_date = p['date']
                    if i + 1 < len(log):
                        exit_p = log[i + 1]
                        exit_date = exit_p['date']
                        days = (exit_date - enter_date).days
                        total_flat += days
                        flat_windows.append({
                            'enter': enter_date,
                            'days': days,
                            'to': exit_p.get('to', '?'),
                            'reason': exit_p.get('reason', '')
                        })
            
            # Get final equity
            equity = eng.equity_curve[-1]['equity'] if eng.equity_curve else 2500
            roi = (equity - 2500) / 2500 * 100
            
            total_days = (END - START).days
            results[coin] = {
                'flat_days': total_flat,
                'flat_pct': total_flat / total_days * 100,
                'windows': len(flat_windows),
                'equity': equity,
                'roi': roi,
                'flat_windows': flat_windows
            }
        except Exception as e:
            print(f"  {coin}: ERROR {e}")
            import traceback; traceback.print_exc()
    return results


def _patch_bear_off(eng, pack):
    """Monkey-patch _check_flat to add bear-OFF fast exit for post-top windows."""
    original_check_flat = eng._check_flat
    
    def patched_check_flat(date, price):
        # If post-top and bear-OFF signal fires, go to DCA immediately
        if eng.flat_from_top:
            days_flat = (date - eng.phase_start_date).days if eng.phase_start_date else 0
            if days_flat >= eng.cfg.FLAT_MIN_EVAL_DAYS:
                # Check Weekly CFGI RSI(7) < 40
                cfgi_rsi = pack.cfgi.weekly_rsi7_at(date) if hasattr(pack.cfgi, 'weekly_rsi7_at') else None
                if cfgi_rsi is None:
                    # Manual calculation: get CFGI values, resample to weekly, RSI(7)
                    cfgi_rsi = _calc_weekly_cfgi_rsi7(pack, date)
                if cfgi_rsi is not None and not np.isnan(cfgi_rsi) and cfgi_rsi < 40:
                    eng._change_phase(date, Phase.DCA,
                        f'FLAT->DCA: Bear-OFF (Weekly CFGI RSI7={cfgi_rsi:.0f}<40, flat {days_flat}d)')
                    return
        original_check_flat(date, price)
    
    eng._check_flat = patched_check_flat


def _calc_weekly_cfgi_rsi7(pack, date):
    """Calculate Weekly CFGI RSI(7) at a given date."""
    try:
        # Get CFGI series from pack
        cfgi_series = pack.cfgi.daily_series if hasattr(pack.cfgi, 'daily_series') else None
        if cfgi_series is None:
            return None
        
        # Filter up to date
        import pandas as pd
        mask = cfgi_series.index <= pd.Timestamp(date)
        s = cfgi_series[mask]
        if len(s) < 14:  # Need enough data for weekly resample + RSI(7)
            return None
        
        # Resample to weekly (Friday close)
        weekly = s.resample('W-FRI').last().dropna()
        if len(weekly) < 8:
            return None
        
        # RSI(7) on weekly CFGI
        delta = weekly.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.rolling(7).mean()
        avg_loss = loss.rolling(7).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1] if not rsi.empty else None
    except:
        return None


# --- Alternative approach: just modify the engine config and re-run ---
# Since monkey-patching is fragile, let's also test by modifying the source
# For now, let's take a simpler approach: measure what WOULD have happened

def analyze_savings():
    """Analyze how many days each win saves without modifying engine."""
    import pandas as pd
    import sqlite3
    
    print("=" * 80)
    print("FLAT DWELL TIME QUICK WINS ANALYSIS")
    print("ETF Era: Jan 2023 → Feb 2026")
    print("=" * 80)
    
    # First run baseline
    print("\n--- BASELINE ---")
    baseline = run_variant("Baseline")
    
    total_baseline_flat = 0
    total_baseline_equity = 0
    for coin in COINS:
        if coin in baseline:
            r = baseline[coin]
            total_baseline_flat += r['flat_days']
            total_baseline_equity += r['equity']
            print(f"  {coin}: {r['flat_days']:3d}d flat ({r['flat_pct']:.0f}%), equity ${r['equity']:,.0f} (+{r['roi']:.1f}%)")
    print(f"  TOTAL: {total_baseline_flat}d flat, ${total_baseline_equity:,.0f} equity")
    
    # Win #2: Reduce ADX sustained days 14 → 7
    print("\n--- WIN #2: ADX sustained 14d → 7d ---")
    win2 = run_variant("ADX 7d", cfg_mods={'FLAT_ADX_SUSTAINED_DAYS': 7, 'PHASE_ADX_SUSTAINED_DAYS': 7})
    
    total_win2_flat = 0
    total_win2_equity = 0
    for coin in COINS:
        if coin in win2:
            r = win2[coin]
            b = baseline[coin]
            total_win2_flat += r['flat_days']
            total_win2_equity += r['equity']
            saved = b['flat_days'] - r['flat_days']
            delta_eq = r['equity'] - b['equity']
            print(f"  {coin}: {r['flat_days']:3d}d flat (saved {saved:+d}d), equity ${r['equity']:,.0f} ({delta_eq:+,.0f})")
    saved2 = total_baseline_flat - total_win2_flat
    delta2 = total_win2_equity - total_baseline_equity
    print(f"  TOTAL: {total_win2_flat}d flat (saved {saved2}d), ${total_win2_equity:,.0f} ({delta2:+,.0f})")
    
    # Now let's also check what happens with the FLAT timeout reduced
    for timeout in [28, 21, 14]:
        print(f"\n--- ALT: FLAT timeout 42d → {timeout}d ---")
        alt = run_variant(f"Timeout {timeout}d", cfg_mods={'FLAT_MAX_EVAL_DAYS': timeout})
        
        total_alt_flat = 0
        total_alt_equity = 0
        for coin in COINS:
            if coin in alt:
                r = alt[coin]
                b = baseline[coin]
                total_alt_flat += r['flat_days']
                total_alt_equity += r['equity']
                saved = b['flat_days'] - r['flat_days']
                delta_eq = r['equity'] - b['equity']
                print(f"  {coin}: {r['flat_days']:3d}d flat (saved {saved:+d}d), equity ${r['equity']:,.0f} ({delta_eq:+,.0f})")
        saved_alt = total_baseline_flat - total_alt_flat
        delta_alt = total_alt_equity - total_baseline_equity
        print(f"  TOTAL: {total_alt_flat}d flat (saved {saved_alt}d), ${total_alt_equity:,.0f} ({delta_alt:+,.0f})")
    
    # Combined: ADX 7d + timeout 21d
    print(f"\n--- COMBINED: ADX 7d + Timeout 21d ---")
    combo = run_variant("Combo", cfg_mods={'FLAT_ADX_SUSTAINED_DAYS': 7, 'PHASE_ADX_SUSTAINED_DAYS': 7, 'FLAT_MAX_EVAL_DAYS': 21})
    
    total_combo_flat = 0
    total_combo_equity = 0
    for coin in COINS:
        if coin in combo:
            r = combo[coin]
            b = baseline[coin]
            total_combo_flat += r['flat_days']
            total_combo_equity += r['equity']
            saved = b['flat_days'] - r['flat_days']
            delta_eq = r['equity'] - b['equity']
            print(f"  {coin}: {r['flat_days']:3d}d flat (saved {saved:+d}d), equity ${r['equity']:,.0f} ({delta_eq:+,.0f})")
    saved_c = total_baseline_flat - total_combo_flat
    delta_c = total_combo_equity - total_baseline_equity
    print(f"  TOTAL: {total_combo_flat}d flat (saved {saved_c}d), ${total_combo_equity:,.0f} ({delta_c:+,.0f})")

    # Also test ADX 7d + timeout 28d 
    print(f"\n--- COMBINED: ADX 7d + Timeout 28d ---")
    combo2 = run_variant("Combo2", cfg_mods={'FLAT_ADX_SUSTAINED_DAYS': 7, 'PHASE_ADX_SUSTAINED_DAYS': 7, 'FLAT_MAX_EVAL_DAYS': 28})
    
    total_combo2_flat = 0
    total_combo2_equity = 0
    for coin in COINS:
        if coin in combo2:
            r = combo2[coin]
            b = baseline[coin]
            total_combo2_flat += r['flat_days']
            total_combo2_equity += r['equity']
            saved = b['flat_days'] - r['flat_days']
            delta_eq = r['equity'] - b['equity']
            print(f"  {coin}: {r['flat_days']:3d}d flat (saved {saved:+d}d), equity ${r['equity']:,.0f} ({delta_eq:+,.0f})")
    saved_c2 = total_baseline_flat - total_combo2_flat
    delta_c2 = total_combo2_equity - total_baseline_equity
    print(f"  TOTAL: {total_combo2_flat}d flat (saved {saved_c2}d), ${total_combo2_equity:,.0f} ({delta_c2:+,.0f})")


if __name__ == '__main__':
    analyze_savings()
