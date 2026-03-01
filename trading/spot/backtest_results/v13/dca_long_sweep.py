"""DCA Long-Only Parameter Sweep — Optimize grinding during V13 DCA phases.

Sweeps TP, deviation, SO multiplier, max layers, and base order size
on 15m candles within V13-defined DCA (accumulation) windows. Long only.

Goal: find the optimal DCA config to maximize compounding during sideways periods.
"""
import sqlite3
import sys
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
from pathlib import Path
from datetime import datetime, timezone
from itertools import product as cartesian

sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack

DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'candles.db'

# ── Regime multipliers (from V12f) ───────────────────────────────────

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


@dataclass
class SweepParams:
    tp_pct: float           # TP target %
    dev_pct: float          # SO deviation %
    so_mult: float          # SO size multiplier
    max_layers: int         # Max safety orders
    base_pct: float         # Base order as % of available capital
    adaptive: bool          # Use ATR/regime adaptation
    atr_baseline: float = 0.008
    maker_fee: float = 0.0
    taker_fee: float = 0.0004

    @property
    def label(self):
        adapt = 'A' if self.adaptive else 'F'
        return f"TP{self.tp_pct*100:.1f}_D{self.dev_pct*100:.1f}_M{self.so_mult:.1f}_L{self.max_layers}_B{self.base_pct*100:.0f}_{adapt}"


@dataclass
class Lot:
    layer: int
    price: float
    qty: float
    cost: float
    ts: str
    closed: bool = False
    close_price: float = 0.0
    pnl: float = 0.0


class LongDCAEngine:
    """Optimized long-only DCA engine for sweep testing."""

    def __init__(self, p: SweepParams, capital: float):
        self.p = p
        self.initial_capital = capital
        self.cash = capital
        self.lots: List[Lot] = []  # Current open deal lots
        self.total_pnl = 0.0
        self.wins = 0
        self.losses = 0
        self.total_lots_closed = 0
        self.deals_completed = 0
        self._atr_pct = 0.008
        self._regime = 'UNKNOWN'
        self._peak_equity = capital
        self._max_dd = 0.0

    def _effective_tp(self):
        if not self.p.adaptive:
            return self.p.tp_pct
        ratio = self._atr_pct / self.p.atr_baseline if self.p.atr_baseline > 0 else 1.0
        tp = self.p.tp_pct * ratio * REGIME_TP_MULT.get(self._regime, 1.0)
        return max(self.p.tp_pct * 0.4, min(self.p.tp_pct * 1.7, tp))

    def _effective_dev(self, tp):
        if not self.p.adaptive:
            return self.p.dev_pct
        ratio = self._atr_pct / self.p.atr_baseline if self.p.atr_baseline > 0 else 1.0
        dev = self.p.dev_pct * ratio * REGIME_DEV_MULT.get(self._regime, 1.0)
        dev = max(self.p.dev_pct * 0.5, min(self.p.dev_pct * 1.6, dev))
        return max(dev, tp * 1.5)  # Floor: dev >= 1.5x TP

    def update_regime(self, regime: str, atr_pct: float):
        self._regime = regime
        if atr_pct > 0:
            self._atr_pct = atr_pct

    def tick(self, price: float, high: float, low: float, ts: str):
        tp = self._effective_tp()
        dev = self._effective_dev(tp)

        # Check TPs (sell largest/deepest lots first — scale-out)
        for lot in sorted(self.lots, key=lambda l: l.layer, reverse=True):
            if lot.closed:
                continue
            tp_price = lot.price * (1 + tp)
            if high >= tp_price:
                pnl = (tp_price - lot.price) * lot.qty
                fee = tp_price * lot.qty * self.p.maker_fee
                pnl -= fee
                lot.closed = True
                lot.close_price = tp_price
                lot.pnl = pnl
                self.cash += lot.cost + pnl
                self.total_pnl += pnl
                self.total_lots_closed += 1
                if pnl > 0:
                    self.wins += 1
                else:
                    self.losses += 1

        # Remove fully closed deals
        open_lots = [l for l in self.lots if not l.closed]
        if self.lots and not open_lots:
            self.deals_completed += 1
        self.lots = open_lots

        # Check safety orders
        if self.lots:
            n = len(self.lots)
            if n < self.p.max_layers:
                so_price = self.lots[0].price * (1 - dev * n)
                if low <= so_price:
                    base_cost = self.lots[0].cost
                    so_cost = base_cost * (self.p.so_mult ** min(n, 4))
                    so_cost = min(so_cost, self.cash * 0.30)
                    if so_cost >= 5 and self.cash >= so_cost:
                        fee = so_cost * self.p.taker_fee
                        qty = (so_cost - fee) / so_price
                        self.lots.append(Lot(layer=n, price=so_price, qty=qty, cost=so_cost, ts=ts))
                        self.cash -= so_cost

        # Open new deal if none open
        if not self.lots:
            available = self.cash * 0.90
            base_cost = available * self.p.base_pct
            if base_cost >= 5 and self.cash >= base_cost:
                fee = base_cost * self.p.taker_fee
                qty = (base_cost - fee) / price
                self.lots.append(Lot(layer=0, price=price, qty=qty, cost=base_cost, ts=ts))
                self.cash -= base_cost

        # Track drawdown
        eq = self.equity(price)
        if eq > self._peak_equity:
            self._peak_equity = eq
        dd = (self._peak_equity - eq) / self._peak_equity if self._peak_equity > 0 else 0
        if dd > self._max_dd:
            self._max_dd = dd

    def force_close(self, price: float, ts: str) -> float:
        pnl = 0
        for lot in self.lots:
            if not lot.closed:
                p = (price - lot.price) * lot.qty
                fee = price * lot.qty * self.p.taker_fee
                p -= fee
                lot.closed = True
                lot.pnl = p
                self.cash += lot.cost + p
                self.total_pnl += p
                self.total_lots_closed += 1
                pnl += p
                if p > 0:
                    self.wins += 1
                else:
                    self.losses += 1
        self.lots = []
        self.deals_completed += 1
        return pnl

    def equity(self, price: float) -> float:
        unrealized = sum((price - l.price) * l.qty for l in self.lots if not l.closed)
        return self.cash + sum(l.cost for l in self.lots if not l.closed) + unrealized

    @property
    def win_rate(self):
        total = self.wins + self.losses
        return self.wins / total * 100 if total > 0 else 0

    @property
    def roi(self):
        return (self.cash - self.initial_capital) / self.initial_capital * 100


# ── Phase Windows ─────────────────────────────────────────────────────

def get_dca_windows(coin: str, profile: str = 'high') -> List[dict]:
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
            windows.append({'start': dca_start, 'end': str(date)[:10], 'exit_to': to_phase})
            dca_start = None
    if dca_start:
        windows.append({'start': dca_start, 'end': '2026-02-27', 'exit_to': 'END'})
    return windows


# ── Candle Loading + Regime ───────────────────────────────────────────

def load_candles(coin: str, tf: str, start: str, end: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    start_ms = int(datetime.strptime(start, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.strptime(end, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp() * 1000)
    for sym in [coin, coin.replace('/USDC', '/USDT')]:
        df = pd.read_sql_query(
            "SELECT timestamp,open,high,low,close,volume FROM candles WHERE symbol=? AND timeframe=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp",
            conn, params=(sym, tf, start_ms, end_ms))
        if not df.empty:
            conn.close()
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            return df
    conn.close()
    return pd.DataFrame()


def add_regime(df: pd.DataFrame, lookback: int = 14) -> pd.DataFrame:
    df = df.copy()
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift(1)).abs(),
        (df['low'] - df['close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    df['atr'] = tr.rolling(lookback).mean()
    df['atr_pct'] = df['atr'] / df['close']
    roll = 96 * 7  # 7 days of 15m
    df['atr_rank'] = df['atr_pct'].rolling(roll, min_periods=96).rank(pct=True)
    df['regime'] = 'RANGING'
    df.loc[df['atr_rank'] > 0.8, 'regime'] = 'TRENDING'
    df.loc[df['atr_rank'] > 0.95, 'regime'] = 'EXTREME'
    df.loc[df['atr_rank'] < 0.3, 'regime'] = 'ACCUMULATION'
    return df


# ── Sweep Runner ──────────────────────────────────────────────────────

def run_single(coin: str, params: SweepParams, windows: List[dict],
               capital: float = 2500, tf: str = '15m') -> dict:
    engine = LongDCAEngine(params, capital)
    total_candles = 0

    for w in windows:
        df = load_candles(coin, tf, w['start'], w['end'])
        if df.empty:
            continue
        df = add_regime(df)
        for _, row in df.iterrows():
            if pd.notna(row.get('atr_pct')):
                engine.update_regime(row['regime'], row['atr_pct'])
            engine.tick(row['close'], row['high'], row['low'], str(row['date']))
            total_candles += 1
        # Force close at window end
        if len(df) > 0:
            engine.force_close(df.iloc[-1]['close'], str(df.iloc[-1]['date']))

    return {
        'coin': coin, 'params': params.label,
        'roi': engine.roi, 'pnl': engine.total_pnl,
        'lots': engine.total_lots_closed, 'deals': engine.deals_completed,
        'wr': engine.win_rate, 'max_dd': engine._max_dd * 100,
        'final': engine.cash, 'candles': total_candles,
    }


def main():
    COINS = ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']
    CAPITAL = 2500
    TF = '15m'

    print("=" * 110)
    print("DCA LONG-ONLY PARAMETER SWEEP")
    print(f"Capital: ${CAPITAL}/coin | Timeframe: {TF} | Coins: {', '.join(c.split('/')[0] for c in COINS)}")
    print("=" * 110)

    # Get DCA windows
    print("\nExtracting DCA windows...")
    all_windows = {}
    for coin in COINS:
        try:
            windows = get_dca_windows(coin, 'high')
            # Filter to 15m data availability (Mar 2023+)
            windows = [w for w in windows if w['end'] >= '2023-03-12']
            all_windows[coin] = windows
            total_days = sum(
                max(0, (datetime.strptime(w['end'], '%Y-%m-%d') -
                         datetime.strptime(max(w['start'], '2023-03-12'), '%Y-%m-%d')).days)
                for w in windows)
            print(f"  {coin}: {len(windows)} windows, ~{total_days}d")
        except Exception as e:
            print(f"  {coin}: FAILED - {e}")

    # Parameter sweep dimensions
    TP_VALUES =     [0.008, 0.010, 0.012, 0.015, 0.018, 0.020, 0.025]
    DEV_VALUES =    [0.012, 0.015, 0.020, 0.025, 0.030, 0.035]
    SO_MULTS =      [1.5, 2.0, 2.5]
    MAX_LAYERS =    [5, 8, 10, 12]
    BASE_PCTS =     [0.03, 0.05, 0.07, 0.10]
    ADAPTIVE =      [True, False]

    # Full cartesian is huge — do focused sweeps instead

    # Sweep 1: TP × Deviation (core grid) — fixed: SO=2.0, layers=8, base=5%, adaptive
    print("\n" + "=" * 110)
    print("SWEEP 1: TP vs Deviation (SO=2.0, layers=8, base=5%, adaptive)")
    print("=" * 110)

    sweep1_results = []
    for tp, dev in cartesian(TP_VALUES, DEV_VALUES):
        if dev < tp * 1.3:  # Dev must be meaningfully wider than TP
            continue
        p = SweepParams(tp_pct=tp, dev_pct=dev, so_mult=2.0, max_layers=8,
                        base_pct=0.05, adaptive=True)
        row_results = {}
        for coin in COINS:
            if coin not in all_windows:
                continue
            r = run_single(coin, p, all_windows[coin], CAPITAL, TF)
            row_results[coin] = r
        if row_results:
            avg_roi = np.mean([r['roi'] for r in row_results.values()])
            total_pnl = sum(r['pnl'] for r in row_results.values())
            avg_wr = np.mean([r['wr'] for r in row_results.values()])
            avg_lots = np.mean([r['lots'] for r in row_results.values()])
            max_dd = max(r['max_dd'] for r in row_results.values())
            sweep1_results.append({
                'tp': tp, 'dev': dev, 'avg_roi': avg_roi, 'total_pnl': total_pnl,
                'avg_wr': avg_wr, 'avg_lots': avg_lots, 'max_dd': max_dd,
                'per_coin': row_results
            })

    # Print sweep 1 as heatmap
    print(f"\n  {'TP \\ DEV':>12}", end='')
    for dev in DEV_VALUES:
        print(f" {dev*100:>6.1f}%", end='')
    print(f" {'|':>3}")
    print(f"  {'':>12}", end='')
    for _ in DEV_VALUES:
        print(f" {'------':>6}", end='')
    print()

    for tp in TP_VALUES:
        print(f"  {tp*100:>6.1f}%     ", end='')
        for dev in DEV_VALUES:
            match = [s for s in sweep1_results if s['tp'] == tp and s['dev'] == dev]
            if match:
                roi = match[0]['avg_roi']
                # Color coding via symbols
                if roi > 5:
                    marker = f"{roi:>+5.1f}%"
                elif roi > 0:
                    marker = f"{roi:>+5.1f}%"
                else:
                    marker = f"{roi:>+5.1f}%"
                print(f" {marker:>6}", end='')
            else:
                print(f" {'--':>6}", end='')
        print()

    # Top 10 from sweep 1
    sweep1_sorted = sorted(sweep1_results, key=lambda x: x['avg_roi'], reverse=True)
    print(f"\n  TOP 10 TP/DEV COMBOS:")
    print(f"  {'TP%':>6} {'DEV%':>6} {'AVG_ROI':>8} {'TOTAL$':>9} {'WR%':>6} {'LOTS':>6} {'MAX_DD':>7}  per-coin ROI")
    print(f"  {'---':>6} {'---':>6} {'-------':>8} {'------':>9} {'---':>6} {'----':>6} {'------':>7}  {'---'*20}")
    for s in sweep1_sorted[:10]:
        coins_str = '  '.join(f"{c.split('/')[0]}:{s['per_coin'][c]['roi']:+.1f}%" for c in COINS if c in s['per_coin'])
        print(f"  {s['tp']*100:>5.1f}% {s['dev']*100:>5.1f}% {s['avg_roi']:>+7.1f}% ${s['total_pnl']:>+8.1f} "
              f"{s['avg_wr']:>5.1f}% {s['avg_lots']:>5.0f}  {s['max_dd']:>6.1f}%  {coins_str}")

    # Use top TP/DEV for remaining sweeps
    if sweep1_sorted:
        best_tp = sweep1_sorted[0]['tp']
        best_dev = sweep1_sorted[0]['dev']
    else:
        best_tp, best_dev = 0.015, 0.025

    # Sweep 2: SO multiplier × Max layers
    print(f"\n{'=' * 110}")
    print(f"SWEEP 2: SO_mult x Max_layers (TP={best_tp*100:.1f}%, DEV={best_dev*100:.1f}%, base=5%, adaptive)")
    print(f"{'=' * 110}")

    print(f"\n  {'SO \\ Layers':>12}", end='')
    for ml in MAX_LAYERS:
        print(f" {'L='+str(ml):>8}", end='')
    print()

    sweep2_best = None
    for so in SO_MULTS:
        print(f"  {so:>6.1f}x      ", end='')
        for ml in MAX_LAYERS:
            p = SweepParams(tp_pct=best_tp, dev_pct=best_dev, so_mult=so,
                            max_layers=ml, base_pct=0.05, adaptive=True)
            rois = []
            for coin in COINS:
                if coin not in all_windows:
                    continue
                r = run_single(coin, p, all_windows[coin], CAPITAL, TF)
                rois.append(r['roi'])
            avg = np.mean(rois) if rois else 0
            print(f" {avg:>+7.1f}%", end='')
            if sweep2_best is None or avg > sweep2_best[2]:
                sweep2_best = (so, ml, avg)
        print()

    best_so = sweep2_best[0] if sweep2_best else 2.0
    best_ml = sweep2_best[1] if sweep2_best else 8

    # Sweep 3: Base order size
    print(f"\n{'=' * 110}")
    print(f"SWEEP 3: Base order % (TP={best_tp*100:.1f}%, DEV={best_dev*100:.1f}%, SO={best_so}x, L={best_ml})")
    print(f"{'=' * 110}\n")

    for bp in BASE_PCTS:
        p = SweepParams(tp_pct=best_tp, dev_pct=best_dev, so_mult=best_so,
                        max_layers=best_ml, base_pct=bp, adaptive=True)
        coin_results = {}
        for coin in COINS:
            if coin not in all_windows:
                continue
            r = run_single(coin, p, all_windows[coin], CAPITAL, TF)
            coin_results[coin] = r
        avg_roi = np.mean([r['roi'] for r in coin_results.values()])
        total_pnl = sum(r['pnl'] for r in coin_results.values())
        coins_str = '  '.join(f"{c.split('/')[0]}:{coin_results[c]['roi']:+.1f}%" for c in COINS if c in coin_results)
        print(f"  Base={bp*100:.0f}%  AVG={avg_roi:>+7.1f}%  Total=${total_pnl:>+8.1f}  {coins_str}")

    # Sweep 4: Adaptive vs Fixed
    print(f"\n{'=' * 110}")
    print(f"SWEEP 4: Adaptive vs Fixed (TP={best_tp*100:.1f}%, DEV={best_dev*100:.1f}%, SO={best_so}x, L={best_ml}, base=5%)")
    print(f"{'=' * 110}\n")

    for adapt in [True, False]:
        label = "Adaptive" if adapt else "Fixed"
        p = SweepParams(tp_pct=best_tp, dev_pct=best_dev, so_mult=best_so,
                        max_layers=best_ml, base_pct=0.05, adaptive=adapt)
        coin_results = {}
        for coin in COINS:
            if coin not in all_windows:
                continue
            r = run_single(coin, p, all_windows[coin], CAPITAL, TF)
            coin_results[coin] = r
        avg_roi = np.mean([r['roi'] for r in coin_results.values()])
        total_pnl = sum(r['pnl'] for r in coin_results.values())
        avg_wr = np.mean([r['wr'] for r in coin_results.values()])
        max_dd = max(r['max_dd'] for r in coin_results.values())
        coins_str = '  '.join(f"{c.split('/')[0]}:{coin_results[c]['roi']:+.1f}%" for c in COINS if c in coin_results)
        print(f"  {label:<10}  AVG={avg_roi:>+7.1f}%  WR={avg_wr:.1f}%  DD={max_dd:.1f}%  Total=${total_pnl:>+8.1f}  {coins_str}")

    # Final summary
    print(f"\n{'=' * 110}")
    print(f"OPTIMAL PARAMETERS:")
    print(f"  TP:         {best_tp*100:.1f}%")
    print(f"  Deviation:  {best_dev*100:.1f}%")
    print(f"  SO mult:    {best_so}x")
    print(f"  Max layers: {best_ml}")
    print(f"  Base order: 5% (adjust per sweep 3)")
    print(f"  Adaptive:   Yes (adjust per sweep 4)")
    print(f"{'=' * 110}")


if __name__ == '__main__':
    main()
