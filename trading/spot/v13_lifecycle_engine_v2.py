"""
V13 Lifecycle Engine v2 -- Live wrapper around V13 Phase Backtest v8.

This wraps the ACTUAL v8 phase backtest engine (v13_phase_backtest_v8.py) for live trading.
Same code, same signals, same state machine. No reimplementation.

The v8 engine runs on daily candles. This wrapper:
1. Accumulates 1h candles and triggers daily tick at midnight UTC
2. Runs the DCA engine on hourly price updates (live mode only)
3. Emits actions (BUY/SELL/SHORT/SHORT_CLOSE) for the paper runner
4. Provides state persistence (snapshot/restore)
5. Provides dashboard-compatible status output
"""

import logging
import json
import numpy as np
import pandas as pd
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import sys

# Import v8 PHASE backtest engine and its dependencies
_V13_DIR = Path(__file__).parent / 'backtest_results' / 'v13'
sys.path.insert(0, str(_V13_DIR))
from v13_phase_backtest_v8 import V13BacktestV8, V13Config as V8Config, Phase
from v13_signals import V13SignalPack

logger = logging.getLogger(__name__)


# Profile presets matching v13_phase_backtest_v8 config
# The 'high' profile matches the backtest defaults exactly
PROFILES = {
    'low': {
        'TIER1_PCT': 0.40, 'TIER2_PCT': 0.15, 'TIER3_PCT': 0.05,
        'TIER2_DELAY_WEEKS': 3, 'TIER3_DELAY_WEEKS': 6,
        'SHORT_TIER1_PCT': 0.40, 'SHORT_TIER2_PCT': 0.15, 'SHORT_TIER3_PCT': 0.05,
        'SHORT_TIER2_DELAY_WEEKS': 3, 'SHORT_TIER3_DELAY_WEEKS': 6,
        'DCA_BO_PCT': 0.05, 'DCA_MAX_LAYERS': 5,
    },
    'medium': {
        'TIER1_PCT': 0.50, 'TIER2_PCT': 0.20, 'TIER3_PCT': 0.10,
        'TIER2_DELAY_WEEKS': 2, 'TIER3_DELAY_WEEKS': 4,
        'SHORT_TIER1_PCT': 0.50, 'SHORT_TIER2_PCT': 0.20, 'SHORT_TIER3_PCT': 0.10,
        'SHORT_TIER2_DELAY_WEEKS': 2, 'SHORT_TIER3_DELAY_WEEKS': 4,
        'DCA_BO_PCT': 0.06, 'DCA_MAX_LAYERS': 6,
    },
    'high': {
        'TIER1_PCT': 0.60, 'TIER2_PCT': 0.20, 'TIER3_PCT': 0.10,
        'TIER2_DELAY_WEEKS': 1, 'TIER3_DELAY_WEEKS': 2,
        'SHORT_TIER1_PCT': 0.60, 'SHORT_TIER2_PCT': 0.20, 'SHORT_TIER3_PCT': 0.10,
        'SHORT_TIER2_DELAY_WEEKS': 1, 'SHORT_TIER3_DELAY_WEEKS': 2,
        'DCA_BO_PCT': 0.08, 'DCA_MAX_LAYERS': 8,
    },
}


class V13Config:
    """Config wrapper that creates a V8Config with profile settings."""

    @staticmethod
    def from_profile(profile: str = 'high', capital: float = 10000) -> V8Config:
        cfg = V8Config()
        cfg.CAPITAL = capital
        p = PROFILES.get(profile, PROFILES['high'])
        for key, val in p.items():
            setattr(cfg, key, val)
        return cfg


class V13LifecycleEngineV2:
    """
    Live wrapper around V13BacktestV8 (from v13_phase_backtest_v8.py).

    The v8 engine is a daily-tick state machine. This wrapper:
    - Feeds it daily candles (resampled from 1h during live)
    - Intercepts its trades list to emit actions
    - Provides persistence via snapshot/restore
    - Runs the DCA engine on hourly updates for responsiveness (live only)
    """

    def __init__(self, symbol: str, capital: float, config=None):
        self.symbol = symbol
        self.initial_capital = capital
        self.coin = symbol.split('/')[0] if '/' in symbol else symbol

        # Create v8 config
        if isinstance(config, V8Config):
            self._v8_config = config
        else:
            self._v8_config = V8Config()
        self._v8_config.CAPITAL = capital

        # Initialize signal pack from DB
        try:
            self.pack = V13SignalPack(self.coin)
        except Exception as e:
            logger.error(f"Failed to load V13SignalPack for {self.coin}: {e}")
            self.pack = None

        # Create the v8 engine (the ACTUAL phase backtest engine)
        if self.pack:
            self._engine = V13BacktestV8(self.pack, self._v8_config)
        else:
            self._engine = None

        # Tracking for live wrapper
        self._last_daily_date: Optional[str] = None
        self._last_trade_count: int = 0
        self._live_mode: bool = False
        self._candles_1h: List[dict] = []
        self.current_price: float = 0.0
        self.start_time: float = datetime.now(timezone.utc).timestamp()

        logger.info(f"V13EngineV2 initialized for {symbol}, capital=${capital:,.0f}")

    # Properties that delegate to the v8 engine (runner accesses these directly)
    @property
    def phase(self):
        return self._engine.phase if self._engine else 'DCA'

    @property
    def realized_pnl(self):
        """Total realized PnL from ALL closed trades (markup sells + shorts + DCA)."""
        if not self._engine:
            return 0.0
        total = 0.0
        for t in self._engine.trades:
            if 'pnl_pct' in t and 'OPEN_END' not in t.get('action', ''):
                amount = t.get('amount', 0)
                pnl_pct = t.get('pnl_pct', 0)
                pnl_dollar = amount * pnl_pct / (100 + pnl_pct) if (100 + pnl_pct) != 0 else 0
                total += pnl_dollar
        return total

    @property
    def deals_completed(self):
        return self._engine.dca_trades if self._engine else 0

    @property
    def deals_won(self):
        return self._engine.dca_wins if self._engine else 0

    @property
    def max_drawdown_pct(self):
        if not self._engine or not self._engine.equity_curve:
            return 0.0
        eq = pd.Series([e['equity'] for e in self._engine.equity_curve])
        peak = eq.expanding().max()
        dd = (eq - peak) / peak * 100
        return abs(dd.min()) if len(dd) > 0 else 0.0

    def tick(self, candle_1h: dict, cash_available: float) -> List[dict]:
        """
        Process one 1h candle. Returns list of action dicts.

        Accumulates 1h candles. On daily boundary, triggers the v8 engine's
        full daily tick (phase checks, signal evaluation, tier adds, etc).
        Between daily ticks, runs DCA engine for responsiveness (live only).
        """
        actions = []
        if self._engine is None:
            return actions

        try:
            ts = self._parse_timestamp(candle_1h.get('timestamp'))
            price = float(candle_1h['close'])
            self.current_price = price

            # Initialize engine phase start on first tick
            if self._engine.phase_start_date is None:
                self._engine.phase_start_date = ts.replace(tzinfo=None)

            # Accumulate for daily resampling
            self._candles_1h.append({
                'timestamp': ts,
                'open': float(candle_1h['open']),
                'high': float(candle_1h['high']),
                'low': float(candle_1h['low']),
                'close': price,
                'volume': float(candle_1h.get('volume', 0))
            })

            # Check daily boundary (midnight UTC)
            current_date = ts.strftime('%Y-%m-%d')
            new_daily = False
            if self._last_daily_date is None:
                self._last_daily_date = current_date
            elif current_date != self._last_daily_date:
                self._last_daily_date = current_date
                new_daily = True

            if new_daily:
                # Refresh signal pack in live mode
                if self._live_mode:
                    try:
                        self.pack = V13SignalPack(self.coin)
                        self._engine.pack = self.pack
                        self._engine.daily = self.pack.daily
                        self._engine._precompute_stoch()
                        logger.info(f"{self.symbol} Signal pack refreshed")
                    except Exception as e:
                        logger.warning(f"Signal pack refresh failed for {self.symbol}: {e}")

                # Use previous day's daily close from the signal pack
                # v8 backtest iterates daily bars: for date, row: price = row['close']
                # So daily tick should use the daily close at prev day's date
                prev_date_str = (ts - timedelta(days=1)).strftime('%Y-%m-%d')
                prev_date_ts = pd.Timestamp(prev_date_str)
                daily_close = self._engine._price(prev_date_ts)
                if np.isnan(daily_close):
                    daily_close = price  # fallback to current 1h price

                # Run daily tick at prev day's date with daily close price
                actions.extend(self._run_daily_tick(prev_date_ts.to_pydatetime(), daily_close))

                # Clear old candles (keep only current day)
                self._candles_1h = [c for c in self._candles_1h
                                    if c['timestamp'].strftime('%Y-%m-%d') == current_date]

            else:
                # Between daily ticks: run DCA engine for hourly responsiveness
                # In live mode: hourly DCA for better fills
                # In backfill mode: skip hourly DCA (match v8 backtest = daily only)
                if self._live_mode and self._engine.phase in (Phase.DCA, Phase.MARKUP):
                    date_ts = pd.Timestamp(ts.replace(tzinfo=None))
                    old_trade_count = len(self._engine.trades)
                    self._engine._dca_tick(date_ts, price)
                    actions.extend(self._extract_new_actions(old_trade_count))

        except Exception as e:
            logger.error(f"V13EngineV2 tick error for {self.symbol}: {e}", exc_info=True)

        return actions

    def _run_daily_tick(self, ts: datetime, price: float) -> List[dict]:
        """Run the v8 engine's full daily logic for one day.
        
        Matches the v8 phase backtest run() loop exactly:
        - Record equity
        - 3-day min hold check
        - Phase-specific logic via _check_dca/_check_markup/_check_flat/_check_markdown
        """
        actions = []
        date = pd.Timestamp(ts)
        eng = self._engine

        old_trade_count = len(eng.trades)
        old_phase = eng.phase

        # Record equity
        equity = eng._total_equity(date)
        eng.equity_curve.append({
            'date': date, 'equity': equity, 'price': price, 'phase': eng.phase
        })

        # 3-day min hold check (matches v8: MIN_PHASE_DAYS)
        if (eng.phase_start_date and
                (date - pd.Timestamp(eng.phase_start_date)).days < eng.cfg.MIN_PHASE_DAYS):
            # Still run DCA ticks during hold
            if eng.phase in (Phase.DCA, Phase.MARKUP) and eng.dca_coins > 0:
                eng._dca_tick(date, price)
        else:
            # Full phase logic (matches v8 run() loop exactly)
            if eng.phase == Phase.DCA:
                eng._check_dca(date, price)
            elif eng.phase == Phase.MARKUP:
                eng._check_markup(date, price)
            elif eng.phase == Phase.FLAT:
                eng._check_flat(date, price)
            elif eng.phase == Phase.MARKDOWN:
                eng._check_markdown(date, price)

        # Extract any new actions from engine trades
        actions.extend(self._extract_new_actions(old_trade_count))

        # Emit phase change if it changed
        if eng.phase != old_phase:
            actions.insert(0, {
                'action': 'PHASE_CHANGE',
                'from': old_phase,
                'to': eng.phase,
                'reason': eng.phase_log[-1]['reason'] if eng.phase_log else 'unknown',
                'symbol': self.symbol,
                'price': price,
            })
            logger.info(f"{self.symbol} Phase: {old_phase} -> {eng.phase} | "
                       f"{eng.phase_log[-1]['reason'] if eng.phase_log else 'unknown'}")

        return actions

    def _extract_new_actions(self, old_count: int) -> List[dict]:
        """Convert new v8 engine trades into runner-compatible actions."""
        actions = []
        new_trades = self._engine.trades[old_count:]

        for trade in new_trades:
            action_str = trade.get('action', '')
            price = trade.get('price', 0)
            amount = trade.get('amount', 0)
            coins = trade.get('coins', 0)

            # Preserve historical date from v8 engine trades for backfill accuracy
            trade_date = trade.get('date')

            if 'BUY_T' in action_str:
                actions.append({
                    'action': 'BUY', 'symbol': self.symbol,
                    'qty': coins, 'price': price,
                    'reason': action_str, 'cost': amount,
                    'phase': trade.get('phase', ''),
                    'date': trade_date,
                })
            elif 'SELL_ALL' in action_str:
                pnl_pct = trade.get('pnl_pct', 0)
                # amount = proceeds from sale; compute dollar PnL from pnl_pct
                pnl_dollar = amount * pnl_pct / (100 + pnl_pct) if (100 + pnl_pct) != 0 else 0
                actions.append({
                    'action': 'SELL', 'symbol': self.symbol,
                    'qty': coins, 'price': price,
                    'reason': action_str, 'pnl': pnl_dollar, 'pnl_pct': pnl_pct,
                    'phase': trade.get('phase', ''),
                    'date': trade_date,
                })
            elif 'SHORT_T' in action_str:
                actions.append({
                    'action': 'SHORT_OPEN', 'symbol': f'{self.symbol}:USDC',
                    'qty': coins, 'price': price,
                    'reason': action_str, 'cost': amount,
                    'phase': trade.get('phase', ''),
                    'date': trade_date,
                })
            elif 'SHORT_CLOSE' in action_str:
                pnl_pct = trade.get('pnl_pct', 0)
                pnl_dollar = amount * pnl_pct / (100 + pnl_pct) if (100 + pnl_pct) != 0 else 0
                actions.append({
                    'action': 'SHORT_CLOSE', 'symbol': f'{self.symbol}:USDC',
                    'qty': coins, 'price': price,
                    'reason': action_str, 'pnl': pnl_dollar, 'pnl_pct': pnl_pct,
                    'phase': trade.get('phase', ''),
                    'date': trade_date,
                })
            elif 'DCA_BUY' in action_str:
                actions.append({
                    'action': 'BUY', 'symbol': self.symbol,
                    'qty': coins, 'price': price,
                    'reason': action_str, 'cost': amount,
                    'phase': trade.get('phase', ''),
                    'date': trade_date,
                })
            elif 'DCA_TP' in action_str:
                pnl_pct = trade.get('pnl_pct', 0)
                pnl_dollar = amount * pnl_pct / (100 + pnl_pct) if (100 + pnl_pct) != 0 else 0
                actions.append({
                    'action': 'SELL', 'symbol': self.symbol,
                    'qty': coins, 'price': price,
                    'reason': action_str, 'pnl': pnl_dollar, 'pnl_pct': pnl_pct,
                    'phase': trade.get('phase', ''),
                    'date': trade_date,
                })
            elif 'DCA_CLOSE' in action_str:
                pnl_pct = trade.get('pnl_pct', 0)
                pnl_dollar = amount * pnl_pct / (100 + pnl_pct) if (100 + pnl_pct) != 0 else 0
                actions.append({
                    'action': 'SELL', 'symbol': self.symbol,
                    'qty': coins, 'price': price,
                    'reason': action_str, 'pnl': pnl_dollar, 'pnl_pct': pnl_pct,
                    'phase': trade.get('phase', ''),
                    'date': trade_date,
                })
            # Skip informational trades (EARLY_WARNING, SHORTS_ENABLED)

        return actions

    def backfill_direct(self, start_date: str, end_date: str) -> List[dict]:
        """Run backfill using the v8 engine's run() method directly.

        This guarantees IDENTICAL results to the standalone backtest — no
        wrapper reimplementation bugs. After backfill, the engine state is
        ready for live ticking.

        Returns list of action dicts (same format as tick()).
        """
        if self._engine is None:
            logger.error(f"No engine for {self.symbol}, cannot backfill")
            return []

        eng = self._engine

        # Configure the v8 engine for the backfill period
        eng.cfg.START_DATE = start_date
        eng.cfg.END_DATE = end_date

        # Run the standalone backtest — this is the EXACT same code path
        logger.info(f"{self.symbol}: Running v8 backfill {start_date} -> {end_date}")
        result = eng.run()

        if result is None:
            logger.error(f"{self.symbol}: v8 backfill returned None")
            return []

        # --- Restore open positions that run() force-closed for equity calc ---
        # v8's run() closes all open positions with 'OPEN_END' action for final
        # equity calculation. We need to: (1) remove those fake closing trades,
        # (2) restore the engine's position state so live mode picks up correctly.
        open_at_end = getattr(eng, '_open_at_end', {})

        # Remove OPEN_END trades from the trade list
        eng.trades = [t for t in eng.trades if 'OPEN_END' not in t.get('action', '')]

        # Restore engine position state (undo the OPEN_END force-closes)
        if 'capital_before_close' in open_at_end:
            eng.capital = open_at_end['capital_before_close']
        eng.position_coins = open_at_end.get('markup_coins', 0)
        eng.entry_price = open_at_end.get('markup_entry', 0)
        eng.tier = open_at_end.get('markup_tier', 0)
        eng.dca_coins = open_at_end.get('dca_coins', 0)
        eng.dca_cost = open_at_end.get('dca_cost', 0)
        eng.dca_avg_entry = open_at_end.get('dca_avg_entry', 0)
        eng.dca_layers = open_at_end.get('dca_layers', 0)
        eng.dca_tp = open_at_end.get('dca_tp', 0)
        eng.short_coins = open_at_end.get('short_coins', 0)
        eng.short_entry = open_at_end.get('short_entry', 0)
        eng.short_cost = open_at_end.get('short_cost', 0)
        eng.short_tier = open_at_end.get('short_tier', 0)

        if open_at_end.get('short_coins', 0) > 0:
            logger.info(f"{self.symbol}: Restored open short — "
                       f"{eng.short_coins:.4f} coins @ ${eng.short_entry:.2f}")
        if open_at_end.get('markup_coins', 0) > 0:
            logger.info(f"{self.symbol}: Restored open long — "
                       f"{eng.position_coins:.4f} coins @ ${eng.entry_price:.2f}")

        # Set wrapper state from engine (for live mode transition)
        if eng.phase_log:
            last_date = eng.phase_log[-1].get('date')
            if last_date:
                self._last_daily_date = str(last_date)[:10]
        self._last_trade_count = len(eng.trades)

        # Convert all trades to action dicts (OPEN_END already removed)
        actions = self._extract_new_actions(0)

        phase_name = eng.phase.name if hasattr(eng.phase, 'name') else str(eng.phase)
        logger.info(f"{self.symbol}: v8 backfill complete — phase={phase_name}, "
                    f"equity=${result['final_equity']:,.1f}, "
                    f"trades={len(eng.trades)}, actions={len(actions)}")

        return actions

    def feed_daily(self, daily_df: pd.DataFrame):
        """Bootstrap signal pack with historical daily data (for logging only)."""
        if daily_df is not None and len(daily_df) > 0:
            logger.info(f"Fed {len(daily_df)} daily candles for {self.symbol}, "
                       f"signals date={daily_df.index[-1].date()}")

    def set_cfgi(self, value: float):
        """Update externally-provided CFGI value (not used by v8 engine directly)."""
        pass  # v8 engine reads CFGI from signal pack

    def snapshot_state(self) -> dict:
        """Serialize the v8 engine state for persistence."""
        if self._engine is None:
            return {}

        eng = self._engine
        return {
            'symbol': self.symbol,
            'initial_capital': self.initial_capital,
            'phase': eng.phase,
            'capital': eng.capital,
            'position_coins': eng.position_coins,
            'entry_price': eng.entry_price,
            'tier': eng.tier,
            'phase_start_date': str(eng.phase_start_date) if eng.phase_start_date else None,
            'early_warning_date': str(eng.early_warning_date) if eng.early_warning_date else None,
            'failsafe_armed': eng.failsafe_armed,
            'peak_2w_k': eng.peak_2w_k,
            'short_coins': eng.short_coins,
            'short_entry': eng.short_entry,
            'short_cost': eng.short_cost,
            'short_tier': eng.short_tier,
            'markup_cycles_completed': eng.markup_cycles_completed,
            'shorts_enabled': eng.shorts_enabled,
            'adx_below_20_streak': eng.adx_below_20_streak,
            'flat_from_top': eng.flat_from_top,
            'flat_from_markdown': eng.flat_from_markdown,
            'dca_coins': eng.dca_coins,
            'dca_avg_entry': eng.dca_avg_entry,
            'dca_layers': eng.dca_layers,
            'dca_last_buy': str(eng.dca_last_buy) if eng.dca_last_buy else None,
            'dca_tp': eng.dca_tp,
            'dca_cost': eng.dca_cost,
            'dca_trades': eng.dca_trades,
            'dca_wins': eng.dca_wins,
            'dca_pnl': eng.dca_pnl,
            # Wrapper state
            '_last_daily_date': self._last_daily_date,
            '_live_mode': self._live_mode,
            'start_time': self.start_time,
            'current_price': self.current_price,
        }

    def restore_state(self, state: dict):
        """Restore v8 engine state from saved dict."""
        if self._engine is None:
            return

        eng = self._engine

        # Restore engine state
        eng.phase = state.get('phase', Phase.DCA)
        eng.capital = state.get('capital', self.initial_capital)
        eng.position_coins = state.get('position_coins', 0.0)
        eng.entry_price = state.get('entry_price', 0.0)
        eng.tier = state.get('tier', 0)
        eng.failsafe_armed = state.get('failsafe_armed', False)
        eng.peak_2w_k = state.get('peak_2w_k', 0.0)
        eng.short_coins = state.get('short_coins', 0.0)
        eng.short_entry = state.get('short_entry', 0.0)
        eng.short_cost = state.get('short_cost', 0.0)
        eng.short_tier = state.get('short_tier', 0)
        eng.markup_cycles_completed = state.get('markup_cycles_completed', 0)
        eng.shorts_enabled = state.get('shorts_enabled', False)
        eng.adx_below_20_streak = state.get('adx_below_20_streak', 0)
        eng.flat_from_top = state.get('flat_from_top', False)
        eng.flat_from_markdown = state.get('flat_from_markdown', False)
        eng.dca_coins = state.get('dca_coins', 0.0)
        eng.dca_avg_entry = state.get('dca_avg_entry', 0.0)
        eng.dca_layers = state.get('dca_layers', 0)
        eng.dca_tp = state.get('dca_tp', 0.0)
        eng.dca_cost = state.get('dca_cost', 0.0)
        eng.dca_trades = state.get('dca_trades', 0)
        eng.dca_wins = state.get('dca_wins', 0)
        eng.dca_pnl = state.get('dca_pnl', 0.0)

        # Parse dates
        psd = state.get('phase_start_date')
        eng.phase_start_date = pd.Timestamp(psd) if psd else None
        ewd = state.get('early_warning_date')
        eng.early_warning_date = pd.Timestamp(ewd) if ewd else None
        dlb = state.get('dca_last_buy')
        eng.dca_last_buy = pd.Timestamp(dlb) if dlb else None

        # Wrapper state
        self._last_daily_date = state.get('_last_daily_date')
        self._live_mode = state.get('_live_mode', False)
        self.start_time = state.get('start_time', datetime.now(timezone.utc).timestamp())
        self.current_price = state.get('current_price', 0.0)

        logger.info(f"V13EngineV2 state restored for {self.symbol}, phase={eng.phase}")

    def get_status(self) -> dict:
        """Return status dict matching dashboard format."""
        if self._engine is None:
            return {'running': False}

        eng = self._engine
        price = self.current_price

        # Calculate equity
        equity = eng.capital
        equity += eng.position_coins * price if price > 0 else 0
        equity += eng.dca_coins * price if price > 0 else 0
        if eng.short_coins > 0 and price > 0:
            short_pnl = (eng.short_entry - price) * eng.short_coins
            equity += eng.short_cost + short_pnl

        pnl_pct = ((equity - self.initial_capital) / self.initial_capital * 100
                   if self.initial_capital > 0 else 0.0)

        # Unrealized PnL
        unrealized = 0.0
        if eng.position_coins > 0 and eng.entry_price > 0:
            unrealized += (price - eng.entry_price) * eng.position_coins
        if eng.short_coins > 0 and eng.short_entry > 0:
            unrealized += (eng.short_entry - price) * eng.short_coins
        if eng.dca_coins > 0 and eng.dca_avg_entry > 0:
            unrealized += (price - eng.dca_avg_entry) * eng.dca_coins

        invested = (eng.position_coins * eng.entry_price if eng.position_coins > 0 else 0) + \
                   eng.short_cost + eng.dca_cost

        # State mapping
        state_map = {
            Phase.DCA: 'ACCUMULATING',
            Phase.MARKUP: 'RIDING',
            Phase.FLAT: 'WAITING',
            Phase.MARKDOWN: 'SHORTING',
        }
        side = 'none'
        if eng.position_coins > 0 or eng.dca_coins > 0:
            side = 'long'
        elif eng.short_coins > 0:
            side = 'short'

        regime_map = {
            Phase.DCA: 'ACCUMULATION',
            Phase.MARKUP: 'TRENDING',
            Phase.FLAT: 'RANGING',
            Phase.MARKDOWN: 'TRENDING',
        }
        trend_dir = 'bullish' if eng.phase in (Phase.DCA, Phase.MARKUP) else 'bearish'

        uptime_h = (datetime.now(timezone.utc).timestamp() - self.start_time) / 3600
        win_rate = (eng.dca_wins / eng.dca_trades * 100
                   if eng.dca_trades > 0 else 0.0)

        return {
            'running': True,
            'mode': 'paper',
            'profile': 'high',
            'exchange': 'hyperliquid',
            'capital': self.initial_capital,
            'equity': round(equity, 2),
            'cash': round(eng.capital, 2),
            'pnl_pct': round(pnl_pct, 2),
            'coins': {
                self.symbol: {
                    'state': state_map.get(eng.phase, 'UNKNOWN'),
                    'side': side,
                    'layers': eng.dca_layers,
                    'avg_entry': eng.short_entry or eng.dca_avg_entry or eng.entry_price or 0,
                    'current_price': price,
                    'unrealized_pnl': round(unrealized, 2),
                    'next_so_price': None,
                    'next_tp_price': eng.dca_tp if eng.dca_tp > 0 else None,
                    'invested': round(invested, 2),
                    'realized_pnl': round(self.realized_pnl, 2),
                    'lifecycle_phase': eng.phase,
                    'cfgi': None,
                }
            },
            'lifecycle': {
                self.symbol: {
                    'phase': eng.phase,
                    'score': 0.0,
                    'daily_score': 0.0,
                    'metrics': {
                        'markup_cycles': eng.markup_cycles_completed,
                        'shorts_enabled': eng.shorts_enabled,
                        'tier': max(eng.tier, eng.short_tier),
                        'dca_trades': eng.dca_trades,
                        'dca_pnl': round(eng.dca_pnl, 2),
                        'total_pnl': round(self.realized_pnl, 2),
                    },
                    'gate_decisions': {},
                }
            },
            'symbols': [self.symbol],
            'regime': regime_map.get(eng.phase, 'UNKNOWN'),
            'trend_direction': trend_dir,
            'total_realized_pnl': round(self.realized_pnl, 2),
            'deals_completed': len([t for t in eng.trades if 'pnl_pct' in t and 'OPEN_END' not in t.get('action', '')]),
            'win_rate': round(win_rate, 1),
            'max_drawdown_pct': round(self.max_drawdown_pct, 2),
            'uptime_hours': round(uptime_h, 2),
            'fear_greed_index': None,
            'last_update': datetime.now(timezone.utc).isoformat(),
            'timeframe': '1h',
        }

    def _parse_timestamp(self, ts) -> datetime:
        """Parse various timestamp formats to UTC datetime."""
        if isinstance(ts, datetime):
            return ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts
        if isinstance(ts, (int, float)):
            if ts > 1e12:
                ts = ts / 1000
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        if isinstance(ts, str):
            return pd.Timestamp(ts).to_pydatetime().replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc)
