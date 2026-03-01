"""
V13 Phase-Riding Backtest v8 — Signal-Driven Architecture

ALL transitions driven by validated signals from matrix testing:
  DCA → MARKUP:   HH_HL + Fib_support (94.0 score, 100% acc, 20% FP)
  DCA → MARKDOWN: ADX>20 + Fib_break (94.0 score, 100% acc, 20% FP)
  MARKUP → FLAT:  2W OB93 (primary) / 1W OB85 (fallback) / 1W K<50 (failsafe)
  FLAT → routing:  HVF-driven (>0.4 = stay flat, <0.2 for 7d = enter DCA)
  MARKDOWN → DCA: HH_HL + Fib_support (structure turning bullish)

NO fixed timers. NO 1h conductor. NO channel breakout. NO CFGI momentum.
Pure signal-driven phase riding.

Period: Oct 2024 → current (one full cycle)
Coins: BTC, ETH, SOL

Usage:
    python v13_backtest_v8.py
"""

import sys
import sqlite3
import pandas as pd
import numpy as np
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
from test_hvf_daily import (
    composite_hvf_score, detect_swing_points, hvf_harmonic_pattern
)

DB_PATH = Path(__file__).resolve().parents[2] / 'data' / 'candles.db'


# ── Fibonacci Calculator ────────────────────────────────────────────────

class FibonacciLevels:
    """Compute dynamic Fibonacci retracement and extension levels from swing structure."""

    FIB_RETRACE = [0.236, 0.382, 0.5, 0.618, 0.786]
    FIB_EXT = [1.0, 1.272, 1.618, 2.0, 2.618]
    TOLERANCE = 0.03  # 3% proximity

    def __init__(self, daily_df, swing_lookback=10):
        self.df = daily_df
        self.swings = detect_swing_points(daily_df, lookback=swing_lookback)
        self.swing_highs = [s for s in self.swings if s['type'] == 'high']
        self.swing_lows = [s for s in self.swings if s['type'] == 'low']

    def _get_last_swing(self, date, swing_type, lookback_days=180):
        """Get the most recent swing high or low before date."""
        candidates = self.swing_highs if swing_type == 'high' else self.swing_lows
        recent = [s for s in candidates
                  if s['date'] < date and (date - s['date']).days < lookback_days]
        if not recent:
            return None
        return max(recent, key=lambda s: s['date'])

    def _get_major_swing_low(self, date, lookback_days=180):
        """Get the lowest swing low in the lookback window."""
        candidates = [s for s in self.swing_lows
                      if s['date'] < date and (date - s['date']).days < lookback_days]
        if not candidates:
            return None
        return min(candidates, key=lambda s: s['price'])

    def _get_major_swing_high(self, date, lookback_days=180):
        """Get the highest swing high in the lookback window."""
        candidates = [s for s in self.swing_highs
                      if s['date'] < date and (date - s['date']).days < lookback_days]
        if not candidates:
            return None
        return max(candidates, key=lambda s: s['price'])

    def support_levels(self, date):
        """Compute Fibonacci retracement support levels from the last major high→low swing.
        Returns dict of {ratio: price_level}."""
        high = self._get_major_swing_high(date)
        low = self._get_major_swing_low(date)
        if not high or not low or high['date'] <= low['date']:
            # Need high BEFORE low for retracement of a downswing
            # Or high AFTER low for retracement of an upswing
            # Try both orderings
            pass

        if not high or not low:
            return {}

        swing_range = abs(high['price'] - low['price'])
        if swing_range < 1:
            return {}

        levels = {}
        if high['date'] > low['date']:
            # Upswing retracement: support levels below current high
            for ratio in self.FIB_RETRACE:
                levels[ratio] = high['price'] - swing_range * ratio
        else:
            # Downswing retracement: support levels above current low
            for ratio in self.FIB_RETRACE:
                levels[ratio] = low['price'] + swing_range * ratio

        return levels

    def at_fib_support(self, date, price):
        """Check if price is near any Fibonacci support level."""
        levels = self.support_levels(date)
        for ratio, level in levels.items():
            if level > 0:
                dist = abs(price - level) / level
                if dist < self.TOLERANCE:
                    return True, ratio, level
        return False, None, None

    def broke_fib_support(self, date, price):
        """Check if price has broken below a Fibonacci support level."""
        levels = self.support_levels(date)
        for ratio, level in levels.items():
            if level > 0 and price < level * (1 - self.TOLERANCE):
                return True, ratio, level
        return False, None, None

    def extension_levels(self, swing_low_price, swing_high_price):
        """Compute Fibonacci extension levels for cycle top detection.
        Used in Cycle 2+ only, from previous cycle's swing."""
        swing_range = abs(swing_high_price - swing_low_price)
        levels = {}
        for ratio in self.FIB_EXT:
            levels[ratio] = swing_low_price + swing_range * ratio
        return levels


# ── HVF Calculator ──────────────────────────────────────────────────────

class HVFCalculator:
    """Compute HVF composite score for daily candles."""

    def __init__(self, daily_df):
        self.df = daily_df

    def score_at(self, date, lookback=44):
        """Get HVF composite score at a date."""
        mask = self.df.index <= date
        if mask.sum() < lookback:
            return 0.0
        window = self.df.loc[mask].iloc[-lookback:]
        result = composite_hvf_score(window)
        # composite_hvf_score returns (composite, vuvu, vol_comp, price_comp)
        # Each may be a Series; we want the last value of composite
        if isinstance(result, tuple):
            val = result[0]
        else:
            val = result
        if hasattr(val, 'iloc'):
            return float(val.iloc[-1])
        return float(val)


# ── Configuration ──────────────────────────────────────────────────────

class V8Config:
    """V13 v8 backtest configuration — all signal-driven."""

    # === Top Detection (MARKUP → FLAT) ===
    OB_THRESHOLD_2W = 93       # Primary top: 2W K crosses below this
    EARLY_WARNING_1W = 97      # 1W early warning threshold
    FAILSAFE_1W = 50           # 1W failsafe exit: K crosses below this
    FAILSAFE_WINDOW_WEEKS = 2  # Weeks after early warning before failsafe arms
    OB_FALLBACK_1W = 85        # 1W fallback when 2W never reaches OB

    # === DCA → MARKUP: HH_HL + Fib_support ===
    HH_HL_LOOKBACK = 20        # Days to look for higher-high/higher-low pattern
    FIB_TOLERANCE = 0.03       # 3% proximity to Fib level
    CFGI_MARKUP_GATE = 40      # Optional CFGI confirmation (>40)

    # === DCA → MARKDOWN: ADX>20 + Fib_break ===
    ADX_THRESHOLD = 20         # Confirms trending market
    # Fib_break uses same FIB_TOLERANCE

    # === FLAT → Routing: HVF-driven ===
    HVF_MARKDOWN_THRESHOLD = 0.4   # HVF > this = markdown building, stay flat
    HVF_SAFE_THRESHOLD = 0.2       # HVF < this for 7 days = safe to DCA
    HVF_SAFE_DAYS = 7              # Consecutive days below threshold

    # === Tier Sizing (MARKUP) ===
    TIER1_PCT = 0.60           # Entry (heavy at lowest price)
    TIER2_PCT = 0.20           # Confirmation add
    TIER3_PCT = 0.10           # Momentum add
    TIER2_DELAY_WEEKS = 1
    TIER3_DELAY_WEEKS = 2

    # === Shorts (MARKDOWN) ===
    SHORT_PCT = 0.60           # 60% of capital in short

    # === DCA Engine ===
    DCA_BO_PCT = 0.08          # 8% base order
    DCA_SO_DEVIATION = 0.025   # 2.5% between layers
    DCA_SO_MULTIPLIER = 1.5    # Volume multiplier
    DCA_TP_PCT = 0.015         # 1.5% take profit
    DCA_MAX_LAYERS = 8
    DCA_RESERVE_PCT = 0.10     # 10% reserve

    # === General ===
    MIN_PHASE_WEEKS = 2        # Minimum hold time
    CAPITAL = 10_000
    START_DATE = '2024-10-01'  # One full cycle start
    END_DATE = '2026-02-25'


# ── Phase State Machine ───────────────────────────────────────────────

class Phase:
    DCA = 'DCA'
    MARKUP = 'MARKUP'
    FLAT = 'FLAT'              # Post-top, HVF-driven routing (replaces COOLDOWN)
    MARKDOWN = 'MARKDOWN'


# ── Backtest Engine ───────────────────────────────────────────────────

class V13BacktestV8:
    """V13 v8 — Pure signal-driven phase riding."""

    def __init__(self, pack: V13SignalPack, config: V8Config = None):
        self.pack = pack
        self.cfg = config or V8Config()
        self.coin = pack.coin

        # Signals
        self.fib = FibonacciLevels(pack.daily)
        self.hvf = HVFCalculator(pack.daily)

        # State
        self.phase = Phase.DCA
        self.capital = self.cfg.CAPITAL
        self.position_coins = 0.0
        self.entry_price = 0.0
        self.tier = 0
        self.phase_start_date = None
        self.early_warning_date = None
        self.failsafe_armed = False
        self.peak_2w_k = 0.0

        # Short state
        self.short_coins = 0.0
        self.short_entry = 0.0
        self.short_cost = 0.0
        self.markup_cycles_completed = 0
        self.shorts_enabled = False

        # FLAT state
        self.hvf_low_streak = 0  # Consecutive days HVF < threshold

        # DCA state
        self.dca_position_coins = 0.0
        self.dca_entry_price = 0.0
        self.dca_layers = 0
        self.dca_last_buy = None
        self.dca_tp_target = 0.0
        self.dca_total_cost = 0.0
        self.dca_trades = 0
        self.dca_wins = 0
        self.dca_total_pnl = 0.0

        # Logs
        self.trades = []
        self.phase_log = []
        self.equity_curve = []

        # Precompute StochRSI signal events
        self._precompute_stoch_signals()

    def _precompute_stoch_signals(self):
        """Precompute StochRSI crossing events."""
        stoch_2w = self.pack.stoch_2w
        stoch_1w = self.pack.stoch_1w

        # 2W OB exits (K crosses below threshold from above)
        self.ob_exits_2w = set(stoch_2w.ob_exits(self.cfg.OB_THRESHOLD_2W).index)
        # 2W OS exits (K crosses above threshold from below)
        self.os_exits_2w = set(stoch_2w.os_exits(20).index)

        # 1W early warning (K crosses below 97)
        df_1w = stoch_1w.df
        prev_k = df_1w['K'].shift(1)
        ew_mask = (prev_k >= self.cfg.EARLY_WARNING_1W) & (df_1w['K'] < self.cfg.EARLY_WARNING_1W)
        self.early_warnings_1w = set(df_1w[ew_mask].index)

        # 1W failsafe (K crosses below 50)
        fs_mask = (prev_k >= self.cfg.FAILSAFE_1W) & (df_1w['K'] < self.cfg.FAILSAFE_1W)
        self.failsafe_1w = set(df_1w[fs_mask].index)

        # 1W OB85 fallback exits
        ob85_mask = (prev_k >= self.cfg.OB_FALLBACK_1W) & (df_1w['K'] < self.cfg.OB_FALLBACK_1W)
        self.ob85_exits_1w = set(df_1w[ob85_mask].index)

    def _signal_on_date(self, date, signal_set, tolerance_days=7):
        """Check if signal fired on or near this date."""
        for s in signal_set:
            if 0 <= (date - s).days <= tolerance_days:
                return s
        return None

    def _get_price(self, date):
        """Get close price at date."""
        mask = self.pack.daily.index <= date
        if not mask.any():
            return np.nan
        return self.pack.daily.loc[mask, 'close'].iloc[-1]

    # ── Position Management ──────────────────────────────────────────

    def _buy(self, date, tier_pct, tier_num):
        """Buy into markup position."""
        price = self._get_price(date)
        if np.isnan(price):
            return
        amount = self.capital * tier_pct
        if amount <= 0:
            return
        coins = amount / price
        self.position_coins += coins
        self.capital -= amount
        if self.entry_price == 0:
            self.entry_price = price
        self.tier = tier_num
        self.trades.append({
            'date': date, 'action': f'BUY_T{tier_num}', 'price': price,
            'amount': amount, 'coins': coins, 'phase': self.phase
        })

    def _sell_all(self, date, reason):
        """Sell entire markup position."""
        price = self._get_price(date)
        if np.isnan(price) or self.position_coins <= 0:
            return 0
        proceeds = self.position_coins * price
        pnl_pct = (price - self.entry_price) / self.entry_price * 100 if self.entry_price > 0 else 0
        self.capital += proceeds
        self.trades.append({
            'date': date, 'action': f'SELL_ALL ({reason})', 'price': price,
            'amount': proceeds, 'coins': self.position_coins, 'phase': self.phase,
            'pnl_pct': pnl_pct
        })
        self.position_coins = 0
        self.entry_price = 0
        self.tier = 0
        return pnl_pct

    def _open_short(self, date, pct):
        """Open short position."""
        price = self._get_price(date)
        if np.isnan(price):
            return
        amount = self.capital * pct
        if amount <= 0:
            return
        coins = amount / price
        self.short_coins = coins
        self.short_entry = price
        self.short_cost = amount
        self.capital -= amount
        self.trades.append({
            'date': date, 'action': 'SHORT_OPEN', 'price': price,
            'amount': amount, 'coins': coins, 'phase': self.phase
        })

    def _close_short(self, date, reason):
        """Close short position."""
        if self.short_coins <= 0:
            return 0
        price = self._get_price(date)
        if np.isnan(price):
            return 0
        pnl = (self.short_entry - price) * self.short_coins
        pnl_pct = (self.short_entry - price) / self.short_entry * 100
        self.capital += self.short_cost + pnl
        self.trades.append({
            'date': date, 'action': f'SHORT_CLOSE ({reason})', 'price': price,
            'amount': self.short_cost + pnl, 'coins': self.short_coins,
            'phase': self.phase, 'pnl_pct': pnl_pct
        })
        self.short_coins = 0
        self.short_entry = 0
        self.short_cost = 0
        return pnl_pct

    # ── DCA Engine ──────────────────────────────────────────────────

    def _dca_tick(self, date, price):
        """Run one DCA tick."""
        if np.isnan(price):
            return

        cfg = self.cfg
        available = self.capital * (1 - cfg.DCA_RESERVE_PCT)

        # Check TP first
        if self.dca_position_coins > 0 and self.dca_tp_target > 0:
            if price >= self.dca_tp_target:
                proceeds = self.dca_position_coins * price
                pnl = proceeds - self.dca_total_cost
                pnl_pct = pnl / self.dca_total_cost * 100
                self.capital += proceeds
                self.dca_trades += 1
                self.dca_wins += 1
                self.dca_total_pnl += pnl
                self.trades.append({
                    'date': date, 'action': f'DCA_TP ({self.dca_layers}L)',
                    'price': price, 'amount': proceeds,
                    'coins': self.dca_position_coins, 'phase': self.phase,
                    'pnl_pct': pnl_pct
                })
                self.dca_position_coins = 0
                self.dca_entry_price = 0
                self.dca_layers = 0
                self.dca_tp_target = 0
                self.dca_total_cost = 0
                self.dca_last_buy = None
                return

        # Check for new layer
        if self.dca_layers >= cfg.DCA_MAX_LAYERS:
            return
        if self.dca_last_buy and (date - self.dca_last_buy).days < 1:
            return

        should_buy = False
        if self.dca_layers == 0:
            should_buy = True
        else:
            target_drop = cfg.DCA_SO_DEVIATION * self.dca_layers
            if self.dca_entry_price > 0:
                current_drop = (self.dca_entry_price - price) / self.dca_entry_price
                if current_drop >= target_drop:
                    should_buy = True

        if should_buy:
            if self.dca_layers == 0:
                order_size = available * cfg.DCA_BO_PCT
            else:
                order_size = available * cfg.DCA_BO_PCT * (cfg.DCA_SO_MULTIPLIER ** min(self.dca_layers, 4))

            order_size = min(order_size, self.capital * 0.3)
            if order_size < 10 or order_size > self.capital:
                return

            coins = order_size / price
            self.dca_position_coins += coins
            self.capital -= order_size
            self.dca_total_cost += order_size
            self.dca_layers += 1
            self.dca_last_buy = date
            self.dca_entry_price = self.dca_total_cost / self.dca_position_coins
            self.dca_tp_target = self.dca_entry_price * (1 + cfg.DCA_TP_PCT)

            self.trades.append({
                'date': date, 'action': f'DCA_BUY_L{self.dca_layers}',
                'price': price, 'amount': order_size,
                'coins': coins, 'phase': self.phase
            })

    def _dca_close_at_market(self, date, reason):
        """HARD EXIT: Force-close all DCA positions."""
        if self.dca_position_coins <= 0:
            return
        price = self._get_price(date)
        if np.isnan(price):
            return
        proceeds = self.dca_position_coins * price
        pnl = proceeds - self.dca_total_cost
        pnl_pct = pnl / self.dca_total_cost * 100 if self.dca_total_cost > 0 else 0
        self.capital += proceeds
        self.dca_trades += 1
        if pnl > 0:
            self.dca_wins += 1
        self.dca_total_pnl += pnl
        self.trades.append({
            'date': date, 'action': f'DCA_CLOSE ({reason}, {self.dca_layers}L)',
            'price': price, 'amount': proceeds,
            'coins': self.dca_position_coins, 'phase': self.phase,
            'pnl_pct': pnl_pct
        })
        self.dca_position_coins = 0
        self.dca_entry_price = 0
        self.dca_layers = 0
        self.dca_tp_target = 0
        self.dca_total_cost = 0
        self.dca_last_buy = None

    # ── Equity ──────────────────────────────────────────────────────

    def _total_equity(self, date):
        """Total equity = cash + markup position + DCA position + short PnL."""
        price = self._get_price(date)
        if np.isnan(price):
            return self.capital
        equity = self.capital + self.position_coins * price + self.dca_position_coins * price
        if self.short_coins > 0:
            short_pnl = (self.short_entry - price) * self.short_coins
            equity += short_pnl + self.short_cost
        return equity

    # ── Phase Changes ───────────────────────────────────────────────

    def _change_phase(self, date, new_phase, reason):
        """Transition to new phase."""
        old = self.phase

        # Close short if leaving MARKDOWN
        if old == Phase.MARKDOWN and self.short_coins > 0:
            self._close_short(date, f'EXIT_MD->{new_phase}')

        self.phase = new_phase
        self.phase_start_date = date
        self.hvf_low_streak = 0  # Reset FLAT tracking
        self.phase_log.append({
            'date': date, 'from': old, 'to': new_phase, 'reason': reason,
            'equity': self._total_equity(date), 'price': self._get_price(date)
        })

        # Track completed markup cycles
        if old == Phase.MARKUP and new_phase == Phase.FLAT:
            self.markup_cycles_completed += 1
            if not self.shorts_enabled:
                self.shorts_enabled = True
                self.trades.append({
                    'date': date, 'action': f'SHORTS_ENABLED (cycle #{self.markup_cycles_completed})',
                    'price': self._get_price(date), 'amount': 0, 'coins': 0, 'phase': new_phase
                })

        # Open short when entering MARKDOWN (if enabled)
        if new_phase == Phase.MARKDOWN and self.capital > 0 and self.shorts_enabled:
            self._open_short(date, self.cfg.SHORT_PCT)

    # ── Signal Checks ───────────────────────────────────────────────

    def _check_markup_entry(self, date, price):
        """DCA → MARKUP: HH_HL + Fib_support (+ optional CFGI>40)."""
        hh_hl = self.pack.structure.hh_hl_streak(date, 2)
        if not hh_hl:
            return False

        at_fib, ratio, level = self.fib.at_fib_support(date, price)
        if not at_fib:
            return False

        # Optional CFGI gate
        cfgi = self.pack.cfgi.value_at(date)
        cfgi_ok = not np.isnan(cfgi) and cfgi > self.cfg.CFGI_MARKUP_GATE

        reason = f'HH_HL + Fib_{ratio:.3f} (${level:,.0f})'
        if cfgi_ok:
            reason += f' + CFGI={cfgi:.0f}'

        # DCA → Markup = GRACEFUL EXIT (let TPs hit naturally, don't force-close)
        self._change_phase(date, Phase.MARKUP, reason)
        self._buy(date, self.cfg.TIER1_PCT, 1)
        self.early_warning_date = None
        self.failsafe_armed = False
        self.peak_2w_k = 0
        return True

    def _check_markdown_entry(self, date, price):
        """DCA → MARKDOWN: ADX>20 + Fib_break."""
        adx = self.pack.structure.adx_at(date)
        if np.isnan(adx) or adx < self.cfg.ADX_THRESHOLD:
            return False

        broke, ratio, level = self.fib.broke_fib_support(date, price)
        if not broke:
            return False

        # HARD EXIT all DCA positions
        if self.dca_position_coins > 0:
            self._dca_close_at_market(date, 'MARKDOWN_HARD_EXIT')

        reason = f'ADX={adx:.0f} + Fib_break_{ratio:.3f} (${level:,.0f})'
        self._change_phase(date, Phase.MARKDOWN, reason)
        return True

    def _check_top_exit(self, date):
        """MARKUP → FLAT: Three-layer exit defense."""
        # Track peak 2W K
        k_2w = self.pack.stoch_2w.get_k_at(date)
        if not np.isnan(k_2w) and k_2w > self.peak_2w_k:
            self.peak_2w_k = k_2w

        # Layer 1: Early warning (1W crosses below 97)
        sig = self._signal_on_date(date, self.early_warnings_1w)
        if sig and self.early_warning_date is None:
            self.early_warning_date = date
            self.trades.append({
                'date': date, 'action': f'EARLY_WARNING_1W_97 (2W_peak={self.peak_2w_k:.0f})',
                'price': self._get_price(date), 'amount': 0, 'coins': 0, 'phase': self.phase
            })

        # Layer 2: Primary exit (2W OB93)
        sig = self._signal_on_date(date, self.ob_exits_2w)
        if sig:
            pnl = self._sell_all(date, 'PRIMARY_2W_OB93')
            if self.dca_position_coins > 0:
                self._dca_close_at_market(date, 'TOP_EXIT')
            self._change_phase(date, Phase.FLAT, f'2W OB exit th=93, pnl={pnl:+.1f}%')
            self.early_warning_date = None
            self.failsafe_armed = False
            self.peak_2w_k = 0
            return True

        # Layer 2b: Fallback (1W OB85 when 2W never reached OB)
        if self.peak_2w_k < self.cfg.OB_THRESHOLD_2W and self.early_warning_date:
            sig = self._signal_on_date(date, self.ob85_exits_1w)
            if sig:
                pnl = self._sell_all(date, 'FALLBACK_1W_OB85')
                if self.dca_position_coins > 0:
                    self._dca_close_at_market(date, 'TOP_EXIT')
                self._change_phase(date, Phase.FLAT,
                    f'1W OB85 fallback (2W peak={self.peak_2w_k:.0f}<93), pnl={pnl:+.1f}%')
                self.early_warning_date = None
                self.failsafe_armed = False
                self.peak_2w_k = 0
                return True

        # Layer 3: Failsafe (1W K<50 after armed)
        if self.early_warning_date and not self.failsafe_armed:
            weeks_since = (date - self.early_warning_date).days / 7
            if weeks_since >= self.cfg.FAILSAFE_WINDOW_WEEKS:
                self.failsafe_armed = True

        if self.failsafe_armed:
            sig = self._signal_on_date(date, self.failsafe_1w)
            if sig:
                pnl = self._sell_all(date, 'FAILSAFE_1W_K50')
                if self.dca_position_coins > 0:
                    self._dca_close_at_market(date, 'TOP_EXIT')
                self._change_phase(date, Phase.FLAT, f'Failsafe 1W K<50, pnl={pnl:+.1f}%')
                self.early_warning_date = None
                self.failsafe_armed = False
                self.peak_2w_k = 0
                return True

        return False

    def _check_flat_routing(self, date, price):
        """FLAT → DCA or MARKDOWN: HVF-driven routing."""
        hvf_score = self.hvf.score_at(date)

        # Check for direct transitions first (signals override HVF routing)
        # If markup signal fires → go to MARKUP
        hh_hl = self.pack.structure.hh_hl_streak(date, 2)
        if hh_hl:
            at_fib, ratio, level = self.fib.at_fib_support(date, price)
            if at_fib:
                self._change_phase(date, Phase.MARKUP,
                    f'FLAT->MARKUP: HH_HL + Fib_{ratio:.3f} (HVF={hvf_score:.2f})')
                self._buy(date, self.cfg.TIER1_PCT, 1)
                self.early_warning_date = None
                self.failsafe_armed = False
                self.peak_2w_k = 0
                return

        # If markdown signal fires while HVF is high → go to MARKDOWN
        if hvf_score >= self.cfg.HVF_MARKDOWN_THRESHOLD:
            adx = self.pack.structure.adx_at(date)
            if not np.isnan(adx) and adx >= self.cfg.ADX_THRESHOLD:
                broke, ratio, level = self.fib.broke_fib_support(date, price)
                if broke:
                    self._change_phase(date, Phase.MARKDOWN,
                        f'FLAT->MARKDOWN: ADX={adx:.0f} + Fib_break_{ratio:.3f} + HVF={hvf_score:.2f}')
                    return

        # HVF routing
        if hvf_score < self.cfg.HVF_SAFE_THRESHOLD:
            self.hvf_low_streak += 1
        else:
            self.hvf_low_streak = 0

        # If HVF has been low for 7+ days → safe to enter DCA
        if self.hvf_low_streak >= self.cfg.HVF_SAFE_DAYS:
            cfgi = self.pack.cfgi.value_at(date)
            self._change_phase(date, Phase.DCA,
                f'FLAT->DCA: HVF<{self.cfg.HVF_SAFE_THRESHOLD} for {self.hvf_low_streak}d (CFGI={cfgi:.0f})')

    def _check_markdown_exit(self, date, price):
        """MARKDOWN → DCA: HH_HL structure turning bullish."""
        hh_hl = self.pack.structure.hh_hl_streak(date, 2)
        if hh_hl:
            at_fib, ratio, level = self.fib.at_fib_support(date, price)
            if at_fib:
                self._change_phase(date, Phase.DCA,
                    f'MARKDOWN->DCA: HH_HL + Fib_{ratio:.3f} (${level:,.0f})')
                return

        # Fallback: 2W OS exit (cycle bottom)
        sig = self._signal_on_date(date, self.os_exits_2w)
        if sig:
            self._change_phase(date, Phase.DCA, '2W OS exit (cycle bottom)')

    def _check_markup_tiers(self, date):
        """Add T2/T3 if conditions met."""
        if self.tier >= 3 or self.phase_start_date is None:
            return
        weeks_in = (date - self.phase_start_date).days / 7
        price = self._get_price(date)

        if self.tier == 1 and weeks_in >= self.cfg.TIER2_DELAY_WEEKS:
            cfgi = self.pack.cfgi.value_at(date)
            if (not np.isnan(price) and self.entry_price > 0 and
                price >= self.entry_price and
                not np.isnan(cfgi) and cfgi > 40):
                self._buy(date, self.cfg.TIER2_PCT, 2)

        elif self.tier == 2 and weeks_in >= self.cfg.TIER3_DELAY_WEEKS:
            adx = self.pack.structure.adx_at(date)
            hh = self.pack.structure.hh_hl_streak(date, 1)
            if (not np.isnan(price) and self.entry_price > 0 and
                price >= self.entry_price and
                not np.isnan(adx) and adx > 25 and hh):
                self._buy(date, self.cfg.TIER3_PCT, 3)

    # ── Main Loop ───────────────────────────────────────────────────

    def run(self):
        """Run the backtest."""
        daily = self.pack.daily
        start = pd.Timestamp(self.cfg.START_DATE)
        end = pd.Timestamp(self.cfg.END_DATE)

        test_data = daily[(daily.index >= start) & (daily.index <= end)]
        if len(test_data) == 0:
            print(f"  No data for {self.coin} in test period")
            return None

        self.phase = Phase.DCA
        self.phase_start_date = test_data.index[0]
        self.phase_log.append({
            'date': test_data.index[0], 'from': None, 'to': Phase.DCA,
            'reason': 'START', 'equity': self.cfg.CAPITAL,
            'price': test_data['close'].iloc[0]
        })

        for i, (date, row) in enumerate(test_data.iterrows()):
            price = row['close']
            equity = self._total_equity(date)
            self.equity_curve.append({
                'date': date, 'equity': equity, 'price': price, 'phase': self.phase
            })

            # Min hold time
            if self.phase_start_date and (date - self.phase_start_date).days < self.cfg.MIN_PHASE_WEEKS * 7:
                # Still run DCA ticks during hold period
                if self.phase == Phase.DCA:
                    self._dca_tick(date, price)
                elif self.phase == Phase.MARKUP and self.dca_position_coins > 0:
                    self._dca_tick(date, price)
                continue

            if self.phase == Phase.DCA:
                self._dca_tick(date, price)
                # Check transitions (markup first, then markdown)
                if not self._check_markup_entry(date, price):
                    self._check_markdown_entry(date, price)

            elif self.phase == Phase.MARKUP:
                # Let DCA TPs hit naturally (graceful)
                if self.dca_position_coins > 0:
                    self._dca_tick(date, price)
                if not self._check_top_exit(date):
                    self._check_markup_tiers(date)

            elif self.phase == Phase.FLAT:
                self._check_flat_routing(date, price)

            elif self.phase == Phase.MARKDOWN:
                self._check_markdown_exit(date, price)

        # Close open positions at end
        if self.position_coins > 0:
            self._sell_all(test_data.index[-1], 'BACKTEST_END')
        if self.dca_position_coins > 0:
            self._dca_close_at_market(test_data.index[-1], 'BACKTEST_END')
        if self.short_coins > 0:
            self._close_short(test_data.index[-1], 'BACKTEST_END')

        return self._results()

    def _results(self):
        """Compute results."""
        if not self.equity_curve:
            return None

        eq = pd.DataFrame(self.equity_curve)
        eq.set_index('date', inplace=True)

        final_equity = eq['equity'].iloc[-1]
        roi = (final_equity - self.cfg.CAPITAL) / self.cfg.CAPITAL * 100

        peak = eq['equity'].expanding().max()
        dd = (eq['equity'] - peak) / peak * 100
        max_dd = dd.min()

        phase_changes = len(self.phase_log) - 1
        total = len(self.equity_curve)
        time_in = {p: sum(1 for e in self.equity_curve if e['phase'] == p) for p in
                   [Phase.DCA, Phase.MARKUP, Phase.FLAT, Phase.MARKDOWN]}

        trades_with_pnl = [t for t in self.trades if 'pnl_pct' in t]
        wins = [t for t in trades_with_pnl if t['pnl_pct'] > 0]
        losses = [t for t in trades_with_pnl if t['pnl_pct'] <= 0]

        start_price = eq['price'].iloc[0]
        end_price = eq['price'].iloc[-1]
        bh_return = (end_price - start_price) / start_price * 100

        return {
            'coin': self.coin,
            'start': eq.index[0], 'end': eq.index[-1],
            'capital': self.cfg.CAPITAL,
            'final_equity': final_equity,
            'roi': roi, 'max_drawdown': max_dd,
            'buy_hold_return': bh_return,
            'outperformance': roi - bh_return,
            'phase_changes': phase_changes,
            'time_markup_pct': time_in[Phase.MARKUP] / total * 100,
            'time_dca_pct': time_in[Phase.DCA] / total * 100,
            'time_flat_pct': time_in[Phase.FLAT] / total * 100,
            'time_markdown_pct': time_in[Phase.MARKDOWN] / total * 100,
            'total_trades': len(self.trades),
            'closed_trades': len(trades_with_pnl),
            'wins': len(wins), 'losses': len(losses),
            'win_rate': len(wins) / len(trades_with_pnl) * 100 if trades_with_pnl else 0,
            'avg_win': np.mean([t['pnl_pct'] for t in wins]) if wins else 0,
            'avg_loss': np.mean([t['pnl_pct'] for t in losses]) if losses else 0,
            'dca_trades': self.dca_trades, 'dca_wins': self.dca_wins,
            'dca_total_pnl': self.dca_total_pnl,
            'equity_curve': eq, 'trades': self.trades, 'phases': self.phase_log,
        }


# ── Runner ─────────────────────────────────────────────────────────────

def print_results(r):
    if r is None:
        return
    print(f"\n  {r['coin']} Results:")
    print(f"  {'-' * 50}")
    print(f"  ROI:              {r['roi']:+.1f}%")
    print(f"  Buy & Hold:       {r['buy_hold_return']:+.1f}%")
    print(f"  Alpha:            {r['outperformance']:+.1f}%")
    print(f"  Max Drawdown:     {r['max_drawdown']:.1f}%")
    print(f"  Final Equity:     ${r['final_equity']:,.0f}")
    print(f"  Phase Changes:    {r['phase_changes']}")
    print(f"  Time MARKUP:      {r['time_markup_pct']:.0f}%")
    print(f"  Time DCA:         {r['time_dca_pct']:.0f}%")
    print(f"  Time FLAT:        {r['time_flat_pct']:.0f}%")
    print(f"  Time MARKDOWN:    {r['time_markdown_pct']:.0f}%")
    print(f"  Closed Trades:    {r['closed_trades']} ({r['wins']}W / {r['losses']}L, {r['win_rate']:.0f}%)")
    if r['wins']:
        print(f"  Avg Win:          {r['avg_win']:+.1f}%")
    if r['losses']:
        print(f"  Avg Loss:         {r['avg_loss']:+.1f}%")
    if r['dca_trades'] > 0:
        print(f"  DCA Trades:       {r['dca_trades']} ({r['dca_wins']}W, ${r['dca_total_pnl']:+,.0f})")

    print(f"\n  Phase Timeline:")
    for p in r['phases']:
        print(f"    {p['date'].date()}: {p['from'] or 'START'} -> {p['to']} | {p['reason']} | eq=${p['equity']:,.0f}")

    print(f"\n  Key Trades:")
    for t in r['trades']:
        extra = f" pnl={t['pnl_pct']:+.1f}%" if 'pnl_pct' in t else ""
        if any(k in t['action'] for k in ['BUY_T', 'SELL_ALL', 'SHORT', 'DCA_CLOSE', 'DCA_TP', 'EARLY', 'ENABLED']):
            print(f"    {t['date'].date()}: {t['action']} @ ${t['price']:,.2f} (${t['amount']:,.0f}){extra}")


def main():
    print("=" * 80)
    print("  V13 PHASE-RIDING BACKTEST v8")
    print("  Signal-driven: HH_HL+Fib (markup), ADX+Fib (markdown), HVF routing (flat)")
    print("  Top detection: 2W OB93 / 1W OB85 fallback / 1W K<50 failsafe")
    print("  Period: Oct 2024 -> Feb 2026 (one full cycle)")
    print("  Coins: BTC, ETH, SOL")
    print("=" * 80)

    config = V8Config()

    print(f"\n  Configuration:")
    print(f"  {'-' * 40}")
    print(f"  Start:        {config.START_DATE}")
    print(f"  End:          {config.END_DATE}")
    print(f"  Capital:      ${config.CAPITAL:,}")
    print(f"  Tiers:        T1={config.TIER1_PCT:.0%} T2={config.TIER2_PCT:.0%} T3={config.TIER3_PCT:.0%} Reserve=10%")
    print(f"  Short alloc:  {config.SHORT_PCT:.0%}")
    print(f"  DCA:          {config.DCA_BO_PCT:.0%} BO, {config.DCA_SO_MULTIPLIER}x mult, {config.DCA_TP_PCT:.1%} TP, {config.DCA_MAX_LAYERS} layers")
    print(f"  MARKUP entry: HH_HL + Fib_support (CFGI>{config.CFGI_MARKUP_GATE} optional)")
    print(f"  MARKDOWN entry: ADX>{config.ADX_THRESHOLD} + Fib_break")
    print(f"  Top exit:     2W OB{config.OB_THRESHOLD_2W} / 1W OB{config.OB_FALLBACK_1W} fallback / 1W K<{config.FAILSAFE_1W} failsafe")
    print(f"  FLAT routing: HVF>{config.HVF_MARKDOWN_THRESHOLD} stay flat, HVF<{config.HVF_SAFE_THRESHOLD} for {config.HVF_SAFE_DAYS}d -> DCA")

    coins = ['BTC', 'ETH', 'SOL']
    all_results = []

    for coin in coins:
        print(f"\n{'=' * 60}")
        print(f"  Loading {coin}...")
        try:
            pack = V13SignalPack(coin)
        except ValueError as e:
            print(f"  SKIP: {e}")
            continue

        bt = V13BacktestV8(pack, config)
        result = bt.run()
        if result:
            print_results(result)
            all_results.append(result)

    if all_results:
        print(f"\n{'=' * 80}")
        print(f"  PORTFOLIO SUMMARY")
        print(f"{'=' * 80}")
        avg_roi = np.mean([r['roi'] for r in all_results])
        avg_bh = np.mean([r['buy_hold_return'] for r in all_results])
        avg_dd = np.mean([r['max_drawdown'] for r in all_results])
        worst_dd = min(r['max_drawdown'] for r in all_results)

        print(f"  Avg ROI:          {avg_roi:+.1f}% (vs B&H {avg_bh:+.1f}%)")
        print(f"  Avg Alpha:        {avg_roi - avg_bh:+.1f}%")
        print(f"  Avg Max DD:       {avg_dd:.1f}%")
        print(f"  Worst DD:         {worst_dd:.1f}%")

        print(f"\n  {'Coin':<6} {'ROI':>8} {'B&H':>8} {'Alpha':>8} {'MaxDD':>8} {'Phases':>8}")
        print(f"  {'-'*48}")
        for r in all_results:
            print(f"  {r['coin']:<6} {r['roi']:>+7.1f}% {r['buy_hold_return']:>+7.1f}% "
                  f"{r['outperformance']:>+7.1f}% {r['max_drawdown']:>7.1f}% {r['phase_changes']:>8}")


if __name__ == '__main__':
    main()
