"""
V14 Lifecycle Engine — Live wrapper around V14DCAEngine.

Wraps the V14 DCA-only engine (from trading.spot.engine.v14_dca_engine) for
live/paper trading. Pattern matches v13_lifecycle_engine_v2.py.

Architecture:
  - Backfill: calls engine.run() directly (100% match with standalone backtest)
  - Live: accumulates 1h candles, triggers daily signal eval at midnight UTC,
    runs DCA grid via engine's internal methods for hourly responsiveness
  - State persistence via snapshot/restore
  - Dashboard-compatible status output

V14 Risk Profiles (LOCKED):
  Low:    leverage=1.0, BO=40%, Dev=2.0%, Mult=1.5x, Layers=10, TP=1.5%
  Medium: leverage=1.5, BO=40%, Dev=2.0%, Mult=1.5x, Layers=10, TP=1.5%
  High:   leverage=1.5, BO=40%, Dev=1.5%, Mult=1.5x, Layers=12, TP=1.5%
"""

import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import sys

# Import V14 DCA engine and dependencies
# Import V14 DCA engine and dependencies (clean package — no sys.path manipulation)
from trading.spot.engine.v14_dca_engine import V14DCAEngine, V14Config, Phase
from trading.spot.engine.v13_signals import V13SignalPack
from trading.spot.engine.v13_router_engine_v2 import HybridDetector2D

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Risk Profiles (LOCKED)
# ---------------------------------------------------------------------------

V14_PROFILES = {
    'low': {
        'leverage': 1.0,
        'DCA_BO_PCT': 0.40,
        'DCA_SO_DEVIATION': 0.02,
        'DCA_SO_MULTIPLIER': 1.5,
        'DCA_MAX_LAYERS': 10,
        'DCA_TP_PCT': 0.015,
    },
    'medium': {
        'leverage': 1.5,
        'DCA_BO_PCT': 0.40,
        'DCA_SO_DEVIATION': 0.02,
        'DCA_SO_MULTIPLIER': 1.5,
        'DCA_MAX_LAYERS': 10,
        'DCA_TP_PCT': 0.015,
    },
    'high': {
        'leverage': 1.5,
        'DCA_BO_PCT': 0.40,
        'DCA_SO_DEVIATION': 0.015,
        'DCA_SO_MULTIPLIER': 1.5,
        'DCA_MAX_LAYERS': 4,
        'DCA_TP_PCT': 0.030,
    },
}


def _make_v14_config(profile: str = 'medium', capital: float = 10000) -> V14Config:
    """Create V14Config with profile overrides for paper bot."""
    cfg = V14Config()
    cfg.CAPITAL = capital

    # Paper bot overrides (cycling mode)
    cfg.DCA_ACCUMULATE = False
    cfg.OB_FALLBACK_1W = 99          # Disabled
    cfg.DCA_CAPITAL_PCT = 0.90
    cfg.CONVICTION_MIN_SCORE = 3
    cfg.TOP_DIVERGENCE_TIMEOUT = 35

    # Apply profile
    p = V14_PROFILES.get(profile, V14_PROFILES['medium'])
    for key, val in p.items():
        if key != 'leverage':
            setattr(cfg, key, val)

    return cfg


class V14LifecycleEngine:
    """
    Live wrapper around V14DCAEngine.

    The V14 engine is a daily-tick state machine with three phases:
    LONG_DCA, SHORT_DCA, ROUTER. This wrapper:
    - Feeds it daily candles (resampled from 1h during live)
    - Runs DCA grid hourly for responsive TP fills
    - Intercepts its trades list to emit actions
    - Provides persistence via snapshot/restore
    """

    def __init__(self, symbol: str, capital: float, profile: str = 'medium', leverage: float = None):
        self.symbol = symbol
        self.initial_capital = capital
        self.profile = profile
        self.coin = symbol.split('/')[0] if '/' in symbol else symbol

        # Leverage from profile, with optional override
        self.leverage = leverage if leverage is not None else V14_PROFILES.get(profile, V14_PROFILES['medium'])['leverage']

        # Create config
        self._config = _make_v14_config(profile, capital)

        # Initialize signal pack from DB
        try:
            self.pack = V13SignalPack(self.coin)
        except Exception as e:
            logger.error(f"Failed to load V13SignalPack for {self.coin}: {e}")
            self.pack = None

        # Create the V14 engine
        if self.pack:
            self._engine = V14DCAEngine(self.pack, self._config)
        else:
            self._engine = None

        # Tracking for live wrapper
        self._last_daily_date: Optional[str] = None
        self._last_trade_count: int = 0
        self._live_mode: bool = False
        self._candles_1h: List[dict] = []
        self._last_candle_ts: int = 0  # Last processed 1h candle timestamp (ms)
        self.current_price: float = 0.0
        self.start_time: float = datetime.now(timezone.utc).timestamp()
        self._warmed_up: bool = False  # Engine must see a daily boundary before trading

        logger.info(f"V14Engine initialized for {symbol}, capital=${capital:,.0f}, "
                    f"profile={profile}, leverage={self.leverage}x")

    # -----------------------------------------------------------------------
    # Properties delegating to engine
    # -----------------------------------------------------------------------

    @property
    def phase(self):
        return self._engine.phase if self._engine else Phase.LONG_DCA

    @property
    def realized_pnl(self):
        """Total realized PnL from all closed trades."""
        if not self._engine:
            return 0.0
        return self._engine.long_pnl + self._engine.short_pnl

    @property
    def deals_completed(self):
        if not self._engine:
            return 0
        return self._engine.long_trades + self._engine.short_trades

    @property
    def deals_won(self):
        if not self._engine:
            return 0
        return self._engine.long_wins + self._engine.short_wins

    @property
    def max_drawdown_pct(self):
        if not self._engine or not self._engine.equity_curve:
            return 0.0
        eq = pd.Series([e['equity'] for e in self._engine.equity_curve])
        peak = eq.expanding().max()
        dd = (eq - peak) / peak * 100
        return abs(dd.min()) if len(dd) > 0 else 0.0

    # -----------------------------------------------------------------------
    # Tick (main entry point for live candles)
    # -----------------------------------------------------------------------

    def tick(self, candle_1h: dict, cash_available: float) -> List[dict]:
        """
        Process one 1h candle. Returns list of action dicts.

        On daily boundary: refresh signals, run full daily tick matching
        the V14 run() loop order exactly.
        Between daily: run DCA grid tick for hourly TP responsiveness.
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
                        # Re-initialize detector and div_dates
                        self._engine.detector = HybridDetector2D(
                            self._engine.coin, exhaustion_k_min=5.0,
                            exhaustion_tf='2W', exhaustion_mode='k_lift'
                        )
                        self._engine.div_dates = self._engine.detector.compute_2d_divergence_dates()
                        logger.info(f"{self.symbol} Signal pack refreshed")
                    except Exception as e:
                        logger.warning(f"Signal pack refresh failed for {self.symbol}: {e}")

                # Use previous day's date and price from signal pack
                prev_date_str = (ts - timedelta(days=1)).strftime('%Y-%m-%d')
                prev_date_ts = pd.Timestamp(prev_date_str)
                daily_close = self._engine._price(prev_date_ts)
                if np.isnan(daily_close):
                    daily_close = price  # fallback

                # Run full daily tick (router evaluates direction, signals compute)
                actions.extend(self._run_daily_tick(prev_date_ts, daily_close))

                # Engine is now warmed up — router has set direction, signals are loaded
                if not self._warmed_up:
                    self._warmed_up = True
                    logger.info(f"{self.symbol} warmup complete — router direction set, "
                                f"phase={self._engine.phase.name}, trading enabled")

                # Clear old candles (keep current day only)
                self._candles_1h = [c for c in self._candles_1h
                                    if c['timestamp'].strftime('%Y-%m-%d') == current_date]
            else:
                # Between daily: run DCA grid for hourly TP responsiveness
                # BUT only if warmed up (router has set direction at least once)
                if self._live_mode and self._warmed_up:
                    date_ts = pd.Timestamp(ts.replace(tzinfo=None))
                    old_trade_count = len(self._engine.trades)

                    if self._engine.phase == Phase.LONG_DCA:
                        self._engine._long_dca_tick(date_ts, price)
                        # Check orphaned short TP (manual phase override — close only, no new layers)
                        if self._engine.short_coins > 0 and self._engine.short_tp > 0 and price <= self._engine.short_tp:
                            old_unwinding = self._engine.unwinding
                            self._engine.unwinding = True  # Prevent new layers
                            self._engine._short_dca_tick(date_ts, price)
                            self._engine.unwinding = old_unwinding
                    elif self._engine.phase == Phase.SHORT_DCA:
                        self._engine._short_dca_tick(date_ts, price)

                    actions.extend(self._extract_new_actions(old_trade_count))
                elif self._live_mode and not self._warmed_up:
                    # Accumulating candles, tracking price, but not trading yet
                    pass

        except Exception as e:
            logger.error(f"V14Engine tick error for {self.symbol}: {e}", exc_info=True)

        return actions

    def _run_daily_tick(self, date: pd.Timestamp, price: float) -> List[dict]:
        """Run the V14 engine's full daily logic, matching run() loop order exactly."""
        actions = []
        eng = self._engine
        old_trade_count = len(eng.trades)
        old_phase = eng.phase

        # Compute signals first
        signals = eng._compute_signals(date, price)

        # Phase-specific logic (EXACT order from V14 run() loop)
        if eng.phase == Phase.LONG_DCA:
            eng._long_dca_tick(date, price)
            # Check orphaned short TP (manual phase override — close only, no new layers)
            if eng.short_coins > 0 and eng.short_tp > 0 and price <= eng.short_tp:
                old_unwinding = eng.unwinding
                eng.unwinding = True
                eng._short_dca_tick(date, price)
                eng.unwinding = old_unwinding
            eng._check_top_signals(date, price, signals)
        elif eng.phase == Phase.SHORT_DCA:
            eng._short_dca_tick(date, price)
            eng._check_bottom_signals(date, price, signals)
            eng._check_markdown_exit(date, price, signals)
        elif eng.phase == Phase.ROUTER:
            eng._check_router(date, price, signals)

        # Record equity
        long_val = eng.long_coins * price if eng.long_coins > 0 else 0
        short_unreal = (eng.short_avg_entry - price) * eng.short_coins if eng.short_coins > 0 else 0
        equity = eng.capital + long_val + eng.short_cost + short_unreal
        eng.equity_curve.append({
            'date': date, 'equity': equity, 'price': price, 'phase': eng.phase
        })

        # Extract new actions
        actions.extend(self._extract_new_actions(old_trade_count))

        # Emit phase change
        if eng.phase != old_phase:
            reason = eng.phase_log[-1]['reason'] if eng.phase_log else 'unknown'
            actions.insert(0, {
                'action': 'PHASE_CHANGE',
                'from': old_phase,
                'to': eng.phase,
                'reason': reason,
                'symbol': self.symbol,
                'price': price,
            })
            logger.info(f"{self.symbol} Phase: {old_phase} -> {eng.phase} | {reason}")

        return actions

    def _extract_new_actions(self, old_count: int) -> List[dict]:
        """Convert new V14 engine trades into runner-compatible action dicts."""
        actions = []
        new_trades = self._engine.trades[old_count:]

        for trade in new_trades:
            action_str = trade.get('action', '')
            price = trade.get('price', 0)
            amount = trade.get('amount', 0)
            coins = trade.get('coins', 0)
            trade_date = trade.get('date')
            phase = trade.get('phase', '')
            pnl_pct = trade.get('pnl_pct', 0)

            # Skip informational entries (EARLY_WARNING, OB93_ARMED)
            if coins == 0 and amount == 0:
                continue

            if 'LONG_DCA_BUY' in action_str:
                actions.append({
                    'action': 'BUY', 'symbol': self.symbol,
                    'qty': coins, 'price': price,
                    'reason': action_str, 'cost': amount,
                    'phase': 'LONG_DCA', 'date': trade_date,
                })
            elif 'LONG_DCA_TP' in action_str or 'LONG_DCA_CLOSE' in action_str:
                pnl_dollar = trade.get('pnl', amount * pnl_pct / (100 + pnl_pct) if (100 + pnl_pct) != 0 else 0)
                # Skip OPEN_END fake closes
                if 'OPEN_END' in action_str:
                    continue
                actions.append({
                    'action': 'SELL', 'symbol': self.symbol,
                    'qty': coins, 'price': price,
                    'reason': action_str, 'pnl': pnl_dollar, 'pnl_pct': pnl_pct,
                    'phase': 'LONG_DCA', 'date': trade_date,
                })
            elif 'SHORT_DCA_SELL' in action_str:
                actions.append({
                    'action': 'SHORT_OPEN', 'symbol': f'{self.symbol}:USDC',
                    'qty': coins, 'price': price,
                    'reason': action_str, 'cost': amount,
                    'phase': 'SHORT_DCA', 'date': trade_date,
                })
            elif 'SHORT_DCA_TP' in action_str or 'SHORT_DCA_CLOSE' in action_str:
                pnl_dollar = trade.get('pnl', amount * pnl_pct / (100 + pnl_pct) if (100 + pnl_pct) != 0 else 0)
                if 'OPEN_END' in action_str:
                    continue
                actions.append({
                    'action': 'SHORT_CLOSE', 'symbol': f'{self.symbol}:USDC',
                    'qty': coins, 'price': price,
                    'reason': action_str, 'pnl': pnl_dollar, 'pnl_pct': pnl_pct,
                    'phase': 'SHORT_DCA', 'date': trade_date,
                })

        return actions

    # -----------------------------------------------------------------------
    # Backfill
    # -----------------------------------------------------------------------

    def backfill_direct(self, start_date: str, end_date: str) -> List[dict]:
        """Run backfill using V14 engine's run() method directly.

        Guarantees IDENTICAL results to standalone backtest.
        After backfill, engine state is ready for live ticking.
        """
        if self._engine is None:
            logger.error(f"No engine for {self.symbol}, cannot backfill")
            return []

        eng = self._engine
        eng.cfg.START_DATE = start_date
        eng.cfg.END_DATE = end_date

        logger.info(f"{self.symbol}: Running V14 backfill {start_date} -> {end_date}")
        result = eng.run()

        if result is None:
            logger.error(f"{self.symbol}: V14 backfill returned None")
            return []

        # V14 run() force-closes positions with OPEN_END for equity calc.
        # We need to restore open position state for live mode transition.
        # Check if there were OPEN_END trades and undo them.
        open_end_trades = [t for t in eng.trades if 'OPEN_END' in t.get('action', '')]

        if open_end_trades:
            # Restore capital and position state from before the force-close
            # We need to re-open the positions that run() closed
            for t in open_end_trades:
                action = t.get('action', '')
                if 'LONG_DCA_CLOSE' in action:
                    # Undo: give back proceeds, restore long position
                    proceeds = t['amount']
                    pnl_pct = t.get('pnl_pct', 0)
                    cost = proceeds / (1 + pnl_pct / 100) if (1 + pnl_pct / 100) != 0 else proceeds
                    eng.capital -= proceeds
                    eng.long_coins = t['coins']
                    eng.long_cost = cost
                    eng.long_avg_entry = cost / t['coins'] if t['coins'] > 0 else 0
                    eng.long_layers = 1  # approximate
                    eng.long_tp = eng.long_avg_entry * (1 + eng.cfg.DCA_TP_PCT)
                    eng.long_trades -= 1
                    if pnl_pct > 0:
                        eng.long_wins -= 1
                    eng.long_pnl -= (proceeds - cost)
                    logger.info(f"{self.symbol}: Restored open long — "
                               f"{eng.long_coins:.4f} coins @ ${eng.long_avg_entry:.2f}")
                elif 'SHORT_DCA_CLOSE' in action:
                    # Undo: restore short position
                    pnl_pct = t.get('pnl_pct', 0)
                    returned = t['amount']  # short_cost + pnl
                    buy_cost = t['coins'] * t['price']
                    pnl = returned - buy_cost if 'SHORT_DCA_CLOSE' in action else 0
                    orig_cost = returned - pnl
                    eng.capital -= returned
                    eng.short_coins = t['coins']
                    eng.short_cost = orig_cost
                    eng.short_avg_entry = orig_cost / t['coins'] if t['coins'] > 0 else 0
                    eng.short_layers = 1  # approximate
                    eng.short_tp = eng.short_avg_entry * (1 - eng.cfg.DCA_TP_PCT)
                    eng.short_trades -= 1
                    if pnl > 0:
                        eng.short_wins -= 1
                    eng.short_pnl -= pnl
                    logger.info(f"{self.symbol}: Restored open short — "
                               f"{eng.short_coins:.4f} coins @ ${eng.short_avg_entry:.2f}")

            # Remove OPEN_END trades from the list
            eng.trades = [t for t in eng.trades if 'OPEN_END' not in t.get('action', '')]

        # Set current price from last equity curve entry
        if eng.equity_curve:
            self.current_price = eng.equity_curve[-1].get('price', 0)

        # Set wrapper state for live mode transition
        if eng.phase_log:
            last_date = eng.phase_log[-1].get('date')
            if last_date:
                self._last_daily_date = str(last_date)[:10]
        self._last_trade_count = len(eng.trades)

        # Convert all trades to action dicts
        actions = self._extract_new_actions(0)

        logger.info(f"{self.symbol}: V14 backfill complete — phase={eng.phase}, "
                    f"equity=${result['final_equity']:,.1f}, "
                    f"trades={len(eng.trades)}, actions={len(actions)}")

        return actions

    # -----------------------------------------------------------------------
    # State persistence
    # -----------------------------------------------------------------------

    def snapshot_state(self) -> dict:
        """Serialize all V14 engine state for persistence."""
        if self._engine is None:
            return {}

        eng = self._engine
        return {
            'symbol': self.symbol,
            'initial_capital': self.initial_capital,
            'profile': self.profile,
            'leverage': self.leverage,
            # Phase
            'phase': eng.phase,
            'capital': eng.capital,
            'phase_start_date': str(eng.phase_start_date) if eng.phase_start_date else None,
            # Long DCA
            'long_coins': eng.long_coins,
            'long_avg_entry': eng.long_avg_entry,
            'long_layers': eng.long_layers,
            'long_last_buy': str(eng.long_last_buy) if eng.long_last_buy else None,
            'long_tp': eng.long_tp,
            'long_cost': eng.long_cost,
            'long_trades': eng.long_trades,
            'long_wins': eng.long_wins,
            'long_pnl': eng.long_pnl,
            # Short DCA
            'short_coins': eng.short_coins,
            'short_avg_entry': eng.short_avg_entry,
            'short_layers': eng.short_layers,
            'short_last_sell': str(eng.short_last_sell) if eng.short_last_sell else None,
            'short_tp': eng.short_tp,
            'short_cost': eng.short_cost,
            'short_trades': eng.short_trades,
            'short_wins': eng.short_wins,
            'short_pnl': eng.short_pnl,
            # Top detection
            'early_warning_date': str(eng.early_warning_date) if eng.early_warning_date else None,
            'failsafe_armed': eng.failsafe_armed,
            'peak_2w_k': eng.peak_2w_k,
            'ob93_armed': eng.ob93_armed,
            'ob93_armed_date': str(eng.ob93_armed_date) if eng.ob93_armed_date else None,
            'unwinding': eng.unwinding,
            # Bottom detection
            'top_detected': eng.top_detected,
            'conviction_fired': eng.conviction_fired,
            # Cycle tracking
            'markup_cycles_completed': eng.markup_cycles_completed,
            'total_fees': eng.total_fees,
            'adx_below_20_streak': eng.adx_below_20_streak,
            # Router
            'router_from_top': eng.router_from_top,
            'router_from_markdown': eng.router_from_markdown,
            # Wrapper state
            '_last_daily_date': self._last_daily_date,
            '_live_mode': self._live_mode,
            '_last_candle_ts': self._last_candle_ts,
            'start_time': self.start_time,
            'current_price': self.current_price,
        }

    def restore_state(self, state: dict):
        """Restore V14 engine state from saved dict."""
        if self._engine is None:
            # Signal pack failed during init — create a bare engine so we can restore state.
            # Signals will refresh on the next daily boundary tick.
            try:
                from trading.spot.engine.v14_dca_engine import V14DCAEngine
                self._engine = V14DCAEngine.__new__(V14DCAEngine)
                self._engine.cfg = self._config
                self._engine.coin = self.coin
                self._engine.pack = None
                self._engine.daily = pd.DataFrame()
                self._engine.trades = []
                self._engine.equity_curve = []
                self._engine.phase_log = []
                self._engine.total_fees = 0.0
                self._engine.markup_cycles_completed = 0
                self._engine.adx_below_20_streak = 0
                self._engine.router_from_top = False
                self._engine.router_from_markdown = False
                logger.info(f"Created bare engine for {self.symbol} (signal pack unavailable, will refresh on daily tick)")
            except Exception as e:
                logger.error(f"Cannot create bare engine for {self.symbol}: {e}")
                return

        eng = self._engine

        # Phase
        eng.phase = state.get('phase', Phase.LONG_DCA)
        eng.capital = state.get('capital', self.initial_capital)
        psd = state.get('phase_start_date')
        eng.phase_start_date = pd.Timestamp(psd) if psd else None

        # Long DCA
        eng.long_coins = state.get('long_coins', 0.0)
        eng.long_avg_entry = state.get('long_avg_entry', 0.0)
        eng.long_layers = state.get('long_layers', 0)
        llb = state.get('long_last_buy')
        eng.long_last_buy = pd.Timestamp(llb) if llb else None
        eng.long_tp = state.get('long_tp', 0.0)
        eng.long_cost = state.get('long_cost', 0.0)
        eng.long_trades = state.get('long_trades', 0)
        eng.long_wins = state.get('long_wins', 0)
        eng.long_pnl = state.get('long_pnl', 0.0)

        # Short DCA
        eng.short_coins = state.get('short_coins', 0.0)
        eng.short_avg_entry = state.get('short_avg_entry', 0.0)
        eng.short_layers = state.get('short_layers', 0)
        lss = state.get('short_last_sell')
        eng.short_last_sell = pd.Timestamp(lss) if lss else None
        eng.short_tp = state.get('short_tp', 0.0)
        eng.short_cost = state.get('short_cost', 0.0)
        eng.short_trades = state.get('short_trades', 0)
        eng.short_wins = state.get('short_wins', 0)
        eng.short_pnl = state.get('short_pnl', 0.0)

        # Top detection
        ewd = state.get('early_warning_date')
        eng.early_warning_date = pd.Timestamp(ewd) if ewd else None
        eng.failsafe_armed = state.get('failsafe_armed', False)
        eng.peak_2w_k = state.get('peak_2w_k', 0.0)
        eng.ob93_armed = state.get('ob93_armed', False)
        oad = state.get('ob93_armed_date')
        eng.ob93_armed_date = pd.Timestamp(oad) if oad else None
        eng.unwinding = state.get('unwinding', False)

        # Bottom detection
        eng.top_detected = state.get('top_detected', False)
        eng.conviction_fired = state.get('conviction_fired', False)

        # Restored engines are already warmed up — they were trading before the restart
        self._warmed_up = True

        # Cycle tracking
        eng.markup_cycles_completed = state.get('markup_cycles_completed', 0)
        eng.total_fees = state.get('total_fees', 0.0)
        eng.adx_below_20_streak = state.get('adx_below_20_streak', 0)

        # Router
        eng.router_from_top = state.get('router_from_top', False)
        eng.router_from_markdown = state.get('router_from_markdown', False)

        # Wrapper state
        self._last_daily_date = state.get('_last_daily_date')
        self._live_mode = state.get('_live_mode', False)
        self._last_candle_ts = state.get('_last_candle_ts', 0)
        self.start_time = state.get('start_time', datetime.now(timezone.utc).timestamp())
        self.current_price = state.get('current_price', 0.0)

        logger.info(f"V14Engine state restored for {self.symbol}, phase={eng.phase}")

    # -----------------------------------------------------------------------
    # Rollback for Portfolio Router
    # -----------------------------------------------------------------------
    
    def reject_action(self, action_dict: dict):
        """
        Roll back the state of the engine for a specific action (e.g. BUY rejected by router).
        This is used by the portfolio runner when capital is denied.
        """
        if self._engine is None:
            return
            
        eng = self._engine
        action_type = action_dict.get('action')
        reason = action_dict.get('reason', '')
        
        # We only support rolling back recent BUY or SHORT_OPEN actions
        if action_type not in ('BUY', 'SHORT_OPEN'):
            logger.warning(f"Cannot reject action type {action_type} for {self.symbol}")
            return
            
        # Find the trade in the engine's trade list
        trade_idx = -1
        for i in range(len(eng.trades)-1, -1, -1):
            if eng.trades[i].get('action') == reason and eng.trades[i].get('date') == action_dict.get('date'):
                trade_idx = i
                break
                
        if trade_idx == -1:
            logger.warning(f"Could not find trade {reason} to reject for {self.symbol}")
            return
            
        trade = eng.trades.pop(trade_idx)
        amount = trade['amount']
        coins = trade['coins']
        price = trade['price']
        
        if action_type == 'BUY':
            # Rollback long
            eng.capital += amount
            eng.long_coins -= coins
            eng.long_cost -= amount
            if eng.long_coins <= 1e-8:
                eng.long_coins = 0
                eng.long_cost = 0
                eng.long_avg_entry = 0
                eng.long_layers = 0
                eng.long_tp = 0
            else:
                eng.long_avg_entry = eng.long_cost / eng.long_coins
                eng.long_layers -= 1
                # Restore TP roughly
                eng.long_tp = eng.long_avg_entry * (1 + eng.cfg.DCA_TP_PCT)
            eng.long_trades -= 1
            logger.info(f"{self.symbol}: Rejected BUY, rolled back {coins} coins @ ${price}. Refunded ${amount}.")
            
        elif action_type == 'SHORT_OPEN':
            # Rollback short
            eng.capital += amount
            eng.short_coins -= coins
            eng.short_cost -= amount
            if eng.short_coins <= 1e-8:
                eng.short_coins = 0
                eng.short_cost = 0
                eng.short_avg_entry = 0
                eng.short_layers = 0
                eng.short_tp = 0
            else:
                eng.short_avg_entry = eng.short_cost / eng.short_coins
                eng.short_layers -= 1
                # Restore TP roughly
                eng.short_tp = eng.short_avg_entry * (1 - eng.cfg.DCA_TP_PCT)
            eng.short_trades -= 1
            logger.info(f"{self.symbol}: Rejected SHORT_OPEN, rolled back {coins} coins @ ${price}. Refunded ${amount}.")

    # -----------------------------------------------------------------------
    # Feed daily (for signal context on restore)
    # -----------------------------------------------------------------------

    def feed_daily(self, daily_df: pd.DataFrame):
        """Bootstrap signal pack with historical daily data (logging only)."""
        if daily_df is not None and len(daily_df) > 0:
            logger.info(f"Fed {len(daily_df)} daily candles for {self.symbol}, "
                       f"last date={daily_df.index[-1].date()}")

    def set_cfgi(self, value: float):
        """Update externally-provided CFGI value (V14 engine reads from signal pack)."""
        pass

    # -----------------------------------------------------------------------
    # Status
    # -----------------------------------------------------------------------

    def _calc_liq_price(self, eng, side, price):
        """Calculate liquidation price using wrapper's leverage."""
        if self.leverage <= 1.0:
            return None
        mm = 0.005  # Maintenance margin rate (Hyperliquid)
        if side == 'long' and eng.long_avg_entry > 0:
            return round(eng.long_avg_entry * (1 - (1.0 / self.leverage) + mm), 6)
        elif side == 'short' and eng.short_avg_entry > 0:
            return round(eng.short_avg_entry * (1 + (1.0 / self.leverage) - mm), 6)
        return None

    def _calc_distance_to_liq(self, eng, side, price):
        """Calculate distance to liquidation as percentage."""
        liq = self._calc_liq_price(eng, side, price)
        if liq is None or price <= 0:
            return None
        if side == 'long':
            return round((price - liq) / price * 100, 2)
        elif side == 'short':
            return round((liq - price) / price * 100, 2)
        return None

    def get_status(self) -> dict:
        """Return status dict matching dashboard format."""
        if self._engine is None:
            return {'running': False}

        eng = self._engine
        price = self.current_price

        # Calculate engine equity (before leverage)
        engine_equity = eng.capital
        long_val = eng.long_coins * price if eng.long_coins > 0 and price > 0 else 0
        engine_equity += long_val
        if eng.short_coins > 0 and price > 0:
            short_pnl = (eng.short_avg_entry - price) * eng.short_coins
            engine_equity += eng.short_cost + short_pnl

        # Apply leverage as PnL multiplier
        raw_pnl = engine_equity - self.initial_capital
        leveraged_pnl = raw_pnl * self.leverage
        equity = self.initial_capital + leveraged_pnl

        pnl_pct = (leveraged_pnl / self.initial_capital * 100
                   if self.initial_capital > 0 else 0.0)

        # Unrealized PnL
        unrealized = 0.0
        if eng.long_coins > 0 and eng.long_avg_entry > 0:
            unrealized += (price - eng.long_avg_entry) * eng.long_coins
        if eng.short_coins > 0 and eng.short_avg_entry > 0:
            unrealized += (eng.short_avg_entry - price) * eng.short_coins
        unrealized *= self.leverage

        # Side
        side = 'none'
        if eng.long_coins > 0:
            side = 'long'
        elif eng.short_coins > 0:
            side = 'short'

        # Layers and avg entry
        layers = eng.long_layers if eng.phase == Phase.LONG_DCA else eng.short_layers
        avg_entry = eng.long_avg_entry if eng.phase == Phase.LONG_DCA else eng.short_avg_entry

        invested = eng.long_cost + eng.short_cost
        uptime_h = (datetime.now(timezone.utc).timestamp() - self.start_time) / 3600
        total_trades = eng.long_trades + eng.short_trades
        total_wins = eng.long_wins + eng.short_wins
        win_rate = (total_wins / total_trades * 100 if total_trades > 0 else 0.0)

        return {
            'running': True,
            'mode': 'paper',
            'engine': 'v14',
            'profile': self.profile,
            'leverage': self.leverage,
            'exchange': 'hyperliquid',
            'capital': self.initial_capital,
            'equity': round(equity, 2),
            'cash': round(eng.capital, 2),
            'pnl_pct': round(pnl_pct, 2),
            'coins': {
                self.symbol: {
                    'state': eng.phase,
                    'side': side,
                    'layers': layers,
                    'avg_entry': round(avg_entry, 6) if avg_entry else 0,
                    'current_price': round(price, 6) if price else 0,
                    'unrealized_pnl': round(unrealized, 2),
                    'invested': round(invested, 2),
                    'realized_pnl': round((eng.long_pnl + eng.short_pnl) * self.leverage, 2),
                    'lifecycle_phase': eng.phase,
                    'cfgi': None,
                    'next_tp_price': eng.long_tp if eng.long_tp > 0 else (eng.short_tp if eng.short_tp > 0 else None),
                    'liquidation_price': self._calc_liq_price(eng, side, price),
                    'distance_to_liq_pct': self._calc_distance_to_liq(eng, side, price),
                    'total_fees': round(eng.total_fees * self.leverage, 2),
                }
            },
            'symbols': [self.symbol],
            'total_realized_pnl': round((eng.long_pnl + eng.short_pnl) * self.leverage, 2),
            'total_fees': round(eng.total_fees * self.leverage, 2),
            'deals_completed': total_trades,
            'win_rate': round(win_rate, 1),
            'max_drawdown_pct': round(self.max_drawdown_pct, 2),
            'uptime_hours': round(uptime_h, 2),
            'fear_greed_index': None,
            'last_update': datetime.now(timezone.utc).isoformat(),
            'timeframe': '1h',
        }

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

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
