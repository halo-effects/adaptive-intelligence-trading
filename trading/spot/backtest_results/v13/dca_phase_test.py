"""DCA Dual-Track Parameter Matrix Test — Isolated to V13 DCA Phases Only.

1. Run V13 phase engine on daily candles to identify DCA windows + exit direction
2. Run dual-track (long + short) adaptive DCA within each window on 15m candles
3. Sweep DCA parameters (TP, deviation, SO mult, max layers)
4. Directional exits at phase boundaries:
   - DCA → MARKUP: force-close shorts, longs gracefully exit (ride TPs)
   - DCA → MARKDOWN: force-close longs, shorts gracefully exit (ride TPs)
   - Other exits: force-close both
5. Report per-coin, per-param combo results

This measures: "How much money does dual-track DCA grinding make during ranging periods?"
"""
import sqlite3
import sys
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum

sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack

DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'candles.db'


# ── DCA Engine (V12f-style with scale-out exits, supports long+short) ─

REGIME_TP_MULT = {
    'ACCUMULATION': 0.85, 'CHOPPY': 0.90, 'RANGING': 0.85,
    'DISTRIBUTION': 0.90, 'MILD_TREND': 1.05, 'TRENDING': 1.20,
    'EXTREME': 0.70, 'BREAKOUT_WARNING': 0.80, 'UNKNOWN': 1.0,
}
REGIME_DEV_MULT = {
    'ACCUMULATION': 0.85, 'CHOPPY': 0.90, 'RANGING': 0.80,
    'DISTRIBUTION': 0.90, 'MILD_TREND': 1.10, 'TRENDING': 1.30,
    'EXTREME': 1.50, 'BREAKOUT_WARNING': 1.20, 'UNKNOWN': 1.0,
}


class Direction(Enum):
    LONG = 'long'
    SHORT = 'short'


@dataclass
class DCAParams:
    """DCA parameter set to test."""
    name: str
    base_order_pct: float = 0.05       # % of capital for base order
    tp_baseline: float = 0.015         # 1.5% baseline TP
    tp_min: float = 0.006
    tp_max: float = 0.025
    deviation_baseline: float = 0.025  # 2.5% baseline deviation
    deviation_min: float = 0.012
    deviation_max: float = 0.040
    so_multiplier: float = 2.0         # SO size multiplier per layer
    max_layers: int = 8
    atr_baseline_pct: float = 0.008    # 0.8% ATR baseline
    adaptive: bool = True              # Use ATR/regime adaptation
    maker_fee: float = 0.0             # Aster-like maker free
    taker_fee: float = 0.0004          # 0.04% taker
    dual_track: bool = True            # Run both long + short simultaneously
    long_alloc: float = 0.50           # % of capital for long side
    short_alloc: float = 0.50          # % of capital for short side


@dataclass
class Lot:
    """A single buy/sell lot."""
    layer: int
    price: float
    qty: float
    cost: float
    timestamp: str
    direction: str = 'long'  # 'long' or 'short'
    closed: bool = False
    close_price: float = 0.0
    close_ts: str = ''
    pnl: float = 0.0


@dataclass
class Deal:
    """One DCA deal: base order + safety orders, closed individually (scale-out)."""
    direction: str = 'long'
    lots: List[Lot] = field(default_factory=list)

    @property
    def is_open(self):
        return any(not lot.closed for lot in self.lots)

    @property
    def open_lots(self):
        return [lot for lot in self.lots if not lot.closed]

    @property
    def avg_entry(self):
        ol = self.open_lots
        if not ol:
            return 0
        total_cost = sum(l.cost for l in ol)
        total_qty = sum(l.qty for l in ol)
        return total_cost / total_qty if total_qty > 0 else 0

    @property
    def total_invested(self):
        return sum(l.cost for l in self.open_lots)

    @property
    def total_pnl(self):
        return sum(l.pnl for l in self.lots if l.closed)


class DCATrack:
    """Single-direction DCA track (long or short)."""

    def __init__(self, direction: Direction, params: DCAParams, capital: float):
        self.dir = direction
        self.p = params
        self.initial_capital = capital
        self.cash = capital
        self.deals: List[Deal] = []
        self.completed_deals: List[Deal] = []
        self.trade_log: List[dict] = []
        self._current_atr_pct = 0.008
        self._current_regime = 'UNKNOWN'

    def _adaptive_tp(self):
        if not self.p.adaptive:
            return self.p.tp_baseline
        atr_ratio = self._current_atr_pct / self.p.atr_baseline_pct if self.p.atr_baseline_pct > 0 else 1.0
        tp = self.p.tp_baseline * atr_ratio
        tp *= REGIME_TP_MULT.get(self._current_regime, 1.0)
        return max(self.p.tp_min, min(self.p.tp_max, tp))

    def _adaptive_deviation(self, current_tp):
        if not self.p.adaptive:
            return self.p.deviation_baseline
        atr_ratio = self._current_atr_pct / self.p.atr_baseline_pct if self.p.atr_baseline_pct > 0 else 1.0
        dev = self.p.deviation_baseline * atr_ratio
        dev *= REGIME_DEV_MULT.get(self._current_regime, 1.0)
        dev = max(self.p.deviation_min, min(self.p.deviation_max, dev))
        dev = max(dev, current_tp * 1.5)
        return min(self.p.deviation_max, dev)

    def update_regime(self, regime: str, atr_pct: float):
        self._current_regime = regime
        if atr_pct > 0:
            self._current_atr_pct = atr_pct

    def tick(self, price: float, high: float, low: float, ts: str):
        """Process one candle. Returns list of trade events."""
        events = []
        is_long = self.dir == Direction.LONG

        tp_pct = self._adaptive_tp()
        dev_pct = self._adaptive_deviation(tp_pct)

        # Check TPs on open deals (scale-out: close lots individually, largest first)
        for deal in self.deals[:]:
            # Sort unsold lots by layer descending (sell largest/deepest first = V12f scale-out)
            for lot in sorted(deal.open_lots, key=lambda l: l.layer, reverse=True):
                if is_long:
                    lot_tp_price = lot.price * (1 + tp_pct)
                    hit = high >= lot_tp_price
                else:
                    lot_tp_price = lot.price * (1 - tp_pct)
                    hit = low <= lot_tp_price

                if hit:
                    close_price = lot_tp_price
                    if is_long:
                        pnl = (close_price - lot.price) * lot.qty
                    else:
                        pnl = (lot.price - close_price) * lot.qty
                    fee = close_price * lot.qty * self.p.maker_fee
                    pnl -= fee
                    lot.closed = True
                    lot.close_price = close_price
                    lot.close_ts = ts
                    lot.pnl = pnl
                    self.cash += lot.cost + pnl  # Return capital + profit
                    events.append({
                        'type': f'TP_{self.dir.value.upper()}',
                        'layer': lot.layer, 'price': close_price,
                        'pnl': pnl, 'ts': ts
                    })

            if not deal.is_open:
                self.completed_deals.append(deal)
                self.deals.remove(deal)

        # Check safety order fills
        for deal in self.deals:
            n_lots = len(deal.lots)
            if n_lots >= self.p.max_layers:
                continue

            if is_long:
                so_price = deal.lots[0].price * (1 - dev_pct * n_lots)
                hit = low <= so_price
            else:
                so_price = deal.lots[0].price * (1 + dev_pct * n_lots)
                hit = high >= so_price

            if hit:
                base_cost = deal.lots[0].cost
                so_cost = base_cost * (self.p.so_multiplier ** min(n_lots, 4))
                so_cost = min(so_cost, self.cash * 0.30)

                if so_cost < 5 or self.cash < so_cost:
                    continue

                fee = so_cost * self.p.taker_fee
                qty = (so_cost - fee) / so_price
                lot = Lot(
                    layer=n_lots, price=so_price, qty=qty,
                    cost=so_cost, timestamp=ts, direction=self.dir.value
                )
                deal.lots.append(lot)
                self.cash -= so_cost
                events.append({
                    'type': f'SO_{self.dir.value.upper()}',
                    'layer': n_lots, 'price': so_price,
                    'cost': so_cost, 'ts': ts
                })

        # Open new deal if no open deals
        if not self.deals:
            available = self.cash * 0.90  # 10% reserve
            base_cost = available * self.p.base_order_pct
            if base_cost >= 5 and self.cash >= base_cost:
                fee = base_cost * self.p.taker_fee
                qty = (base_cost - fee) / price
                lot = Lot(
                    layer=0, price=price, qty=qty, cost=base_cost,
                    timestamp=ts, direction=self.dir.value
                )
                deal = Deal(direction=self.dir.value, lots=[lot])
                self.deals.append(deal)
                self.cash -= base_cost
                events.append({
                    'type': f'OPEN_{self.dir.value.upper()}',
                    'layer': 0, 'price': price,
                    'cost': base_cost, 'ts': ts
                })

        return events

    def force_close_all(self, price: float, ts: str) -> float:
        """Force close all open positions at market price."""
        total_pnl = 0
        is_long = self.dir == Direction.LONG
        for deal in self.deals:
            for lot in deal.open_lots:
                if is_long:
                    pnl = (price - lot.price) * lot.qty
                else:
                    pnl = (lot.price - price) * lot.qty
                fee = price * lot.qty * self.p.taker_fee
                pnl -= fee
                lot.closed = True
                lot.close_price = price
                lot.close_ts = ts
                lot.pnl = pnl
                self.cash += lot.cost + pnl
                total_pnl += pnl
            self.completed_deals.append(deal)
        self.deals.clear()
        return total_pnl

    @property
    def has_open_positions(self):
        return len(self.deals) > 0

    @property
    def equity(self):
        # Cash + unrealized (can't compute without current price, use cash as proxy)
        return self.cash

    @property
    def total_completed_lots(self):
        return sum(len([l for l in d.lots if l.closed]) for d in self.completed_deals)

    @property
    def total_pnl(self):
        return sum(d.total_pnl for d in self.completed_deals)

    @property
    def win_rate(self):
        wins = sum(1 for d in self.completed_deals for l in d.lots if l.closed and l.pnl > 0)
        total = sum(1 for d in self.completed_deals for l in d.lots if l.closed)
        return wins / total * 100 if total > 0 else 0


class DualTrackDCA:
    """Dual-track DCA engine: long + short simultaneously, with directional exits."""

    def __init__(self, params: DCAParams, capital: float):
        self.p = params
        self.initial_capital = capital

        if params.dual_track:
            long_cap = capital * params.long_alloc
            short_cap = capital * params.short_alloc
        else:
            long_cap = capital
            short_cap = 0

        self.long_track = DCATrack(Direction.LONG, params, long_cap)
        self.short_track = DCATrack(Direction.SHORT, params, short_cap) if params.dual_track else None

    def update_regime(self, regime: str, atr_pct: float):
        self.long_track.update_regime(regime, atr_pct)
        if self.short_track:
            self.short_track.update_regime(regime, atr_pct)

    def tick(self, price: float, high: float, low: float, ts: str):
        events = self.long_track.tick(price, high, low, ts)
        if self.short_track:
            events += self.short_track.tick(price, high, low, ts)
        return events

    def directional_exit(self, exit_to: str, price: float, ts: str) -> dict:
        """
        Phase-boundary exit with directional logic:
        - MARKUP: force-close shorts, longs ride (graceful)
        - MARKDOWN: force-close longs, shorts ride (graceful)
        - other: force-close both
        
        Returns dict with force_close_pnl and graceful status.
        """
        result = {
            'exit_to': exit_to,
            'long_force_pnl': 0.0, 'short_force_pnl': 0.0,
            'long_graceful': False, 'short_graceful': False,
            'long_open_lots': 0, 'short_open_lots': 0,
        }

        if exit_to == 'MARKUP':
            # Force-close shorts, longs ride
            if self.short_track and self.short_track.has_open_positions:
                result['short_force_pnl'] = self.short_track.force_close_all(price, ts)
            if self.long_track.has_open_positions:
                result['long_graceful'] = True
                result['long_open_lots'] = sum(len(d.open_lots) for d in self.long_track.deals)
        elif exit_to == 'MARKDOWN':
            # Force-close longs, shorts ride
            if self.long_track.has_open_positions:
                result['long_force_pnl'] = self.long_track.force_close_all(price, ts)
            if self.short_track and self.short_track.has_open_positions:
                result['short_graceful'] = True
                result['short_open_lots'] = sum(len(d.open_lots) for d in self.short_track.deals)
        else:
            # FLAT or unknown — force-close both
            if self.long_track.has_open_positions:
                result['long_force_pnl'] = self.long_track.force_close_all(price, ts)
            if self.short_track and self.short_track.has_open_positions:
                result['short_force_pnl'] = self.short_track.force_close_all(price, ts)

        return result

    def graceful_runoff(self, price: float, high: float, low: float, ts: str) -> List[dict]:
        """
        After phase exit, continue ticking only the graceful track to let TPs hit.
        Returns events. Call until no more open positions on the graceful side.
        """
        events = []
        if self.long_track.has_open_positions:
            events += self.long_track.tick(price, high, low, ts)
        if self.short_track and self.short_track.has_open_positions:
            events += self.short_track.tick(price, high, low, ts)
        return events

    def force_close_all(self, price: float, ts: str) -> float:
        """Force close everything — final cleanup."""
        pnl = self.long_track.force_close_all(price, ts)
        if self.short_track:
            pnl += self.short_track.force_close_all(price, ts)
        return pnl

    @property
    def total_cash(self):
        c = self.long_track.cash
        if self.short_track:
            c += self.short_track.cash
        return c

    @property
    def total_pnl(self):
        p = self.long_track.total_pnl
        if self.short_track:
            p += self.short_track.total_pnl
        return p

    @property
    def total_completed_lots(self):
        n = self.long_track.total_completed_lots
        if self.short_track:
            n += self.short_track.total_completed_lots
        return n

    @property
    def long_completed(self):
        return self.long_track.total_completed_lots

    @property
    def short_completed(self):
        return self.short_track.total_completed_lots if self.short_track else 0

    @property
    def long_pnl(self):
        return self.long_track.total_pnl

    @property
    def short_pnl(self):
        return self.short_track.total_pnl if self.short_track else 0

    @property
    def long_winrate(self):
        return self.long_track.win_rate

    @property
    def short_winrate(self):
        return self.short_track.win_rate if self.short_track else 0


# ── Phase Window Extraction ───────────────────────────────────────────

def get_dca_windows(coin: str, profile: str = 'high') -> List[dict]:
    """
    Run V13 phase engine and extract DCA phase windows with exit direction.
    Returns list of {start, end, exit_to} dicts.
    """
    pack = V13SignalPack(coin)

    from run_new_coins_profiles import make_config
    cfg = make_config(profile)
    bt = V13BacktestV8(pack, cfg)
    bt.run()

    windows = []
    dca_start = None

    for t in bt.phase_log:
        to_phase = str(t.get('to', ''))
        date = t.get('date')
        if not date:
            continue

        if to_phase == 'DCA' and dca_start is None:
            dca_start = str(date)[:10]
        elif to_phase != 'DCA' and dca_start is not None:
            dca_end = str(date)[:10]
            windows.append({
                'start': dca_start,
                'end': dca_end,
                'exit_to': to_phase,  # MARKUP, MARKDOWN, or FLAT
            })
            dca_start = None

    # If still in DCA at end, close window (force-close both)
    if dca_start is not None:
        windows.append({
            'start': dca_start,
            'end': '2026-02-27',
            'exit_to': 'END',
        })

    return windows


# ── Candle Loading ────────────────────────────────────────────────────

def load_candles(coin: str, timeframe: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Load candles from DB for a specific window."""
    conn = sqlite3.connect(DB_PATH)

    start_ms = int(datetime.strptime(start_date, '%Y-%m-%d').replace(
        tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.strptime(end_date, '%Y-%m-%d').replace(
        tzinfo=timezone.utc).timestamp() * 1000)

    for sym in [coin, coin.replace('/USDC', '/USDT')]:
        df = pd.read_sql_query(
            """SELECT timestamp, open, high, low, close, volume
               FROM candles
               WHERE symbol=? AND timeframe=? AND timestamp>=? AND timestamp<=?
               ORDER BY timestamp""",
            conn, params=(sym, timeframe, start_ms, end_ms)
        )
        if not df.empty:
            conn.close()
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            return df

    conn.close()
    return pd.DataFrame()


def compute_regime_and_atr(df: pd.DataFrame, lookback: int = 14) -> pd.DataFrame:
    """Compute ATR% and simple regime classification on candle data."""
    df = df.copy()

    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift(1)).abs(),
        (df['low'] - df['close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    df['atr'] = tr.rolling(lookback).mean()
    df['atr_pct'] = df['atr'] / df['close']

    # Regime via ATR percentile (7 days of 15m = 672 candles)
    roll_window = 96 * 7  # 15m candles per day × 7 days
    df['atr_pctile'] = df['atr_pct'].rolling(roll_window, min_periods=96).rank(pct=True)
    df['regime'] = 'RANGING'
    df.loc[df['atr_pctile'] > 0.8, 'regime'] = 'TRENDING'
    df.loc[df['atr_pctile'] > 0.95, 'regime'] = 'EXTREME'
    df.loc[df['atr_pctile'] < 0.3, 'regime'] = 'ACCUMULATION'

    return df


# ── Graceful Runoff Helper ────────────────────────────────────────────

GRACEFUL_RUNOFF_MAX_CANDLES = 96 * 7  # 7 days max runoff at 15m

def run_graceful_runoff(engine: DualTrackDCA, coin: str, timeframe: str,
                        start_date: str, max_candles: int = GRACEFUL_RUNOFF_MAX_CANDLES) -> dict:
    """
    After phase exit, keep ticking the graceful side to let TPs hit.
    Loads candles from start_date forward. Force-closes anything left after max_candles.
    """
    # Load a chunk of candles after the window end
    from datetime import timedelta
    end_dt = datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=14)
    df = load_candles(coin, timeframe, start_date, end_dt.strftime('%Y-%m-%d'))
    if df.empty:
        return {'runoff_candles': 0, 'runoff_events': 0, 'force_closed': True}

    df = compute_regime_and_atr(df)
    events_count = 0

    for i, (_, row) in enumerate(df.iterrows()):
        if i >= max_candles:
            break
        if pd.notna(row.get('atr_pct')):
            engine.update_regime(row['regime'], row['atr_pct'])
        evts = engine.graceful_runoff(row['close'], row['high'], row['low'], str(row['date']))
        events_count += len(evts)

        # Check if all graceful positions closed
        long_open = engine.long_track.has_open_positions
        short_open = engine.short_track.has_open_positions if engine.short_track else False
        if not long_open and not short_open:
            return {'runoff_candles': i + 1, 'runoff_events': events_count, 'force_closed': False}

    # Still open after max runoff — force close remainder
    last_price = df.iloc[min(len(df)-1, max_candles-1)]['close']
    engine.force_close_all(last_price, str(df.iloc[min(len(df)-1, max_candles-1)]['date']))
    return {'runoff_candles': min(len(df), max_candles), 'runoff_events': events_count, 'force_closed': True}


# ── Parameter Matrix ──────────────────────────────────────────────────

def build_param_matrix() -> List[DCAParams]:
    params = []

    # V13 current (baseline - fixed, long only)
    params.append(DCAParams(
        name='V13_baseline_long',
        base_order_pct=0.05, tp_baseline=0.015, deviation_baseline=0.025,
        so_multiplier=2.0, max_layers=8, adaptive=False,
        dual_track=False
    ))

    # V12f adaptive long-only (matches V12e paper bot params)
    params.append(DCAParams(
        name='V12f_long_only',
        base_order_pct=0.04, tp_baseline=0.015, tp_min=0.010, tp_max=0.020,
        deviation_baseline=0.025, deviation_min=0.020, deviation_max=0.030,
        so_multiplier=2.0, max_layers=8, adaptive=True,
        dual_track=False
    ))

    # Dual-track adaptive medium
    params.append(DCAParams(
        name='dual_adaptive_med',
        base_order_pct=0.04, tp_baseline=0.015, tp_min=0.010, tp_max=0.020,
        deviation_baseline=0.025, deviation_min=0.020, deviation_max=0.030,
        so_multiplier=2.0, max_layers=8, adaptive=True,
        dual_track=True, long_alloc=0.50, short_alloc=0.50
    ))

    # Dual-track aggressive (tighter TP, more layers)
    params.append(DCAParams(
        name='dual_aggressive',
        base_order_pct=0.06, tp_baseline=0.012, tp_min=0.008, tp_max=0.020,
        deviation_baseline=0.020, deviation_min=0.015, deviation_max=0.030,
        so_multiplier=2.0, max_layers=10, adaptive=True,
        dual_track=True, long_alloc=0.50, short_alloc=0.50
    ))

    # Dual-track tight grid
    params.append(DCAParams(
        name='dual_tight_grid',
        base_order_pct=0.05, tp_baseline=0.010, tp_min=0.006, tp_max=0.015,
        deviation_baseline=0.015, deviation_min=0.012, deviation_max=0.025,
        so_multiplier=1.5, max_layers=6, adaptive=True,
        dual_track=True, long_alloc=0.50, short_alloc=0.50
    ))

    # Dual-track wide grid
    params.append(DCAParams(
        name='dual_wide_grid',
        base_order_pct=0.05, tp_baseline=0.020, tp_min=0.012, tp_max=0.025,
        deviation_baseline=0.030, deviation_min=0.020, deviation_max=0.040,
        so_multiplier=2.0, max_layers=8, adaptive=True,
        dual_track=True, long_alloc=0.50, short_alloc=0.50
    ))

    # Dual-track scalper
    params.append(DCAParams(
        name='dual_scalper',
        base_order_pct=0.04, tp_baseline=0.008, tp_min=0.005, tp_max=0.012,
        deviation_baseline=0.012, deviation_min=0.010, deviation_max=0.020,
        so_multiplier=1.5, max_layers=5, adaptive=True,
        dual_track=True, long_alloc=0.50, short_alloc=0.50
    ))

    # Dual-track conservative
    params.append(DCAParams(
        name='dual_conservative',
        base_order_pct=0.03, tp_baseline=0.020, tp_min=0.015, tp_max=0.025,
        deviation_baseline=0.035, deviation_min=0.025, deviation_max=0.040,
        so_multiplier=2.0, max_layers=6, adaptive=True,
        dual_track=True, long_alloc=0.50, short_alloc=0.50
    ))

    # Dual-track high frequency
    params.append(DCAParams(
        name='dual_high_freq',
        base_order_pct=0.03, tp_baseline=0.010, tp_min=0.006, tp_max=0.015,
        deviation_baseline=0.020, deviation_min=0.015, deviation_max=0.030,
        so_multiplier=1.5, max_layers=12, adaptive=True,
        dual_track=True, long_alloc=0.50, short_alloc=0.50
    ))

    return params


# ── Main Test Runner ──────────────────────────────────────────────────

def run_dca_test(coin: str, timeframe: str, params: DCAParams,
                 windows: List[dict], capital: float = 2500) -> dict:
    """Run DCA test for one coin + param combo across all DCA windows."""
    engine = DualTrackDCA(params, capital)
    total_candles = 0
    window_results = []

    for w in windows:
        w_start, w_end, exit_to = w['start'], w['end'], w['exit_to']
        df = load_candles(coin, timeframe, w_start, w_end)
        if df.empty:
            continue

        df = compute_regime_and_atr(df)

        window_start_cash = engine.total_cash

        for _, row in df.iterrows():
            if pd.isna(row.get('atr_pct')):
                continue
            engine.update_regime(row['regime'], row['atr_pct'])
            engine.tick(row['close'], row['high'], row['low'], str(row['date']))
            total_candles += 1

        # Directional exit at window boundary
        if df.shape[0] > 0:
            last_price = df.iloc[-1]['close']
            last_ts = str(df.iloc[-1]['date'])
            exit_result = engine.directional_exit(exit_to, last_price, last_ts)

            # Run graceful runoff for surviving track
            runoff = {'runoff_candles': 0, 'runoff_events': 0, 'force_closed': False}
            if exit_result['long_graceful'] or exit_result['short_graceful']:
                runoff = run_graceful_runoff(engine, coin, timeframe, w_end)
        else:
            exit_result = {'exit_to': exit_to, 'long_force_pnl': 0, 'short_force_pnl': 0,
                           'long_graceful': False, 'short_graceful': False,
                           'long_open_lots': 0, 'short_open_lots': 0}
            runoff = {'runoff_candles': 0, 'runoff_events': 0, 'force_closed': False}

        window_pnl = engine.total_cash - window_start_cash
        window_results.append({
            'start': w_start, 'end': w_end, 'exit_to': exit_to,
            'candles': len(df), 'pnl': window_pnl,
            'exit': exit_result,
            'runoff': runoff,
        })

    roi = (engine.total_cash - engine.initial_capital) / engine.initial_capital * 100

    return {
        'coin': coin,
        'timeframe': timeframe,
        'params': params.name,
        'dual_track': params.dual_track,
        'capital': capital,
        'final_cash': engine.total_cash,
        'roi': roi,
        'long_lots': engine.long_completed,
        'short_lots': engine.short_completed,
        'long_pnl': engine.long_pnl,
        'short_pnl': engine.short_pnl,
        'long_wr': engine.long_winrate,
        'short_wr': engine.short_winrate,
        'total_lots': engine.total_completed_lots,
        'total_pnl': engine.total_pnl,
        'candles_processed': total_candles,
        'windows': len(windows),
        'window_results': window_results,
    }


def main():
    COINS = ['ETH/USDC', 'BTC/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
    CAPITAL = 2500
    TF = '15m'

    print("=" * 100)
    print("DCA DUAL-TRACK PARAMETER MATRIX TEST")
    print("Isolated to V13 DCA phases. V12f-style adaptive engine. Directional exits.")
    print(f"Capital: ${CAPITAL}/coin | Timeframe: {TF} | Period: Jan 2023 – Feb 2026")
    print("=" * 100)

    # Extract DCA windows with exit direction
    print("\n── V13 Phase Windows ──")
    all_windows = {}
    for coin in COINS:
        try:
            windows = get_dca_windows(coin, 'high')
            # Filter to windows with 15m data coverage (Mar 2023+)
            windows = [w for w in windows if w['end'] >= '2023-03-12']
            all_windows[coin] = windows
            total_days = sum(
                max(0, (datetime.strptime(w['end'], '%Y-%m-%d') -
                         datetime.strptime(max(w['start'], '2023-03-12'), '%Y-%m-%d')).days)
                for w in windows
            )
            exits = {}
            for w in windows:
                exits[w['exit_to']] = exits.get(w['exit_to'], 0) + 1
            exit_str = ', '.join(f"{k}:{v}" for k, v in sorted(exits.items()))
            print(f"  {coin:12} {len(windows)} windows, ~{total_days:>4}d in DCA  exits: {exit_str}")
        except Exception as e:
            print(f"  {coin:12} FAILED — {e}")

    # Check data coverage
    print("\n── 15m Data Coverage ──")
    conn = sqlite3.connect(DB_PATH)
    for coin in COINS:
        for sym in [coin, coin.replace('/USDC', '/USDT')]:
            r = conn.execute(
                "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol=? AND timeframe='15m'",
                (sym,)
            ).fetchone()
            if r[0] > 0:
                from datetime import datetime as dt
                mn = dt.utcfromtimestamp(r[1]/1000).strftime('%Y-%m-%d')
                mx = dt.utcfromtimestamp(r[2]/1000).strftime('%Y-%m-%d')
                print(f"  {sym:15} {r[0]:>8} candles  {mn}..{mx}")
                break
    conn.close()

    # Run tests
    param_matrix = build_param_matrix()
    results = []

    for coin in COINS:
        if coin not in all_windows or not all_windows[coin]:
            print(f"\n  {coin}: No DCA windows, skipping")
            continue

        windows = all_windows[coin]
        print(f"\n{'─' * 100}")
        print(f"  {coin} ({TF}) — {len(windows)} DCA windows")
        print(f"  {'Params':<25} {'Track':>6} {'ROI':>8} {'Lots':>6} {'L/S':>10} {'WR%':>6} "
              f"{'L_PnL':>9} {'S_PnL':>9} {'Total':>9}")
        print(f"  {'─'*25} {'─'*6} {'─'*8} {'─'*6} {'─'*10} {'─'*6} {'─'*9} {'─'*9} {'─'*9}")

        for params in param_matrix:
            r = run_dca_test(coin, TF, params, windows, CAPITAL)
            results.append(r)
            track = 'DUAL' if params.dual_track else 'LONG'
            ls = f"{r['long_lots']}/{r['short_lots']}" if params.dual_track else f"{r['long_lots']}/-"
            wr = (r['long_wr'] + r['short_wr']) / 2 if params.dual_track and r['short_lots'] > 0 else r['long_wr']
            print(f"  {params.name:<25} {track:>6} {r['roi']:>+7.1f}% {r['total_lots']:>6} "
                  f"{ls:>10} {wr:>5.1f}% ${r['long_pnl']:>+8.1f} ${r['short_pnl']:>+8.1f} "
                  f"${r['total_pnl']:>+8.1f}")

    # Cross-coin summary
    print(f"\n{'=' * 100}")
    print("CROSS-COIN SUMMARY")
    print(f"{'=' * 100}")

    param_names = [p.name for p in param_matrix]
    coin_labels = [c.split('/')[0] for c in COINS]

    print(f"\n  {'Params':<25}", end='')
    for cl in coin_labels:
        print(f" {cl:>8}", end='')
    print(f" {'AVG':>8} {'TOTAL$':>9}")
    print(f"  {'─'*25}", end='')
    for _ in coin_labels:
        print(f" {'─'*8}", end='')
    print(f" {'─'*8} {'─'*9}")

    for pname in param_names:
        print(f"  {pname:<25}", end='')
        rois = []
        total_pnl = 0
        for coin in COINS:
            matching = [r for r in results if r['coin'] == coin and r['params'] == pname]
            if matching:
                roi = matching[0]['roi']
                rois.append(roi)
                total_pnl += matching[0]['total_pnl']
                print(f" {roi:>+7.1f}%", end='')
            else:
                print(f" {'n/a':>8}", end='')
        avg = np.mean(rois) if rois else 0
        print(f" {avg:>+7.1f}% ${total_pnl:>+8.1f}")

    # Per-window detail for best performer
    if results:
        best = max(results, key=lambda r: r['roi'])
        print(f"\n── Best Single Result: {best['coin']} / {best['params']} ({best['roi']:+.1f}%) ──")
        for w in best['window_results']:
            exit_info = w['exit']
            graceful = 'L_grace' if exit_info.get('long_graceful') else (
                'S_grace' if exit_info.get('short_graceful') else 'force')
            runoff_info = ''
            if w['runoff']['runoff_candles'] > 0:
                hours = w['runoff']['runoff_candles'] * 15 / 60
                runoff_info = f" runoff={hours:.0f}h"
                if w['runoff']['force_closed']:
                    runoff_info += '(forced)'
            print(f"    {w['start']}..{w['end']} → {w['exit_to']:>10}  "
                  f"{w['candles']:>6} candles  pnl=${w['pnl']:>+8.1f}  "
                  f"exit={graceful}{runoff_info}")

    print(f"\n{'=' * 100}")
    print("Done.")


if __name__ == '__main__':
    main()
