"""
Bottom Detection Signal Stack Backtest
Test: 2D death cross + Below SMA200 + CFGI < 35 + Spring + Weekly RSI < 30
as ROUTER->MARKUP transition signal.

Compare against v8 baseline to measure dollar impact.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase, price_near_fib_support, price_broke_fib_support
from v13_signals import V13SignalPack

DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'


class BottomStackDetector:
    """Detect bottom signal convergence for ROUTER->MARKUP."""
    
    def __init__(self, coin, daily_df=None):
        self.coin = coin
        self.base = coin.split('/')[0].upper()
        
        if daily_df is not None:
            self.daily = daily_df
        else:
            self.daily = self._load_daily()
        
        # Precompute all signals
        self._compute_2d_death_cross()
        self._compute_weekly_rsi()
        self._compute_spring_signals()
        self._load_cfgi()
    
    def _load_daily(self):
        conn = sqlite3.connect(str(DB_PATH))
        df = pd.read_sql_query(
            f"SELECT * FROM candles_daily WHERE symbol LIKE '{self.base}%' ORDER BY timestamp", conn)
        conn.close()
        if df['timestamp'].dtype in ['int64', 'float64']:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        else:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp').sort_index()
        df = df[~df.index.duplicated(keep='last')]
        df = df[df.index.notna()]
        # Daily SMAs
        df['sma200'] = df['close'].rolling(200).mean()
        return df
    
    def _compute_2d_death_cross(self):
        """Compute 2D death cross status as a daily series."""
        df_2d = self.daily.resample('2D').agg({
            'open': 'first', 'high': 'max', 'low': 'min',
            'close': 'last', 'volume': 'sum'
        }).dropna()
        df_2d['sma50'] = df_2d['close'].rolling(50).mean()
        df_2d['sma200'] = df_2d['close'].rolling(200).mean()
        
        # Track death cross state and days since
        self._2d_death_cross_active = {}
        self._2d_days_since_cross = {}
        
        active = False
        cross_date = None
        
        for i in range(len(df_2d)):
            s50 = df_2d['sma50'].iloc[i]
            s200 = df_2d['sma200'].iloc[i]
            if pd.isna(s50) or pd.isna(s200):
                continue
            
            was_above = not active  # If not in death cross, sma50 was above
            currently_above = s50 > s200
            
            if not currently_above and (cross_date is None or currently_above != active):
                if not active:  # Just crossed to death
                    cross_date = df_2d.index[i]
                active = True
            elif currently_above:
                active = False
                cross_date = None
            
            date = df_2d.index[i]
            self._2d_death_cross_active[date] = active
            self._2d_days_since_cross[date] = (date - cross_date).days if cross_date and active else 0
        
        # Forward-fill to daily resolution
        self.death_cross_active = {}
        self.days_since_death_cross = {}
        last_active = False
        last_days = 0
        
        for date in self.daily.index:
            # Find nearest 2D date
            for d2 in sorted(self._2d_death_cross_active.keys()):
                if d2 <= date:
                    last_active = self._2d_death_cross_active[d2]
                    last_days = self._2d_days_since_cross[d2]
            
            self.death_cross_active[date] = last_active
            if last_active and last_days > 0:
                # Adjust days for the daily date
                self.days_since_death_cross[date] = last_days + (date - max(d for d in self._2d_death_cross_active.keys() if d <= date)).days
            else:
                self.days_since_death_cross[date] = 0
    
    def _compute_weekly_rsi(self):
        """Compute weekly RSI(7)."""
        weekly = self.daily['close'].resample('W').last().dropna()
        delta = weekly.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.rolling(7).mean()
        avg_loss = loss.rolling(7).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # Forward-fill to daily
        self.weekly_rsi = {}
        last_rsi = 50
        for date in self.daily.index:
            nearest = rsi.index[rsi.index.get_indexer([date], method='ffill')]
            if len(nearest) > 0 and not pd.isna(rsi.get(nearest[0])):
                last_rsi = float(rsi.loc[nearest[0]])
            self.weekly_rsi[date] = last_rsi
    
    def _compute_spring_signals(self):
        """Detect spring patterns: break below 20-day support + recover within 3 days."""
        self.spring_active = {}
        df = self.daily
        
        support = df['low'].rolling(20).min()
        
        for i in range(23, len(df)):
            date = df.index[i]
            self.spring_active[date] = False
            
            # Check if there was a spring in the last 5 days
            for lookback in range(1, 6):
                if i - lookback < 20:
                    continue
                
                spring_date = df.index[i - lookback]
                sup = support.iloc[i - lookback - 1]  # Support BEFORE the break
                
                if pd.isna(sup):
                    continue
                
                # Did price break below support?
                if df['low'].iloc[i - lookback] >= sup:
                    continue
                
                # Did price recover above support?
                if df['close'].iloc[i] > sup:
                    self.spring_active[date] = True
                    break
    
    def _load_cfgi(self):
        """Load CFGI data."""
        conn = sqlite3.connect(str(DB_PATH))
        df = pd.read_sql_query(
            f"SELECT * FROM cfgi_daily WHERE symbol LIKE '{self.base}%' ORDER BY date", conn)
        conn.close()
        
        self.cfgi = {}
        if df.empty:
            return
        
        df['date'] = pd.to_datetime(df['date'], format='mixed')
        df = df.set_index('date').sort_index()
        df = df[~df.index.duplicated(keep='last')]
        
        val_col = 'value' if 'value' in df.columns else df.columns[-1]
        
        last_val = 50
        for date in self.daily.index:
            nearest = df.index[df.index.get_indexer([date], method='ffill')]
            if len(nearest) > 0 and nearest[0] in df.index:
                last_val = float(df.loc[nearest[0], val_col])
            self.cfgi[date] = last_val
    
    def check_bottom_stack(self, date, min_dx_days=10, cfgi_thresh=35, rsi_thresh=30):
        """Check if bottom signal stack is active on this date.
        Returns (is_active, signals_dict)."""
        if date not in self.death_cross_active:
            return False, {}
        
        dx_active = self.death_cross_active.get(date, False)
        dx_days = self.days_since_death_cross.get(date, 0)
        below_sma200 = False
        if date in self.daily.index:
            row = self.daily.loc[date]
            sma200 = row.get('sma200', np.nan)
            if hasattr(sma200, 'iloc'):
                sma200 = float(sma200.iloc[0])
            if not pd.isna(sma200):
                below_sma200 = float(row['close'] if not hasattr(row['close'], 'iloc') else row['close'].iloc[0]) < sma200
        
        cfgi = self.cfgi.get(date, 50)
        wrsi = self.weekly_rsi.get(date, 50)
        spring = self.spring_active.get(date, False)
        
        signals = {
            'dx_active': dx_active,
            'dx_days': dx_days,
            'below_sma200': below_sma200,
            'cfgi': cfgi,
            'wrsi': wrsi,
            'spring': spring,
        }
        
        # Count how many signals are active
        active_count = 0
        if dx_active and dx_days >= min_dx_days:
            active_count += 1
        if below_sma200:
            active_count += 1
        if cfgi < cfgi_thresh:
            active_count += 1
        if wrsi < rsi_thresh:
            active_count += 1
        if spring:
            active_count += 1
        
        signals['active_count'] = active_count
        
        return active_count, signals


class V13WithBottomStack(V13BacktestV8):
    """V13 with bottom signal stack for ROUTER->MARKUP."""
    
    def __init__(self, pack, cfg, bottom_detector=None, min_signals=3):
        super().__init__(pack, cfg)
        self.bottom_detector = bottom_detector
        self.min_signals = min_signals
        self.bottom_triggers = []
    
    def _check_flat(self, date, price):
        """Override: add bottom stack check for ROUTER->MARKUP."""
        if self.phase_start_date is None:
            return
        
        adx = self._adx(date)
        days_flat = (date - self.phase_start_date).days
        
        if days_flat < self.cfg.FLAT_MIN_EVAL_DAYS:
            return
        
        # --- PATH 1: From TOP SIGNAL ---
        if self.flat_from_top:
            # Check MARKDOWN first (highest priority)
            fib = self._fib_levels(date)
            lh_ll = self.pack.structure.lh_ll_streak(date, self.cfg.HH_HL_LOOKBACK)
            if lh_ll and not np.isnan(adx) and adx > self.cfg.ADX_THRESHOLD:
                if price_broke_fib_support(price, fib):
                    overext = self.pack.sma200.overextension_at(date)
                    note = f'FLAT->MARKDOWN: Post-top, LH_LL+ADX={adx:.0f}+Fib_break'
                    if not np.isnan(overext):
                        note += f' (SMA200={overext*100:+.0f}%)'
                    note += f' (flat {days_flat}d)'
                    self._change_phase(date, Phase.MARKDOWN, note)
                    return
            
            # --- NEW: Bottom stack check for direct MARKUP ---
            if self.bottom_detector and days_flat >= 10:
                count, signals = self.bottom_detector.check_bottom_stack(date)
                if count >= self.min_signals and signals.get('spring', False):
                    # Spring is required as the structural confirmation
                    note = (f'BOTTOM_STACK->MARKUP: {count}/5 signals '
                            f'(DX={signals["dx_days"]}d, CFGI={signals["cfgi"]:.0f}, '
                            f'WRSI={signals["wrsi"]:.0f}, Spring=YES, flat {days_flat}d)')
                    self.bottom_triggers.append({
                        'date': date, 'days_flat': days_flat, 
                        'signals': count, 'details': signals
                    })
                    self._change_phase(date, Phase.MARKUP, note)
                    return
            
            # Timeout
            if days_flat >= self.cfg.FLAT_MAX_EVAL_DAYS:
                self._change_phase(date, Phase.DCA,
                    f'FLAT->DCA: Post-top, no markdown signal after {days_flat}d')
            return
        
        # --- PATH 2 & 3: From RANGING EXIT or MARKDOWN ---
        # Bottom stack check here too
        if self.bottom_detector and days_flat >= 10:
            count, signals = self.bottom_detector.check_bottom_stack(date)
            if count >= self.min_signals and signals.get('spring', False):
                note = (f'BOTTOM_STACK->MARKUP: {count}/5 signals '
                        f'(DX={signals["dx_days"]}d, CFGI={signals["cfgi"]:.0f}, '
                        f'WRSI={signals["wrsi"]:.0f}, Spring=YES, flat {days_flat}d)')
                self.bottom_triggers.append({
                    'date': date, 'days_flat': days_flat,
                    'signals': count, 'details': signals
                })
                self._change_phase(date, Phase.MARKUP, note)
                return
        
        # ADX ranging confirmation (existing)
        if not np.isnan(adx) and adx < self.cfg.FLAT_ADX_RANGING:
            self.adx_below_20_streak += 1
        else:
            self.adx_below_20_streak = 0
        
        if self.adx_below_20_streak >= self.cfg.FLAT_ADX_SUSTAINED_DAYS:
            self._change_phase(date, Phase.DCA,
                f'FLAT->DCA: Ranging confirmed (ADX<{self.cfg.FLAT_ADX_RANGING} for {self.adx_below_20_streak}d)')
            self.adx_below_20_streak = 0


def run_variant(coins, min_signals, label):
    """Run backtest with bottom stack requiring min_signals convergence."""
    results = {}
    total_equity = 0
    total_triggers = 0
    
    for coin in coins:
        pack = V13SignalPack(coin)
        cfg = V13Config()
        cfg.START_DATE = '2023-01-01'
        cfg.END_DATE = '2026-02-25'
        cfg.CAPITAL = 2500
        
        if min_signals == 0:
            # Baseline — no bottom stack
            bt = V13BacktestV8(pack, cfg)
        else:
            detector = BottomStackDetector(coin)
            bt = V13WithBottomStack(pack, cfg, bottom_detector=detector, min_signals=min_signals)
        
        result = bt.run()
        if result is None:
            continue
        
        triggers = len(bt.bottom_triggers) if hasattr(bt, 'bottom_triggers') else 0
        router_days = sum(1 for e in bt.equity_curve if e.get('phase') == Phase.FLAT)
        
        results[coin] = {
            'equity': result['final_equity'],
            'trades': result['total_trades'],
            'triggers': triggers,
            'router_days': router_days,
        }
        total_equity += result['final_equity']
        total_triggers += triggers
        
        if triggers > 0 and hasattr(bt, 'bottom_triggers'):
            for t in bt.bottom_triggers:
                print(f"    {coin} TRIGGER: {t['date'].strftime('%Y-%m-%d')} "
                      f"({t['signals']}/5 signals, {t['days_flat']}d in router)")
    
    return results, total_equity, total_triggers


def main():
    coins = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']
    
    print("=" * 130)
    print("  BOTTOM SIGNAL STACK BACKTEST")
    print("  2D Death Cross + Below SMA200 + CFGI<35 + Spring + Weekly RSI<30")
    print("=" * 130)
    
    variants = [
        (0, 'BASELINE (no bottom stack)'),
        (3, 'Bottom Stack >= 3/5 signals (+ Spring required)'),
        (4, 'Bottom Stack >= 4/5 signals (+ Spring required)'),
        (5, 'Bottom Stack = 5/5 signals (all converge)'),
    ]
    
    baseline_equity = None
    
    print(f"\n{'Variant':<55} {'Total$':>10} {'Delta':>8} {'Trig':>5} {'RtrDays':>8}  ", end="")
    for c in coins:
        print(f" {c:>7}", end="")
    print()
    print("-" * 130)
    
    for min_sig, label in variants:
        print(f"\n  Running: {label}")
        results, total_eq, total_trig = run_variant(coins, min_sig, label)
        
        if baseline_equity is None:
            baseline_equity = total_eq
        
        delta = total_eq - baseline_equity
        total_router = sum(r['router_days'] for r in results.values())
        
        d_str = f"{delta:+,.0f}" if delta != 0 else "BASE"
        print(f"\n{label:<55} ${total_eq:>9,.0f} {d_str:>8} {total_trig:>5} {total_router:>8}  ", end="")
        for c in coins:
            if c in results:
                coin_delta = results[c]['equity'] - (baseline_equity / len(coins)) if min_sig == 0 else results[c]['equity']
                print(f" ${results[c]['equity']:>6,.0f}", end="")
            else:
                print(f" {'N/A':>7}", end="")
        print()


if __name__ == '__main__':
    main()
