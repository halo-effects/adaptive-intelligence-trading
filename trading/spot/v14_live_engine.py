"""
V14 Live Engine -- DCA-Only Live Wrapper

Architecture:
- Processes 1h candles tick-by-tick via tick(candle, cash_available) method
- Manages DCA grid state (long/short positions, layers, avg entry, TP levels)
- Implements ROUTER v2 signal stack for top/bottom detection (same as backtest)
- Returns list of actions (BUY, SELL, SHORT_OPEN, SHORT_CLOSE, PHASE_CHANGE)
- State persistence: snapshot_state() → dict, restore_state(state_dict)
- Dashboard compatibility: get_status() → status dict per coin
- Backfill support: backfill_direct(start_date, end_date) → run backtest engine directly

Signal Stack (from V14 backtest):
- Top: OB93 arm → 2D divergence (35d timeout). Fallbacks: failsafe K<50. NO OB85 (disabled).
- Bottom: 3D death cross + 2W K≥5 + conviction score ≥3/4
- Phase transitions: LONG_DCA ↔ SHORT_DCA (no ROUTER phase in between)

DCA Grid: Cycling mode (fixed TP), safety orders with volume scaling, grid resets after TP hit
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

# Import V14 DCA backtest engine and dependencies
_V14_DIR = Path(__file__).parent / 'backtest_results' / 'v13'
sys.path.insert(0, str(_V14_DIR))

try:
    from v14_dca_engine import V14DCAEngine, V14Config, Phase
    from v13_signals import V13SignalPack
    from v13_router_engine_v2 import HybridDetector2D
except ImportError as e:
    logging.error(f"Failed to import V14 engine components: {e}")
    raise

logger = logging.getLogger(__name__)

# Risk profile configurations matching the specification
PROFILES = {
    'low': {
        'leverage': 1.0, 'bo': 0.40, 'dev': 0.02, 'mult': 1.5, 'layers': 10, 'tp': 0.015
    },
    'medium': {
        'leverage': 1.5, 'bo': 0.40, 'dev': 0.02, 'mult': 1.5, 'layers': 10, 'tp': 0.015
    },
    'high': {
        'leverage': 1.5, 'bo': 0.40, 'dev': 0.015, 'mult': 1.5, 'layers': 12, 'tp': 0.015
    }
}


class V14LiveConfig:
    """Live configuration based on risk profiles."""
    
    @staticmethod
    def from_profile(profile: str = 'medium', capital: float = 10000, leverage: Optional[float] = None) -> V14Config:
        """Create V14Config from risk profile."""
        cfg = V14Config()
        cfg.CAPITAL = capital
        
        p = PROFILES.get(profile, PROFILES['medium'])
        
        # Apply profile settings to V14Config
        cfg.DCA_BO_PCT = p['bo']
        cfg.DCA_SO_DEVIATION = p['dev'] 
        cfg.DCA_SO_MULTIPLIER = p['mult']
        cfg.DCA_MAX_LAYERS = p['layers']
        cfg.DCA_TP_PCT = p['tp']
        
        # Apply leverage at capital utilization level (capped at 1.0)
        effective_leverage = leverage or p['leverage']
        cfg.DCA_CAPITAL_PCT = min(1.0, cfg.DCA_CAPITAL_PCT * effective_leverage)
        
        # V14-specific: cycling mode (no accumulate), equal weight
        cfg.DCA_ACCUMULATE = False  # Fixed TP mode for live trading
        
        return cfg


class V14LiveEngine:
    """
    Live wrapper around V14DCAEngine (from v14_dca_engine.py).
    
    The V14 backtest engine operates on daily data. This wrapper:
    - Accumulates 1h candles and triggers daily evaluation at midnight UTC
    - Runs the V14 DCA engine for both long and short grids
    - Emits actions (BUY/SELL/SHORT_OPEN/SHORT_CLOSE/PHASE_CHANGE) for the paper runner
    - Provides state persistence and dashboard-compatible status
    """

    def __init__(self, symbol: str, capital: float, config=None):
        self.symbol = symbol
        self.initial_capital = capital
        self.coin = symbol.split('/')[0] if '/' in symbol else symbol
        
        # Create V14 config
        if isinstance(config, V14Config):
            self._v14_config = config
        else:
            self._v14_config = V14Config()
        self._v14_config.CAPITAL = capital

        # Initialize signal pack from DB
        try:
            self.pack = V13SignalPack(self.coin)
        except Exception as e:
            logger.error(f"Failed to load V13SignalPack for {self.coin}: {e}")
            self.pack = None

        # Create the V14 engine (the ACTUAL DCA backtest engine)
        if self.pack:
            self._engine = V14DCAEngine(self.pack, self._v14_config, initial_phase='LONG_DCA')
        else:
            self._engine = None

        # Live wrapper tracking
        self._last_daily_date: Optional[str] = None
        self._last_trade_count: int = 0
        self._live_mode: bool = False
        self._candles_1h: List[dict] = []
        self.current_price: float = 0.0
        self.start_time: float = datetime.now(timezone.utc).timestamp()

        logger.info(f"V14LiveEngine initialized for {symbol}, capital=${capital:,.0f}")

    # Properties that delegate to the V14 engine
    @property
    def phase(self):
        return self._engine.phase if self._engine else Phase.LONG_DCA

    @property
    def realized_pnl(self):
        """Total realized PnL from ALL closed trades (long DCA + short DCA)."""
        if not self._engine:
            return 0.0
        return self._engine.long_pnl + self._engine.short_pnl

    @property
    def deals_completed(self):
        """Total completed DCA deals (long + short)."""
        return self._engine.long_trades + self._engine.short_trades if self._engine else 0

    @property
    def deals_won(self):
        """Total winning deals.""" 
        return self._engine.long_wins + self._engine.short_wins if self._engine else 0

    @property
    def max_drawdown_pct(self):
        """Calculate max drawdown from equity curve."""
        if not self._engine or not self._engine.equity_curve:
            return 0.0
        eq = pd.Series([e['equity'] for e in self._engine.equity_curve])
        peak = eq.expanding().max()
        dd = (eq - peak) / peak * 100
        return abs(dd.min()) if len(dd) > 0 else 0.0

    def tick(self, candle_1h: dict, cash_available: float) -> List[dict]:
        """
        Process one 1h candle. Returns list of action dicts.

        Accumulates 1h candles. On daily boundary (midnight UTC), triggers the V14 engine's
        full daily evaluation (signal checks, phase transitions, DCA grid management).
        Between daily ticks, runs DCA grids for hourly responsiveness in live mode.
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
                        # Refresh conviction detector
                        self._engine.detector = HybridDetector2D(
                            self.pack.coin, exhaustion_k_min=5.0,
                            exhaustion_tf='2W', exhaustion_mode='k_lift'
                        )
                        self._engine.div_dates = self._engine.detector.compute_2d_divergence_dates()
                        logger.info(f"{self.symbol} Signal pack refreshed")
                    except Exception as e:
                        logger.warning(f"Signal pack refresh failed for {self.symbol}: {e}")

                # Build daily bar from accumulated 1h candles for yesterday
                prev_date_str = (ts - timedelta(days=1)).strftime('%Y-%m-%d')
                prev_date_ts = pd.Timestamp(prev_date_str)
                
                # Use daily close from signal pack if available
                daily_close = self._engine._price(prev_date_ts)
                if np.isnan(daily_close):
                    daily_close = price  # fallback to current 1h price

                # Run full daily tick at previous day's date with daily close price
                actions.extend(self._run_daily_tick(prev_date_ts.to_pydatetime(), daily_close))

                # Clear old candles (keep only current day)
                self._candles_1h = [c for c in self._candles_1h
                                    if c['timestamp'].strftime('%Y-%m-%d') == current_date]

            else:
                # Between daily ticks: run DCA grids for hourly responsiveness
                # In live mode: hourly DCA for better fills and stops
                # In backfill mode: skip hourly DCA (match V14 backtest = daily only)
                if self._live_mode:
                    date_ts = pd.Timestamp(ts.replace(tzinfo=None))
                    old_trade_count = len(self._engine.trades)
                    
                    # Run appropriate DCA grid based on current phase
                    if self._engine.phase == Phase.LONG_DCA:
                        self._engine._long_dca_tick(date_ts, price)
                    elif self._engine.phase == Phase.SHORT_DCA:
                        self._engine._short_dca_tick(date_ts, price)
                    
                    actions.extend(self._extract_new_actions(old_trade_count))

        except Exception as e:
            logger.error(f"V14LiveEngine tick error for {self.symbol}: {e}", exc_info=True)

        return actions

    def _run_daily_tick(self, ts: datetime, price: float) -> List[dict]:
        """
        Run the V14 engine's full daily logic for one day.
        
        This calls into the V14DCAEngine's main loop logic:
        - Compute all signals for the date
        - Check phase-specific logic (long DCA top detection, short DCA bottom detection)
        - Run DCA grids
        - Phase transitions
        """
        actions = []
        date = pd.Timestamp(ts)
        eng = self._engine

        old_trade_count = len(eng.trades)
        old_phase = eng.phase

        # Compute signals (same as V14 backtest)
        signals = eng._compute_signals(date, price)

        # Phase-specific logic (matches V14DCAEngine.run() exactly)
        if eng.phase == Phase.LONG_DCA:
            # Run long DCA grid
            eng._long_dca_tick(date, price)
            # Check for top signals → transition to SHORT_DCA
            if eng._check_top_signals(date, price, signals):
                pass  # Phase change already handled in _check_top_signals

        elif eng.phase == Phase.SHORT_DCA:
            # Run short DCA grid
            eng._short_dca_tick(date, price)
            # Check for bottom signals → transition to LONG_DCA
            if eng._check_bottom_signals(date, price, signals):
                pass  # Phase change already handled in _check_bottom_signals
            # Also check markdown exit (safety net)
            if eng._check_markdown_exit(date, price, signals):
                pass  # Phase change already handled

        # Record equity (same as V14 backtest)
        long_val = eng.long_coins * price if eng.long_coins > 0 else 0
        short_unreal = (eng.short_avg_entry - price) * eng.short_coins if eng.short_coins > 0 else 0
        equity = eng.capital + long_val + eng.short_cost + short_unreal
        eng.equity_curve.append({
            'date': date, 'equity': equity, 'price': price, 'phase': eng.phase
        })

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
        """Convert new V14 engine trades into runner-compatible actions."""
        actions = []
        new_trades = self._engine.trades[old_count:]

        for trade in new_trades:
            action_str = trade.get('action', '')
            price = trade.get('price', 0)
            amount = trade.get('amount', 0)
            coins = trade.get('coins', 0)

            # Preserve historical date from V14 engine trades for backfill accuracy
            trade_date = trade.get('date')

            if 'LONG_DCA_BUY' in action_str:
                actions.append({
                    'action': 'BUY', 'symbol': self.symbol,
                    'qty': coins, 'price': price,
                    'reason': action_str, 'cost': amount,
                    'phase': trade.get('phase', ''),
                    'date': trade_date,
                })
            elif 'LONG_DCA_TP' in action_str or 'LONG_DCA_CLOSE' in action_str:
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
            elif 'SHORT_DCA_SELL' in action_str:
                actions.append({
                    'action': 'SHORT_OPEN', 'symbol': f'{self.symbol}:USDC',
                    'qty': coins, 'price': price,
                    'reason': action_str, 'cost': amount,
                    'phase': trade.get('phase', ''),
                    'date': trade_date,
                })
            elif 'SHORT_DCA_TP' in action_str or 'SHORT_DCA_CLOSE' in action_str:
                pnl_pct = trade.get('pnl_pct', 0)
                pnl_dollar = amount * pnl_pct / (100 + pnl_pct) if (100 + pnl_pct) != 0 else 0
                actions.append({
                    'action': 'SHORT_CLOSE', 'symbol': f'{self.symbol}:USDC',
                    'qty': coins, 'price': price,
                    'reason': action_str, 'pnl': pnl_dollar, 'pnl_pct': pnl_pct,
                    'phase': trade.get('phase', ''),
                    'date': trade_date,
                })
            # Skip informational trades (EARLY_WARNING_UNWIND, OB93_ARMED, etc.)

        return actions

    def backfill_direct(self, start_date: str, end_date: str) -> List[dict]:
        """
        Run backfill using the V14 engine's run() method directly.

        This guarantees IDENTICAL results to the standalone backtest — no
        wrapper reimplementation bugs. After backfill, the engine state is
        ready for live ticking.

        Returns list of action dicts (same format as tick()).
        """
        if self._engine is None:
            logger.error(f"No engine for {self.symbol}, cannot backfill")
            return []

        eng = self._engine

        # Configure the V14 engine for the backfill period
        eng.cfg.START_DATE = start_date
        eng.cfg.END_DATE = end_date

        # Run the standalone backtest — this is the EXACT same code path
        logger.info(f"{self.symbol}: Running V14 backfill {start_date} -> {end_date}")
        result = eng.run()

        if result is None:
            logger.error(f"{self.symbol}: V14 backfill returned None")
            return []

        # Set wrapper state from engine (for live mode transition)
        if eng.phase_log:
            last_date = eng.phase_log[-1].get('date')
            if last_date:
                self._last_daily_date = str(last_date)[:10]
        self._last_trade_count = len(eng.trades)

        # Convert all trades to action dicts
        actions = self._extract_new_actions(0)

        phase_name = eng.phase
        logger.info(f"{self.symbol}: V14 backfill complete — phase={phase_name}, "
                    f"equity=${result['final_equity']:,.1f}, "
                    f"trades={len(eng.trades)}, actions={len(actions)}")

        return actions

    def feed_daily(self, daily_df: pd.DataFrame):
        """Bootstrap signal pack with historical daily data (for logging only)."""
        if daily_df is not None and len(daily_df) > 0:
            logger.info(f"Fed {len(daily_df)} daily candles for {self.symbol}, "
                       f"signals date={daily_df.index[-1].date()}")

    def snapshot_state(self) -> dict:
        """Serialize the V14 engine state for persistence."""
        if self._engine is None:
            return {}

        eng = self._engine
        return {
            'symbol': self.symbol,
            'initial_capital': self.initial_capital,
            'phase': eng.phase,
            'capital': eng.capital,
            'phase_start_date': str(eng.phase_start_date) if eng.phase_start_date else None,
            
            # Long DCA grid state
            'long_coins': eng.long_coins,
            'long_avg_entry': eng.long_avg_entry,
            'long_layers': eng.long_layers,
            'long_last_buy': str(eng.long_last_buy) if eng.long_last_buy else None,
            'long_tp': eng.long_tp,
            'long_cost': eng.long_cost,
            'long_trades': eng.long_trades,
            'long_wins': eng.long_wins,
            'long_pnl': eng.long_pnl,
            
            # Short DCA grid state
            'short_coins': eng.short_coins,
            'short_avg_entry': eng.short_avg_entry,
            'short_layers': eng.short_layers,
            'short_last_sell': str(eng.short_last_sell) if eng.short_last_sell else None,
            'short_tp': eng.short_tp,
            'short_cost': eng.short_cost,
            'short_trades': eng.short_trades,
            'short_wins': eng.short_wins,
            'short_pnl': eng.short_pnl,
            
            # Top detection state
            'early_warning_date': str(eng.early_warning_date) if eng.early_warning_date else None,
            'failsafe_armed': eng.failsafe_armed,
            'peak_2w_k': eng.peak_2w_k,
            'ob93_armed': eng.ob93_armed,
            'ob93_armed_date': str(eng.ob93_armed_date) if eng.ob93_armed_date else None,
            'unwinding': eng.unwinding,
            
            # Bottom detection state  
            'top_detected': eng.top_detected,
            'conviction_fired': eng.conviction_fired,
            
            # Cycle tracking
            'markup_cycles_completed': eng.markup_cycles_completed,
            'adx_below_20_streak': eng.adx_below_20_streak,
            
            # Wrapper state
            '_last_daily_date': self._last_daily_date,
            '_live_mode': self._live_mode,
            'start_time': self.start_time,
            'current_price': self.current_price,
        }

    def restore_state(self, state: dict):
        """Restore V14 engine state from saved dict."""
        if self._engine is None:
            return

        eng = self._engine

        # Restore engine state
        eng.phase = state.get('phase', Phase.LONG_DCA)
        eng.capital = state.get('capital', self.initial_capital)
        
        # Long DCA grid
        eng.long_coins = state.get('long_coins', 0.0)
        eng.long_avg_entry = state.get('long_avg_entry', 0.0)
        eng.long_layers = state.get('long_layers', 0)
        eng.long_tp = state.get('long_tp', 0.0)
        eng.long_cost = state.get('long_cost', 0.0)
        eng.long_trades = state.get('long_trades', 0)
        eng.long_wins = state.get('long_wins', 0)
        eng.long_pnl = state.get('long_pnl', 0.0)
        
        # Short DCA grid
        eng.short_coins = state.get('short_coins', 0.0)
        eng.short_avg_entry = state.get('short_avg_entry', 0.0)
        eng.short_layers = state.get('short_layers', 0)
        eng.short_tp = state.get('short_tp', 0.0)
        eng.short_cost = state.get('short_cost', 0.0)
        eng.short_trades = state.get('short_trades', 0)
        eng.short_wins = state.get('short_wins', 0)
        eng.short_pnl = state.get('short_pnl', 0.0)
        
        # Top detection state
        eng.failsafe_armed = state.get('failsafe_armed', False)
        eng.peak_2w_k = state.get('peak_2w_k', 0.0)
        eng.ob93_armed = state.get('ob93_armed', False)
        eng.unwinding = state.get('unwinding', False)
        
        # Bottom detection state
        eng.top_detected = state.get('top_detected', False)
        eng.conviction_fired = state.get('conviction_fired', False)
        
        # Cycle tracking
        eng.markup_cycles_completed = state.get('markup_cycles_completed', 0)
        eng.adx_below_20_streak = state.get('adx_below_20_streak', 0)

        # Parse dates
        psd = state.get('phase_start_date')
        eng.phase_start_date = pd.Timestamp(psd) if psd else None
        ewd = state.get('early_warning_date')
        eng.early_warning_date = pd.Timestamp(ewd) if ewd else None
        oad = state.get('ob93_armed_date')
        eng.ob93_armed_date = pd.Timestamp(oad) if oad else None
        llb = state.get('long_last_buy')
        eng.long_last_buy = pd.Timestamp(llb) if llb else None
        sls = state.get('short_last_sell')
        eng.short_last_sell = pd.Timestamp(sls) if sls else None

        # Wrapper state
        self._last_daily_date = state.get('_last_daily_date')
        self._live_mode = state.get('_live_mode', False)
        self.start_time = state.get('start_time', datetime.now(timezone.utc).timestamp())
        self.current_price = state.get('current_price', 0.0)

        logger.info(f"V14LiveEngine state restored for {self.symbol}, phase={eng.phase}")

    def get_status(self) -> dict:
        """Return status dict matching dashboard format."""
        if self._engine is None:
            return {'running': False}

        eng = self._engine
        price = self.current_price

        # Calculate equity
        equity = eng.capital
        equity += eng.long_coins * price if price > 0 else 0
        equity += eng.short_coins * price if price > 0 else 0
        if eng.short_coins > 0 and price > 0:
            short_pnl = (eng.short_avg_entry - price) * eng.short_coins
            equity += eng.short_cost + short_pnl

        pnl_pct = ((equity - self.initial_capital) / self.initial_capital * 100
                   if self.initial_capital > 0 else 0.0)

        # Unrealized PnL
        unrealized = 0.0
        if eng.long_coins > 0 and eng.long_avg_entry > 0:
            unrealized += (price - eng.long_avg_entry) * eng.long_coins
        if eng.short_coins > 0 and eng.short_avg_entry > 0:
            unrealized += (eng.short_avg_entry - price) * eng.short_coins

        invested = eng.long_cost + eng.short_cost

        # State mapping
        state_map = {
            Phase.LONG_DCA: 'ACCUMULATING',
            Phase.SHORT_DCA: 'SHORTING',
        }
        side = 'none'
        if eng.long_coins > 0:
            side = 'long'
        elif eng.short_coins > 0:
            side = 'short'

        regime_map = {
            Phase.LONG_DCA: 'ACCUMULATION',  
            Phase.SHORT_DCA: 'TRENDING',
        }
        trend_dir = 'bullish' if eng.phase == Phase.LONG_DCA else 'bearish'

        uptime_h = (datetime.now(timezone.utc).timestamp() - self.start_time) / 3600
        total_deals = eng.long_trades + eng.short_trades
        total_wins = eng.long_wins + eng.short_wins
        win_rate = (total_wins / total_deals * 100) if total_deals > 0 else 0.0
        
        # TP prices
        next_tp = None
        if eng.long_coins > 0 and eng.long_tp > 0:
            next_tp = eng.long_tp
        elif eng.short_coins > 0 and eng.short_tp > 0:
            next_tp = eng.short_tp

        return {
            'running': True,
            'mode': 'paper',
            'profile': 'medium',  # Default
            'exchange': 'hyperliquid',
            'capital': self.initial_capital,
            'equity': round(equity, 2),
            'cash': round(eng.capital, 2),
            'pnl_pct': round(pnl_pct, 2),
            'coins': {
                self.symbol: {
                    'state': state_map.get(eng.phase, 'UNKNOWN'),
                    'side': side,
                    'layers': eng.long_layers + eng.short_layers,
                    'avg_entry': eng.long_avg_entry or eng.short_avg_entry or 0,
                    'current_price': price,
                    'unrealized_pnl': round(unrealized, 2),
                    'next_so_price': None,  # Not tracked in V14 engine
                    'next_tp_price': next_tp,
                    'invested': round(invested, 2),
                    'realized_pnl': round(self.realized_pnl, 2),
                    'lifecycle_phase': eng.phase,
                    'cfgi': None,  # Populated externally
                }
            },
            'lifecycle': {
                self.symbol: {
                    'phase': eng.phase,
                    'score': 0.0,  # Not applicable for V14
                    'daily_score': 0.0,
                    'metrics': {
                        'markup_cycles': eng.markup_cycles_completed,
                        'long_layers': eng.long_layers,
                        'short_layers': eng.short_layers,
                        'long_trades': eng.long_trades,
                        'short_trades': eng.short_trades,
                        'long_pnl': round(eng.long_pnl, 2),
                        'short_pnl': round(eng.short_pnl, 2),
                        'total_pnl': round(self.realized_pnl, 2),
                    },
                    'gate_decisions': {},
                }
            },
            'symbols': [self.symbol],
            'regime': regime_map.get(eng.phase, 'UNKNOWN'),
            'trend_direction': trend_dir,
            'total_realized_pnl': round(self.realized_pnl, 2),
            'deals_completed': total_deals,
            'win_rate': round(win_rate, 1),
            'max_drawdown_pct': round(self.max_drawdown_pct, 2),
            'uptime_hours': round(uptime_h, 2),
            'fear_greed_index': None,  # Populated externally
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


# Alias for consistency with V13 naming
V14LifecycleEngine = V14LiveEngine