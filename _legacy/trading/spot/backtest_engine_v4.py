"""Spot DCA Backtest Engine V4 — V3 + Dwell-Time Compression.

Extends V3 with dwell-time decay: the longer BBW stays below its rolling median,
the tighter the grid becomes (deviation shrinks toward a floor). On breakout signals,
snap back to normal spacing.

See: projects/ait-product/dwell-time-compression-spec.md
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..regime_detector import classify_regime_v2
from ..indicators import (
    atr as compute_atr,
    atr_pct as compute_atr_pct,
    compute_all as compute_all_indicators,
    bollinger_band_width,
    volume_sma,
)

# Patch missing regime_transition_signals if needed (v3 imports it but it may not exist)
import trading.indicators as _ind
if not hasattr(_ind, 'regime_transition_signals'):
    def _regime_transition_signals_stub(df, regimes):
        """Stub: returns DataFrame with neutral stability/pressure."""
        return pd.DataFrame({
            "regime_stability": pd.Series(0.5, index=df.index),
            "regime_transition_pressure": pd.Series(0.0, index=df.index),
        })
    _ind.regime_transition_signals = _regime_transition_signals_stub

if not hasattr(_ind, 'compute_all'):
    pass  # already imported above

# Ensure compute_all accepts include_leading kwarg
_original_compute_all = _ind.compute_all
def _patched_compute_all(df, include_leading=False):
    return _original_compute_all(df)
_ind.compute_all = _patched_compute_all

from .backtest_engine_v3 import (
    SpotBacktestEngineV3,
    BacktestResult,
    ExitModeParams,
    BLOCKED_REGIMES,
)

logger = logging.getLogger(__name__)

# ── Dwell-time profiles ───────────────────────────────────────────────────

@dataclass
class DwellProfile:
    name: str
    floor: float           # minimum dwell_decay multiplier
    threshold: int         # candles before tightening begins
    decay_rate: float      # per-candle decay once threshold is reached
    cooldown: int = 24     # candles to wait after snap-back before re-counting

DWELL_PROFILES: Dict[str, DwellProfile] = {
    "none":         DwellProfile("none",         1.00, 999999, 0.0,   0),
    "conservative": DwellProfile("conservative", 0.60, 96,     0.003, 24),
    "moderate":     DwellProfile("moderate",     0.50, 48,     0.005, 24),
    "aggressive":   DwellProfile("aggressive",   0.40, 24,     0.008, 24),
}

# Regimes that trigger HARD snap-back (full reset)
HARD_SNAPBACK_REGIMES = {"BREAKOUT_WARNING", "EXTREME"}
# Regimes that trigger SOFT snap-back (halve the count instead of zeroing)
SOFT_SNAPBACK_REGIMES = {"TRENDING"}


class SpotBacktestEngineV4(SpotBacktestEngineV3):
    """V3 engine extended with dwell-time compression."""

    def __init__(self, dwell_profile: str = "none", **kwargs):
        super().__init__(**kwargs)
        self.dwell = DWELL_PROFILES[dwell_profile]
        self._dwell_candle_count: int = 0
        self._dwell_decay: float = 1.0
        self._dwell_cooldown_remaining: int = 0

        # Per-candle timeline for analysis
        self._candle_timeline: List[dict] = []

    def _calculate_dwell_decay(self) -> float:
        if self.dwell.name == "none":
            return 1.0
        if self._dwell_cooldown_remaining > 0:
            return 1.0
        if self._dwell_candle_count <= self.dwell.threshold:
            return 1.0
        excess = self._dwell_candle_count - self.dwell.threshold
        return max(self.dwell.floor, 1.0 - excess * self.dwell.decay_rate)

    def _snap_back(self, hard: bool = True):
        """Reset dwell state on breakout signal.
        Hard: full reset (BREAKOUT_WARNING, EXTREME)
        Soft: halve the count (TRENDING) — allows gradual re-tightening
        """
        if hard:
            self._dwell_candle_count = 0
            self._dwell_decay = 1.0
            self._dwell_cooldown_remaining = self.dwell.cooldown
        else:
            self._dwell_candle_count = self._dwell_candle_count // 2
            self._dwell_cooldown_remaining = min(self.dwell.cooldown // 2, 12)

    def _adaptive_deviation_v4(self, regime: str, atr_pct: float,
                                current_tp: float) -> float:
        """Override deviation with dwell decay applied."""
        dev = self._adaptive_deviation(regime, atr_pct, current_tp)
        dev *= self._dwell_decay
        # Re-enforce min and TP floor
        p = self.profile
        dev = max(p.deviation_min * self.dwell.floor, dev)
        dev = max(dev, current_tp * 1.5)
        return min(p.deviation_max, round(dev, 3))

    def run(self, df: pd.DataFrame) -> BacktestResult:
        """Full simulation with dwell-time tracking."""
        if len(df) < 100:
            logger.warning("Not enough data (%d rows)", len(df))
            return BacktestResult()

        # Compute indicators
        df = compute_all_indicators(df)
        regimes = classify_regime_v2(df, self.timeframe)
        atr_pct_series = compute_atr_pct(df, 14)
        atr_abs_series = compute_atr(df, 14)
        sma50 = df["close"].rolling(50).mean()

        # BBW and rolling median for dwell detection
        bbw = df["bbw"] if "bbw" in df.columns else bollinger_band_width(df["close"], 20)
        bbw_median = bbw.rolling(100, min_periods=20).median()

        # Volume for spike detection
        vol = df["volume"]
        vol_avg = volume_sma(df, 20)

        logger.info("Running V4 backtest (dwell=%s): %s %s, $%.0f, profile=%s",
                     self.dwell.name, self.symbol, self.timeframe,
                     self.initial_capital, self.profile.name)

        peak_equity = self.initial_capital

        for i in range(100, len(df)):
            row = df.iloc[i]
            ts = str(row["timestamp"])
            price = float(row["close"])
            high = float(row["high"])
            low = float(row["low"])

            regime = regimes.iloc[i] if i < len(regimes) else "UNKNOWN"
            self._current_regime = regime
            self._current_atr_pct = float(atr_pct_series.iloc[i]) if not pd.isna(atr_pct_series.iloc[i]) else 0.0
            self._current_atr_abs = float(atr_abs_series.iloc[i]) if not pd.isna(atr_abs_series.iloc[i]) else 0.0
            self._trend_bullish = price >= float(sma50.iloc[i]) if not pd.isna(sma50.iloc[i]) else True

            # ── Dwell-time logic ──────────────────────────────────────
            cur_bbw = float(bbw.iloc[i]) if not pd.isna(bbw.iloc[i]) else 0.0
            cur_bbw_med = float(bbw_median.iloc[i]) if not pd.isna(bbw_median.iloc[i]) else cur_bbw

            # Check snap-back triggers
            vol_val = float(vol.iloc[i]) if not pd.isna(vol.iloc[i]) else 0.0
            vol_avg_val = float(vol_avg.iloc[i]) if not pd.isna(vol_avg.iloc[i]) and vol_avg.iloc[i] > 0 else 1.0
            vol_spike = vol_val > vol_avg_val * 2.0

            if regime in HARD_SNAPBACK_REGIMES or vol_spike:
                self._snap_back(hard=True)
            elif regime in SOFT_SNAPBACK_REGIMES:
                self._snap_back(hard=False)
            else:
                # Cooldown tick
                if self._dwell_cooldown_remaining > 0:
                    self._dwell_cooldown_remaining -= 1
                # Dwell counting — gradual decay instead of hard reset when BBW crosses above
                if self._dwell_cooldown_remaining <= 0:
                    if cur_bbw < cur_bbw_med:
                        self._dwell_candle_count += 1
                    else:
                        # Gradual decay: reduce by 1 instead of zeroing out
                        self._dwell_candle_count = max(0, self._dwell_candle_count - 1)

            self._dwell_decay = self._calculate_dwell_decay()

            # ── Standard engine logic (from V3.run) ───────────────────
            exit_mode = self._get_exit_mode(regime)
            self._mode_candle_counts[exit_mode.name] = self._mode_candle_counts.get(exit_mode.name, 0) + 1

            tp_pct = self._adaptive_tp(regime, self._current_atr_pct)
            dev_pct = self._adaptive_deviation_v4(regime, self._current_atr_pct, tp_pct)

            # Conviction mode support
            if self.conviction_mode:
                try:
                    from ..indicators import regime_transition_signals
                    regime_trans = regime_transition_signals(df, regimes)
                    conviction = self._compute_conviction(df, i, price, regime, regime_trans)
                    tp_pct, dev_pct = self._apply_conviction_to_params(tp_pct, dev_pct, conviction)
                except (ImportError, AttributeError):
                    pass

            if self._halted:
                self._check_exits(high, low, price, ts, regime, exit_mode)
            else:
                self._check_safety_order_fills(low, price, ts, regime, dev_pct, tp_pct)
                self._check_exits(high, low, price, ts, regime, exit_mode)
                if not self.deals and regime not in BLOCKED_REGIMES:
                    self._open_deal(price, ts, regime, tp_pct)

            equity = self._equity(price)
            self.equity_snapshots.append({
                "timestamp": ts, "equity": equity, "cash": self.cash, "price": price
            })

            deployed = sum(d.capital_deployed for d in self.deals)
            self._utilization_samples.append(
                deployed / self.initial_capital * 100 if self.initial_capital > 0 else 0
            )

            if equity > peak_equity:
                peak_equity = equity
            dd = (peak_equity - equity) / peak_equity * 100
            if dd >= self.profile.max_drawdown_pct and not self._halted:
                logger.warning("Drawdown halt: %.1f%% >= %.1f%%", dd, self.profile.max_drawdown_pct)
                self._halted = True

            # Conviction score for timeline
            conv_score = self._last_conviction.score if self._last_conviction else 0.0

            # Layers filled
            layers_filled = sum(len(d.lots) for d in self.deals)

            # Record per-candle timeline
            self._candle_timeline.append({
                "timestamp": ts,
                "price": round(price, 4),
                "regime": regime,
                "bbw": round(cur_bbw, 4),
                "bbw_median": round(cur_bbw_med, 4),
                "dwell_count": self._dwell_candle_count,
                "dwell_decay": round(self._dwell_decay, 4),
                "effective_dev": round(dev_pct, 4),
                "conviction": round(conv_score, 1),
                "layers_filled": layers_filled,
            })

            if i % 500 == 0:
                logger.info("  [%d/%d] eq=$%.0f dwell=%d decay=%.3f dev=%.2f%% deals=%d",
                            i, len(df), equity, self._dwell_candle_count,
                            self._dwell_decay, dev_pct, len(self.deals))

        # Force-close remaining
        last_price = float(df.iloc[-1]["close"])
        last_ts = str(df.iloc[-1]["timestamp"])
        for deal in list(self.deals):
            self._force_close_deal(deal, last_price, last_ts)

        result = self._compile_results(df)
        result.variant = f"dwell_{self.dwell.name}"
        return result

    def get_candle_timeline(self) -> pd.DataFrame:
        """Return per-candle timeline as DataFrame."""
        return pd.DataFrame(self._candle_timeline)
