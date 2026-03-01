"""
Full-cycle backtest: V13 with 2D RSI bearish divergence as top signal

Compares:
  1. Current v8 engine (OB93 top detection) — should match dashboard ~$28,438
  2. V8 with 2D divergence replacing OB93 as primary top signal

Same settings as live paper bot:
  - Coins: ETH/USDC, SOL/USDC, LINK/USDC, XRP/USDC
  - Start: Oct 1, 2024
  - Capital: $10,000 ($2,500/coin)
  - Profile: High (T1=60%, T2=20%, T3=10%)
  
2D divergence config (from our testing):
  - 30-bar lookback on 2D candles
  - RSI gap >= 8 (current RSI vs peak RSI in lookback)
  - Price within 3% of lookback high
  - Current RSI > 60 (still elevated)
  - Peak RSI in lookback > 75 (real overbought existed)
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from copy import deepcopy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase

import sqlite3

DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'


def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


class BearishDivergence2D:
    """
    Detect bearish divergence on 2D chart.
    
    Signal fires when:
    - Price is within price_pct% of its lookback-period high (on 2D candles)
    - RSI is at least rsi_gap below its lookback-period peak
    - RSI is still above min_rsi (elevated territory)
    - Peak RSI in lookback was above rsi_peak_min (real overbought existed)
    """
    
    def __init__(self, daily_df, lookback=30, rsi_gap=8, price_pct=3.0, 
                 min_rsi=60, rsi_peak_min=75):
        self.lookback = lookback
        self.rsi_gap = rsi_gap
        self.price_pct = price_pct
        self.min_rsi = min_rsi
        self.rsi_peak_min = rsi_peak_min
        
        # Resample daily to 2D
        df = daily_df.copy()
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'date' in df.columns:
                df = df.set_index('date')
            elif 'dt' in df.columns:
                df = df.set_index('dt')
        
        df_2d = df[['open', 'high', 'low', 'close', 'volume']].resample('2D').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 
            'close': 'last', 'volume': 'sum'
        }).dropna()
        
        df_2d['rsi'] = compute_rsi(df_2d['close'], 14)
        df_2d['price_high_N'] = df_2d['high'].rolling(lookback).max()
        df_2d['rsi_high_N'] = df_2d['rsi'].rolling(lookback).max()
        
        df_2d['signal'] = (
            (df_2d['high'] >= df_2d['price_high_N'] * (1 - price_pct / 100)) &
            ((df_2d['rsi_high_N'] - df_2d['rsi']) >= rsi_gap) &
            (df_2d['rsi'] >= min_rsi) &
            (df_2d['rsi_high_N'] > rsi_peak_min)
        )
        
        self._signals = df_2d
    
    def is_divergent_at(self, date):
        """Check if bearish divergence is active at or near this date."""
        # Find nearest 2D candle at or before this date
        mask = self._signals.index <= date
        if not mask.any():
            return False
        nearest = self._signals[mask].iloc[-1]
        # Must be within 2 days (since it's 2D candles)
        if (date - self._signals[mask].index[-1]).days > 3:
            return False
        return bool(nearest['signal'])
    
    def signal_dates(self):
        """Return all dates where divergence fired."""
        return self._signals[self._signals['signal']].index.tolist()


class V13WithDivergenceTop(V13BacktestV8):
    """
    V13 engine with 2D bearish divergence replacing OB93 as primary top signal.
    
    Changes:
    - Layer 2 (primary exit): 2D RSI bearish divergence replaces 2W OB93
    - All other layers unchanged (fallback, failsafe, ranging, markup fail)
    """
    
    def __init__(self, pack, config=None, divergence_detector=None):
        super().__init__(pack, config)
        self._div_detector = divergence_detector
    
    def _check_markup(self, date, price):
        """Override markup check to use divergence instead of OB93."""
        # Let DCA TPs hit naturally
        if self.dca_coins > 0:
            self._dca_tick(date, price)
        
        # Track peak 2W K (still needed for fallback logic)
        k_2w = self.pack.stoch_2w.get_k_at(date)
        if not np.isnan(k_2w) and k_2w > self.peak_2w_k:
            self.peak_2w_k = k_2w
        
        # Layer 1: Early warning (unchanged)
        if self._signal_near(date, self.early_warnings_1w) and self.early_warning_date is None:
            self.early_warning_date = date
            self.trades.append({
                'date': date, 'action': f'EARLY_WARNING_1W_97 (2W_peak={self.peak_2w_k:.0f})',
                'price': price, 'amount': 0, 'coins': 0, 'phase': self.phase
            })
        
        # Layer 2: PRIMARY — 2D bearish divergence (NEW — replaces OB93)
        if self._div_detector and self._div_detector.is_divergent_at(date):
            pnl = self._sell_all(date, 'PRIMARY_2D_DIVERGENCE')
            if self.dca_coins > 0:
                self._dca_close(date, 'TOP_EXIT')
            self._change_phase(date, Phase.FLAT, f'2D bearish divergence exit, pnl={pnl:+.1f}%')
            self._reset_top_state()
            return
        
        # Layer 2b: Fallback — 1W OB85 when 2W never reached OB (unchanged)
        if self.peak_2w_k < self.cfg.OB_THRESHOLD_2W and self.early_warning_date:
            if self._signal_near(date, self.ob85_1w):
                pnl = self._sell_all(date, f'FALLBACK_1W_OB85 (2W_peak={self.peak_2w_k:.0f})')
                if self.dca_coins > 0:
                    self._dca_close(date, 'TOP_EXIT')
                self._change_phase(date, Phase.FLAT,
                    f'1W OB85 fallback (2W peak={self.peak_2w_k:.0f}<93), pnl={pnl:+.1f}%')
                self._reset_top_state()
                return
        
        # Layer 3: Failsafe — 1W K<50 (unchanged)
        if self.early_warning_date and not self.failsafe_armed:
            if (date - self.early_warning_date).days >= self.cfg.FAILSAFE_WINDOW_WEEKS * 7:
                self.failsafe_armed = True
        if self.failsafe_armed and self._signal_near(date, self.failsafe_1w):
            pnl = self._sell_all(date, 'FAILSAFE_1W_K50')
            if self.dca_coins > 0:
                self._dca_close(date, 'TOP_EXIT')
            self._change_phase(date, Phase.FLAT, f'Failsafe 1W K<50, pnl={pnl:+.1f}%')
            self._reset_top_state()
            return
        
        # Layer 4: Ranging exit (unchanged)
        days_in = (date - self.phase_start_date).days if self.phase_start_date else 0
        if days_in >= 14:
            adx = self._adx(date)
            if not np.isnan(adx) and adx < self.cfg.PHASE_ADX_RANGING:
                self.adx_below_20_streak += 1
                if self.adx_below_20_streak >= self.cfg.PHASE_ADX_SUSTAINED_DAYS:
                    pnl = self._sell_all(date, f'MARKUP_RANGING (ADX<{self.cfg.PHASE_ADX_RANGING} for {self.adx_below_20_streak}d)')
                    if self.dca_coins > 0:
                        self._dca_close(date, 'RANGING_EXIT')
                    self._change_phase(date, Phase.FLAT,
                        f'Markup ranging: ADX<{self.cfg.PHASE_ADX_RANGING} for {self.adx_below_20_streak}d')
                    self._reset_top_state()
                    return
            else:
                self.adx_below_20_streak = 0
        
        # Layer 5: Markup failure (unchanged)
        if self.entry_price > 0:
            dd_from_entry = (price - self.entry_price) / self.entry_price
            if dd_from_entry < -self.cfg.MARKUP_FAIL_DD_PCT:
                adx = self._adx(date)
                if not np.isnan(adx) and adx > self.cfg.MARKUP_FAIL_ADX:
                    pnl = self._sell_all(date, f'MARKUP_FAIL (dd={dd_from_entry*100:.0f}%, ADX={adx:.0f})')
                    if self.dca_coins > 0:
                        self._dca_close(date, 'MARKUP_FAIL')
                    self._change_phase(date, Phase.FLAT,
                        f'Markup failed: {dd_from_entry*100:.0f}% below entry')
                    self._reset_top_state()
                    return
        
        # Tier adds (unchanged)
        self._check_markup_tiers(date, price)


# ============================================================
# RUN BACKTEST
# ============================================================

from v13_signals import V13SignalPack

COINS = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
START = '2024-10-01'
CAPITAL = 10000
PER_COIN = CAPITAL / len(COINS)

def make_config():
    c = V13Config()
    c.PROFILE = 'high'
    c.TIER1_PCT = 0.60
    c.TIER2_PCT = 0.20
    c.TIER3_PCT = 0.10
    c.SHORT_TIER1_PCT = 0.60
    c.SHORT_TIER2_PCT = 0.20
    c.SHORT_TIER3_PCT = 0.10
    c.START_DATE = START
    c.CAPITAL = PER_COIN
    return c

print("=" * 90)
print("V13 FULL CYCLE BACKTEST — OB93 vs 2D Divergence Top Signal")
print(f"Coins: {', '.join(COINS)}  |  Start: {START}  |  Capital: ${CAPITAL:,}")
print("=" * 90)

# ── Run 1: Baseline (current OB93 engine) ──
print("\n--- BASELINE: Current V8 Engine (OB93 top detection) ---")
baseline_equity = 0
baseline_trades = {}
for coin in COINS:
    try:
        pack = V13SignalPack(coin)
    except Exception as e:
        print(f"  {coin}: SKIP ({e})")
        continue
    
    cfg = make_config()
    engine = V13BacktestV8(pack, cfg)
    result = engine.run()
    eq = result['final_equity']
    baseline_equity += eq
    baseline_trades[coin] = result
    pnl_pct = (eq - PER_COIN) / PER_COIN * 100
    roi = result.get('roi', pnl_pct)
    print(f"  {coin}: ${eq:,.0f} ({roi:+.1f}%)  trades={result.get('total_trades', '?')}")

baseline_pnl = (baseline_equity - CAPITAL) / CAPITAL * 100
print(f"\n  BASELINE TOTAL: ${baseline_equity:,.0f} ({baseline_pnl:+.1f}%)")

# ── Run 2: 2D Divergence Top Signal ──
print("\n--- NEW: V8 + 2D Divergence Top Signal ---")
div_equity = 0
div_trades = {}
for coin in COINS:
    try:
        pack = V13SignalPack(coin)
    except Exception as e:
        print(f"  {coin}: SKIP ({e})")
        continue
    
    # Build divergence detector from daily data
    div_detector = BearishDivergence2D(pack.daily)
    
    cfg = make_config()
    engine = V13WithDivergenceTop(pack, cfg, divergence_detector=div_detector)
    result = engine.run()
    eq = result['final_equity']
    div_equity += eq
    div_trades[coin] = result
    pnl_pct = (eq - PER_COIN) / PER_COIN * 100
    roi = result.get('roi', pnl_pct)
    print(f"  {coin}: ${eq:,.0f} ({roi:+.1f}%)  trades={result.get('total_trades', '?')}")

div_pnl = (div_equity - CAPITAL) / CAPITAL * 100
print(f"\n  DIVERGENCE TOTAL: ${div_equity:,.0f} ({div_pnl:+.1f}%)")

# ── Comparison ──
print(f"\n{'='*90}")
print("COMPARISON")
print(f"{'='*90}")
print(f"  Baseline (OB93):     ${baseline_equity:,.0f} ({baseline_pnl:+.1f}%)")
print(f"  2D Divergence:       ${div_equity:,.0f} ({div_pnl:+.1f}%)")
print(f"  Delta:               ${div_equity - baseline_equity:+,.0f} ({div_pnl - baseline_pnl:+.1f}%)")

print(f"\n  Per-coin comparison:")
print(f"  {'Coin':>12s}  {'Baseline':>10s}  {'Divergence':>10s}  {'Delta':>10s}")
print(f"  {'-'*48}")
for coin in COINS:
    if coin in baseline_trades and coin in div_trades:
        b_eq = baseline_trades[coin]['final_equity']
        d_eq = div_trades[coin]['final_equity']
        print(f"  {coin:>12s}  ${b_eq:>9,.0f}  ${d_eq:>9,.0f}  ${d_eq - b_eq:>+9,.0f}")

# ── Show key trade differences ──
print(f"\n  Key trade differences (top exits):")
for coin in COINS:
    if coin in baseline_trades and coin in div_trades:
        top_keywords = ['OB93', 'OB85', 'FAILSAFE', 'DIVERGENCE', 'RANGING', 'MARKUP_FAIL']
        b_trades = [t for t in baseline_trades[coin].get('trades', []) if any(k in str(t.get('action', '')) for k in top_keywords)]
        d_trades = [t for t in div_trades[coin].get('trades', []) if any(k in str(t.get('action', '')) for k in top_keywords)]
        
        print(f"\n  {coin}:")
        print(f"    Baseline top exits:")
        for t in b_trades:
            print(f"      {t.get('date', '?')} — {t.get('action', '?')} @ ${t.get('price', 0):,.2f}")
        if not b_trades:
            print(f"      (none)")
        print(f"    Divergence top exits:")
        for t in d_trades:
            print(f"      {t.get('date', '?')} — {t.get('action', '?')} @ ${t.get('price', 0):,.2f}")
        if not d_trades:
            print(f"      (none)")
