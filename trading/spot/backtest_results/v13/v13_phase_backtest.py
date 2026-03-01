"""
V13 Phase-Riding Backtest — Simulates the full V13 trading system.

Uses winning signals from matrix testing:
- Primary top: 2W StochRSI OB exit at th=93
- Failsafe top: 1W StochRSI K crosses below 50 (if primary hasn't fired)
- Early warning: 1W StochRSI K crosses below 97
- Bottom: 2W StochRSI OS exit at th=20
- Markup entry: 2W OS<20
- Confirmation: Daily SMA50 slope, BMSB, CFGI

Phases: DCA (home base) → MARKUP (long tiers) → DCA → MARKDOWN (flat/short) → DCA
Execution: simplified — no actual DCA engine, just track phase entries/exits and P&L.

Usage:
    python v13_phase_backtest.py
"""

import sys
import pandas as pd
import numpy as np
from datetime import timedelta
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack


# ── Configuration ──────────────────────────────────────────────────────

class V13Config:
    """V13 backtest configuration."""
    # StochRSI thresholds
    OB_THRESHOLD_2W = 93       # Primary top signal
    OS_THRESHOLD_2W = 20       # Primary bottom signal
    EARLY_WARNING_1W = 97      # 1W early warning threshold
    FAILSAFE_1W = 50           # 1W failsafe exit threshold
    FAILSAFE_WINDOW_WEEKS = 2  # Weeks after early warning before failsafe arms

    # Tier sizing (% of capital) — 90% total, 10% reserve
    # Front-loaded: high conviction = heavy early at lowest price
    TIER1_PCT = 0.60  # Entry — go heavy when conviction is high
    TIER2_PCT = 0.20  # Confirmation add
    TIER3_PCT = 0.10  # Momentum add
    TIER2_DELAY_WEEKS = 1  # Wait N weeks before T2
    TIER3_DELAY_WEEKS = 2  # Wait N weeks before T3

    # Minimum hold time before phase change allowed
    MIN_PHASE_WEEKS = 2

    # Cooldown period after top exit (weeks) before conductor can transition
    COOLDOWN_WEEKS = 4

    # Minimum 2W K peak during markup to consider it valid
    # SOL's false markup had 2W peak of only 29 — too low conviction
    MIN_MARKUP_2W_PEAK = 50  # If 2W K never reaches this, don't enter T2/T3

    # Starting capital
    CAPITAL = 10000

    # Test period
    START_DATE = '2024-09-01'
    END_DATE = '2026-02-17'


# ── Phase State Machine ───────────────────────────────────────────────

class PhaseState:
    DCA = 'DCA'
    MARKUP = 'MARKUP'
    MARKDOWN = 'MARKDOWN'
    COOLDOWN = 'COOLDOWN'  # Flat after exit signal, no buying, wait for conductor


class V13Backtest:
    """V13 Phase-Riding Backtest Engine."""

    def __init__(self, pack: V13SignalPack, config: V13Config = None):
        self.pack = pack
        self.cfg = config or V13Config()
        self.coin = pack.coin

        # State
        self.phase = PhaseState.DCA
        self.capital = self.cfg.CAPITAL
        self.position_value = 0.0  # Current position value in coin terms
        self.position_coins = 0.0
        self.entry_price = 0.0
        self.tier = 0  # 0=none, 1/2/3
        self.phase_start_date = None
        self.early_warning_date = None  # When 1W 97 cross-down fired
        self.failsafe_armed = False
        self.peak_2w_k = 0.0  # Track highest 2W K during markup

        # Short state (for MARKDOWN phase)
        self.short_coins = 0.0      # Coins shorted (positive = short position size)
        self.short_entry = 0.0      # Avg entry price of short
        self.short_cost = 0.0       # Capital used to open short
        self.markup_cycles_completed = 0  # Track completed markup→exit cycles
        self.shorts_enabled = False   # Only enable after first confirmed markup cycle

        # DCA state
        self.dca_position_coins = 0.0
        self.dca_entry_price = 0.0
        self.dca_layers = 0
        self.dca_last_buy = None
        self.dca_tp_target = 0.0  # TP price target
        self.dca_total_cost = 0.0
        self.dca_trades = 0
        self.dca_wins = 0
        self.dca_total_pnl = 0.0

        # Trade log
        self.trades = []
        self.phase_log = []
        self.equity_curve = []

        # Channel breakout detector (cold start fallback)
        from channel_breakout import ChannelBreakout
        self.channel_bo = ChannelBreakout(pack.daily)

        # Precompute signal series
        self._precompute_signals()

    def _get_first_breakout_after(self, start_date, current_date):
        """Get the first confirmed breakout dict after start_date that's <= current_date."""
        best = None
        best_date = None
        for bo in self.channel_bo.breakouts:
            if not bo['confirmed']:
                continue
            confirm_date = bo['retest_date'] or bo['breakout_date']
            if confirm_date and confirm_date > start_date and confirm_date <= current_date:
                if best_date is None or confirm_date < best_date:
                    best = bo
                    best_date = confirm_date
        return best

    def _precompute_signals(self):
        """Precompute all signal events for the backtest period."""
        stoch_2w = self.pack.stoch_2w
        stoch_1w = self.pack.stoch_1w

        # 2W OB exits at th=93
        self.ob_exits_2w = set(stoch_2w.ob_exits(self.cfg.OB_THRESHOLD_2W).index)
        # 2W OS exits at th=20
        self.os_exits_2w = set(stoch_2w.os_exits(self.cfg.OS_THRESHOLD_2W).index)

        # 1W early warning (K crosses below 97)
        df_1w = stoch_1w.df
        prev_k = df_1w['K'].shift(1)
        ew_mask = (prev_k >= self.cfg.EARLY_WARNING_1W) & (df_1w['K'] < self.cfg.EARLY_WARNING_1W)
        self.early_warnings_1w = set(df_1w[ew_mask].index)

        # 1W failsafe (K crosses below 50)
        fs_mask = (prev_k >= self.cfg.FAILSAFE_1W) & (df_1w['K'] < self.cfg.FAILSAFE_1W)
        self.failsafe_1w = set(df_1w[fs_mask].index)

        # 1W OS exits at th=20 (for faster bottom detection)
        self.os_exits_1w = set(stoch_1w.os_exits(20).index)

    def _nearest_signal(self, date, signal_set, tolerance_days=14):
        """Check if any signal fired within tolerance of this date."""
        for s in signal_set:
            if abs((s - date).days) <= tolerance_days:
                return s
        return None

    def _signal_on_date(self, date, signal_set, tolerance_days=7):
        """Check if signal fired on or very near this date."""
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

    def _buy(self, date, tier_pct, tier_num):
        """Buy into position."""
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
        """Sell entire position."""
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

    # ── DCA Engine (simplified) ──────────────────────────────────────

    def _dca_tick(self, date, price):
        """Run one DCA tick. Buys layers on dips, sells on TP."""
        if np.isnan(price):
            return

        # DCA parameters (Medium profile, more aggressive sizing)
        BO_PCT = 0.08       # 8% base order (was 4%)
        SO_DEVIATION = 0.025  # 2.5% between layers
        SO_MULTIPLIER = 1.5   # Volume multiplier (was 2.0 — less extreme scaling)
        TP_PCT = 0.015        # 1.5% take profit
        MAX_LAYERS = 8        # Medium profile
        MIN_INTERVAL_DAYS = 1  # Min days between buys

        available = self.capital * 0.90  # 90% available for DCA (10% reserve)

        # Check TP first
        if self.dca_position_coins > 0 and self.dca_tp_target > 0:
            if price >= self.dca_tp_target:
                # Hit TP — sell all
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

        # Check for new layer entry
        if self.dca_layers >= MAX_LAYERS:
            return

        if self.dca_last_buy and (date - self.dca_last_buy).days < MIN_INTERVAL_DAYS:
            return

        should_buy = False
        if self.dca_layers == 0:
            # Base order: buy if no position and we have capital
            should_buy = True
        else:
            # Safety order: buy if price dropped enough from avg entry
            target_drop = SO_DEVIATION * self.dca_layers
            if self.dca_entry_price > 0:
                current_drop = (self.dca_entry_price - price) / self.dca_entry_price
                if current_drop >= target_drop:
                    should_buy = True

        if should_buy:
            if self.dca_layers == 0:
                order_size = available * BO_PCT
            else:
                order_size = available * BO_PCT * (SO_MULTIPLIER ** min(self.dca_layers, 4))

            order_size = min(order_size, self.capital * 0.3)  # Cap single order at 30%
            if order_size < 10 or order_size > self.capital:
                return

            coins = order_size / price
            self.dca_position_coins += coins
            self.capital -= order_size
            self.dca_total_cost += order_size
            self.dca_layers += 1
            self.dca_last_buy = date

            # Recalc avg entry
            self.dca_entry_price = self.dca_total_cost / self.dca_position_coins

            # Set TP
            self.dca_tp_target = self.dca_entry_price * (1 + TP_PCT)

            self.trades.append({
                'date': date, 'action': f'DCA_BUY_L{self.dca_layers}',
                'price': price, 'amount': order_size,
                'coins': coins, 'phase': self.phase
            })

    def _dca_close_at_market(self, date, reason):
        """Force-close DCA position (for phase transition)."""
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

    def _open_short(self, date, pct):
        """Open a short position with pct of capital."""
        price = self._get_price(date)
        if np.isnan(price):
            return
        amount = self.capital * pct
        if amount <= 0:
            return
        coins = amount / price
        self.short_coins += coins
        self.short_entry = price if self.short_entry == 0 else (
            (self.short_cost + amount) / (self.short_coins) * (self.short_coins / (self.short_coins)) 
        )
        # Recalc avg entry properly
        self.short_cost += amount
        self.short_entry = self.short_cost / self.short_coins
        self.capital -= amount  # Margin locked
        self.trades.append({
            'date': date, 'action': f'SHORT_OPEN', 'price': price,
            'amount': amount, 'coins': coins, 'phase': self.phase
        })

    def _close_short(self, date, reason):
        """Close short position."""
        if self.short_coins <= 0:
            return 0
        price = self._get_price(date)
        if np.isnan(price):
            return 0
        # Short profit = (entry - current) * coins
        pnl = (self.short_entry - price) * self.short_coins
        pnl_pct = (self.short_entry - price) / self.short_entry * 100
        # Return margin + profit (or minus loss)
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

    def _total_equity(self, date):
        """Total equity = cash + markup position + DCA position + short PnL."""
        price = self._get_price(date)
        if np.isnan(price):
            return self.capital
        equity = self.capital + self.position_coins * price + self.dca_position_coins * price
        # Short position: margin is already subtracted from capital, add unrealized PnL
        if self.short_coins > 0:
            short_pnl = (self.short_entry - price) * self.short_coins
            equity += short_pnl + self.short_cost  # margin + unrealized PnL
        return equity

    def _change_phase(self, date, new_phase, reason):
        """Transition to new phase."""
        old = self.phase

        # Close short if leaving MARKDOWN
        if old == PhaseState.MARKDOWN and self.short_coins > 0:
            self._close_short(date, f'EXIT_MARKDOWN->{new_phase}')

        self.phase = new_phase
        self.phase_start_date = date
        self.phase_log.append({
            'date': date, 'from': old, 'to': new_phase, 'reason': reason,
            'equity': self._total_equity(date), 'price': self._get_price(date)
        })

        # Track completed markup cycles (markup → cooldown = confirmed cycle)
        if old == PhaseState.MARKUP and new_phase == PhaseState.COOLDOWN:
            self.markup_cycles_completed += 1
            if not self.shorts_enabled:
                self.shorts_enabled = True
                self.trades.append({
                    'date': date, 'action': f'SHORTS_ENABLED (cycle #{self.markup_cycles_completed})',
                    'price': self._get_price(date), 'amount': 0, 'coins': 0, 'phase': new_phase
                })

        # Open short when entering MARKDOWN — only if shorts enabled (after first confirmed cycle)
        if new_phase == PhaseState.MARKDOWN and self.capital > 0 and self.shorts_enabled:
            self._open_short(date, 0.60)

    def run(self):
        """Run the backtest."""
        daily = self.pack.daily
        start = pd.Timestamp(self.cfg.START_DATE)
        end = pd.Timestamp(self.cfg.END_DATE)

        # Filter to test period
        test_data = daily[(daily.index >= start) & (daily.index <= end)]
        if len(test_data) == 0:
            print(f"  No data for {self.coin} in test period")
            return

        self.phase = PhaseState.DCA
        self.phase_start_date = test_data.index[0]
        self.start_date = test_data.index[0]
        self._cold_start_used = False
        self.phase_log.append({
            'date': test_data.index[0], 'from': None, 'to': PhaseState.DCA,
            'reason': 'START', 'equity': self.cfg.CAPITAL,
            'price': test_data['close'].iloc[0]
        })

        # Check every day (but signals fire on weekly boundaries)
        for i, (date, row) in enumerate(test_data.iterrows()):
            price = row['close']
            equity = self._total_equity(date)
            self.equity_curve.append({'date': date, 'equity': equity, 'price': price, 'phase': self.phase})

            # Minimum hold time check
            if self.phase_start_date and (date - self.phase_start_date).days < self.cfg.MIN_PHASE_WEEKS * 7:
                continue

            if self.phase == PhaseState.DCA:
                # Run DCA engine every day
                self._dca_tick(date, price)
                # Check for phase transitions (after DCA tick so TPs can hit)
                self._check_dca_transitions(date)
            elif self.phase == PhaseState.MARKUP:
                # DCA positions ride alongside markup — let TPs hit naturally (graceful)
                if self.dca_position_coins > 0:
                    self._dca_tick(date, price)
                self._check_markup_transitions(date)
                self._check_markup_tiers(date)
            elif self.phase == PhaseState.COOLDOWN:
                # Flat — no buying. Wait for conductor to determine next phase.
                self._check_cooldown_transitions(date)
            elif self.phase == PhaseState.MARKDOWN:
                self._check_markdown_transitions(date)

        # Close any open positions at end
        if self.position_coins > 0:
            self._sell_all(test_data.index[-1], 'BACKTEST_END')
        if self.dca_position_coins > 0:
            self._dca_close_at_market(test_data.index[-1], 'BACKTEST_END')
        if self.short_coins > 0:
            self._close_short(test_data.index[-1], 'BACKTEST_END')

        return self._results()

    def _check_dca_transitions(self, date):
        """From DCA, check for markup or markdown entry."""
        # Check for markup entry: 2W OS exit
        sig = self._signal_on_date(date, self.os_exits_2w)
        if sig:
            sma50_pos = self.pack.structure.sma50_slope_positive(date, 10)
            hh_hl = self.pack.structure.hh_hl_streak(date, 2)
            bmsb = self.pack.bmsb.status_at(date)

            dca_note = ""
            if self.dca_position_coins > 0:
                dca_note = f", DCA riding ({self.dca_layers}L, {self.dca_position_coins:.4f} coins)"
            self._change_phase(date, PhaseState.MARKUP,
                f'2W OS exit + daily={sma50_pos or hh_hl} + BMSB={bmsb}{dca_note}')
            self._buy(date, self.cfg.TIER1_PCT, 1)
            self.early_warning_date = None
            self.failsafe_armed = False
            self.peak_2w_k = 0
            return

        # Cold start fallback: channel breakout detection
        # Retest-confirmed = strong signal → enter phase directly
        # Run without retest = weak signal → orient only (know where we are, don't chase)
        if self.markup_cycles_completed == 0 and not self._cold_start_used:
            bo = self._get_first_breakout_after(self.start_date, date)
            if bo:
                strong = bo['retest_found'] and bo['retest_held'] and not bo['no_retest_run']
                bo_dir = 'MARKUP' if bo['direction'] == 'BULLISH' else 'MARKDOWN'
                confirm_date = bo['retest_date'] or bo['breakout_date']

                if strong:
                    # Strong signal (retest confirmed) → enter phase directly
                    self._cold_start_used = True
                    self.markup_cycles_completed = 1
                    self.shorts_enabled = True
                    if bo_dir == 'MARKUP':
                        dca_note = ""
                        if self.dca_position_coins > 0:
                            dca_note = f", DCA riding ({self.dca_layers}L)"
                        self._change_phase(date, PhaseState.MARKUP,
                            f'CHANNEL_BREAKOUT+RETEST {confirm_date.date()} (strong cold start){dca_note}')
                        self._buy(date, self.cfg.TIER1_PCT, 1)
                        self.early_warning_date = None
                        self.failsafe_armed = False
                        self.peak_2w_k = 0
                        return
                    else:  # MARKDOWN
                        if self.dca_position_coins > 0:
                            self._dca_close_at_market(date, 'CHANNEL_BREAKDOWN+RETEST')
                        self._change_phase(date, PhaseState.MARKDOWN,
                            f'CHANNEL_BREAKDOWN+RETEST {confirm_date.date()} (strong cold start)')
                        return
                else:
                    # Weak signal (ran without retest) → orient only, don't chase
                    # Only enable shorts if we've observed both bullish AND bearish structure
                    self._cold_start_used = True
                    self.markup_cycles_completed = 1
                    # Don't enable shorts on weak signal — need retest-confirmed cycle first
                    self.trades.append({
                        'date': date, 'action': f'COLD_START_ORIENTED ({bo_dir} run {confirm_date.date()})',
                        'price': self._get_price(date), 'amount': 0, 'coins': 0, 'phase': self.phase
                    })

        # Check for markdown entry — two paths:
        # Path A: 2W OB exit + below BMSB (direct, after distribution)
        sig = self._signal_on_date(date, self.ob_exits_2w)
        if sig:
            bmsb = self.pack.bmsb.status_at(date)
            if bmsb == 'BELOW':
                cfgi = self.pack.cfgi.value_at(date)
                if self.dca_position_coins > 0:
                    self._dca_close_at_market(date, 'MARKDOWN_ENTRY')
                self._change_phase(date, PhaseState.MARKDOWN,
                    f'2W OB exit + BMSB=BELOW + CFGI={cfgi:.0f}')
                return

        # Path B: Bear market detection from DCA (no prior OB exit needed)
        # Requires: BELOW BMSB + SMA50 declining + 1W K < 30 (sustained weakness)
        bmsb = self.pack.bmsb.status_at(date)
        if bmsb == 'BELOW':
            k_1w = self.pack.stoch_1w.get_k_at(date)
            slope = self.pack.structure.sma50_slope_at(date, 10)
            adx = self.pack.structure.adx_at(date)
            if (not np.isnan(k_1w) and k_1w < 30 and
                not np.isnan(slope) and slope < -1 and
                not np.isnan(adx) and adx > 20):
                cfgi = self.pack.cfgi.value_at(date)
                if self.dca_position_coins > 0:
                    self._dca_close_at_market(date, 'MARKDOWN_DETECTED')
                self._change_phase(date, PhaseState.MARKDOWN,
                    f'Bear detected: BMSB=BELOW + SMA50={slope:.1f}% + 1W_K={k_1w:.0f} + ADX={adx:.0f} + CFGI={cfgi:.0f}')
                return

    def _check_markup_transitions(self, date):
        """From MARKUP, check for exit signals."""
        # Track peak 2W K during this markup phase
        k_2w = self.pack.stoch_2w.get_k_at(date)
        if not np.isnan(k_2w) and k_2w > self.peak_2w_k:
            self.peak_2w_k = k_2w

        # Layer 1: Early warning — 1W crosses below 97
        sig = self._signal_on_date(date, self.early_warnings_1w)
        if sig and self.early_warning_date is None:
            self.early_warning_date = date
            self.trades.append({
                'date': date, 'action': f'EARLY_WARNING_1W_97 (2W_peak={self.peak_2w_k:.0f})',
                'price': self._get_price(date), 'amount': 0, 'coins': 0,
                'phase': self.phase
            })

        # Layer 2: Primary exit — 2W OB exit at th=93
        sig = self._signal_on_date(date, self.ob_exits_2w)
        if sig:
            pnl = self._sell_all(date, 'PRIMARY_2W_OB93')
            if self.dca_position_coins > 0:
                self._dca_close_at_market(date, 'TOP_EXIT_CLEANUP')
            self._change_phase(date, PhaseState.COOLDOWN, f'2W OB exit th=93, pnl={pnl:+.1f}%')
            self.early_warning_date = None
            self.failsafe_armed = False
            self.peak_2w_k = 0
            return

        # Layer 2b: If 2W never reached OB (peak < 93), use 1W OB exit at th=85 as primary
        if self.peak_2w_k < self.cfg.OB_THRESHOLD_2W and self.early_warning_date:
            # 1W was OB but 2W wasn't strong enough — use 1W as primary
            stoch_1w = self.pack.stoch_1w
            df_1w = stoch_1w.df
            prev_k = df_1w['K'].shift(1)
            ob85_mask = (prev_k >= 85) & (df_1w['K'] < 85)
            ob85_exits = set(df_1w[ob85_mask].index)
            sig = self._signal_on_date(date, ob85_exits)
            if sig:
                pnl = self._sell_all(date, 'FALLBACK_1W_OB85 (2W never OB)')
                if self.dca_position_coins > 0:
                    self._dca_close_at_market(date, 'TOP_EXIT_CLEANUP')
                self._change_phase(date, PhaseState.COOLDOWN,
                    f'1W OB exit th=85 (2W peak={self.peak_2w_k:.0f}<93), pnl={pnl:+.1f}%')
                self.early_warning_date = None
                self.failsafe_armed = False
                self.peak_2w_k = 0
                return

        # Layer 3: Failsafe — arm after early warning + window
        if self.early_warning_date and not self.failsafe_armed:
            weeks_since = (date - self.early_warning_date).days / 7
            if weeks_since >= self.cfg.FAILSAFE_WINDOW_WEEKS:
                self.failsafe_armed = True

        if self.failsafe_armed:
            sig = self._signal_on_date(date, self.failsafe_1w)
            if sig:
                pnl = self._sell_all(date, 'FAILSAFE_1W_K50')
                if self.dca_position_coins > 0:
                    self._dca_close_at_market(date, 'TOP_EXIT_CLEANUP')
                self._change_phase(date, PhaseState.COOLDOWN, f'Failsafe 1W K<50, pnl={pnl:+.1f}%')
                self.early_warning_date = None
                self.failsafe_armed = False
                self.peak_2w_k = 0
                return

    def _check_markup_tiers(self, date):
        """Add T2/T3 if conditions met."""
        if self.tier >= 3 or self.phase_start_date is None:
            return
        weeks_in = (date - self.phase_start_date).days / 7

        if self.tier == 1 and weeks_in >= self.cfg.TIER2_DELAY_WEEKS:
            # T2: price must be above entry (not falling knife) + CFGI not fearful
            price = self._get_price(date)
            cfgi = self.pack.cfgi.value_at(date)
            if (not np.isnan(price) and self.entry_price > 0 and
                price >= self.entry_price and
                not np.isnan(cfgi) and cfgi > 40):
                self._buy(date, self.cfg.TIER2_PCT, 2)

        elif self.tier == 2 and weeks_in >= self.cfg.TIER3_DELAY_WEEKS:
            # T3: price above entry + strong trend + higher high structure
            price = self._get_price(date)
            adx = self.pack.structure.adx_at(date)
            hh = self.pack.structure.hh_hl_streak(date, 1)
            if (not np.isnan(price) and self.entry_price > 0 and
                price >= self.entry_price and
                not np.isnan(adx) and adx > 25 and hh):
                self._buy(date, self.cfg.TIER3_PCT, 3)

    def _check_cooldown_transitions(self, date):
        """From COOLDOWN (flat after top exit), let conductor determine next phase."""
        # Check for markup re-entry: 2W OS exit (new cycle bottom)
        sig = self._signal_on_date(date, self.os_exits_2w)
        if sig:
            sma50_pos = self.pack.structure.sma50_slope_positive(date, 10)
            bmsb = self.pack.bmsb.status_at(date)
            self._change_phase(date, PhaseState.MARKUP,
                f'COOLDOWN->MARKUP: 2W OS exit + daily={sma50_pos} + BMSB={bmsb}')
            self._buy(date, self.cfg.TIER1_PCT, 1)
            self.early_warning_date = None
            self.failsafe_armed = False
            self.peak_2w_k = 0
            return

        # Check for markdown: sustained weakness below BMSB
        bmsb = self.pack.bmsb.status_at(date)
        if bmsb == 'BELOW':
            k_1w = self.pack.stoch_1w.get_k_at(date)
            slope = self.pack.structure.sma50_slope_at(date, 10)
            adx = self.pack.structure.adx_at(date)
            if (not np.isnan(k_1w) and k_1w < 30 and
                not np.isnan(slope) and slope < -1 and
                not np.isnan(adx) and adx > 20):
                cfgi = self.pack.cfgi.value_at(date)
                self._change_phase(date, PhaseState.MARKDOWN,
                    f'COOLDOWN->MARKDOWN: BMSB=BELOW + SMA50={slope:.1f}% + 1W_K={k_1w:.0f} + ADX={adx:.0f} + CFGI={cfgi:.0f}')
                return

        # Check for DCA re-entry: if market stabilizes (above BMSB + no bear signals)
        # Only after cooldown period — market didn't go markdown, resume DCA
        if self.phase_start_date and (date - self.phase_start_date).days >= self.cfg.COOLDOWN_WEEKS * 7:
            if bmsb == 'ABOVE':
                cfgi = self.pack.cfgi.value_at(date)
                if not np.isnan(cfgi) and cfgi > 40:
                    self._change_phase(date, PhaseState.DCA,
                        f'COOLDOWN->DCA: 4wk+ flat + BMSB=ABOVE + CFGI={cfgi:.0f}')
                    return

    def _check_markdown_transitions(self, date):
        """From MARKDOWN, check for exit to DCA."""
        # 2W OS exit
        sig = self._signal_on_date(date, self.os_exits_2w)
        if sig:
            sma50_pos = self.pack.structure.sma50_slope_positive(date, 10)
            cfgi_rising = self.pack.cfgi.rising_from_fear(date)
            self._change_phase(date, PhaseState.DCA,
                f'2W OS exit + sma50_pos={sma50_pos} + cfgi_rising={cfgi_rising}')
            return

        # Fallback: 1W OS exit (faster)
        sig = self._signal_on_date(date, self.os_exits_1w)
        if sig:
            sma50_pos = self.pack.structure.sma50_slope_positive(date, 10)
            if sma50_pos:
                self._change_phase(date, PhaseState.DCA, f'1W OS exit + SMA50 positive')
                return

    def _results(self):
        """Compute backtest results."""
        if not self.equity_curve:
            return None

        eq = pd.DataFrame(self.equity_curve)
        eq.set_index('date', inplace=True)

        final_equity = eq['equity'].iloc[-1]
        roi = (final_equity - self.cfg.CAPITAL) / self.cfg.CAPITAL * 100

        # Max drawdown
        peak = eq['equity'].expanding().max()
        dd = (eq['equity'] - peak) / peak * 100
        max_dd = dd.min()

        # Phase counts
        phase_changes = len(self.phase_log) - 1  # Exclude initial
        time_in_markup = sum(1 for e in self.equity_curve if e['phase'] == PhaseState.MARKUP)
        time_in_dca = sum(1 for e in self.equity_curve if e['phase'] == PhaseState.DCA)
        time_in_markdown = sum(1 for e in self.equity_curve if e['phase'] == PhaseState.MARKDOWN)
        time_in_cooldown = sum(1 for e in self.equity_curve if e['phase'] == PhaseState.COOLDOWN)
        total = len(self.equity_curve)

        # Trade stats
        trades_with_pnl = [t for t in self.trades if 'pnl_pct' in t]
        wins = [t for t in trades_with_pnl if t['pnl_pct'] > 0]
        losses = [t for t in trades_with_pnl if t['pnl_pct'] <= 0]

        # Buy & hold comparison
        start_price = eq['price'].iloc[0]
        end_price = eq['price'].iloc[-1]
        bh_return = (end_price - start_price) / start_price * 100

        return {
            'coin': self.coin,
            'start': eq.index[0],
            'end': eq.index[-1],
            'capital': self.cfg.CAPITAL,
            'final_equity': final_equity,
            'roi': roi,
            'max_drawdown': max_dd,
            'buy_hold_return': bh_return,
            'outperformance': roi - bh_return,
            'phase_changes': phase_changes,
            'time_markup_pct': time_in_markup / total * 100,
            'time_dca_pct': time_in_dca / total * 100,
            'time_cooldown_pct': time_in_cooldown / total * 100,
            'time_markdown_pct': time_in_markdown / total * 100,
            'total_trades': len(self.trades),
            'closed_trades': len(trades_with_pnl),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(trades_with_pnl) * 100 if trades_with_pnl else 0,
            'avg_win': np.mean([t['pnl_pct'] for t in wins]) if wins else 0,
            'avg_loss': np.mean([t['pnl_pct'] for t in losses]) if losses else 0,
            'dca_trades': self.dca_trades,
            'dca_wins': self.dca_wins,
            'dca_total_pnl': self.dca_total_pnl,
            'equity_curve': eq,
            'trades': self.trades,
            'phases': self.phase_log,
        }


# ── Runner ─────────────────────────────────────────────────────────────

def print_results(r):
    """Pretty print backtest results."""
    if r is None:
        return
    print(f"\n  {r['coin']} Results:")
    print(f"  {'─' * 50}")
    print(f"  ROI:              {r['roi']:+.1f}%")
    print(f"  Buy & Hold:       {r['buy_hold_return']:+.1f}%")
    print(f"  Outperformance:   {r['outperformance']:+.1f}%")
    print(f"  Max Drawdown:     {r['max_drawdown']:.1f}%")
    print(f"  Final Equity:     ${r['final_equity']:,.0f}")
    print(f"  Phase Changes:    {r['phase_changes']}")
    print(f"  Time in MARKUP:   {r['time_markup_pct']:.0f}%")
    print(f"  Time in DCA:      {r['time_dca_pct']:.0f}%")
    print(f"  Time in COOLDOWN: {r['time_cooldown_pct']:.0f}%")
    print(f"  Time in MARKDOWN: {r['time_markdown_pct']:.0f}%")
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

    print(f"\n  Trades:")
    for t in r['trades']:
        extra = f" pnl={t['pnl_pct']:+.1f}%" if 'pnl_pct' in t else ""
        print(f"    {t['date'].date()}: {t['action']} @ ${t['price']:,.2f} "
              f"(${t['amount']:,.0f}, {t['coins']:.4f} coins){extra}")


def run_sweep():
    """Sweep cooldown period to find optimal value."""
    print("=" * 80)
    print("  COOLDOWN PERIOD SWEEP")
    print("=" * 80)

    coins = ['BTC', 'ETH', 'SOL']
    cooldown_weeks = [2, 3, 4, 6, 8]

    print(f"\n  {'CD_WK':>5} | {'Avg ROI':>8} | {'Avg DD':>8} | {'Worst DD':>9} | {'BTC':>7} | {'ETH':>7} | {'SOL':>7}")
    print(f"  {'─'*70}")

    for cd in cooldown_weeks:
        config = V13Config()
        config.COOLDOWN_WEEKS = cd
        results = []
        for coin in coins:
            pack = V13SignalPack(coin)
            bt = V13Backtest(pack, config)
            r = bt.run()
            if r:
                results.append(r)
        if results:
            avg_roi = np.mean([r['roi'] for r in results])
            avg_dd = np.mean([r['max_drawdown'] for r in results])
            worst_dd = min(r['max_drawdown'] for r in results)
            rois = {r['coin']: r['roi'] for r in results}
            print(f"  {cd:>5} | {avg_roi:>+7.1f}% | {avg_dd:>7.1f}% | {worst_dd:>8.1f}% | "
                  f"{rois.get('BTC',0):>+6.1f}% | {rois.get('ETH',0):>+6.1f}% | {rois.get('SOL',0):>+6.1f}%")

    print()


def main():
    import sys as _sys
    if '--sweep-cooldown' in _sys.argv:
        run_sweep()
        return

    print("=" * 80)
    print("  V13 PHASE-RIDING BACKTEST")
    print("  Signals: 2W OB>93 (top) + 1W K<50 failsafe + 2W OS<20 (bottom)")
    print("  Period: Sep 2024 -> Feb 2026")
    print("=" * 80)

    coins = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP']
    config = V13Config()
    all_results = []

    for coin in coins:
        print(f"\n{'=' * 60}")
        print(f"  Loading {coin}...")

        try:
            pack = V13SignalPack(coin)
        except ValueError as e:
            print(f"  SKIP: {e}")
            continue

        bt = V13Backtest(pack, config)
        result = bt.run()
        if result:
            print_results(result)
            all_results.append(result)

    # Portfolio summary
    if all_results:
        print(f"\n{'=' * 80}")
        print(f"  PORTFOLIO SUMMARY (equal weight)")
        print(f"{'=' * 80}")
        avg_roi = np.mean([r['roi'] for r in all_results])
        avg_bh = np.mean([r['buy_hold_return'] for r in all_results])
        avg_dd = np.mean([r['max_drawdown'] for r in all_results])
        worst_dd = min(r['max_drawdown'] for r in all_results)
        total_changes = sum(r['phase_changes'] for r in all_results)

        print(f"  Avg ROI:            {avg_roi:+.1f}% (vs B&H {avg_bh:+.1f}%)")
        print(f"  Avg Outperformance: {avg_roi - avg_bh:+.1f}%")
        print(f"  Avg Max DD:         {avg_dd:.1f}%")
        print(f"  Worst DD:           {worst_dd:.1f}%")
        print(f"  Total Phase Changes:{total_changes} across {len(all_results)} coins")

        print(f"\n  Per-Coin Summary:")
        print(f"  {'Coin':<6} {'ROI':>8} {'B&H':>8} {'Alpha':>8} {'MaxDD':>8} {'Phases':>8}")
        print(f"  {'─'*48}")
        for r in all_results:
            print(f"  {r['coin']:<6} {r['roi']:>+7.1f}% {r['buy_hold_return']:>+7.1f}% "
                  f"{r['outperformance']:>+7.1f}% {r['max_drawdown']:>7.1f}% {r['phase_changes']:>8}")


if __name__ == '__main__':
    main()
