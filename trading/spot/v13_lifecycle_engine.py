"""
V13 Lifecycle Engine — Live phase-riding engine for paper trading.

Ticks on 1h candles (DCA execution), resamples to daily for phase signals.
Implements the 4-phase state machine: DCA → MARKUP → FLAT → MARKDOWN.

Each engine instance manages ONE coin. The paper bot runner creates one per coin.

Architecture:
    - tick(candle_1h, cash_available) → list of actions (every 1h)
    - Daily signal recomputation on midnight UTC crossing
    - State serializable via snapshot_state() / restore_state()
    - Dashboard-compatible status via get_status()
"""

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class V13Config:
    """V13 lifecycle engine configuration."""

    # ─ Top Detection (StochRSI) ─
    OB_THRESHOLD_2W: float = 93
    EARLY_WARNING_1W: float = 97
    FAILSAFE_1W: float = 50
    FAILSAFE_WINDOW_WEEKS: int = 2
    OB_FALLBACK_1W: float = 85

    # ─ DCA Transition Signals ─
    HH_HL_LOOKBACK: int = 2
    ADX_THRESHOLD: float = 20

    # ─ Markup Entry Gate ─
    SMA200_OVEREXTENSION: float = 0.20

    # ─ Markup/Markdown Ranging Exit ─
    PHASE_ADX_RANGING: float = 20
    PHASE_ADX_SUSTAINED_DAYS: int = 21

    # ─ Markup Failure ─
    MARKUP_FAIL_DD_PCT: float = 0.25
    MARKUP_FAIL_ADX: float = 25

    # ─ FLAT Phase ─
    FLAT_MIN_EVAL_DAYS: int = 14
    FLAT_MAX_EVAL_DAYS: int = 42
    FLAT_ADX_RANGING: float = 20
    FLAT_ADX_SUSTAINED_DAYS: int = 14
    HVF_LOOKBACK: int = 44

    # ─ Capital Allocation: MARKUP ─
    TIER1_PCT: float = 0.60
    TIER2_PCT: float = 0.20
    TIER3_PCT: float = 0.10
    TIER2_DELAY_WEEKS: int = 1
    TIER3_DELAY_WEEKS: int = 2

    # ─ Capital Allocation: SHORTS ─
    SHORT_TIER1_PCT: float = 0.60
    SHORT_TIER2_PCT: float = 0.20
    SHORT_TIER3_PCT: float = 0.10
    SHORT_TIER2_DELAY_WEEKS: int = 1
    SHORT_TIER3_DELAY_WEEKS: int = 2

    # ─ DCA Engine ─
    DCA_BO_PCT: float = 0.08
    DCA_SO_DEVIATION: float = 0.025
    DCA_SO_MULTIPLIER: float = 1.5
    DCA_TP_PCT: float = 0.015
    DCA_MAX_LAYERS: int = 8

    # ─ General ─
    MIN_PHASE_DAYS: int = 3

    # ─ Fibonacci ─
    FIB_RATIOS: list = field(default_factory=lambda: [0.236, 0.382, 0.5, 0.618, 0.786])
    FIB_TOLERANCE: float = 0.03
    FIB_LOOKBACK: int = 120


# ═══════════════════════════════════════════════════════════════════════════
# Technical Indicator Helpers (pure computation, no DB)
# ═══════════════════════════════════════════════════════════════════════════

def _stoch_rsi(close: pd.Series, rsi_period=14, stoch_period=14,
               k_smooth=3, d_smooth=3) -> Tuple[pd.Series, pd.Series]:
    """Compute Stochastic RSI K and D from a close Series."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / rsi_period, min_periods=rsi_period).mean()
    avg_loss = loss.ewm(alpha=1 / rsi_period, min_periods=rsi_period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi_low = rsi.rolling(stoch_period).min()
    rsi_high = rsi.rolling(stoch_period).max()
    denom = (rsi_high - rsi_low).replace(0, np.nan)
    k = (100 * (rsi - rsi_low) / denom).rolling(k_smooth).mean()
    d = k.rolling(d_smooth).mean()
    return k, d


def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Compute ADX from OHLC DataFrame."""
    high, low, close = df['high'], df['low'], df['close']
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    # Zero out whichever is smaller
    plus_dm[plus_dm < minus_dm] = 0
    minus_dm[minus_dm < plus_dm] = 0

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1 / period, min_periods=period).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, min_periods=period).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, min_periods=period).mean() / atr
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx = dx.ewm(alpha=1 / period, min_periods=period).mean()
    return adx


def compute_sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period, min_periods=period).mean()


def detect_swing_points(df: pd.DataFrame, lookback: int = 5) -> list:
    """Identify swing highs and lows using fractal method."""
    swings = []
    highs, lows = df['high'].values, df['low'].values
    dates = df.index
    for i in range(lookback, len(df) - lookback):
        if highs[i] == max(highs[i - lookback:i + lookback + 1]):
            swings.append({'date': dates[i], 'type': 'high', 'price': highs[i], 'idx': i})
        if lows[i] == min(lows[i - lookback:i + lookback + 1]):
            swings.append({'date': dates[i], 'type': 'low', 'price': lows[i], 'idx': i})
    return sorted(swings, key=lambda x: x['date'])


def compute_fib_levels(df: pd.DataFrame, lookback: int = 120,
                       fib_ratios=None) -> Optional[Dict]:
    """Compute Fibonacci retracement levels from recent swing points."""
    if fib_ratios is None:
        fib_ratios = [0.236, 0.382, 0.5, 0.618, 0.786]
    if len(df) < 60:
        return None
    window = df.iloc[-min(lookback, len(df)):]
    swings = detect_swing_points(window, lookback=10)
    if len(swings) < 2:
        return None
    highs = [s for s in swings if s['type'] == 'high']
    lows = [s for s in swings if s['type'] == 'low']
    if not highs or not lows:
        return None
    swing_high = max(highs, key=lambda s: s['price'])
    swing_low = min(lows, key=lambda s: s['price'])
    if swing_high['price'] <= swing_low['price']:
        return None
    rng = swing_high['price'] - swing_low['price']
    levels = {r: swing_high['price'] - rng * r for r in fib_ratios}
    levels['swing_high'] = swing_high['price']
    levels['swing_low'] = swing_low['price']
    return levels


def price_near_fib_support(price: float, fib_levels: Optional[Dict],
                           tolerance: float = 0.03) -> bool:
    if fib_levels is None:
        return False
    for ratio in [0.236, 0.382, 0.5, 0.618, 0.786]:
        level = fib_levels.get(ratio, 0)
        if level > 0 and abs(price - level) / level < tolerance:
            return True
    return False


def price_broke_fib_support(price: float, fib_levels: Optional[Dict],
                            tolerance: float = 0.03) -> bool:
    if fib_levels is None:
        return False
    golden = fib_levels.get(0.618, 0)
    if golden > 0 and price < golden * (1 - tolerance):
        return True
    deep = fib_levels.get(0.786, 0)
    if deep > 0 and price < deep * (1 - tolerance):
        return True
    return False


def resample_to_nweek(daily_close: pd.Series, n_weeks: int) -> pd.Series:
    """Resample daily close to n-week periods."""
    if n_weeks == 1:
        return daily_close.resample('W').last().dropna()
    start = daily_close.index[0]
    days = (daily_close.index - start).days
    period = days // (n_weeks * 7)
    grouped = daily_close.groupby(period)
    result = grouped.last()
    dates = daily_close.groupby(period).apply(lambda x: x.index[-1])
    result.index = dates.values
    return result


def compute_hh_hl_streak(df: pd.DataFrame, lookback: int = 10) -> pd.Series:
    """Compute consecutive HH/HL streak from daily OHLC."""
    streak = pd.Series(0, index=df.index, dtype=int)
    highs, lows = df['high'].values, df['low'].values
    for i in range(1, len(df)):
        if highs[i] > highs[i - 1] and lows[i] > lows[i - 1]:
            streak.iloc[i] = streak.iloc[i - 1] + 1
        else:
            streak.iloc[i] = 0
    return streak


def compute_lh_ll_streak(df: pd.DataFrame) -> pd.Series:
    """Compute consecutive LH/LL streak from daily OHLC."""
    streak = pd.Series(0, index=df.index, dtype=int)
    highs, lows = df['high'].values, df['low'].values
    for i in range(1, len(df)):
        if highs[i] < highs[i - 1] and lows[i] < lows[i - 1]:
            streak.iloc[i] = streak.iloc[i - 1] + 1
        else:
            streak.iloc[i] = 0
    return streak


# ═══════════════════════════════════════════════════════════════════════════
# Daily Signal Cache — recomputed once per daily candle close
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DailySignals:
    """Snapshot of all daily-timeframe signals. Recomputed once per day."""
    date: Optional[str] = None
    price: float = 0.0
    adx: float = np.nan
    sma50: float = np.nan
    sma200: float = np.nan
    price_vs_sma200: float = np.nan
    consec_hh_hl: int = 0
    consec_lh_ll: int = 0
    stoch_1w_k: float = np.nan
    stoch_1w_k_prev: float = np.nan
    stoch_2w_k: float = np.nan
    stoch_2w_k_prev: float = np.nan
    fib_levels: Optional[Dict] = None
    hvf_composite: float = 0.0
    cfgi: float = np.nan

    def to_dict(self) -> dict:
        d = {}
        for k, v in self.__dict__.items():
            if k == 'fib_levels':
                d[k] = v if v is None else {str(kk): vv for kk, vv in v.items()}
            elif isinstance(v, (float, np.floating)) and np.isnan(v):
                d[k] = None
            else:
                d[k] = v
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'DailySignals':
        obj = cls()
        for k, v in d.items():
            if k == 'fib_levels' and v is not None:
                converted = {}
                for kk, vv in v.items():
                    try:
                        converted[float(kk)] = vv
                    except ValueError:
                        converted[kk] = vv
                setattr(obj, k, converted)
            elif v is None and k not in ('date', 'fib_levels'):
                setattr(obj, k, np.nan)
            else:
                setattr(obj, k, v)
        return obj


# ═══════════════════════════════════════════════════════════════════════════
# V13 Lifecycle Engine
# ═══════════════════════════════════════════════════════════════════════════

class V13LifecycleEngine:
    """
    Live V13 phase-riding engine for a single coin.

    Feed 1h candles via tick(). The engine:
      - Executes DCA buys/TPs on every 1h tick
      - Detects daily candle boundaries (midnight UTC)
      - Resamples accumulated 1h candles to daily for signal computation
      - Runs 4-phase state machine: DCA → MARKUP → FLAT → MARKDOWN
    """

    # Phase constants
    DCA = 'DCA'
    MARKUP = 'MARKUP'
    FLAT = 'FLAT'
    MARKDOWN = 'MARKDOWN'

    def __init__(self, symbol: str, capital: float, config: V13Config = None):
        self.symbol = symbol
        self.initial_capital = capital
        self.cfg = config or V13Config()

        # ── 1h candle accumulator (list of dicts for efficiency) ──
        self._candles_1h: List[dict] = []
        self._last_candle_ts: Optional[datetime] = None
        self._last_daily_date: Optional[str] = None  # 'YYYY-MM-DD' of last computed daily

        # ── Daily DataFrame (resampled from 1h) ──
        self._daily_df: Optional[pd.DataFrame] = None

        # ── Current daily signals ──
        self.signals = DailySignals()

        # ── Phase state ──
        self.phase: str = self.DCA
        self.phase_start_date: Optional[str] = None  # ISO date
        self.phase_start_ts: Optional[float] = None   # epoch seconds

        # ── Markup position ──
        self.position_coins: float = 0.0
        self.entry_price: float = 0.0
        self.markup_cost: float = 0.0
        self.tier: int = 0

        # ── Short position ──
        self.short_coins: float = 0.0
        self.short_entry: float = 0.0
        self.short_cost: float = 0.0
        self.short_tier: int = 0

        # ── Top detection state ──
        self.early_warning_date: Optional[str] = None
        self.failsafe_armed: bool = False
        self.peak_2w_k: float = 0.0

        # ── Cycle tracking ──
        self.markup_cycles_completed: int = 0
        self.shorts_enabled: bool = False

        # ── FLAT state ──
        self.adx_below_20_streak: int = 0
        self.flat_from_top: bool = False
        self.flat_from_markdown: bool = False

        # ── DCA state ──
        self.dca_coins: float = 0.0
        self.dca_avg_entry: float = 0.0
        self.dca_layers: int = 0
        self.dca_last_buy_ts: Optional[float] = None
        self.dca_tp: float = 0.0
        self.dca_cost: float = 0.0

        # ── Tracking / metrics ──
        self.current_price: float = 0.0
        self.realized_pnl: float = 0.0
        self.deals_completed: int = 0
        self.deals_won: int = 0
        self.max_equity: float = capital
        self.max_drawdown_pct: float = 0.0
        self.start_time: float = datetime.now(timezone.utc).timestamp()
        self.cfgi_external: float = np.nan  # Set externally

        # Phase metrics
        self.exit_phases: int = 0
        self.markdown_phases: int = 0
        self.markup_phases: int = 0
        self.short_pnl: float = 0.0
        self.markup_pnl: float = 0.0

        logger.info(f"V13Engine initialized for {symbol}, capital=${capital:,.0f}")

    # ═══════════════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════════════

    def tick(self, candle_1h: dict, cash_available: float) -> List[dict]:
        """
        Process one 1h candle. Returns list of action dicts.

        candle_1h format: {
            'timestamp': epoch_ms or datetime,
            'open': float, 'high': float, 'low': float, 'close': float,
            'volume': float
        }
        """
        actions = []
        try:
            ts = self._parse_ts(candle_1h.get('timestamp'))
            price = float(candle_1h['close'])
            self.current_price = price

            # Initialize phase start on first tick
            if self.phase_start_ts is None:
                self.phase_start_date = str(ts.date())
                self.phase_start_ts = ts.timestamp()
                self.start_time = ts.timestamp()

            # Accumulate 1h candle
            self._candles_1h.append({
                'timestamp': ts, 'open': float(candle_1h['open']),
                'high': float(candle_1h['high']), 'low': float(candle_1h['low']),
                'close': price, 'volume': float(candle_1h.get('volume', 0))
            })
            self._last_candle_ts = ts

            # Check if a new daily candle completed (midnight UTC crossing)
            new_daily = self._check_daily_boundary(ts)
            if new_daily:
                self._recompute_daily_signals()

            # Update drawdown tracking
            eq = self._equity(price, cash_available)
            if eq > self.max_equity:
                self.max_equity = eq
            if self.max_equity > 0:
                dd = (self.max_equity - eq) / self.max_equity * 100
                if dd > self.max_drawdown_pct:
                    self.max_drawdown_pct = dd

            # Min phase hold — prevent phase TRANSITIONS but allow DCA buys/TPs
            days_in_phase = self._days_in_phase(ts)
            if days_in_phase < self.cfg.MIN_PHASE_DAYS:
                # Still run DCA engine during hold (buys AND TPs)
                if self.phase in (self.DCA, self.MARKUP):
                    acts = self._dca_tick(price, cash_available, ts)
                    actions.extend(acts)
                return actions

            # Phase dispatch — DCA ticks happen every 1h, signal checks on daily
            if self.phase == self.DCA:
                actions.extend(self._phase_dca(price, cash_available, ts, new_daily))
            elif self.phase == self.MARKUP:
                actions.extend(self._phase_markup(price, cash_available, ts, new_daily))
            elif self.phase == self.FLAT:
                if new_daily:
                    actions.extend(self._phase_flat(price, cash_available, ts))
            elif self.phase == self.MARKDOWN:
                actions.extend(self._phase_markdown(price, cash_available, ts, new_daily))

        except Exception as e:
            logger.error(f"V13Engine tick error for {self.symbol}: {e}", exc_info=True)

        return actions

    def feed_daily(self, daily_df: pd.DataFrame):
        """
        Bootstrap signals from historical daily candles.
        Call once at startup before live ticking.

        daily_df: DataFrame with DatetimeIndex and columns: open, high, low, close, volume
        """
        self._daily_df = daily_df.copy()
        self._recompute_daily_signals()
        # Don't set phase_start_date here — let the first tick() set it
        # so days_in_phase is calculated correctly from the first live candle
        logger.info(f"Fed {len(daily_df)} daily candles for {self.symbol}, "
                     f"signals date={self.signals.date}")

    def set_cfgi(self, value: float):
        """Update the externally-provided CFGI value."""
        self.cfgi_external = value
        self.signals.cfgi = value

    def snapshot_state(self) -> dict:
        """Serialize all engine state to a dict for persistence."""
        return {
            'symbol': self.symbol,
            'initial_capital': self.initial_capital,
            'phase': self.phase,
            'phase_start_date': self.phase_start_date,
            'phase_start_ts': self.phase_start_ts,
            # Markup position
            'position_coins': self.position_coins,
            'entry_price': self.entry_price,
            'markup_cost': self.markup_cost,
            'tier': self.tier,
            # Short position
            'short_coins': self.short_coins,
            'short_entry': self.short_entry,
            'short_cost': self.short_cost,
            'short_tier': self.short_tier,
            # Top detection
            'early_warning_date': self.early_warning_date,
            'failsafe_armed': self.failsafe_armed,
            'peak_2w_k': self.peak_2w_k,
            # Cycles
            'markup_cycles_completed': self.markup_cycles_completed,
            'shorts_enabled': self.shorts_enabled,
            # FLAT
            'adx_below_20_streak': self.adx_below_20_streak,
            'flat_from_top': self.flat_from_top,
            'flat_from_markdown': self.flat_from_markdown,
            # DCA
            'dca_coins': self.dca_coins,
            'dca_avg_entry': self.dca_avg_entry,
            'dca_layers': self.dca_layers,
            'dca_last_buy_ts': self.dca_last_buy_ts,
            'dca_tp': self.dca_tp,
            'dca_cost': self.dca_cost,
            # Metrics
            'current_price': self.current_price,
            'realized_pnl': self.realized_pnl,
            'deals_completed': self.deals_completed,
            'deals_won': self.deals_won,
            'max_equity': self.max_equity,
            'max_drawdown_pct': self.max_drawdown_pct,
            'start_time': self.start_time,
            'cfgi_external': self.cfgi_external if not np.isnan(self.cfgi_external) else None,
            'exit_phases': self.exit_phases,
            'markdown_phases': self.markdown_phases,
            'markup_phases': self.markup_phases,
            'short_pnl': self.short_pnl,
            'markup_pnl': self.markup_pnl,
            # Signals snapshot
            'signals': self.signals.to_dict(),
            # Last daily date
            '_last_daily_date': self._last_daily_date,
        }

    def restore_state(self, state: dict):
        """Restore engine state from a saved dict."""
        for key in [
            'phase', 'phase_start_date', 'phase_start_ts',
            'position_coins', 'entry_price', 'markup_cost', 'tier',
            'short_coins', 'short_entry', 'short_cost', 'short_tier',
            'early_warning_date', 'failsafe_armed', 'peak_2w_k',
            'markup_cycles_completed', 'shorts_enabled',
            'adx_below_20_streak', 'flat_from_top', 'flat_from_markdown',
            'dca_coins', 'dca_avg_entry', 'dca_layers', 'dca_last_buy_ts',
            'dca_tp', 'dca_cost',
            'current_price', 'realized_pnl', 'deals_completed', 'deals_won',
            'max_equity', 'max_drawdown_pct', 'start_time',
            'exit_phases', 'markdown_phases', 'markup_phases',
            'short_pnl', 'markup_pnl', '_last_daily_date',
        ]:
            if key in state:
                setattr(self, key, state[key])

        cfgi_val = state.get('cfgi_external')
        self.cfgi_external = cfgi_val if cfgi_val is not None else np.nan

        if 'signals' in state and state['signals']:
            self.signals = DailySignals.from_dict(state['signals'])

        logger.info(f"V13Engine state restored for {self.symbol}, phase={self.phase}")

    def get_status(self) -> dict:
        """Return status dict matching dashboard format."""
        price = self.current_price
        cash = self.initial_capital  # Approximation; real cash tracked by runner
        invested = self.markup_cost + self.dca_cost + self.short_cost
        equity = self._equity(price, cash - invested)

        # Unrealized PnL
        unrealized = 0.0
        if self.position_coins > 0 and self.entry_price > 0:
            unrealized += (price - self.entry_price) * self.position_coins
        if self.dca_coins > 0 and self.dca_avg_entry > 0:
            unrealized += (price - self.dca_avg_entry) * self.dca_coins
        if self.short_coins > 0 and self.short_entry > 0:
            unrealized += (self.short_entry - price) * self.short_coins

        pnl_pct = ((equity - self.initial_capital) / self.initial_capital * 100
                    if self.initial_capital > 0 else 0.0)

        # Map phase to V12-compatible state
        state_map = {
            self.DCA: 'ACCUMULATING',
            self.MARKUP: 'RIDING',
            self.FLAT: 'WAITING',
            self.MARKDOWN: 'SHORTING',
        }
        side = 'none'
        if self.position_coins > 0 or self.dca_coins > 0:
            side = 'long'
        elif self.short_coins > 0:
            side = 'short'

        # Next SO / TP prices
        next_so = None
        if self.dca_layers > 0 and self.dca_avg_entry > 0:
            target_drop = self.cfg.DCA_SO_DEVIATION * self.dca_layers
            next_so = self.dca_avg_entry * (1 - target_drop)
        next_tp = self.dca_tp if self.dca_tp > 0 else None

        # Regime from phase
        regime_map = {
            self.DCA: 'ACCUMULATION',
            self.MARKUP: 'TRENDING',
            self.FLAT: 'RANGING',
            self.MARKDOWN: 'TRENDING',
        }
        trend_dir = 'bullish' if self.phase in (self.DCA, self.MARKUP) else 'bearish'

        uptime_h = (datetime.now(timezone.utc).timestamp() - self.start_time) / 3600

        win_rate = (self.deals_won / self.deals_completed * 100
                    if self.deals_completed > 0 else 0.0)

        return {
            'running': True,
            'mode': 'paper',
            'profile': 'medium',
            'exchange': 'hyperliquid',
            'capital': self.initial_capital,
            'equity': equity,
            'cash': cash - invested,
            'pnl_pct': pnl_pct,
            'coins': {
                self.symbol: {
                    'state': state_map.get(self.phase, 'UNKNOWN'),
                    'side': side,
                    'layers': self.dca_layers,
                    'avg_entry': self.dca_avg_entry or self.entry_price or 0,
                    'current_price': price,
                    'unrealized_pnl': unrealized,
                    'next_so_price': next_so,
                    'next_tp_price': next_tp,
                    'invested': invested,
                    'realized_pnl': self.realized_pnl,
                    'lifecycle_phase': self.phase,
                    'cfgi': self.cfgi_external if not np.isnan(self.cfgi_external) else None,
                }
            },
            'lifecycle': {
                self.symbol: {
                    'phase': self.phase,
                    'score': self.signals.hvf_composite,
                    'daily_score': self.signals.adx if not np.isnan(self.signals.adx) else 0,
                    'metrics': {
                        'exit_phases': self.exit_phases,
                        'markdown_phases': self.markdown_phases,
                        'markup_phases': self.markup_phases,
                        'short_pnl': self.short_pnl,
                        'markup_pnl': self.markup_pnl,
                    },
                    'gate_decisions': {},
                }
            },
            'symbols': [self.symbol],
            'regime': regime_map.get(self.phase, 'UNKNOWN'),
            'trend_direction': trend_dir,
            'total_realized_pnl': self.realized_pnl,
            'deals_completed': self.deals_completed,
            'win_rate': win_rate,
            'max_drawdown_pct': self.max_drawdown_pct,
            'uptime_hours': uptime_h,
            'fear_greed_index': self.cfgi_external if not np.isnan(self.cfgi_external) else None,
            'last_update': datetime.now(timezone.utc).isoformat(),
            'timeframe': '1h',
        }

    # ═══════════════════════════════════════════════════════════════════
    # Internal: Daily boundary detection & signal recomputation
    # ═══════════════════════════════════════════════════════════════════

    def _parse_ts(self, ts) -> datetime:
        if isinstance(ts, datetime):
            return ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts
        if isinstance(ts, (int, float)):
            if ts > 1e12:
                ts = ts / 1000  # ms → s
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        if isinstance(ts, str):
            return pd.Timestamp(ts).to_pydatetime().replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc)

    def _check_daily_boundary(self, ts: datetime) -> bool:
        """Returns True if this 1h candle starts a new UTC day."""
        current_date = ts.strftime('%Y-%m-%d')
        if self._last_daily_date is None:
            self._last_daily_date = current_date
            return len(self._candles_1h) > 24  # Only if we have enough data
        if current_date != self._last_daily_date:
            self._last_daily_date = current_date
            return True
        return False

    def _resample_1h_to_daily(self) -> pd.DataFrame:
        """Resample accumulated 1h candles to daily OHLCV."""
        if not self._candles_1h:
            return pd.DataFrame()
        df = pd.DataFrame(self._candles_1h)
        df['dt'] = pd.to_datetime(df['timestamp'])
        df.set_index('dt', inplace=True)
        df.sort_index(inplace=True)
        daily = df.resample('D').agg({
            'open': 'first', 'high': 'max', 'low': 'min',
            'close': 'last', 'volume': 'sum'
        }).dropna(subset=['close'])
        return daily

    def _recompute_daily_signals(self):
        """Recompute all daily-timeframe signals from current data."""
        # Merge bootstrapped daily with resampled 1h
        resampled = self._resample_1h_to_daily()

        if self._daily_df is not None and len(self._daily_df) > 0:
            if len(resampled) > 0:
                # Only append days not already in bootstrapped data
                new_days = resampled[resampled.index > self._daily_df.index[-1]]
                if len(new_days) > 0:
                    self._daily_df = pd.concat([self._daily_df, new_days])

            # Truncate to current candle date so signals reflect point-in-time
            # (critical for backfill: bootstrapped data may extend beyond current tick)
            if self._last_candle_ts is not None:
                cutoff = pd.Timestamp(self._last_candle_ts.date(), tz='UTC')
                daily = self._daily_df[self._daily_df.index <= cutoff]
            else:
                daily = self._daily_df
        else:
            self._daily_df = resampled
            daily = resampled

        if len(daily) < 20:
            logger.debug(f"Not enough daily data ({len(daily)}) to compute signals")
            return

        try:
            price = daily['close'].iloc[-1]
            sig = DailySignals()
            sig.date = str(daily.index[-1].date())
            sig.price = price
            sig.cfgi = self.cfgi_external

            # ADX
            adx_series = compute_adx(daily, 14)
            sig.adx = float(adx_series.iloc[-1]) if not adx_series.empty else np.nan

            # SMAs
            sig.sma50 = float(compute_sma(daily['close'], 50).iloc[-1])
            sig.sma200 = float(compute_sma(daily['close'], 200).iloc[-1])
            if not np.isnan(sig.sma200) and sig.sma200 > 0:
                sig.price_vs_sma200 = (price - sig.sma200) / sig.sma200

            # HH/HL and LH/LL streaks
            hh_hl = compute_hh_hl_streak(daily)
            lh_ll = compute_lh_ll_streak(daily)
            sig.consec_hh_hl = int(hh_hl.iloc[-1])
            sig.consec_lh_ll = int(lh_ll.iloc[-1])

            # StochRSI on 1W and 2W
            close_1w = resample_to_nweek(daily['close'], 1)
            close_2w = resample_to_nweek(daily['close'], 2)

            if len(close_1w) >= 20:
                k1w, _ = _stoch_rsi(close_1w)
                if len(k1w) >= 2:
                    sig.stoch_1w_k = float(k1w.iloc[-1])
                    sig.stoch_1w_k_prev = float(k1w.iloc[-2])

            if len(close_2w) >= 20:
                k2w, _ = _stoch_rsi(close_2w)
                if len(k2w) >= 2:
                    sig.stoch_2w_k = float(k2w.iloc[-1])
                    sig.stoch_2w_k_prev = float(k2w.iloc[-2])

            # Fibonacci
            sig.fib_levels = compute_fib_levels(daily, self.cfg.FIB_LOOKBACK,
                                                 self.cfg.FIB_RATIOS)

            # HVF composite (for logging)
            try:
                from trading.spot.backtest_results.v13.test_hvf_daily import composite_hvf_score
                hvf_window = daily.iloc[-min(self.cfg.HVF_LOOKBACK, len(daily)):]
                result = composite_hvf_score(hvf_window)
                composite = result[0]
                if hasattr(composite, 'iloc') and len(composite) > 0:
                    sig.hvf_composite = float(composite.iloc[-1])
                else:
                    sig.hvf_composite = float(composite)
            except Exception:
                sig.hvf_composite = 0.0

            self.signals = sig
            logger.debug(f"Daily signals updated for {self.symbol}: "
                         f"ADX={sig.adx:.1f}, HH_HL={sig.consec_hh_hl}, "
                         f"1W_K={sig.stoch_1w_k:.1f}, 2W_K={sig.stoch_2w_k:.1f}")

        except Exception as e:
            logger.error(f"Signal computation error for {self.symbol}: {e}", exc_info=True)

    # ═══════════════════════════════════════════════════════════════════
    # Internal: Equity helper
    # ═══════════════════════════════════════════════════════════════════

    def _equity(self, price: float, cash: float) -> float:
        eq = cash
        eq += self.position_coins * price
        eq += self.dca_coins * price
        if self.short_coins > 0:
            eq += self.short_cost + (self.short_entry - price) * self.short_coins
        return eq

    def _days_in_phase(self, ts: datetime) -> float:
        if self.phase_start_ts is None:
            return 999
        return (ts.timestamp() - self.phase_start_ts) / 86400

    # ═══════════════════════════════════════════════════════════════════
    # Internal: DCA Engine (runs every 1h tick)
    # ═══════════════════════════════════════════════════════════════════

    def _dca_tick(self, price: float, cash_available: float,
                  ts: datetime) -> List[dict]:
        """Run DCA logic: check TP, then check for new layer buy."""
        actions = []
        cfg = self.cfg

        # Check TP first
        if self.dca_coins > 0 and self.dca_tp > 0 and price >= self.dca_tp:
            proceeds = self.dca_coins * price
            pnl = proceeds - self.dca_cost
            pnl_pct = pnl / self.dca_cost * 100 if self.dca_cost > 0 else 0
            self.realized_pnl += pnl
            self.deals_completed += 1
            if pnl > 0:
                self.deals_won += 1
            actions.append({
                'action': 'SELL', 'symbol': self.symbol,
                'qty': self.dca_coins, 'price': price,
                'reason': f'DCA_TP_{self.dca_layers}L',
                'pnl': pnl, 'pnl_pct': pnl_pct,
            })
            logger.info(f"{self.symbol} DCA TP hit: {self.dca_layers}L, "
                        f"pnl={pnl_pct:+.1f}%")
            self.dca_coins = 0
            self.dca_avg_entry = 0
            self.dca_layers = 0
            self.dca_tp = 0
            self.dca_cost = 0
            self.dca_last_buy_ts = None
            return actions

        # Check for new layer buy
        if self.dca_layers >= cfg.DCA_MAX_LAYERS:
            return actions

        # Don't buy more than once per hour
        if self.dca_last_buy_ts and (ts.timestamp() - self.dca_last_buy_ts) < 3600:
            return actions

        available = cash_available * 0.90

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
                order_size = available * cfg.DCA_BO_PCT
            else:
                order_size = available * cfg.DCA_BO_PCT * (
                    cfg.DCA_SO_MULTIPLIER ** min(self.dca_layers, 4))
            order_size = min(order_size, cash_available * 0.3)

            if order_size < 10 or order_size > cash_available:
                return actions

            coins = order_size / price
            self.dca_coins += coins
            self.dca_cost += order_size
            self.dca_layers += 1
            self.dca_last_buy_ts = ts.timestamp()
            self.dca_avg_entry = self.dca_cost / self.dca_coins
            self.dca_tp = self.dca_avg_entry * (1 + cfg.DCA_TP_PCT)

            actions.append({
                'action': 'BUY', 'symbol': self.symbol,
                'qty': coins, 'price': price,
                'reason': f'DCA_L{self.dca_layers}',
                'cost': order_size,
            })
            logger.info(f"{self.symbol} DCA buy L{self.dca_layers}: "
                        f"${order_size:.0f} @ {price:.2f}, "
                        f"avg={self.dca_avg_entry:.2f}, tp={self.dca_tp:.2f}")

        return actions

    def _dca_close(self, price: float, reason: str) -> List[dict]:
        """Hard-exit all DCA positions."""
        actions = []
        if self.dca_coins <= 0:
            return actions
        proceeds = self.dca_coins * price
        pnl = proceeds - self.dca_cost
        pnl_pct = pnl / self.dca_cost * 100 if self.dca_cost > 0 else 0
        self.realized_pnl += pnl
        self.deals_completed += 1
        if pnl > 0:
            self.deals_won += 1
        actions.append({
            'action': 'SELL', 'symbol': self.symbol,
            'qty': self.dca_coins, 'price': price,
            'reason': f'DCA_CLOSE_{reason}',
            'pnl': pnl, 'pnl_pct': pnl_pct,
        })
        logger.info(f"{self.symbol} DCA close ({reason}): {self.dca_layers}L, "
                     f"pnl={pnl_pct:+.1f}%")
        self.dca_coins = 0
        self.dca_avg_entry = 0
        self.dca_layers = 0
        self.dca_tp = 0
        self.dca_cost = 0
        self.dca_last_buy_ts = None
        return actions

    # ═══════════════════════════════════════════════════════════════════
    # Internal: Position management
    # ═══════════════════════════════════════════════════════════════════

    def _buy_markup(self, price: float, pct: float, tier: int,
                    cash_available: float) -> List[dict]:
        actions = []
        amount = cash_available * pct
        if amount <= 0 or amount > cash_available:
            return actions
        coins = amount / price
        self.position_coins += coins
        self.markup_cost += amount
        if self.entry_price == 0:
            self.entry_price = price
        self.tier = tier
        actions.append({
            'action': 'BUY', 'symbol': self.symbol,
            'qty': coins, 'price': price,
            'reason': f'MARKUP_T{tier}', 'cost': amount,
        })
        logger.info(f"{self.symbol} Markup T{tier}: ${amount:.0f} @ {price:.2f}")
        return actions

    def _sell_all_markup(self, price: float, reason: str) -> List[dict]:
        actions = []
        if self.position_coins <= 0:
            return actions
        proceeds = self.position_coins * price
        pnl = proceeds - self.markup_cost
        pnl_pct = ((price - self.entry_price) / self.entry_price * 100
                    if self.entry_price > 0 else 0)
        self.realized_pnl += pnl
        self.markup_pnl += pnl
        self.deals_completed += 1
        if pnl > 0:
            self.deals_won += 1
        actions.append({
            'action': 'SELL', 'symbol': self.symbol,
            'qty': self.position_coins, 'price': price,
            'reason': reason, 'pnl': pnl, 'pnl_pct': pnl_pct,
        })
        logger.info(f"{self.symbol} Markup sell ({reason}): pnl={pnl_pct:+.1f}%")
        self.position_coins = 0
        self.entry_price = 0
        self.markup_cost = 0
        self.tier = 0
        return actions

    def _open_short(self, price: float, pct: float, tier: int,
                    cash_available: float) -> List[dict]:
        actions = []
        amount = cash_available * pct
        if amount <= 0 or amount > cash_available:
            return actions
        coins = amount / price
        self.short_coins += coins
        self.short_cost += amount
        self.short_entry = self.short_cost / self.short_coins
        self.short_tier = tier
        actions.append({
            'action': 'SHORT_OPEN', 'symbol': f'{self.symbol}:USDC',
            'qty': coins, 'price': price,
            'reason': f'MARKDOWN_T{tier}', 'cost': amount,
        })
        logger.info(f"{self.symbol} Short T{tier}: ${amount:.0f} @ {price:.2f}")
        return actions

    def _close_short(self, price: float, reason: str) -> List[dict]:
        actions = []
        if self.short_coins <= 0:
            return actions
        pnl = (self.short_entry - price) * self.short_coins
        pnl_pct = ((self.short_entry - price) / self.short_entry * 100
                    if self.short_entry > 0 else 0)
        self.realized_pnl += pnl
        self.short_pnl += pnl
        self.deals_completed += 1
        if pnl > 0:
            self.deals_won += 1
        actions.append({
            'action': 'SHORT_CLOSE', 'symbol': f'{self.symbol}:USDC',
            'qty': self.short_coins, 'price': price,
            'reason': reason, 'pnl': pnl, 'pnl_pct': pnl_pct,
        })
        logger.info(f"{self.symbol} Short close ({reason}): pnl={pnl_pct:+.1f}%")
        self.short_coins = 0
        self.short_entry = 0
        self.short_cost = 0
        self.short_tier = 0
        return actions

    # ═══════════════════════════════════════════════════════════════════
    # Internal: Phase transitions
    # ═══════════════════════════════════════════════════════════════════

    def _change_phase(self, new_phase: str, reason: str, price: float,
                      cash_available: float, ts: datetime) -> List[dict]:
        actions = []
        old = self.phase

        # Close short if leaving MARKDOWN
        if old == self.MARKDOWN and self.short_coins > 0:
            actions.extend(self._close_short(price, f'{old}->{new_phase}'))

        self.phase = new_phase
        self.phase_start_date = str(ts.date()) if hasattr(ts, 'date') else ts
        self.phase_start_ts = ts.timestamp()

        actions.append({
            'action': 'PHASE_CHANGE', 'from': old, 'to': new_phase,
            'reason': reason, 'symbol': self.symbol, 'price': price,
        })
        logger.info(f"{self.symbol} Phase: {old} -> {new_phase} | {reason}")

        # Track completed markup cycles
        if old == self.MARKUP and new_phase == self.FLAT:
            self.markup_cycles_completed += 1
            self.exit_phases += 1
            self.markup_phases += 1
            if not self.shorts_enabled:
                self.shorts_enabled = True
                logger.info(f"{self.symbol} Shorts enabled after cycle "
                            f"#{self.markup_cycles_completed}")

        if new_phase == self.MARKDOWN:
            self.markdown_phases += 1

        # Reset ADX streak
        self.adx_below_20_streak = 0

        # Track FLAT entry context
        if new_phase == self.FLAT:
            self.flat_from_top = (old == self.MARKUP and
                                  ('OB' in reason or 'failsafe' in reason.lower()))
            self.flat_from_markdown = (old == self.MARKDOWN)

        # Open short T1 when entering MARKDOWN
        if (new_phase == self.MARKDOWN and self.shorts_enabled
                and cash_available > 0):
            actions.extend(self._open_short(
                price, self.cfg.SHORT_TIER1_PCT, 1, cash_available))

        return actions

    # ═══════════════════════════════════════════════════════════════════
    # Internal: Phase logic
    # ═══════════════════════════════════════════════════════════════════

    def _phase_dca(self, price: float, cash: float, ts: datetime,
                   new_daily: bool) -> List[dict]:
        """DCA phase: run DCA engine + check for transitions on daily."""
        actions = self._dca_tick(price, cash, ts)

        if not new_daily:
            return actions

        sig = self.signals

        # DCA → MARKUP: HH_HL + Fib_support + SMA200 not overextended
        if sig.consec_hh_hl >= self.cfg.HH_HL_LOOKBACK:
            if price_near_fib_support(price, sig.fib_levels, self.cfg.FIB_TOLERANCE):
                overext = sig.price_vs_sma200
                if not np.isnan(overext) and overext > self.cfg.SMA200_OVEREXTENSION:
                    pass  # Blocked by overextension
                else:
                    note = f'HH_HL+Fib_support'
                    if not np.isnan(sig.cfgi) and sig.cfgi > 40:
                        note += f'+CFGI={sig.cfgi:.0f}'
                    if not np.isnan(overext):
                        note += f' (SMA200={overext * 100:+.0f}%)'
                    if self.dca_coins > 0:
                        note += f' (DCA riding {self.dca_layers}L)'
                    acts = self._change_phase(self.MARKUP, note, price, cash, ts)
                    actions.extend(acts)
                    actions.extend(self._buy_markup(
                        price, self.cfg.TIER1_PCT, 1, cash))
                    self.early_warning_date = None
                    self.failsafe_armed = False
                    self.peak_2w_k = 0
                    return actions

        # DCA → MARKDOWN: ADX>20 + Fib_break (SMA200 gate removed — crashes start
        # from above 200-SMA; gate delayed legitimate shorts for 4/5 coins to save
        # one XRP edge case. Failure detector handles bad shorts instead.)
        if not np.isnan(sig.adx) and sig.adx > self.cfg.ADX_THRESHOLD:
            if price_broke_fib_support(price, sig.fib_levels, self.cfg.FIB_TOLERANCE):
                overext = sig.price_vs_sma200
                if self.shorts_enabled:
                    note = f'ADX={sig.adx:.0f}+Fib_break'
                    if not np.isnan(overext):
                        note += f' (SMA200={overext * 100:+.0f}%)'
                    if self.dca_coins > 0:
                        actions.extend(self._dca_close(price, 'HARD_EXIT_MARKDOWN'))
                    acts = self._change_phase(self.MARKDOWN, note, price, cash, ts)
                    actions.extend(acts)

        return actions

    def _phase_markup(self, price: float, cash: float, ts: datetime,
                      new_daily: bool) -> List[dict]:
        """MARKUP phase: let DCA TPs hit, tier adds, top detection."""
        actions = []

        # Let DCA TPs hit naturally
        if self.dca_coins > 0:
            actions.extend(self._dca_tick(price, cash, ts))

        if not new_daily:
            return actions

        sig = self.signals

        # Track peak 2W K
        if not np.isnan(sig.stoch_2w_k) and sig.stoch_2w_k > self.peak_2w_k:
            self.peak_2w_k = sig.stoch_2w_k

        # ── Layer 1: Early warning — 1W crosses below 97 ──
        if (not np.isnan(sig.stoch_1w_k) and not np.isnan(sig.stoch_1w_k_prev)
                and sig.stoch_1w_k_prev >= self.cfg.EARLY_WARNING_1W
                and sig.stoch_1w_k < self.cfg.EARLY_WARNING_1W
                and self.early_warning_date is None):
            self.early_warning_date = str(ts.date())
            logger.info(f"{self.symbol} Early warning: 1W K crossed below "
                        f"{self.cfg.EARLY_WARNING_1W} (2W peak={self.peak_2w_k:.0f})")

        # ── Layer 2: Primary exit — 2W OB93 cross-down ──
        if (not np.isnan(sig.stoch_2w_k) and not np.isnan(sig.stoch_2w_k_prev)
                and sig.stoch_2w_k_prev >= self.cfg.OB_THRESHOLD_2W
                and sig.stoch_2w_k < self.cfg.OB_THRESHOLD_2W):
            actions.extend(self._sell_all_markup(price, 'PRIMARY_2W_OB93'))
            if self.dca_coins > 0:
                actions.extend(self._dca_close(price, 'TOP_EXIT'))
            actions.extend(self._change_phase(
                self.FLAT, f'2W OB93 exit', price, cash, ts))
            self._reset_top_state()
            return actions

        # ── Layer 2b: Fallback — 1W OB85 when 2W never reached OB ──
        if (self.peak_2w_k < self.cfg.OB_THRESHOLD_2W
                and self.early_warning_date is not None):
            if (not np.isnan(sig.stoch_1w_k) and not np.isnan(sig.stoch_1w_k_prev)
                    and sig.stoch_1w_k_prev >= self.cfg.OB_FALLBACK_1W
                    and sig.stoch_1w_k < self.cfg.OB_FALLBACK_1W):
                reason = (f'FALLBACK_1W_OB85 (2W_peak={self.peak_2w_k:.0f})')
                actions.extend(self._sell_all_markup(price, reason))
                if self.dca_coins > 0:
                    actions.extend(self._dca_close(price, 'TOP_EXIT'))
                actions.extend(self._change_phase(
                    self.FLAT,
                    f'1W OB85 fallback (2W peak={self.peak_2w_k:.0f}<93)',
                    price, cash, ts))
                self._reset_top_state()
                return actions

        # ── Layer 3: Failsafe — 1W K<50 after armed ──
        if self.early_warning_date and not self.failsafe_armed:
            ew_date = datetime.strptime(self.early_warning_date, '%Y-%m-%d')
            if (ts - ew_date.replace(tzinfo=timezone.utc)).days >= (
                    self.cfg.FAILSAFE_WINDOW_WEEKS * 7):
                self.failsafe_armed = True
                logger.info(f"{self.symbol} Failsafe armed")

        if self.failsafe_armed:
            if (not np.isnan(sig.stoch_1w_k) and not np.isnan(sig.stoch_1w_k_prev)
                    and sig.stoch_1w_k_prev >= self.cfg.FAILSAFE_1W
                    and sig.stoch_1w_k < self.cfg.FAILSAFE_1W):
                actions.extend(self._sell_all_markup(price, 'FAILSAFE_1W_K50'))
                if self.dca_coins > 0:
                    actions.extend(self._dca_close(price, 'TOP_EXIT'))
                actions.extend(self._change_phase(
                    self.FLAT, 'Failsafe 1W K<50', price, cash, ts))
                self._reset_top_state()
                return actions

        # ── Layer 4: Ranging exit — ADX<20 sustained, min 14d in phase ──
        days_in = self._days_in_phase(ts)
        if days_in >= 14:
            if not np.isnan(sig.adx) and sig.adx < self.cfg.PHASE_ADX_RANGING:
                self.adx_below_20_streak += 1
                if self.adx_below_20_streak >= self.cfg.PHASE_ADX_SUSTAINED_DAYS:
                    reason = (f'MARKUP_RANGING (ADX<{self.cfg.PHASE_ADX_RANGING} '
                              f'for {self.adx_below_20_streak}d)')
                    actions.extend(self._sell_all_markup(price, reason))
                    if self.dca_coins > 0:
                        actions.extend(self._dca_close(price, 'RANGING_EXIT'))
                    actions.extend(self._change_phase(
                        self.FLAT, f'Markup ranging exit', price, cash, ts))
                    self._reset_top_state()
                    return actions
            else:
                self.adx_below_20_streak = 0

        # ── Layer 5: Failure — 25% DD + ADX>25 ──
        if self.entry_price > 0:
            dd = (price - self.entry_price) / self.entry_price
            if dd < -self.cfg.MARKUP_FAIL_DD_PCT:
                if not np.isnan(sig.adx) and sig.adx > self.cfg.MARKUP_FAIL_ADX:
                    reason = f'MARKUP_FAIL (dd={dd * 100:.0f}%, ADX={sig.adx:.0f})'
                    actions.extend(self._sell_all_markup(price, reason))
                    if self.dca_coins > 0:
                        actions.extend(self._dca_close(price, 'MARKUP_FAIL'))
                    actions.extend(self._change_phase(
                        self.FLAT, reason, price, cash, ts))
                    self._reset_top_state()
                    return actions

        # ── Tier adds ──
        actions.extend(self._check_markup_tiers(price, cash, ts))

        return actions

    def _check_markup_tiers(self, price: float, cash: float,
                            ts: datetime) -> List[dict]:
        actions = []
        if self.tier >= 3 or self.phase_start_ts is None:
            return actions
        weeks_in = self._days_in_phase(ts) / 7
        sig = self.signals

        if self.tier == 1 and weeks_in >= self.cfg.TIER2_DELAY_WEEKS:
            if (self.entry_price > 0 and price >= self.entry_price
                    and not np.isnan(sig.cfgi) and sig.cfgi > 40):
                actions.extend(self._buy_markup(
                    price, self.cfg.TIER2_PCT, 2, cash))

        elif self.tier == 2 and weeks_in >= self.cfg.TIER3_DELAY_WEEKS:
            if (self.entry_price > 0 and price >= self.entry_price
                    and not np.isnan(sig.adx) and sig.adx > 25
                    and sig.consec_hh_hl >= self.cfg.HH_HL_LOOKBACK):
                actions.extend(self._buy_markup(
                    price, self.cfg.TIER3_PCT, 3, cash))

        return actions

    def _phase_flat(self, price: float, cash: float,
                    ts: datetime) -> List[dict]:
        """FLAT phase: route based on entry context."""
        actions = []
        sig = self.signals
        days_flat = self._days_in_phase(ts)

        if days_flat < self.cfg.FLAT_MIN_EVAL_DAYS:
            return actions

        # PATH 1: From TOP → check for MARKDOWN (SMA200 gate removed)
        if self.flat_from_top:
            if not np.isnan(sig.adx) and sig.adx > self.cfg.ADX_THRESHOLD:
                if price_broke_fib_support(price, sig.fib_levels, self.cfg.FIB_TOLERANCE):
                    overext = sig.price_vs_sma200
                    note = (f'FLAT->MARKDOWN: Post-top, ADX={sig.adx:.0f}'
                            f'+Fib_break (flat {days_flat:.0f}d)')
                    if not np.isnan(overext):
                        note += f' (SMA200={overext * 100:+.0f}%)'
                    actions.extend(self._change_phase(
                        self.MARKDOWN, note, price, cash, ts))
                    return actions

            if days_flat >= self.cfg.FLAT_MAX_EVAL_DAYS:
                actions.extend(self._change_phase(
                    self.DCA,
                    f'FLAT->DCA: No markdown after {days_flat:.0f}d',
                    price, cash, ts))
            return actions

        # PATH 2 & 3: From RANGING or MARKDOWN → wait for ADX ranging → DCA
        if not np.isnan(sig.adx) and sig.adx < self.cfg.FLAT_ADX_RANGING:
            self.adx_below_20_streak += 1
        else:
            self.adx_below_20_streak = 0

        if self.adx_below_20_streak >= self.cfg.FLAT_ADX_SUSTAINED_DAYS:
            actions.extend(self._change_phase(
                self.DCA,
                f'FLAT->DCA: Ranging confirmed '
                f'(ADX<{self.cfg.FLAT_ADX_RANGING} for '
                f'{self.adx_below_20_streak}d)',
                price, cash, ts))
            self.adx_below_20_streak = 0

        return actions

    def _phase_markdown(self, price: float, cash: float, ts: datetime,
                        new_daily: bool) -> List[dict]:
        """MARKDOWN phase: hold shorts, check for exit."""
        actions = []
        if not new_daily:
            return actions

        sig = self.signals
        days_in = self._days_in_phase(ts)

        # ADX trend exhaustion → FLAT
        if days_in >= 14:
            if not np.isnan(sig.adx) and sig.adx < self.cfg.PHASE_ADX_RANGING:
                self.adx_below_20_streak += 1
                if self.adx_below_20_streak >= self.cfg.PHASE_ADX_SUSTAINED_DAYS:
                    actions.extend(self._change_phase(
                        self.FLAT,
                        f'MARKDOWN->FLAT: Ranging '
                        f'(ADX<{self.cfg.PHASE_ADX_RANGING} for '
                        f'{self.adx_below_20_streak}d)',
                        price, cash, ts))
                    return actions
            else:
                self.adx_below_20_streak = 0

        # Failure: 25% rise + ADX>25
        if self.short_entry > 0 and self.short_coins > 0:
            rise = (price - self.short_entry) / self.short_entry
            if rise > self.cfg.MARKUP_FAIL_DD_PCT:
                if not np.isnan(sig.adx) and sig.adx > self.cfg.MARKUP_FAIL_ADX:
                    actions.extend(self._change_phase(
                        self.FLAT,
                        f'MARKDOWN_FAIL: +{rise * 100:.0f}% above short, '
                        f'ADX={sig.adx:.0f}',
                        price, cash, ts))
                    return actions

        # Short tier adds
        if self.short_tier < 3 and self.phase_start_ts is not None:
            weeks_in = days_in / 7

            if (self.short_tier == 1
                    and weeks_in >= self.cfg.SHORT_TIER2_DELAY_WEEKS
                    and self.shorts_enabled and cash > 0):
                if (self.short_entry > 0 and price <= self.short_entry
                        and not np.isnan(sig.cfgi) and sig.cfgi < 40):
                    actions.extend(self._open_short(
                        price, self.cfg.SHORT_TIER2_PCT, 2, cash))

            elif (self.short_tier == 2
                  and weeks_in >= self.cfg.SHORT_TIER3_DELAY_WEEKS
                  and self.shorts_enabled and cash > 0):
                if (self.short_entry > 0 and price <= self.short_entry
                        and not np.isnan(sig.adx) and sig.adx > 25
                        and sig.consec_lh_ll >= 2):
                    actions.extend(self._open_short(
                        price, self.cfg.SHORT_TIER3_PCT, 3, cash))

        return actions

    def _reset_top_state(self):
        self.early_warning_date = None
        self.failsafe_armed = False
        self.peak_2w_k = 0