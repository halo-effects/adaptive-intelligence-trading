"""
V13 ROUTER Engine v1 — Refactored from V13 Phase Backtest v8

Architectural refactor: centralizes all transition logic into an always-on
ROUTER orchestration layer. Phase.FLAT renamed to Phase.ROUTER.
Signal computation centralized in _compute_router_signals().

MUST produce 100% identical results to v8 (pure refactor, no behavior changes).

ALL transitions use matrix-validated signals (no fixed timers):
  DCA -> MARKUP:    HH_HL + Fib_support (94.0 score, 100% acc, 20% FP)
  MARKUP -> ROUTER: 3-layer exit defense (2W OB93 / 1W OB85 / 1W K<50 failsafe)
  ROUTER routing:   HVF-driven (>0.4 = stay router, <0.2 for 7d = DCA)
  DCA -> MARKDOWN:  ADX>20 + Fib_break (94.0 score, 100% acc, 20% FP)
  MARKDOWN -> DCA:  HH_HL + Fib_support (structure turns bullish)

Capital allocation:
  MARKUP:   T1=60%, T2=20%, T3=10%, 10% reserve (front-loaded)
  SHORTS:   T1=60%, T2=20%, T3=10%, 10% reserve (same as markup)
  DCA:      8% base order, 1.5x SO mult, 1.5% TP, max 8 layers

Usage:
    python v13_router_engine_v1.py
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
from test_hvf_daily import (
    composite_hvf_score, detect_swing_points, hvf_harmonic_pattern
)


# -- Fibonacci Levels -------------------------------------------------------

FIB_RATIOS = [0.236, 0.382, 0.5, 0.618, 0.786]
FIB_TOLERANCE = 0.03  # 3% proximity


def compute_fib_levels(df, date, lookback=120):
    """Compute Fibonacci retracement levels from the last major swing.
    Returns dict of {ratio: price_level} or None if no swings found."""
    end_idx = df.index.get_indexer([date], method='pad')[0]
    if end_idx < 60:
        return None
    start_idx = max(0, end_idx - lookback)
    window = df.iloc[start_idx:end_idx + 1]

    swings = detect_swing_points(window, lookback=10)
    if len(swings) < 2:
        return None

    # Find the most recent major swing high and low
    highs = [s for s in swings if s['type'] == 'high']
    lows = [s for s in swings if s['type'] == 'low']
    if not highs or not lows:
        return None

    swing_high = max(highs, key=lambda s: s['price'])
    swing_low = min(lows, key=lambda s: s['price'])

    if swing_high['price'] <= swing_low['price']:
        return None

    rng = swing_high['price'] - swing_low['price']

    # Retracement levels from high to low
    levels = {}
    for ratio in FIB_RATIOS:
        levels[ratio] = swing_high['price'] - rng * ratio

    levels['swing_high'] = swing_high['price']
    levels['swing_low'] = swing_low['price']
    return levels


def price_near_fib_support(price, fib_levels):
    """Check if price is within tolerance of any Fibonacci support level."""
    if fib_levels is None:
        return False
    for ratio in FIB_RATIOS:
        level = fib_levels.get(ratio, 0)
        if level > 0:
            dist = abs(price - level) / level
            if dist < FIB_TOLERANCE:
                return True
    return False


def price_broke_fib_support(price, fib_levels):
    """Check if price has broken below Fibonacci support levels."""
    if fib_levels is None:
        return False
    # Check if price is below the 0.618 level (key support)
    golden = fib_levels.get(0.618, 0)
    if golden > 0 and price < golden * (1 - FIB_TOLERANCE):
        return True
    # Also check 0.786 (deep support)
    deep = fib_levels.get(0.786, 0)
    if deep > 0 and price < deep * (1 - FIB_TOLERANCE):
        return True
    return False


# -- Configuration -----------------------------------------------------------

class V13Config:
    """V13 Router v1 configuration -- signal-driven, no fixed timers."""

    # - Top Detection (StochRSI) -
    OB_THRESHOLD_2W = 93       # Primary top signal
    EARLY_WARNING_1W = 97      # 1W early warning threshold
    FAILSAFE_1W = 50           # 1W failsafe exit threshold
    FAILSAFE_WINDOW_WEEKS = 2  # Weeks after early warning before failsafe arms
    OB_FALLBACK_1W = 85        # Fallback when 2W never reaches OB

    # - DCA Transition Signals -
    # DCA->MARKUP: HH_HL + Fib_support
    HH_HL_LOOKBACK = 2         # Consecutive higher highs needed
    # DCA->MARKDOWN: ADX>20 + Fib_break
    ADX_THRESHOLD = 20         # ADX trend confirmation

    # - Markup Entry Gate (markup only -- markdown gate removed) -
    SMA200_OVEREXTENSION = 20    # Don't enter markup if >20% above 200-SMA (stored as pct, not decimal)

    # - Markup/Markdown Ranging Exit (normal exit) -
    PHASE_ADX_RANGING = 20         # ADX below this = ranging
    PHASE_ADX_SUSTAINED_DAYS = 21  # Must stay below for 21 consecutive days (longer than ROUTER's 14d)

    # - Markup Failure Detection -
    MARKUP_FAIL_DD_PCT = 0.25      # 25% drawdown from entry = failed markup
    MARKUP_FAIL_ADX = 25           # ADX must confirm downtrend (not just a dip)

    # - ROUTER Phase (post-top/post-markdown evaluation) -
    ROUTER_MIN_EVAL_DAYS = 14        # Min days before ANY transition allowed
    ROUTER_MAX_EVAL_DAYS = 42        # Max days before defaulting to DCA (6 weeks)
    ROUTER_ADX_RANGING = 20          # ADX below this = ranging confirmed
    ROUTER_ADX_SUSTAINED_DAYS = 14   # Must stay below for this many consecutive days
    HVF_LOOKBACK = 44              # Days of data for HVF computation

    # - Capital Allocation: MARKUP -
    TIER1_PCT = 0.60           # Entry -- heavy at lowest price
    TIER2_PCT = 0.20           # Confirmation add
    TIER3_PCT = 0.10           # Momentum add
    TIER2_DELAY_WEEKS = 1
    TIER3_DELAY_WEEKS = 2

    # - Capital Allocation: SHORTS (same as markup) -
    SHORT_TIER1_PCT = 0.60
    SHORT_TIER2_PCT = 0.20
    SHORT_TIER3_PCT = 0.10
    SHORT_TIER2_DELAY_WEEKS = 1
    SHORT_TIER3_DELAY_WEEKS = 2

    # - DCA Engine -
    DCA_BO_PCT = 0.08          # 8% base order
    DCA_SO_DEVIATION = 0.025   # 2.5% between layers
    DCA_SO_MULTIPLIER = 1.5    # Volume multiplier
    DCA_TP_PCT = 0.015         # 1.5% take profit
    DCA_MAX_LAYERS = 8

    # - General -
    MIN_PHASE_DAYS = 3         # 3-day minimum -- prevent same-day edge cases
    CAPITAL = 10000
    START_DATE = '2020-10-01'  # Full backtest period
    END_DATE = '2026-02-25'


# -- Phase State -------------------------------------------------------------

class Phase:
    DCA = 'DCA'
    MARKUP = 'MARKUP'
    ROUTER = 'ROUTER'      # Post-top, HVF-driven routing (was FLAT in v8)
    MARKDOWN = 'MARKDOWN'


# -- Backtest Engine ---------------------------------------------------------

class V13RouterV1:
    """V13 Router v1 -- Pure signal-driven phase riding with centralized router."""

    def __init__(self, pack: V13SignalPack, config: V13Config = None):
        self.pack = pack
        self.cfg = config or V13Config()
        self.coin = pack.coin
        self.daily = pack.daily

        # - State -
        self.phase = Phase.DCA
        self.capital = self.cfg.CAPITAL
        self.phase_start_date = None

        # Markup position
        self.position_coins = 0.0
        self.entry_price = 0.0
        self.tier = 0

        # Short position
        self.short_coins = 0.0
        self.short_entry = 0.0
        self.short_cost = 0.0
        self.short_tier = 0

        # Top detection state
        self.early_warning_date = None
        self.failsafe_armed = False
        self.peak_2w_k = 0.0

        # Cycle tracking
        self.markup_cycles_completed = 0
        self.shorts_enabled = False

        # ROUTER ranging confirmation
        self.adx_below_20_streak = 0
        self.router_from_top = False      # Did we enter ROUTER from a top signal?
        self.router_from_markdown = False  # Did we enter ROUTER from markdown?

        # (HVF used for logging only, not routing)

        # DCA state
        self.dca_coins = 0.0
        self.dca_avg_entry = 0.0
        self.dca_layers = 0
        self.dca_last_buy = None
        self.dca_tp = 0.0
        self.dca_cost = 0.0
        self.dca_trades = 0
        self.dca_wins = 0
        self.dca_pnl = 0.0

        # Logging
        self.trades = []
        self.phase_log = []
        self.equity_curve = []

        # Precompute StochRSI signals
        self._precompute_stoch()

    def _precompute_stoch(self):
        """Precompute StochRSI signal dates."""
        s2w = self.pack.stoch_2w
        s1w = self.pack.stoch_1w

        # 2W OB exits at th=93
        self.ob_exits_2w = set(s2w.ob_exits(self.cfg.OB_THRESHOLD_2W).index)

        # 1W early warning: K crosses below 97
        df_1w = s1w.df
        prev = df_1w['K'].shift(1)
        self.early_warnings_1w = set(
            df_1w[(prev >= self.cfg.EARLY_WARNING_1W) & (df_1w['K'] < self.cfg.EARLY_WARNING_1W)].index)

        # 1W failsafe: K crosses below 50
        self.failsafe_1w = set(
            df_1w[(prev >= self.cfg.FAILSAFE_1W) & (df_1w['K'] < self.cfg.FAILSAFE_1W)].index)

        # 1W OB85 fallback: K crosses below 85
        self.ob85_1w = set(
            df_1w[(prev >= self.cfg.OB_FALLBACK_1W) & (df_1w['K'] < self.cfg.OB_FALLBACK_1W)].index)

    # -- Price & Signal Helpers ----------------------------------------------

    def _price(self, date):
        mask = self.daily.index <= date
        if not mask.any():
            return np.nan
        return self.daily.loc[mask, 'close'].iloc[-1]

    def _signal_near(self, date, signal_set, days=7):
        """Check if any signal fired within N days before date."""
        for s in signal_set:
            if 0 <= (date - s).days <= days:
                return s
        return None

    def _hh_hl(self, date):
        """Check for HH_HL pattern on daily candles."""
        return self.pack.structure.hh_hl_streak(date, self.cfg.HH_HL_LOOKBACK)

    def _adx(self, date):
        return self.pack.structure.adx_at(date)

    def _cfgi(self, date):
        return self.pack.cfgi.value_at(date)

    def _hvf(self, date):
        """Compute HVF composite at date."""
        idx = self.daily.index.get_indexer([date], method='pad')[0]
        if idx < self.cfg.HVF_LOOKBACK:
            return 0.0
        window = self.daily.iloc[max(0, idx - self.cfg.HVF_LOOKBACK):idx + 1]
        result = composite_hvf_score(window)
        # Returns (composite, vuvu, vol_comp, price_comp) -- all may be Series
        composite = result[0]
        if hasattr(composite, 'iloc'):
            return float(composite.iloc[-1]) if len(composite) > 0 else 0.0
        return float(composite)

    def _fib_levels(self, date):
        """Get current Fibonacci levels."""
        return compute_fib_levels(self.daily, date)

    def _total_equity(self, date):
        """Total equity = cash + markup position + DCA position + short PnL."""
        price = self._price(date)
        if np.isnan(price):
            return self.capital
        eq = self.capital + self.position_coins * price + self.dca_coins * price
        if self.short_coins > 0:
            short_pnl = (self.short_entry - price) * self.short_coins
            eq += short_pnl + self.short_cost
        return eq

    # -- Position Management -------------------------------------------------

    def _buy(self, date, pct, tier):
        price = self._price(date)
        if np.isnan(price):
            return
        amount = self.capital * pct
        if amount <= 0 or amount > self.capital:
            return
        coins = amount / price
        self.position_coins += coins
        self.capital -= amount
        if self.entry_price == 0:
            self.entry_price = price
        self.tier = tier
        self.trades.append({
            'date': date, 'action': f'BUY_T{tier}', 'price': price,
            'amount': amount, 'coins': coins, 'phase': self.phase
        })

    def _sell_all(self, date, reason):
        price = self._price(date)
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

    def _open_short(self, date, pct, tier):
        price = self._price(date)
        if np.isnan(price):
            return
        amount = self.capital * pct
        if amount <= 0 or amount > self.capital:
            return
        coins = amount / price
        self.short_coins += coins
        self.short_cost += amount
        self.short_entry = self.short_cost / self.short_coins
        self.capital -= amount
        self.short_tier = tier
        self.trades.append({
            'date': date, 'action': f'SHORT_T{tier}', 'price': price,
            'amount': amount, 'coins': coins, 'phase': self.phase
        })

    def _close_short(self, date, reason):
        if self.short_coins <= 0:
            return 0
        price = self._price(date)
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
        self.short_tier = 0
        return pnl_pct

    # -- DCA Engine ----------------------------------------------------------

    def _dca_tick(self, date, price):
        if np.isnan(price):
            return
        available = self.capital * 0.90
        cfg = self.cfg

        # Check TP first
        if self.dca_coins > 0 and self.dca_tp > 0 and price >= self.dca_tp:
            proceeds = self.dca_coins * price
            pnl = proceeds - self.dca_cost
            pnl_pct = pnl / self.dca_cost * 100
            self.capital += proceeds
            self.dca_trades += 1
            self.dca_wins += 1
            self.dca_pnl += pnl
            self.trades.append({
                'date': date, 'action': f'DCA_TP ({self.dca_layers}L)',
                'price': price, 'amount': proceeds, 'coins': self.dca_coins,
                'phase': self.phase, 'pnl_pct': pnl_pct
            })
            self.dca_coins = 0
            self.dca_avg_entry = 0
            self.dca_layers = 0
            self.dca_tp = 0
            self.dca_cost = 0
            self.dca_last_buy = None
            return

        if self.dca_layers >= cfg.DCA_MAX_LAYERS:
            return
        if self.dca_last_buy and (date - self.dca_last_buy).days < 1:
            return

        should_buy = False
        if self.dca_layers == 0:
            should_buy = True
        elif self.dca_avg_entry > 0:
            target_drop = cfg.DCA_SO_DEVIATION * self.dca_layers
            current_drop = (self.dca_avg_entry - price) / self.dca_avg_entry
            if current_drop >= target_drop:
                should_buy = True

        if should_buy:
            if self.dca_layers == 0:
                order = available * cfg.DCA_BO_PCT
            else:
                order = available * cfg.DCA_BO_PCT * (cfg.DCA_SO_MULTIPLIER ** min(self.dca_layers, 4))
            order = min(order, self.capital * 0.3)
            if order < 10 or order > self.capital:
                return

            coins = order / price
            self.dca_coins += coins
            self.capital -= order
            self.dca_cost += order
            self.dca_layers += 1
            self.dca_last_buy = date
            self.dca_avg_entry = self.dca_cost / self.dca_coins
            self.dca_tp = self.dca_avg_entry * (1 + cfg.DCA_TP_PCT)
            self.trades.append({
                'date': date, 'action': f'DCA_BUY_L{self.dca_layers}',
                'price': price, 'amount': order, 'coins': coins, 'phase': self.phase
            })

    def _dca_close(self, date, reason):
        """HARD EXIT all DCA positions."""
        if self.dca_coins <= 0:
            return
        price = self._price(date)
        if np.isnan(price):
            return
        proceeds = self.dca_coins * price
        pnl = proceeds - self.dca_cost
        pnl_pct = pnl / self.dca_cost * 100 if self.dca_cost > 0 else 0
        self.capital += proceeds
        self.dca_trades += 1
        if pnl > 0:
            self.dca_wins += 1
        self.dca_pnl += pnl
        self.trades.append({
            'date': date, 'action': f'DCA_CLOSE ({reason}, {self.dca_layers}L)',
            'price': price, 'amount': proceeds, 'coins': self.dca_coins,
            'phase': self.phase, 'pnl_pct': pnl_pct
        })
        self.dca_coins = 0
        self.dca_avg_entry = 0
        self.dca_layers = 0
        self.dca_tp = 0
        self.dca_cost = 0
        self.dca_last_buy = None

    # -- Phase Transitions ---------------------------------------------------

    def _change_phase(self, date, new_phase, reason):
        old = self.phase
        # Close short if leaving MARKDOWN
        if old == Phase.MARKDOWN and self.short_coins > 0:
            self._close_short(date, f'{old}->{new_phase}')
        self.phase = new_phase
        self.phase_start_date = date
        self.phase_log.append({
            'date': date, 'from': old, 'to': new_phase, 'reason': reason,
            'equity': self._total_equity(date), 'price': self._price(date)
        })
        # Track completed markup cycles
        if old == Phase.MARKUP and new_phase == Phase.ROUTER:
            self.markup_cycles_completed += 1
            if not self.shorts_enabled:
                self.shorts_enabled = True
                self.trades.append({
                    'date': date, 'action': f'SHORTS_ENABLED (cycle #{self.markup_cycles_completed})',
                    'price': self._price(date), 'amount': 0, 'coins': 0, 'phase': new_phase
                })
        # Reset ADX streak on any phase change
        self.adx_below_20_streak = 0
        # Track ROUTER entry context
        if new_phase == Phase.ROUTER:
            self.router_from_top = (old == Phase.MARKUP and 'OB' in reason or 'failsafe' in reason.lower() or 'Failsafe' in reason)
            self.router_from_markdown = (old == Phase.MARKDOWN)
        # Open short T1 when entering MARKDOWN
        if new_phase == Phase.MARKDOWN and self.shorts_enabled and self.capital > 0:
            self._open_short(date, self.cfg.SHORT_TIER1_PCT, 1)

    # -- Centralized Router Signal Computation -------------------------------

    def _compute_router_signals(self, date, price):
        """Compute the full signal stack once per tick."""
        return {
            'hh_hl': self._hh_hl(date),
            'lh_ll': self.pack.structure.lh_ll_streak(date, self.cfg.HH_HL_LOOKBACK),
            'adx': self._adx(date),
            'cfgi': self._cfgi(date),
            'fib_levels': self._fib_levels(date),
            'price': price,
            'date': date,
            'days_in_phase': (date - self.phase_start_date).days if self.phase_start_date else 0,
            # StochRSI signals (precomputed sets, just check membership)
            'ob_2w_93': self._signal_near(date, self.ob_exits_2w),
            'ob_1w_85': self._signal_near(date, self.ob85_1w),
            'early_warning_1w': self._signal_near(date, self.early_warnings_1w),
            'failsafe_1w': self._signal_near(date, self.failsafe_1w),
            # SMA200
            'sma200_overext': self.pack.sma200.overextension_at(date),
        }

    # -- Router Evaluate (main dispatch) -------------------------------------

    def _router_evaluate(self, date, price):
        """Compute signals once and dispatch to phase-specific handler."""
        signals = self._compute_router_signals(date, price)
        if self.phase == Phase.DCA:
            self._router_check_dca(date, price, signals)
        elif self.phase == Phase.MARKUP:
            self._router_check_markup(date, price, signals)
        elif self.phase == Phase.ROUTER:
            self._router_check_router(date, price, signals)
        elif self.phase == Phase.MARKDOWN:
            self._router_check_markdown(date, price, signals)

    # -- Phase Logic (router-aware) ------------------------------------------

    def _router_check_dca(self, date, price, signals):
        """DCA phase: run DCA engine + check for MARKUP or MARKDOWN transition."""
        self._dca_tick(date, price)

        # DCA -> MARKUP: HH_HL + Fib_support
        hh = signals['hh_hl']
        fib = signals['fib_levels']
        if hh and price_near_fib_support(price, fib):
            overext = signals['sma200_overext']
            cfgi = signals['cfgi']
            cfgi_ok = not np.isnan(cfgi) and cfgi > 40
            note = f'HH_HL+Fib_support'
            if cfgi_ok:
                note += f'+CFGI={cfgi:.0f}'
            if not np.isnan(overext):
                note += f' (SMA200={overext*100:+.0f}%)'
            if self.dca_coins > 0:
                note += f' (DCA riding {self.dca_layers}L)'
            self._change_phase(date, Phase.MARKUP, note)
            self._buy(date, self.cfg.TIER1_PCT, 1)
            self.early_warning_date = None
            self.failsafe_armed = False
            self.peak_2w_k = 0
            return

        # DCA -> MARKDOWN: LH_LL + ADX>20 + Fib_break
        lh_ll = signals['lh_ll']
        adx = signals['adx']
        if lh_ll and not np.isnan(adx) and adx > self.cfg.ADX_THRESHOLD:
            if price_broke_fib_support(price, fib):
                overext = signals['sma200_overext']
                note = f'LH_LL+ADX={adx:.0f}+Fib_break'
                if not np.isnan(overext):
                    note += f' (SMA200={overext*100:+.0f}%)'
                if self.dca_coins > 0:
                    self._dca_close(date, 'HARD_EXIT_MARKDOWN')
                self._change_phase(date, Phase.MARKDOWN, note)
                return

    def _router_check_markup(self, date, price, signals):
        """MARKUP phase: tier adds + top detection."""
        # Let DCA TPs hit naturally (graceful exit)
        if self.dca_coins > 0:
            self._dca_tick(date, price)

        # Track peak 2W K
        k_2w = self.pack.stoch_2w.get_k_at(date)
        if not np.isnan(k_2w) and k_2w > self.peak_2w_k:
            self.peak_2w_k = k_2w

        # Layer 1: Early warning -- 1W crosses below 97
        if signals['early_warning_1w'] and self.early_warning_date is None:
            self.early_warning_date = date
            self.trades.append({
                'date': date, 'action': f'EARLY_WARNING_1W_97 (2W_peak={self.peak_2w_k:.0f})',
                'price': price, 'amount': 0, 'coins': 0, 'phase': self.phase
            })

        # Layer 2: Primary exit -- 2W OB93
        if signals['ob_2w_93']:
            pnl = self._sell_all(date, 'PRIMARY_2W_OB93')
            if self.dca_coins > 0:
                self._dca_close(date, 'TOP_EXIT')
            self._change_phase(date, Phase.ROUTER, f'2W OB93 exit, pnl={pnl:+.1f}%')
            self._reset_top_state()
            return

        # Layer 2b: Fallback -- 1W OB85 when 2W never reached OB
        if self.peak_2w_k < self.cfg.OB_THRESHOLD_2W and self.early_warning_date:
            if signals['ob_1w_85']:
                pnl = self._sell_all(date, f'FALLBACK_1W_OB85 (2W_peak={self.peak_2w_k:.0f})')
                if self.dca_coins > 0:
                    self._dca_close(date, 'TOP_EXIT')
                self._change_phase(date, Phase.ROUTER,
                    f'1W OB85 fallback (2W peak={self.peak_2w_k:.0f}<93), pnl={pnl:+.1f}%')
                self._reset_top_state()
                return

        # Layer 3: Failsafe -- 1W K<50 after armed
        if self.early_warning_date and not self.failsafe_armed:
            if (date - self.early_warning_date).days >= self.cfg.FAILSAFE_WINDOW_WEEKS * 7:
                self.failsafe_armed = True
        if self.failsafe_armed and signals['failsafe_1w']:
            pnl = self._sell_all(date, 'FAILSAFE_1W_K50')
            if self.dca_coins > 0:
                self._dca_close(date, 'TOP_EXIT')
            self._change_phase(date, Phase.ROUTER, f'Failsafe 1W K<50, pnl={pnl:+.1f}%')
            self._reset_top_state()
            return

        # Layer 4: Ranging exit (normal exit) -- trend ran out of steam
        days_in = signals['days_in_phase']
        if days_in >= 14:
            adx = signals['adx']
            if not np.isnan(adx) and adx < self.cfg.PHASE_ADX_RANGING:
                self.adx_below_20_streak += 1
                if self.adx_below_20_streak >= self.cfg.PHASE_ADX_SUSTAINED_DAYS:
                    pnl = self._sell_all(date, f'MARKUP_RANGING (ADX<{self.cfg.PHASE_ADX_RANGING} for {self.adx_below_20_streak}d)')
                    if self.dca_coins > 0:
                        self._dca_close(date, 'RANGING_EXIT')
                    self._change_phase(date, Phase.ROUTER,
                        f'Markup ranging: ADX<{self.cfg.PHASE_ADX_RANGING} for {self.adx_below_20_streak}d, sell -> ROUTER -> DCA')
                    self._reset_top_state()
                    return
            else:
                self.adx_below_20_streak = 0

        # Layer 5: Markup failure -- safety net BELOW top signals
        if self.entry_price > 0:
            dd_from_entry = (price - self.entry_price) / self.entry_price
            if dd_from_entry < -self.cfg.MARKUP_FAIL_DD_PCT:
                adx = signals['adx']
                if not np.isnan(adx) and adx > self.cfg.MARKUP_FAIL_ADX:
                    pnl = self._sell_all(date, f'MARKUP_FAIL (dd={dd_from_entry*100:.0f}%, ADX={adx:.0f})')
                    if self.dca_coins > 0:
                        self._dca_close(date, 'MARKUP_FAIL')
                    self._change_phase(date, Phase.ROUTER,
                        f'Markup failed: {dd_from_entry*100:.0f}% below entry, ADX={adx:.0f} confirms downtrend')
                    self._reset_top_state()
                    return

        # Tier adds
        self._router_check_markup_tiers(date, price, signals)

    def _router_check_markup_tiers(self, date, price, signals):
        if self.tier >= 3 or self.phase_start_date is None:
            return
        weeks_in = (date - self.phase_start_date).days / 7

        if self.tier == 1 and weeks_in >= self.cfg.TIER2_DELAY_WEEKS:
            cfgi = signals['cfgi']
            if (self.entry_price > 0 and price >= self.entry_price and
                not np.isnan(cfgi) and cfgi > 40):
                self._buy(date, self.cfg.TIER2_PCT, 2)

        elif self.tier == 2 and weeks_in >= self.cfg.TIER3_DELAY_WEEKS:
            adx = signals['adx']
            hh = signals['hh_hl']
            if (self.entry_price > 0 and price >= self.entry_price and
                not np.isnan(adx) and adx > 25 and hh):
                self._buy(date, self.cfg.TIER3_PCT, 3)

    def _router_check_router(self, date, price, signals):
        """ROUTER phase behavior depends on HOW we got here:
        
        1. From TOP SIGNAL (blow-off top): Conductor waits for phase detection.
           Market is heading down -> check for MARKDOWN entry (ADX+Fib_break).
           Min eval period still applies.
        
        2. From RANGING EXIT (normal): Trend died -> go to DCA.
           Market is directionless -> DCA accumulates while waiting for signals.
        
        3. From MARKDOWN (shorts closed): Go to DCA.
           Same as ranging exit -> accumulate while waiting for direction.
        """
        adx = signals['adx']
        days_router = signals['days_in_phase']

        # Minimum eval period for all ROUTER exits
        if days_router < self.cfg.ROUTER_MIN_EVAL_DAYS:
            return

        # PATH 1: Entered from TOP SIGNAL -> conductor checks for MARKDOWN
        if self.router_from_top:
            fib = signals['fib_levels']
            # Check for MARKDOWN: LH_LL + ADX>20 + Fib_break (mirrors MARKUP's HH_HL gate)
            lh_ll = signals['lh_ll']
            if lh_ll and not np.isnan(adx) and adx > self.cfg.ADX_THRESHOLD:
                if price_broke_fib_support(price, fib):
                    overext = signals['sma200_overext']
                    note = f'ROUTER->MARKDOWN: Post-top, LH_LL+ADX={adx:.0f}+Fib_break'
                    if not np.isnan(overext):
                        note += f' (SMA200={overext*100:+.0f}%)'
                    note += f' (router {days_router}d)'
                    self._change_phase(date, Phase.MARKDOWN, note)
                    return
            
            # If no markdown signal after max eval, fall through to DCA
            if days_router >= self.cfg.ROUTER_MAX_EVAL_DAYS:
                self._change_phase(date, Phase.DCA,
                    f'ROUTER->DCA: Post-top, no markdown signal after {days_router}d')
            return

        # PATH 2 & 3: Entered from RANGING EXIT or MARKDOWN
        # NOTE: ROUTER->MARKUP direct path tested but REVERTED (2026-02-26).
        # HH_HL+Fib fires on bear market rallies without bias filter, causing
        # ETH -225% and BTC -140% regression. Needs 3D candle bias system first.
        # TODO(2C.19): Re-enable once bias trigger (2C.17) is implemented.

        # Wait for ADX ranging -> DCA
        if not np.isnan(adx) and adx < self.cfg.ROUTER_ADX_RANGING:
            self.adx_below_20_streak += 1
        else:
            self.adx_below_20_streak = 0

        ranging_confirmed = self.adx_below_20_streak >= self.cfg.ROUTER_ADX_SUSTAINED_DAYS

        if not ranging_confirmed:
            return

        # Ranging confirmed -> go to DCA
        self._change_phase(date, Phase.DCA,
            f'ROUTER->DCA: Ranging confirmed (ADX<{self.cfg.ROUTER_ADX_RANGING} for {self.adx_below_20_streak}d, router {days_router}d)')
        self.adx_below_20_streak = 0

    def _router_check_markdown(self, date, price, signals):
        """MARKDOWN phase: hold shorts through spring. Only exit to ROUTER when
        downtrend is exhausted (ADX < 20 sustained = ranging confirmed).
        Per Brett: "Until price reaches meaningful support, we don't sell shorts." """
        # MARKDOWN -> ROUTER: ADX trend exhaustion (downtrend dying)
        adx = signals['adx']
        days_in = signals['days_in_phase']
        if days_in >= 14:  # Give markdown 2 weeks minimum
            if not np.isnan(adx) and adx < self.cfg.PHASE_ADX_RANGING:
                self.adx_below_20_streak += 1
                if self.adx_below_20_streak >= self.cfg.PHASE_ADX_SUSTAINED_DAYS:
                    self._change_phase(date, Phase.ROUTER,
                        f'MARKDOWN->ROUTER: Ranging (ADX<{self.cfg.PHASE_ADX_RANGING} for {self.adx_below_20_streak}d, markdown {days_in}d)')
                    return
            else:
                self.adx_below_20_streak = 0

        # Markdown failure detector -- MIRROR of markup failure
        if self.short_entry > 0 and self.short_coins > 0:
            rise_from_entry = (price - self.short_entry) / self.short_entry
            if rise_from_entry > self.cfg.MARKUP_FAIL_DD_PCT:  # Same threshold, mirrored
                adx = signals['adx']
                if not np.isnan(adx) and adx > self.cfg.MARKUP_FAIL_ADX:
                    self._change_phase(date, Phase.ROUTER,
                        f'MARKDOWN_FAIL: price +{rise_from_entry*100:.0f}% above short entry, ADX={adx:.0f} confirms uptrend')
                    return

        # Short tier adds -- MIRROR of markup tiers (symmetric per Brett's spec)
        if self.short_tier >= 3 or self.phase_start_date is None:
            return
        weeks_in = (date - self.phase_start_date).days / 7

        if self.short_tier == 1 and weeks_in >= self.cfg.SHORT_TIER2_DELAY_WEEKS:
            # T2: price must be below entry (trend continuing) + CFGI < 40 (fear)
            if self.shorts_enabled and self.capital > 0:
                cfgi = signals['cfgi']
                if (self.short_entry > 0 and price <= self.short_entry and
                    not np.isnan(cfgi) and cfgi < 40):
                    self._open_short(date, self.cfg.SHORT_TIER2_PCT, 2)

        elif self.short_tier == 2 and weeks_in >= self.cfg.SHORT_TIER3_DELAY_WEEKS:
            # T3: price below entry + ADX>25 + LH/LL structure
            if self.shorts_enabled and self.capital > 0:
                adx = signals['adx']
                lh_ll = self.pack.structure.lh_ll_streak(date, 2) if hasattr(self.pack.structure, 'lh_ll_streak') else False
                if (self.short_entry > 0 and price <= self.short_entry and
                    not np.isnan(adx) and adx > 25 and lh_ll):
                    self._open_short(date, self.cfg.SHORT_TIER3_PCT, 3)

    def _reset_top_state(self):
        self.early_warning_date = None
        self.failsafe_armed = False
        self.peak_2w_k = 0

    # -- Main Loop -----------------------------------------------------------

    def run(self):
        start = pd.Timestamp(self.cfg.START_DATE)
        end = pd.Timestamp(self.cfg.END_DATE)
        data = self.daily[(self.daily.index >= start) & (self.daily.index <= end)]

        if len(data) == 0:
            print(f"  No data for {self.coin}")
            return None

        self.phase = Phase.DCA
        self.phase_start_date = data.index[0]
        self.phase_log.append({
            'date': data.index[0], 'from': None, 'to': Phase.DCA,
            'reason': 'START', 'equity': self.cfg.CAPITAL,
            'price': data['close'].iloc[0]
        })

        for date, row in data.iterrows():
            price = row['close']
            self.equity_curve.append({
                'date': date, 'equity': self._total_equity(date),
                'price': price, 'phase': self.phase
            })

            # 3-day min hold
            if self.phase_start_date and (date - self.phase_start_date).days < self.cfg.MIN_PHASE_DAYS:
                # Still run DCA ticks during hold
                if self.phase in (Phase.DCA, Phase.MARKUP) and self.dca_coins > 0:
                    self._dca_tick(date, price)
                continue

            self._router_evaluate(date, price)

        # Mark open positions at end (don't close -- exclude from P&L)
        self._open_at_end = {
            'markup_coins': self.position_coins,
            'markup_entry': self.entry_price,
            'dca_coins': self.dca_coins,
            'dca_cost': self.dca_cost,
            'short_coins': self.short_coins,
            'short_entry': self.short_entry,
        }
        # Close for equity calc but flag as open
        if self.position_coins > 0:
            self._sell_all(data.index[-1], 'OPEN_END')
        if self.dca_coins > 0:
            self._dca_close(data.index[-1], 'OPEN_END')
        if self.short_coins > 0:
            self._close_short(data.index[-1], 'OPEN_END')

        return self._results()

    def _results(self):
        if not self.equity_curve:
            return None
        eq = pd.DataFrame(self.equity_curve).set_index('date')
        final = eq['equity'].iloc[-1]
        roi = (final - self.cfg.CAPITAL) / self.cfg.CAPITAL * 100
        peak = eq['equity'].expanding().max()
        dd = (eq['equity'] - peak) / peak * 100
        max_dd = dd.min()
        total = len(eq)
        start_p = eq['price'].iloc[0]
        end_p = eq['price'].iloc[-1]
        bh = (end_p - start_p) / start_p * 100

        trades_pnl = [t for t in self.trades if 'pnl_pct' in t]
        # Separate closed trades from open-end trades
        closed_trades = [t for t in trades_pnl if 'OPEN_END' not in t.get('action', '')]
        open_trades = [t for t in trades_pnl if 'OPEN_END' in t.get('action', '')]
        wins = [t for t in closed_trades if t['pnl_pct'] > 0]
        losses = [t for t in closed_trades if t['pnl_pct'] <= 0]

        # Closed-only equity: back out unrealized open position losses
        open_end_pnl = sum(t.get('pnl_pct', 0) * t.get('amount', 0) / 100 for t in open_trades) if open_trades else 0
        closed_equity = final  # We'll compute from trade history instead
        # Simpler: find equity just before the last open position was entered
        last_completed_phase = None
        for p in reversed(self.phase_log):
            if 'OPEN_END' not in p.get('reason', '') and p['to'] in (Phase.ROUTER, Phase.DCA):
                last_completed_phase = p
                break
        closed_equity = last_completed_phase['equity'] if last_completed_phase else final
        closed_roi = (closed_equity - self.cfg.CAPITAL) / self.cfg.CAPITAL * 100

        return {
            'coin': self.coin,
            'start': eq.index[0], 'end': eq.index[-1],
            'capital': self.cfg.CAPITAL, 'final_equity': final,
            'roi': roi, 'closed_roi': closed_roi, 'closed_equity': closed_equity,
            'max_drawdown': max_dd,
            'buy_hold_return': bh, 'outperformance': roi - bh,
            'phase_changes': len(self.phase_log) - 1,
            'time_markup_pct': sum(1 for e in self.equity_curve if e['phase'] == Phase.MARKUP) / total * 100,
            'time_dca_pct': sum(1 for e in self.equity_curve if e['phase'] == Phase.DCA) / total * 100,
            'time_router_pct': sum(1 for e in self.equity_curve if e['phase'] == Phase.ROUTER) / total * 100,
            'time_markdown_pct': sum(1 for e in self.equity_curve if e['phase'] == Phase.MARKDOWN) / total * 100,
            'total_trades': len(self.trades),
            'closed_trades': len(trades_pnl), 'wins': len(wins), 'losses': len(losses),
            'win_rate': len(wins) / len(trades_pnl) * 100 if trades_pnl else 0,
            'avg_win': np.mean([t['pnl_pct'] for t in wins]) if wins else 0,
            'avg_loss': np.mean([t['pnl_pct'] for t in losses]) if losses else 0,
            'dca_trades': self.dca_trades, 'dca_wins': self.dca_wins, 'dca_pnl': self.dca_pnl,
            'markup_cycles': self.markup_cycles_completed,
            'shorts_enabled': self.shorts_enabled,
            'equity_curve': eq, 'trades': self.trades, 'phases': self.phase_log,
        }


# -- Runner ------------------------------------------------------------------

def print_results(r):
    if r is None:
        return
    print(f"\n  {r['coin']} Results:")
    print(f"  {'-' * 50}")
    print(f"  Closed ROI:       {r['closed_roi']:+.1f}% (completed trades only)")
    print(f"  Total ROI:        {r['roi']:+.1f}% (incl open position)")
    print(f"  Buy & Hold:       {r['buy_hold_return']:+.1f}%")
    print(f"  Closed Alpha:     {r['closed_roi'] - r['buy_hold_return']:+.1f}%")
    print(f"  Max Drawdown:     {r['max_drawdown']:.1f}%")
    print(f"  Closed Equity:    ${r['closed_equity']:,.0f}")
    print(f"  Final Equity:     ${r['final_equity']:,.0f} (incl open)")
    print(f"  Markup Cycles:    {r['markup_cycles']}")
    print(f"  Phase Changes:    {r['phase_changes']}")
    print(f"  Time MARKUP:      {r['time_markup_pct']:.0f}%")
    print(f"  Time DCA:         {r['time_dca_pct']:.0f}%")
    print(f"  Time ROUTER:      {r['time_router_pct']:.0f}%")
    print(f"  Time MARKDOWN:    {r['time_markdown_pct']:.0f}%")
    print(f"  Closed Trades:    {r['closed_trades']} ({r['wins']}W / {r['losses']}L, {r['win_rate']:.0f}%)")
    if r['wins']:
        print(f"  Avg Win:          {r['avg_win']:+.1f}%")
    if r['losses']:
        print(f"  Avg Loss:         {r['avg_loss']:+.1f}%")
    if r['dca_trades'] > 0:
        print(f"  DCA Trades:       {r['dca_trades']} ({r['dca_wins']}W, ${r['dca_pnl']:+,.0f})")

    print(f"\n  Phase Timeline:")
    for p in r['phases']:
        print(f"    {p['date'].date()}: {p['from'] or 'START'} -> {p['to']} | {p['reason']} | eq=${p['equity']:,.0f}")

    print(f"\n  Key Trades:")
    for t in r['trades']:
        extra = f" pnl={t['pnl_pct']:+.1f}%" if 'pnl_pct' in t else ""
        if t['action'].startswith(('BUY_T', 'SELL_ALL', 'SHORT_', 'DCA_CLOSE', 'DCA_TP', 'EARLY', 'SHORTS')):
            print(f"    {t['date'].date()}: {t['action']} @ ${t['price']:,.2f} (${t['amount']:,.0f}){extra}")


def main():
    print("=" * 80)
    print("  V13 ROUTER ENGINE v1")
    print("  Signal-driven: HH_HL+Fib (markup), ADX+Fib (markdown), HVF routing (router)")
    print("  Period: Oct 2024 -> Feb 2026 (one full cycle)")
    print("  Coins: BTC, ETH, SOL")
    print("=" * 80)

    config = V13Config()
    print(f"\n  Settings:")
    print(f"    Capital:          ${config.CAPITAL:,}")
    print(f"    Start:            {config.START_DATE}")
    print(f"    End:              {config.END_DATE}")
    print(f"    Markup tiers:     T1={config.TIER1_PCT:.0%} T2={config.TIER2_PCT:.0%} T3={config.TIER3_PCT:.0%}")
    print(f"    Short tiers:      T1={config.SHORT_TIER1_PCT:.0%} T2={config.SHORT_TIER2_PCT:.0%} T3={config.SHORT_TIER3_PCT:.0%}")
    print(f"    DCA:              {config.DCA_BO_PCT:.0%} BO, {config.DCA_SO_MULTIPLIER}x mult, {config.DCA_TP_PCT:.1%} TP, max {config.DCA_MAX_LAYERS}L")
    print(f"    Top detection:    2W OB{config.OB_THRESHOLD_2W} / 1W OB{config.OB_FALLBACK_1W} fallback / 1W K<{config.FAILSAFE_1W} failsafe")
    print(f"    Markup entry:     HH_HL({config.HH_HL_LOOKBACK}) + Fib_support({FIB_TOLERANCE:.0%} tol)")
    print(f"    Markdown entry:   ADX>{config.ADX_THRESHOLD} + Fib_break")
    print(f"    Markup failure:   >{config.MARKUP_FAIL_DD_PCT:.0%} DD + ADX>{config.MARKUP_FAIL_ADX} (safety net)")
    print(f"    ROUTER ranging:   ADX<{config.ROUTER_ADX_RANGING} for {config.ROUTER_ADX_SUSTAINED_DAYS}d + {config.ROUTER_MIN_EVAL_DAYS}d min eval")
    print(f"    Min phase hold:   {config.MIN_PHASE_DAYS} days")

    coins = ['ZEC', 'DOGE']
    all_results = []

    for coin in coins:
        print(f"\n{'=' * 60}")
        print(f"  Loading {coin}...")
        try:
            pack = V13SignalPack(coin)
        except Exception as e:
            print(f"  SKIP: {e}")
            continue

        bt = V13RouterV1(pack, config)
        result = bt.run()
        if result:
            print_results(result)
            all_results.append(result)

    if all_results:
        print(f"\n{'=' * 80}")
        print(f"  PORTFOLIO SUMMARY")
        print(f"{'=' * 80}")
        avg_closed = np.mean([r['closed_roi'] for r in all_results])
        avg_total = np.mean([r['roi'] for r in all_results])
        avg_bh = np.mean([r['buy_hold_return'] for r in all_results])
        worst_dd = min(r['max_drawdown'] for r in all_results)

        print(f"  Avg Closed ROI:     {avg_closed:+.1f}% (completed trades only)")
        print(f"  Avg Total ROI:      {avg_total:+.1f}% (incl open positions)")
        print(f"  Buy & Hold:         {avg_bh:+.1f}%")
        print(f"  Closed Alpha:       {avg_closed - avg_bh:+.1f}%")
        print(f"  Worst DD:           {worst_dd:.1f}%")

        print(f"\n  {'Coin':<6} {'Closed':>8} {'Total':>8} {'B&H':>8} {'Alpha':>8} {'MaxDD':>8} {'Cycles':>8}")
        print(f"  {'-'*58}")
        for r in all_results:
            print(f"  {r['coin']:<6} {r['closed_roi']:>+7.1f}% {r['roi']:>+7.1f}% {r['buy_hold_return']:>+7.1f}% "
                  f"{r['closed_roi'] - r['buy_hold_return']:>+7.1f}% {r['max_drawdown']:>7.1f}% "
                  f"{r['markup_cycles']:>8}")


if __name__ == '__main__':
    main()
