"""V13 Full Lifecycle with Enhanced 1h DCA Grinding.

Replaces V13's daily DCA ticks with 1h DCA ticks using per-coin optimized params.
KEEPS graceful DCA exits — positions ride into MARKUP and hit TPs naturally.
Phase transitions still happen on daily bars (unchanged).

Compare: Baseline (daily DCA) vs Enhanced (1h DCA grinding, same graceful exits).
"""
import sqlite3
import sys
import copy
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack

DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'

COINS = ['ETH/USDC', 'BTC/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
CAPITAL = 2500
PROFILE = 'high'
START = '2023-01-01'
END = '2026-02-27'

# Per-coin 1h DCA configs (from dca_tf_compare.py winners)
# These replace the V13 default DCA params during DCA phase only
DCA_OVERRIDES = {
    'ETH/USDC': {'tp': 0.015, 'dev': 0.025, 'so_mult': 2.0, 'layers': 8, 'bo_pct': 0.05},
    'BTC/USDC': {'tp': 0.015, 'dev': 0.025, 'so_mult': 2.0, 'layers': 8, 'bo_pct': 0.05},
    'SOL/USDC': {'tp': 0.020, 'dev': 0.030, 'so_mult': 2.0, 'layers': 8, 'bo_pct': 0.05},
    'LINK/USDC': {'tp': 0.010, 'dev': 0.020, 'so_mult': 2.0, 'layers': 8, 'bo_pct': 0.05},
    'XRP/USDC': {'tp': 0.015, 'dev': 0.025, 'so_mult': 2.0, 'layers': 8, 'bo_pct': 0.05},
}


def load_1h_candles(coin):
    """Load all 1h candles for a coin from DB."""
    conn = sqlite3.connect(DB_PATH)
    for sym in [coin, coin.replace('/USDC', '/USDT')]:
        df = pd.read_sql_query(
            "SELECT timestamp, open, high, low, close, volume FROM candles "
            "WHERE symbol=? AND timeframe='1h' ORDER BY timestamp",
            conn, params=(sym,))
        if not df.empty:
            conn.close()
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df['date'] = df['date'].dt.tz_localize(None)  # Strip tz to match V13 daily
            df.set_index('date', inplace=True)
            return df
    conn.close()
    return pd.DataFrame()


class V13Enhanced(V13BacktestV8):
    """V13 with ISOLATED 1h DCA grinding. DCA grinder runs in its own capital
    pool so it has ZERO effect on markup/markdown behavior. The grinder P&L
    is purely additive to the baseline lifecycle."""

    def __init__(self, pack, config, dca_override=None, candles_1h=None):
        super().__init__(pack, config)
        self.dca_override = dca_override
        self.candles_1h = candles_1h

        # Isolated DCA grinder state (separate from V13's built-in DCA)
        self._g_coins = 0.0       # grinder coins held
        self._g_avg_entry = 0.0   # grinder avg entry
        self._g_layers = 0        # grinder layers
        self._g_tp = 0.0          # grinder TP price
        self._g_cost = 0.0        # grinder total cost basis
        self._g_capital = 0.0     # grinder capital pool (set at DCA phase start)
        self._g_pnl = 0.0         # grinder realized P&L (cumulative)
        self._g_trades = 0        # grinder completed round-trips
        self._g_wins = 0
        self._g_lots = 0          # total lots opened
        self._g_active = False    # is grinder running?

    def _grinder_start(self, capital_pool):
        """Start grinder with isolated capital at DCA phase entry."""
        self._g_capital = capital_pool
        self._g_active = True

    def _grinder_stop(self, price):
        """Stop grinder at phase exit. Force-close if in MARKDOWN, let ride if MARKUP."""
        self._g_active = False

    def _grinder_force_close(self, price):
        """Force close grinder position (for MARKDOWN exits)."""
        if self._g_coins > 0:
            proceeds = self._g_coins * price
            pnl = proceeds - self._g_cost
            self._g_capital += proceeds
            self._g_pnl += pnl
            self._g_trades += 1
            if pnl > 0:
                self._g_wins += 1
            self._g_coins = 0
            self._g_avg_entry = 0
            self._g_layers = 0
            self._g_tp = 0
            self._g_cost = 0

    def _grinder_tick(self, price, high, low):
        """1h DCA tick on isolated capital pool."""
        if not self._g_active or not self.dca_override:
            return
        ov = self.dca_override

        # Check TP on high
        if self._g_coins > 0 and self._g_tp > 0 and high >= self._g_tp:
            proceeds = self._g_coins * self._g_tp
            pnl = proceeds - self._g_cost
            self._g_capital += proceeds
            self._g_pnl += pnl
            self._g_trades += 1
            self._g_wins += 1
            self._g_coins = 0
            self._g_avg_entry = 0
            self._g_layers = 0
            self._g_tp = 0
            self._g_cost = 0
            return

        if self._g_layers >= ov['layers']:
            return

        # Check buy conditions
        should_buy = False
        if self._g_layers == 0:
            should_buy = True
        elif self._g_avg_entry > 0:
            target_drop = ov['dev'] * self._g_layers
            current_drop = (self._g_avg_entry - low) / self._g_avg_entry
            if current_drop >= target_drop:
                should_buy = True

        if should_buy:
            buy_price = low if self._g_layers > 0 else price
            available = self._g_capital * 0.90
            if self._g_layers == 0:
                order = available * ov['bo_pct']
            else:
                order = available * ov['bo_pct'] * (ov['so_mult'] ** min(self._g_layers, 4))
            order = min(order, self._g_capital * 0.3)
            if order < 10 or order > self._g_capital:
                return

            coins = order / buy_price
            self._g_coins += coins
            self._g_capital -= order
            self._g_cost += order
            self._g_layers += 1
            self._g_avg_entry = self._g_cost / self._g_coins
            self._g_tp = self._g_avg_entry * (1 + ov['tp'])
            self._g_lots += 1

    def _grinder_tp_only(self, high):
        """Check TP only (no new buys) — for graceful exit during MARKUP."""
        if self._g_coins > 0 and self._g_tp > 0 and high >= self._g_tp:
            proceeds = self._g_coins * self._g_tp
            pnl = proceeds - self._g_cost
            self._g_capital += proceeds
            self._g_pnl += pnl
            self._g_trades += 1
            self._g_wins += 1
            self._g_coins = 0
            self._g_avg_entry = 0
            self._g_layers = 0
            self._g_tp = 0
            self._g_cost = 0

    def run(self):
        """Run baseline V13 UNCHANGED + isolated 1h DCA grinder overlay."""
        start = pd.Timestamp(self.cfg.START_DATE)
        end = pd.Timestamp(self.cfg.END_DATE)
        data = self.daily[(self.daily.index >= start) & (self.daily.index <= end)]

        if len(data) == 0:
            return None

        self.phase = Phase.DCA
        self.phase_start_date = data.index[0]
        self.phase_log.append({
            'date': data.index[0], 'from': None, 'to': Phase.DCA,
            'reason': 'START', 'equity': self.cfg.CAPITAL,
            'price': data['close'].iloc[0]
        })

        # Start grinder at beginning (DCA phase)
        grinder_pool = self.cfg.CAPITAL * 0.10  # 10% dedicated to grinding
        self._grinder_start(grinder_pool)

        prev_date = None
        prev_phase = Phase.DCA

        for date, row in data.iterrows():
            price = row['close']

            # --- 1h grinder ticks (isolated, between daily bars) ---
            if prev_date is not None and self.candles_1h is not None:
                mask = (self.candles_1h.index > prev_date) & (self.candles_1h.index <= date)
                hourly = self.candles_1h[mask]
                for _, hrow in hourly.iterrows():
                    if self.phase == Phase.DCA:
                        self._grinder_tick(hrow['close'], hrow['high'], hrow['low'])
                    elif self.phase == Phase.MARKUP and self._g_coins > 0:
                        # Graceful exit: only check TPs, no new buys
                        self._grinder_tp_only(hrow['high'])

            # Detect phase transitions for grinder management
            if self.phase != prev_phase:
                if self.phase == Phase.DCA:
                    # Entering DCA: activate grinder
                    self._g_active = True
                elif prev_phase == Phase.DCA and self.phase == Phase.MARKUP:
                    # DCA->MARKUP: stop new buys, let positions ride (graceful)
                    self._g_active = False
                elif prev_phase == Phase.DCA and self.phase == Phase.MARKDOWN:
                    # DCA->MARKDOWN: force close grinder (hard exit)
                    self._grinder_force_close(price)
                    self._g_active = False
                elif self.phase in (Phase.FLAT, Phase.MARKDOWN):
                    # Any transition to FLAT/MARKDOWN: ensure grinder stopped
                    if self._g_coins > 0:
                        self._grinder_force_close(price)
                    self._g_active = False

            prev_phase = self.phase
            prev_date = date

            # --- Run baseline V13 UNCHANGED ---
            self.equity_curve.append({
                'date': date, 'equity': self._total_equity(date),
                'price': price, 'phase': self.phase
            })

            if self.phase_start_date and (date - self.phase_start_date).days < self.cfg.MIN_PHASE_DAYS:
                if self.phase in (Phase.DCA, Phase.MARKUP) and self.dca_coins > 0:
                    self._dca_tick(date, price)
                continue

            if self.phase == Phase.DCA:
                self._check_dca(date, price)
            elif self.phase == Phase.MARKUP:
                self._check_markup(date, price)
            elif self.phase == Phase.FLAT:
                self._check_flat(date, price)
            elif self.phase == Phase.MARKDOWN:
                self._check_markdown(date, price)

        # Close open positions at end
        if self.position_coins > 0:
            self._sell_all(data.index[-1], 'OPEN_END')
        if self.dca_coins > 0:
            self._dca_close(data.index[-1], 'OPEN_END')
        if self.short_coins > 0:
            self._close_short(data.index[-1], 'OPEN_END')
        # Force close grinder at end
        if self._g_coins > 0:
            self._grinder_force_close(data.iloc[-1]['close'])

        result = self._results()
        # Add grinder metrics to result
        result['grinder_pnl'] = self._g_pnl
        result['grinder_trades'] = self._g_trades
        result['grinder_wins'] = self._g_wins
        result['grinder_lots'] = self._g_lots
        result['grinder_capital'] = grinder_pool
        return result


def run_coin(coin):
    """Run baseline and enhanced for one coin, return results dict."""
    short = coin.split('/')[0]
    print(f"\n{'='*100}")
    print(f"  {coin}")
    print(f"{'='*100}")

    # Config
    cfg = V13Config()
    cfg.CAPITAL = CAPITAL
    cfg.START_DATE = START
    cfg.END_DATE = END
    cfg.TIER1_PCT = 0.60; cfg.TIER2_PCT = 0.20; cfg.TIER3_PCT = 0.10
    cfg.SHORT_TIER1_PCT = 0.60; cfg.SHORT_TIER2_PCT = 0.20; cfg.SHORT_TIER3_PCT = 0.10
    cfg.SHORTS_ENABLED = True

    pack = V13SignalPack(coin, db_path=str(DB_PATH))

    # --- Baseline ---
    baseline = V13BacktestV8(pack, cfg)
    br = baseline.run()
    if not br:
        print(f"  Baseline failed")
        return None

    # --- Enhanced (1h DCA) ---
    candles_1h = load_1h_candles(coin)
    if candles_1h.empty:
        print(f"  No 1h candles for {coin}")
        return None

    pack2 = V13SignalPack(coin, db_path=str(DB_PATH))
    enhanced = V13Enhanced(pack2, cfg, DCA_OVERRIDES.get(coin), candles_1h)
    er = enhanced.run()
    if not er:
        print(f"  Enhanced failed")
        return None

    # The enhanced engine runs baseline V13 UNCHANGED + isolated grinder overlay
    # Baseline metrics are IDENTICAL in both runs (same engine, same capital)
    # Grinder P&L is purely additive
    grinder_pnl = er.get('grinder_pnl', 0)
    grinder_trades = er.get('grinder_trades', 0)
    grinder_wins = er.get('grinder_wins', 0)
    grinder_lots = er.get('grinder_lots', 0)
    grinder_cap = er.get('grinder_capital', 0)
    grinder_wr = grinder_wins / max(grinder_trades, 1) * 100

    # Combined = baseline + grinder (additive)
    combined_equity = br['final_equity'] + grinder_pnl
    combined_roi = (combined_equity - CAPITAL) / CAPITAL * 100

    print(f"\n  --- BASELINE V13 (unchanged) ---")
    print(f"    ROI:           {br['roi']:>+8.1f}%  (${br['final_equity'] - CAPITAL:>+,.0f})")
    print(f"    Closed ROI:    {br['closed_roi']:>+8.1f}%")
    print(f"    DCA P&L:       ${br['dca_pnl']:>+8.1f}  ({br['dca_trades']} trades)")
    print(f"    Max DD:        {br['max_drawdown']:>8.1f}%")
    print(f"    Markup Cycles: {br['markup_cycles']}")

    print(f"\n  --- 1h DCA GRINDER (isolated, additive) ---")
    print(f"    Capital Pool:  ${grinder_cap:>8.0f}  (10% of ${CAPITAL})")
    print(f"    Grinder P&L:   ${grinder_pnl:>+8.1f}  ({grinder_trades} trades, {grinder_wr:.0f}% WR)")
    print(f"    Lots Opened:   {grinder_lots}")
    print(f"    Grinder ROI:   {grinder_pnl/max(grinder_cap,1)*100:>+8.1f}%  (on grinder capital)")

    print(f"\n  --- COMBINED (baseline + grinder) ---")
    print(f"    ROI:           {combined_roi:>+8.1f}%  (${combined_equity - CAPITAL:>+,.0f})")
    print(f"    Lift:          {combined_roi - br['roi']:>+8.1f}%  (${grinder_pnl:>+,.0f})")

    # Verify baseline is identical
    if abs(br['roi'] - er['roi']) > 0.01:
        print(f"\n  WARNING: Baseline ROI mismatch! br={br['roi']:.2f}% er={er['roi']:.2f}%")
        print(f"  Phase counts: baseline={len(baseline.phase_log)}, enhanced={len(enhanced.phase_log)}")

    return {
        'coin': short,
        'baseline_roi': br['roi'],
        'combined_roi': combined_roi,
        'baseline_equity': br['final_equity'],
        'combined_equity': combined_equity,
        'baseline_dca_pnl': br['dca_pnl'],
        'grinder_pnl': grinder_pnl,
        'grinder_trades': grinder_trades,
        'grinder_lots': grinder_lots,
        'grinder_cap': grinder_cap,
        'baseline_dd': br['max_drawdown'],
        'markup_cycles': br['markup_cycles'],
    }


def main():
    print("=" * 100)
    print("V13 FULL LIFECYCLE: BASELINE vs ENHANCED 1h DCA (GRACEFUL EXITS)")
    print(f"Capital: ${CAPITAL}/coin | Profile: {PROFILE} | Period: {START} to {END}")
    print("DCA: 1h candles with per-coin optimized params | Graceful exit into MARKUP preserved")
    print("=" * 100)

    results = []
    for coin in COINS:
        try:
            r = run_coin(coin)
            if r:
                results.append(r)
        except Exception as ex:
            print(f"\n  {coin}: FAILED - {ex}")
            import traceback; traceback.print_exc()

    if not results:
        print("\nNo results!")
        return

    # Portfolio summary
    print(f"\n{'='*100}")
    print("PORTFOLIO SUMMARY")
    print(f"{'='*100}")

    print(f"\n  {'Coin':<6} {'Baseline':>10} {'Combined':>10} {'Grinder$':>10} {'Grind ROI':>10} {'Lots':>6} {'Cycles':>7}")
    print(f"  {'_'*6} {'_'*10} {'_'*10} {'_'*10} {'_'*10} {'_'*6} {'_'*7}")

    total_base_eq = 0
    total_grinder_pnl = 0
    total_capital = len(results) * CAPITAL

    for r in results:
        grind_roi = r['grinder_pnl'] / max(r['grinder_cap'], 1) * 100
        print(f"  {r['coin']:<6} {r['baseline_roi']:>+9.1f}% {r['combined_roi']:>+9.1f}% "
              f"${r['grinder_pnl']:>+9.1f} {grind_roi:>+9.1f}% {r['grinder_lots']:>6} {r['markup_cycles']:>7}")
        total_base_eq += r['baseline_equity']
        total_grinder_pnl += r['grinder_pnl']

    base_port = (total_base_eq - total_capital) / total_capital * 100
    combined_port = (total_base_eq + total_grinder_pnl - total_capital) / total_capital * 100

    print(f"\n  Portfolio ({len(results)} coins, ${total_capital:,}):")
    print(f"    Baseline:  {base_port:>+8.1f}%  (${total_base_eq - total_capital:>+,.0f})")
    print(f"    Combined:  {combined_port:>+8.1f}%  (${total_base_eq + total_grinder_pnl - total_capital:>+,.0f})")
    print(f"    Grinder:   {total_grinder_pnl/total_capital*100:>+8.1f}%  (${total_grinder_pnl:>+,.0f} additive)")

    print(f"\n{'='*100}")
    print("Done.")


if __name__ == '__main__':
    main()
