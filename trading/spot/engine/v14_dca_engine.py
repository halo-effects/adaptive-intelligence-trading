import os
"""
V14 DCA-Only Engine — Signal-Directed Continuous DCA

Architecture:
  - Three phases: LONG_DCA, SHORT_DCA, ROUTER (transition/evaluation)
  - ROUTER v2 signal stack decides direction (top/bottom detection)
  - DCA grids execute with full capital in one direction
  - Graceful unwinding: early signals stop new deals, let TPs hit
  - Direction confirmation: switch to opposite DCA mode

Signal Stack (inherited from V13 ROUTER v2):
  Bottom: 3D death cross + 2W K>=5 + conviction score >=3/4
  Top: OB93 arm -> 2D divergence (35d timeout) + fallback layers

DCA Parameters (from V13 sweep results):
  Timeframe: 1h (dominates 15m on all coins)
  TP: 1.5%, Deviation: 2.5%, SO Mult: 2.5x, Max 8 layers

Base: Cloned from v13_router_engine_v2.py
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict

from .v13_signals import V13SignalPack
from .v13_router_engine_v1 import (
    V13Config as V13ConfigBase, compute_fib_levels, FIB_RATIOS, FIB_TOLERANCE,
    price_near_fib_support, price_broke_fib_support
)
from .v13_router_engine_v2 import HybridDetector2D
from ._steve_3check import Steve3CheckDetector

import sqlite3

DB_PATH = Path(os.environ.get('AIT_CANDLES_DB', str(Path(__file__).resolve().parent.parent / 'data' / 'candles.db')))


# -- Phase State -------------------------------------------------------------

class Phase:
    LONG_DCA = 'LONG_DCA'
    SHORT_DCA = 'SHORT_DCA'
    ROUTER = 'ROUTER'


# -- Configuration -----------------------------------------------------------

class V14Config:
    """V14 DCA-only configuration."""

    # -- DCA Grid Parameters --
    DCA_TP_PCT = 0.015           # 1.5% take profit (cycling mode only)
    DCA_SO_DEVIATION = 0.025     # 2.5% between safety orders
    DCA_SO_MULTIPLIER = 1.5      # 1.5x volume per layer
    DCA_BO_PCT = 0.30            # 30% base order (aggressive initial deployment)
    DCA_MAX_LAYERS = 8           # Max safety orders
    DCA_ACCUMULATE = True        # True = hold position (no TP), exit on signal
                                 # False = cycle TP profits (original DCA grid)

    # -- Top Detection (StochRSI) -- inherited from V13 --
    OB_THRESHOLD_2W = 93
    EARLY_WARNING_1W = 97
    FAILSAFE_1W = 50
    FAILSAFE_WINDOW_WEEKS = 2
    OB_FALLBACK_1W = 85

    # -- Phase Transition Signals -- inherited from V13 --
    HH_HL_LOOKBACK = 2
    ADX_THRESHOLD = 20
    SMA200_OVEREXTENSION = 20
    PHASE_ADX_RANGING = 20
    PHASE_ADX_SUSTAINED_DAYS = 21
    MARKUP_FAIL_DD_PCT = 0.25
    MARKUP_FAIL_ADX = 25

    # -- ROUTER Evaluation --
    ROUTER_MIN_EVAL_DAYS = 14
    ROUTER_MAX_EVAL_DAYS = 42
    ROUTER_ADX_RANGING = 20
    ROUTER_ADX_SUSTAINED_DAYS = 14
    HVF_LOOKBACK = 44

    # -- Top Detection: OB93 arm -> divergence --
    TOP_DIVERGENCE_TIMEOUT = 35  # Days to wait for divergence after OB93

    # -- Bottom Conviction --
    CONVICTION_MIN_SCORE = 3     # 3 of 4 signals required

    # -- Capital --
    CAPITAL = 10000
    START_DATE = '2024-10-01'
    END_DATE = '2026-02-28'

    # -- DCA Capital Utilization --
    DCA_CAPITAL_PCT = 0.90       # Use 90% of capital for DCA grid (10% reserve)

    # -- Leverage & Liquidation --
    LEVERAGE = 1.0               # Default 1x for backtest (wrapper overrides)
    MAINTENANCE_MARGIN = 0.005   # 0.5% maintenance margin (Hyperliquid isolated)

    # -- Trading Fees (Hyperliquid perps) --
    MAKER_FEE = 0.0002           # 0.02% — limit orders (DCA entries, TP closes)
    TAKER_FEE = 0.0005           # 0.05% — market orders (emergency/phase closes, liquidations)


# -- V14 DCA Engine ----------------------------------------------------------

class V14DCAEngine:
    """V14 DCA-Only Engine: Signal-directed continuous DCA with full capital."""

    def __init__(self, pack: V13SignalPack, config: V14Config = None,
                 initial_phase: str = 'LONG_DCA'):
        self.pack = pack
        self.cfg = config or V14Config()
        self.coin = pack.coin
        self.daily = pack.daily
        self.live_mode = False  # Set True by live bots; disables paper-trading caps

        # -- Phase State --
        self.phase = Phase.LONG_DCA if initial_phase == 'LONG_DCA' else Phase.SHORT_DCA
        self.capital = self.cfg.CAPITAL
        self.phase_start_date = None

        # -- Long DCA Grid --
        self.long_coins = 0.0
        self.long_avg_entry = 0.0
        self.long_layers = 0
        self.long_last_buy = None
        self.long_tp = 0.0
        self.long_cost = 0.0
        self.long_trades = 0
        self.long_wins = 0
        self.long_pnl = 0.0

        # -- Short DCA Grid --
        self.short_coins = 0.0
        self.short_avg_entry = 0.0
        self.short_layers = 0
        self.short_last_sell = None
        self.short_tp = 0.0
        self.short_cost = 0.0
        self.short_trades = 0
        self.short_wins = 0
        self.short_pnl = 0.0

        # -- Top Detection State --
        self.early_warning_date = None
        self.failsafe_armed = False
        self.peak_2w_k = 0.0
        self.ob93_armed = False
        self.ob93_armed_date = None
        self.unwinding = False  # Graceful unwind mode (stop new deals)

        # -- Bottom Detection State --
        self.top_detected = False
        self.conviction_fired = False

        # -- Cycle Tracking --
        self.markup_cycles_completed = 0  # Track if shorts should be enabled
        self.adx_below_20_streak = 0

        # -- ROUTER routing state --
        self.router_from_top = False
        self.router_from_markdown = False

        # -- Conviction detector --
        self.detector = HybridDetector2D(
            pack.coin, exhaustion_k_min=5.0,
            exhaustion_tf='2W', exhaustion_mode='k_lift'
        )
        self.div_dates = self.detector.compute_2d_divergence_dates()

        # -- Fee Tracking --
        self.total_fees = 0.0

        # -- Liquidation Tracking --
        self.liquidation_events = 0
        self.max_position_dd_pct = 0.0   # Worst unrealized loss as % of position
        self.min_distance_to_liq_pct = float('inf')  # Closest approach to liquidation

        # -- Logging --
        self.trades = []
        self.phase_log = []
        self.equity_curve = []
        self.conviction_triggers = []
        self.top_triggers = []

        # -- Precompute signals --
        self._precompute_stoch()

    def _precompute_stoch(self):
        """Precompute StochRSI signal dates."""
        s2w = self.pack.stoch_2w
        s1w = self.pack.stoch_1w
        self.ob_exits_2w = set(s2w.ob_exits(self.cfg.OB_THRESHOLD_2W).index)

        # 1W cross-below signals (computed from raw K series)
        df_1w = s1w.df
        prev = df_1w['K'].shift(1)
        self.early_warnings_1w = set(
            df_1w[(prev >= self.cfg.EARLY_WARNING_1W) & (df_1w['K'] < self.cfg.EARLY_WARNING_1W)].index)
        self.failsafe_1w = set(
            df_1w[(prev >= self.cfg.FAILSAFE_1W) & (df_1w['K'] < self.cfg.FAILSAFE_1W)].index)
        self.ob85_1w = set(
            df_1w[(prev >= self.cfg.OB_FALLBACK_1W) & (df_1w['K'] < self.cfg.OB_FALLBACK_1W)].index)

    def _signal_near(self, date, signal_set, window=3):
        """Check if a signal fired within window days of date."""
        for d in range(-window, window + 1):
            check = date + pd.Timedelta(days=d)
            if check in signal_set:
                return True
        return False

    def _price(self, date):
        """Get daily close price (always returns scalar)."""
        if date in self.daily.index:
            val = self.daily.loc[date, 'close']
            if isinstance(val, pd.Series):
                val = val.iloc[-1]
            return float(val)
        prior = self.daily.index[self.daily.index <= date]
        if len(prior):
            val = self.daily.loc[prior[-1], 'close']
            if isinstance(val, pd.Series):
                val = val.iloc[-1]
            return float(val)
        return np.nan

    def _change_phase(self, date, new_phase, reason=''):
        """Change phase with logging."""
        old = self.phase
        self.phase = new_phase
        self.phase_start_date = date
        self.adx_below_20_streak = 0
        self.phase_log.append({
            'date': date, 'from': old, 'to': new_phase, 'reason': reason
        })

    # =========================================================================
    #  FEE HELPER
    # =========================================================================

    def _charge_fee(self, trade_value, is_taker=False):
        """Deduct trading fee from capital. Returns fee amount."""
        rate = self.cfg.TAKER_FEE if is_taker else self.cfg.MAKER_FEE
        fee = trade_value * rate
        self.capital -= fee
        self.total_fees += fee
        return fee

    # =========================================================================
    #  LIQUIDATION
    # =========================================================================

    def _calc_liquidation_price(self, side, avg_entry):
        """Calculate liquidation price (Hyperliquid isolated margin model).
        Returns None if leverage <= 1.0 (no liquidation possible at 1x)."""
        lev = self.cfg.LEVERAGE
        if lev <= 1.0 or avg_entry <= 0:
            return None
        mm = self.cfg.MAINTENANCE_MARGIN
        if side == 'long':
            return avg_entry * (1 - (1.0 / lev) + mm)
        else:  # short
            return avg_entry * (1 + (1.0 / lev) - mm)

    def _check_liquidation(self, date, price):
        """Check if price has crossed liquidation price. Force-close if so."""
        lev = self.cfg.LEVERAGE
        if lev <= 1.0:
            return

        # Check long position
        if self.long_coins > 0 and self.long_avg_entry > 0:
            liq = self._calc_liquidation_price('long', self.long_avg_entry)
            if liq is not None:
                dist_pct = (price - liq) / price * 100
                if dist_pct < self.min_distance_to_liq_pct:
                    self.min_distance_to_liq_pct = dist_pct
                # Track position drawdown
                dd_pct = (self.long_avg_entry - price) / self.long_avg_entry * 100
                if dd_pct > self.max_position_dd_pct:
                    self.max_position_dd_pct = dd_pct
                # Liquidation check
                if price <= liq:
                    self.liquidation_events += 1
                    # Force close at liquidation price (total loss of margin)
                    self.capital += 0  # Margin is lost
                    self.trades.append({
                        'date': date, 'action': f'LONG_LIQUIDATED (liq={liq:.2f})',
                        'price': liq, 'amount': 0, 'coins': self.long_coins,
                        'phase': self.phase, 'pnl_pct': -100
                    })
                    self.long_pnl -= self.long_cost
                    self.long_trades += 1
                    self.long_coins = 0
                    self.long_avg_entry = 0
                    self.long_layers = 0
                    self.long_tp = 0
                    self.long_cost = 0
                    self.long_last_buy = None

        # Check short position
        if self.short_coins > 0 and self.short_avg_entry > 0:
            liq = self._calc_liquidation_price('short', self.short_avg_entry)
            if liq is not None:
                dist_pct = (liq - price) / price * 100
                if dist_pct < self.min_distance_to_liq_pct:
                    self.min_distance_to_liq_pct = dist_pct
                # Track position drawdown
                dd_pct = (price - self.short_avg_entry) / self.short_avg_entry * 100
                if dd_pct > self.max_position_dd_pct:
                    self.max_position_dd_pct = dd_pct
                # Liquidation check
                if price >= liq:
                    self.liquidation_events += 1
                    self.capital += 0  # Margin is lost
                    self.trades.append({
                        'date': date, 'action': f'SHORT_LIQUIDATED (liq={liq:.2f})',
                        'price': liq, 'amount': 0, 'coins': self.short_coins,
                        'phase': self.phase, 'pnl_pct': -100
                    })
                    self.short_pnl -= self.short_cost
                    self.short_trades += 1
                    self.short_coins = 0
                    self.short_avg_entry = 0
                    self.short_layers = 0
                    self.short_tp = 0
                    self.short_cost = 0
                    self.short_last_sell = None

    # =========================================================================
    #  LONG DCA GRID
    # =========================================================================

    def _long_dca_tick(self, date, price, high=None):
        """Process one tick of the long DCA grid.
        
        Args:
            high: Candle high price. When provided, TP is checked against the high
                  (simulating a limit sell order that fills on any wick touch).
                  Falls back to close price if not provided (backward compat).
        """
        if np.isnan(price):
            return
        available = self.capital * self.cfg.DCA_CAPITAL_PCT
        cfg = self.cfg

        # Check TP first (skip in accumulate mode — hold position for signal-based exit)
        # Use candle high for TP check: a limit sell order on the book fills when
        # price touches it, even on a wick. Fill price = TP level (limit order).
        tp_check_price = high if high is not None and not np.isnan(high) else price
        if not cfg.DCA_ACCUMULATE and self.long_coins > 0 and self.long_tp > 0 and tp_check_price >= self.long_tp:
            # Fill at TP price (limit order), not at candle high
            fill_price = self.long_tp
            proceeds = self.long_coins * fill_price
            fee = self._charge_fee(proceeds, is_taker=False)  # TP = maker/limit
            pnl = proceeds - self.long_cost - fee
            pnl_pct = pnl / self.long_cost * 100 if self.long_cost > 0 else 0
            self.capital += proceeds
            self.long_trades += 1
            self.long_wins += 1
            self.long_pnl += pnl
            self.trades.append({
                'date': date, 'action': f'LONG_DCA_TP ({self.long_layers}L)',
                'price': fill_price, 'amount': proceeds, 'coins': self.long_coins,
                'phase': self.phase, 'pnl_pct': pnl_pct, 'pnl': pnl, 'fee': fee
            })
            self.long_coins = 0
            self.long_avg_entry = 0
            self.long_layers = 0
            self.long_tp = 0
            self.long_cost = 0
            self.long_last_buy = None
            return

        # Don't open new deals if unwinding
        if self.unwinding:
            return

        if self.long_layers >= cfg.DCA_MAX_LAYERS:
            return
        should_buy = False
        if self.long_layers == 0:
            should_buy = True
        elif self.long_avg_entry > 0:
            target_drop = cfg.DCA_SO_DEVIATION * self.long_layers
            current_drop = (self.long_avg_entry - price) / self.long_avg_entry
            if current_drop >= target_drop:
                should_buy = True

        if should_buy:
            if self.long_layers == 0:
                order = available * cfg.DCA_BO_PCT
            else:
                order = available * cfg.DCA_BO_PCT * (cfg.DCA_SO_MULTIPLIER ** min(self.long_layers, 4))
            # 30% cap REMOVED (2026-04-10): Was paper-only and completely inverted
            # the Martingale multiplier — deeper layers got SMALLER instead of larger,
            # making paper results non-representative of live bot behavior.
            # Cap at remaining capital (2026-04-11): Deploy whatever's left instead
            # of blocking entirely when order exceeds capital.
            order = min(order, self.capital)
            if order < 10:
                return
            if price <= 0:
                return

            coins = order / price
            fee = self._charge_fee(order, is_taker=False)  # DCA entry = maker/limit
            self.long_coins += coins
            self.capital -= order
            self.long_cost += order
            self.long_layers += 1
            self.long_last_buy = date
            self.long_avg_entry = self.long_cost / self.long_coins
            self.long_tp = self.long_avg_entry * (1 + cfg.DCA_TP_PCT)
            self.trades.append({
                'date': date, 'action': f'LONG_DCA_BUY_L{self.long_layers}',
                'price': price, 'amount': order, 'coins': coins, 'phase': self.phase,
                'fee': fee
            })

    def _long_dca_close(self, date, reason):
        """Force close all long DCA positions."""
        if self.long_coins <= 0:
            return 0
        price = self._price(date)
        if np.isnan(price):
            return 0
        proceeds = self.long_coins * price
        fee = self._charge_fee(proceeds, is_taker=True)  # Emergency/phase close = taker/market
        pnl = proceeds - self.long_cost - fee
        pnl_pct = pnl / self.long_cost * 100 if self.long_cost > 0 else 0
        self.capital += proceeds
        self.long_trades += 1
        if pnl > 0:
            self.long_wins += 1
        self.long_pnl += pnl
        self.trades.append({
            'date': date, 'action': f'LONG_DCA_CLOSE ({reason})',
            'price': price, 'amount': proceeds, 'coins': self.long_coins,
            'phase': self.phase, 'pnl_pct': pnl_pct, 'pnl': pnl, 'fee': fee
        })
        self.long_coins = 0
        self.long_avg_entry = 0
        self.long_layers = 0
        self.long_tp = 0
        self.long_cost = 0
        self.long_last_buy = None
        return pnl_pct

    # =========================================================================
    #  SHORT DCA GRID
    # =========================================================================

    def _short_dca_tick(self, date, price, low=None):
        """Process one tick of the short DCA grid.
        Mirror of long grid: sell high, buy back low.
        
        Args:
            low: Candle low price. When provided, TP is checked against the low
                 (simulating a limit buy-back order that fills on any wick touch).
                 Falls back to close price if not provided (backward compat).
        """
        if np.isnan(price):
            return
        available = self.capital * self.cfg.DCA_CAPITAL_PCT
        cfg = self.cfg

        # Check TP first (skip in accumulate mode — hold for signal-based exit)
        # Use candle low for short TP check: a limit buy-back order fills when
        # price drops to the TP level, even on a wick. Fill price = TP level.
        tp_check_price = low if low is not None and not np.isnan(low) else price
        if not cfg.DCA_ACCUMULATE and self.short_coins > 0 and self.short_tp > 0 and tp_check_price <= self.short_tp:
            # Buy back at TP price (limit order), not at candle low
            fill_price = self.short_tp
            buy_cost = self.short_coins * fill_price
            fee = self._charge_fee(buy_cost, is_taker=False)  # TP = maker/limit
            pnl = self.short_cost - buy_cost - fee  # Sold high, bought low, minus fee
            pnl_pct = pnl / self.short_cost * 100 if self.short_cost > 0 else 0
            self.capital += self.short_cost + pnl  # Return collateral + profit (fee already deducted)
            self.short_trades += 1
            self.short_wins += 1
            self.short_pnl += pnl
            self.trades.append({
                'date': date, 'action': f'SHORT_DCA_TP ({self.short_layers}L)',
                'price': fill_price, 'amount': buy_cost, 'coins': self.short_coins,
                'phase': self.phase, 'pnl_pct': pnl_pct, 'pnl': pnl, 'fee': fee
            })
            self.short_coins = 0
            self.short_avg_entry = 0
            self.short_layers = 0
            self.short_tp = 0
            self.short_cost = 0
            self.short_last_sell = None
            return

        # Don't open new deals if unwinding
        if self.unwinding:
            return

        if self.short_layers >= cfg.DCA_MAX_LAYERS:
            return
        should_sell = False
        if self.short_layers == 0:
            should_sell = True
        elif self.short_avg_entry > 0:
            # For shorts: price must RISE above avg entry by deviation amount
            target_rise = cfg.DCA_SO_DEVIATION * self.short_layers
            current_rise = (price - self.short_avg_entry) / self.short_avg_entry
            if current_rise >= target_rise:
                should_sell = True

        if should_sell:
            if self.short_layers == 0:
                order = available * cfg.DCA_BO_PCT
            else:
                order = available * cfg.DCA_BO_PCT * (cfg.DCA_SO_MULTIPLIER ** min(self.short_layers, 4))
            # 30% cap REMOVED (2026-04-10): See long side comment.
            # Cap at remaining capital (2026-04-11): See long side comment.
            order = min(order, self.capital)
            if order < 10:
                return
            if price <= 0:
                return

            coins = order / price
            fee = self._charge_fee(order, is_taker=False)  # DCA entry = maker/limit
            self.short_coins += coins
            self.capital -= order  # Collateral locked
            self.short_cost += order
            self.short_layers += 1
            self.short_last_sell = date
            self.short_avg_entry = self.short_cost / self.short_coins
            self.short_tp = self.short_avg_entry * (1 - cfg.DCA_TP_PCT)
            self.trades.append({
                'date': date, 'action': f'SHORT_DCA_SELL_L{self.short_layers}',
                'price': price, 'amount': order, 'coins': coins, 'phase': self.phase,
                'fee': fee
            })

    def _short_dca_close(self, date, reason):
        """Force close all short DCA positions."""
        if self.short_coins <= 0:
            return 0
        price = self._price(date)
        if np.isnan(price):
            return 0
        buy_cost = self.short_coins * price
        fee = self._charge_fee(buy_cost, is_taker=True)  # Emergency/phase close = taker/market
        pnl = self.short_cost - buy_cost - fee
        pnl_pct = pnl / self.short_cost * 100 if self.short_cost > 0 else 0
        self.capital += self.short_cost + pnl
        self.short_trades += 1
        if pnl > 0:
            self.short_wins += 1
        self.short_pnl += pnl
        self.trades.append({
            'date': date, 'action': f'SHORT_DCA_CLOSE ({reason})',
            'price': price, 'amount': self.short_cost + pnl, 'coins': self.short_coins,
            'phase': self.phase, 'pnl_pct': pnl_pct, 'pnl': pnl, 'fee': fee
        })
        self.short_coins = 0
        self.short_avg_entry = 0
        self.short_layers = 0
        self.short_tp = 0
        self.short_cost = 0
        self.short_last_sell = None
        return pnl_pct

    # =========================================================================
    #  SIGNAL COMPUTATION
    # =========================================================================

    def _compute_signals(self, date, price):
        """Compute all routing signals for this tick."""
        signals = {}

        # Days in phase
        signals['days_in_phase'] = (date - self.phase_start_date).days if self.phase_start_date else 0

        # Structure signals (booleans)
        signals['hh_hl'] = self.pack.structure.hh_hl_streak(date, self.cfg.HH_HL_LOOKBACK)
        signals['lh_ll'] = self.pack.structure.lh_ll_streak(date, self.cfg.HH_HL_LOOKBACK)

        # ADX
        signals['adx'] = self.pack.structure.adx_at(date)

        # Fibonacci
        signals['fib_levels'] = compute_fib_levels(self.daily, date)
        signals['fib_support'] = price_near_fib_support(price, signals['fib_levels'])
        signals['fib_break'] = price_broke_fib_support(price, signals['fib_levels'])

        # StochRSI signals
        signals['ob_2w_93'] = self._signal_near(date, self.ob_exits_2w)
        signals['ob_1w_85'] = self._signal_near(date, self.ob85_1w)
        signals['early_warning_1w'] = self._signal_near(date, self.early_warnings_1w)
        signals['failsafe_1w'] = self._signal_near(date, self.failsafe_1w)

        # CFGI
        signals['cfgi'] = self.pack.cfgi.value_at(date)

        return signals

    # =========================================================================
    #  TOP DETECTION (during LONG_DCA)
    # =========================================================================

    def _check_top_signals(self, date, price, signals):
        """Check for top signals during LONG_DCA. Returns True if direction should switch."""
        # Track peak 2W K
        k_2w = self.pack.stoch_2w.get_k_at(date)
        if not np.isnan(k_2w) and k_2w > self.peak_2w_k:
            self.peak_2w_k = k_2w

        # Layer 1: Early warning — start unwinding
        if signals['early_warning_1w'] and self.early_warning_date is None:
            self.early_warning_date = date
            self.unwinding = True
            self.trades.append({
                'date': date, 'action': f'EARLY_WARNING_UNWIND (2W_peak={self.peak_2w_k:.0f})',
                'price': price, 'amount': 0, 'coins': 0, 'phase': self.phase
            })

        # Layer 2: OB93 — arm top detection
        if not self.ob93_armed and signals['ob_2w_93']:
            self.ob93_armed = True
            self.ob93_armed_date = date
            self.unwinding = True  # Also start unwinding on OB93
            self.trades.append({
                'date': date, 'action': f'OB93_ARMED (unwinding, {self.cfg.TOP_DIVERGENCE_TIMEOUT}d timeout)',
                'price': price, 'amount': 0, 'coins': 0, 'phase': self.phase
            })

        # Layer 2 continued: divergence or timeout while armed
        if self.ob93_armed:
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            days_armed = (date - self.ob93_armed_date).days
            has_div = date_str in self.div_dates
            timeout = days_armed >= self.cfg.TOP_DIVERGENCE_TIMEOUT

            if has_div or timeout:
                reason = 'DIVERGENCE' if has_div else f'TIMEOUT_{days_armed}d'
                self.top_triggers.append({
                    'date': date, 'coin': self.coin, 'reason': reason,
                    'days_armed': days_armed, 'price': price
                })
                # Close any remaining long DCA positions
                self._long_dca_close(date, f'TOP_OB93+{reason}')
                self._reset_top_state()
                self.top_detected = True
                self.conviction_fired = False
                self._change_phase(date, Phase.SHORT_DCA, f'Top confirmed: OB93+{reason}')
                self.markup_cycles_completed += 1
                return True

        # Layers 2b-5 only if NOT armed
        if not self.ob93_armed:
            # Layer 2b: Fallback — 1W OB85
            if self.peak_2w_k < self.cfg.OB_THRESHOLD_2W and self.early_warning_date:
                if signals['ob_1w_85']:
                    self._long_dca_close(date, 'TOP_FALLBACK_OB85')
                    self._reset_top_state()
                    self.top_detected = True
                    self.conviction_fired = False
                    self._change_phase(date, Phase.SHORT_DCA, f'Top fallback: 1W OB85')
                    self.markup_cycles_completed += 1
                    return True

            # Layer 3: Failsafe — 1W K<50
            if self.early_warning_date and not self.failsafe_armed:
                if (date - self.early_warning_date).days >= self.cfg.FAILSAFE_WINDOW_WEEKS * 7:
                    self.failsafe_armed = True
            if self.failsafe_armed and signals['failsafe_1w']:
                self._long_dca_close(date, 'TOP_FAILSAFE_K50')
                self._reset_top_state()
                self.top_detected = True
                self.conviction_fired = False
                self._change_phase(date, Phase.SHORT_DCA, f'Top failsafe: 1W K<50')
                self.markup_cycles_completed += 1
                return True

        # Layer 4: Ranging exit — REMOVED for V14
        # DCA naturally handles ranging markets (grid buys dips, TPs on bounces)
        # Ranging exit was causing 4+ interruptions per coin in v0.1

        return False

    def _reset_top_state(self):
        """Reset all top detection state."""
        self.early_warning_date = None
        self.failsafe_armed = False
        self.peak_2w_k = 0.0
        self.ob93_armed = False
        self.ob93_armed_date = None
        self.unwinding = False

    # =========================================================================
    #  BOTTOM DETECTION (during SHORT_DCA)
    # =========================================================================

    def _check_bottom_signals(self, date, price, signals):
        """Check for bottom conviction during SHORT_DCA. Returns True if should switch."""
        if not self.top_detected or self.conviction_fired:
            return False

        # Gate 1: 3D death cross active
        if not self.detector.in_death_cross(date, '3D'):
            return False

        # Gate 2: 2W StochRSI exhaustion lift-off
        if not self.detector.has_2w_exhaustion_cross(date):
            return False

        # Check conviction score
        score, details = self.detector.check(date)
        if score >= self.cfg.CONVICTION_MIN_SCORE:
            self.conviction_fired = True

            # Close all short DCA positions (lock in profit)
            short_pnl = self._short_dca_close(date, f'BOTTOM_CONVICTION_{score}/4')

            self.conviction_triggers.append({
                'date': date, 'coin': self.coin, 'score': score,
                'details': details, 'short_pnl_pct': short_pnl
            })

            # Switch to long DCA
            self._change_phase(date, Phase.LONG_DCA,
                f'Bottom conviction {score}/4: switching to LONG_DCA')
            return True

        return False

    # =========================================================================
    #  ROUTER PHASE (evaluation/transition)
    # =========================================================================

    def _check_router(self, date, price, signals):
        """ROUTER phase: evaluate direction, route to LONG_DCA or SHORT_DCA."""
        days_in = signals['days_in_phase']

        if days_in < self.cfg.ROUTER_MIN_EVAL_DAYS:
            return

        # Check for bullish structure → LONG_DCA
        hh_hl = signals['hh_hl']
        if hh_hl and signals['fib_support']:
            self._change_phase(date, Phase.LONG_DCA, f'Router: bullish structure')
            return

        # Check for bearish structure → SHORT_DCA
        lh_ll = signals['lh_ll']
        adx = signals['adx']
        if (lh_ll and
            not np.isnan(adx) and adx > self.cfg.ADX_THRESHOLD and
            signals['fib_break']):
            if self.markup_cycles_completed >= 1:
                self._change_phase(date, Phase.SHORT_DCA,
                    f'Router: bearish structure (ADX={adx:.0f})')
                return

        # Timeout → default to LONG_DCA (market spends more time going up)
        if days_in >= self.cfg.ROUTER_MAX_EVAL_DAYS:
            self._change_phase(date, Phase.LONG_DCA,
                f'Router: timeout ({days_in}d), defaulting to LONG_DCA')
            return

    # =========================================================================
    #  MAIN LOOP
    # =========================================================================

    def run(self):
        """Run the V14 DCA backtest."""
        start = pd.Timestamp(self.cfg.START_DATE)
        end = pd.Timestamp(self.cfg.END_DATE)

        data = self.daily[(self.daily.index >= start) & (self.daily.index <= end)]
        if len(data) == 0:
            return None

        self.phase_start_date = data.index[0]

        for date, row in data.iterrows():
            price = row['close']
            if np.isnan(price):
                continue
            high = float(row['high']) if 'high' in row and not np.isnan(row['high']) else price
            low = float(row['low']) if 'low' in row and not np.isnan(row['low']) else price

            signals = self._compute_signals(date, price)

            if self.phase == Phase.LONG_DCA:
                # Run long DCA grid
                self._long_dca_tick(date, price, high=high)
                # Check for top signals
                self._check_top_signals(date, price, signals)

            elif self.phase == Phase.SHORT_DCA:
                # Run short DCA grid
                self._short_dca_tick(date, price, low=low)
                # Check for bottom signals
                self._check_bottom_signals(date, price, signals)
                # Also check for structural bullish reversal (markdown → DCA transition)
                self._check_markdown_exit(date, price, signals)

            elif self.phase == Phase.ROUTER:
                # Evaluate and route
                self._check_router(date, price, signals)

            # Record equity
            long_val = self.long_coins * price if self.long_coins > 0 else 0
            short_unreal = (self.short_avg_entry - price) * self.short_coins if self.short_coins > 0 else 0
            equity = self.capital + long_val + self.short_cost + short_unreal
            self.equity_curve.append({
                'date': date, 'equity': equity, 'price': price, 'phase': self.phase
            })

            # Check liquidation (only relevant when LEVERAGE > 1.0)
            self._check_liquidation(date, price)

        # End: close any open positions
        if len(data) > 0:
            last_date = data.index[-1]
            if self.long_coins > 0:
                self._long_dca_close(last_date, 'OPEN_END')
            if self.short_coins > 0:
                self._short_dca_close(last_date, 'OPEN_END')

        return self._results()

    def _check_markdown_exit(self, date, price, signals):
        """Check if SHORT_DCA should exit. V14 v0.2: conviction-only direction switches.
        Only safety net (markdown failure) remains — structural exits removed."""
        # Structure-based exit REMOVED in v0.2
        # v0.1 showed HH_HL kicked shorts out in 3-14 days every time
        # DCA shorts need to persist through the bear phase

        # Safety net: markdown failure (capital protection only)
        # If price rises 25%+ against our short grid with strong uptrend, bail out
        if self.short_avg_entry > 0:
            rise = (price - self.short_avg_entry) / self.short_avg_entry
            if rise > self.cfg.MARKUP_FAIL_DD_PCT:
                adx = signals['adx']
                if not np.isnan(adx) and adx > self.cfg.MARKUP_FAIL_ADX:
                    self._short_dca_close(date, 'MARKDOWN_FAIL')
                    self._change_phase(date, Phase.LONG_DCA,
                        f'Short grid failed: +{rise*100:.0f}% against, switching to LONG_DCA')
                    return True

        return False

    def _results(self):
        """Compile results."""
        eq_curve = pd.DataFrame(self.equity_curve)
        final_eq = eq_curve['equity'].iloc[-1] if len(eq_curve) > 0 else self.cfg.CAPITAL
        roi = (final_eq - self.cfg.CAPITAL) / self.cfg.CAPITAL * 100

        max_eq = eq_curve['equity'].cummax() if len(eq_curve) > 0 else pd.Series([self.cfg.CAPITAL])
        drawdown = ((eq_curve['equity'] - max_eq) / max_eq * 100) if len(eq_curve) > 0 else pd.Series([0])

        return {
            'coin': self.coin,
            'final_equity': final_eq,
            'roi': roi,
            'max_drawdown': drawdown.min() if len(drawdown) > 0 else 0,
            'total_long_trades': self.long_trades,
            'total_short_trades': self.short_trades,
            'long_wins': self.long_wins,
            'short_wins': self.short_wins,
            'long_pnl': self.long_pnl,
            'short_pnl': self.short_pnl,
            'phase_changes': len(self.phase_log),
            'phases': self.phase_log,
            'trades': self.trades,
            'equity_curve': eq_curve,
            'conviction_triggers': self.conviction_triggers,
            'top_triggers': self.top_triggers,
            'total_fees': self.total_fees,
            'fees_pct_of_profit': (self.total_fees / max(self.long_pnl + self.short_pnl, 0.01) * 100)
                if (self.long_pnl + self.short_pnl) > 0 else 0.0,
            'liquidation_events': self.liquidation_events,
            'max_position_dd_pct': self.max_position_dd_pct,
            'min_distance_to_liq_pct': self.min_distance_to_liq_pct if self.min_distance_to_liq_pct != float('inf') else None,
        }


# -- Runner ------------------------------------------------------------------

def run_v14(coins=None, capital=10000, start='2024-10-01'):
    """Run V14 DCA-only backtest."""
    if coins is None:
        coins = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']

    per_coin = capital / len(coins)

    print("=" * 80)
    print("V14 DCA-ONLY ENGINE BACKTEST")
    print(f"Start: {start}, Capital: ${capital:,} (${per_coin:,.0f}/coin)")
    mode = "ACCUMULATE (hold, signal exit)" if V14Config.DCA_ACCUMULATE else "CYCLE (TP profits)"
    print(f"DCA: {mode}, BO={V14Config.DCA_BO_PCT*100}%, Dev={V14Config.DCA_SO_DEVIATION*100}%,"
          f" Mult={V14Config.DCA_SO_MULTIPLIER}x, Max={V14Config.DCA_MAX_LAYERS} layers")
    print(f"Top: OB93 arm + 2D divergence ({V14Config.TOP_DIVERGENCE_TIMEOUT}d timeout)")
    print(f"Bottom: 3D DX + 2W K>=5 + conviction >=3/4")
    print("=" * 80)

    results = {}
    for coin in coins:
        base = coin.split('/')[0]
        print(f"\n{'='*50}")
        print(f"  {coin}")
        print(f"{'='*50}")

        try:
            pack = V13SignalPack(coin)
        except Exception as e:
            print(f"  ERROR loading pack: {e}")
            continue

        cfg = V14Config()
        cfg.CAPITAL = per_coin
        cfg.START_DATE = start

        eng = V14DCAEngine(pack, cfg)
        r = eng.run()

        if r:
            results[coin] = r
            print(f"  Equity: ${r['final_equity']:,.2f} ({r['roi']:+.1f}%)")
            print(f"  Max DD: {r['max_drawdown']:.1f}%")
            print(f"  Long trades: {r['total_long_trades']} (wins: {r['long_wins']}, pnl: ${r['long_pnl']:,.2f})")
            print(f"  Short trades: {r['total_short_trades']} (wins: {r['short_wins']}, pnl: ${r['short_pnl']:,.2f})")
            print(f"  Phase changes: {r['phase_changes']}")

            if r['top_triggers']:
                print(f"  Top triggers:")
                for t in r['top_triggers']:
                    print(f"    {t['date'].strftime('%Y-%m-%d')} {t['reason']} @ ${t['price']:.2f}")
            if r['conviction_triggers']:
                print(f"  Bottom triggers:")
                for t in r['conviction_triggers']:
                    print(f"    {t['date'].strftime('%Y-%m-%d')} score={t['score']}/4 short_pnl={t['short_pnl_pct']:+.1f}%")

            # Show phase timeline
            print(f"  Phases:")
            for p in r['phases']:
                print(f"    {p['date'].strftime('%Y-%m-%d')} {p['from']:>10} -> {p['to']:<10} {p['reason']}")

    # Portfolio summary
    if results:
        total = sum(r['final_equity'] for r in results.values())
        roi = (total - capital) / capital * 100
        print(f"\n{'='*80}")
        print(f"PORTFOLIO SUMMARY")
        print(f"{'='*80}")
        for coin in coins:
            if coin in results:
                r = results[coin]
                print(f"  {coin:<12} ${r['final_equity']:>10,.2f} ({r['roi']:>+8.1f}%) "
                      f"L:{r['total_long_trades']}({r['long_wins']}W) "
                      f"S:{r['total_short_trades']}({r['short_wins']}W)")
        print(f"  {'':->65}")
        print(f"  {'TOTAL':<12} ${total:>10,.2f} ({roi:>+8.1f}%)")

    return results


if __name__ == '__main__':
    run_v14()
