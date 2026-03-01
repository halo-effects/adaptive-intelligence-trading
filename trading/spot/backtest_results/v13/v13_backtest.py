"""
V13 Phase-Riding Backtest Engine

Simulates phase-riding strategy using validated signals:
- TOP: 2W StochRSI < 95 (primary) + 1W 97 cross + CFGI declining (early warning)
- BOTTOM/MARKUP ENTRY: 2W StochRSI exits OS + SMA50 slope positive
- CORRECTION FILTER: Price > SMA50 = hold, don't exit
- Phases: DCA (home) → MARKUP (long tiers) → DCA → MARKDOWN (short tiers) → DCA

Runs on daily candles, measures ROI, DD, phase accuracy, capture %.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import timedelta

sys.path.insert(0, str(Path(__file__).parent))
from v13_signals import V13SignalPack


class V13Backtest:
    """Phase-riding backtest with layered signal detection."""

    def __init__(self, coin, capital=10000, profile='high'):
        self.pack = V13SignalPack(coin)
        self.coin = coin
        self.initial_capital = capital
        self.capital = capital
        self.profile = profile

        # Profile settings
        profiles = {
            'low':    {'t1': 0.10, 't2': 0.15, 't3': 0.20, 't2_weeks': 3, 't3_weeks': 6},
            'medium': {'t1': 0.15, 't2': 0.20, 't3': 0.25, 't2_weeks': 2, 't3_weeks': 4},
            'high':   {'t1': 0.20, 't2': 0.25, 't3': 0.30, 't2_weeks': 1, 't3_weeks': 2},
        }
        self.pf = profiles[profile]

        # State
        self.phase = 'DCA'  # DCA, MARKUP, MARKDOWN
        self.phase_history = []
        self.trades = []
        self.equity_curve = []

        # Position tracking
        self.position_size = 0  # Total position in coin units
        self.position_cost = 0  # Total cost basis
        self.position_tier = 0  # 0=none, 1=T1, 2=T2, 3=T3
        self.tier_entry_date = None  # When current tier was entered
        self.phase_entry_date = None

        # DCA state (simplified)
        self.dca_active = False
        self.dca_entry_price = 0
        self.dca_size = 0

        # Signal state
        self.early_warning_active = False
        self.early_warning_date = None

    def run(self, start='2024-09-01', end='2026-02-17'):
        """Run backtest over date range."""
        daily = self.pack.daily
        dates = daily[(daily.index >= start) & (daily.index <= end)].index

        print(f"\n{'='*70}")
        print(f"  V13 Backtest: {self.coin} | {start} → {end} | ${self.initial_capital} | {self.profile}")
        print(f"{'='*70}")

        for dt in dates:
            price = daily.loc[dt, 'close']
            self._update_equity(dt, price)
            self._check_signals(dt, price)

        # Close any open positions at end
        if self.position_size != 0:
            self._close_position(dates[-1], daily.loc[dates[-1], 'close'], 'END_OF_TEST')

        self._print_results(dates)
        return self

    def _update_equity(self, dt, price):
        """Track equity curve."""
        unrealized = 0
        if self.position_size > 0:  # Long
            unrealized = self.position_size * price - self.position_cost
        elif self.position_size < 0:  # Short
            unrealized = self.position_cost - abs(self.position_size) * price

        equity = self.capital + unrealized
        self.equity_curve.append({'date': dt, 'equity': equity, 'price': price,
                                  'phase': self.phase, 'tier': self.position_tier})

    def _check_signals(self, dt, price):
        """Check all signals and manage phase transitions."""

        if self.phase == 'DCA':
            self._check_dca_signals(dt, price)
        elif self.phase == 'MARKUP':
            self._check_markup_signals(dt, price)
        elif self.phase == 'MARKDOWN':
            self._check_markdown_signals(dt, price)

    def _check_dca_signals(self, dt, price):
        """From DCA: check for markup or markdown entry."""

        # Check for MARKUP entry
        # 2W StochRSI exits OS (K was <5, now rising) + SMA50 slope positive
        stoch_2w = self.pack.stoch_2w
        k_2w = stoch_2w.get_k_at(dt)

        # Check if 2W just exited oversold (K > 5 after being < 5)
        os_exits = stoch_2w.os_exits(threshold=10)
        recent_os_exit = any(0 <= (dt - d).days <= 14 for d in os_exits.index)

        if recent_os_exit and self.pack.structure.sma50_slope_positive(dt, window=10):
            # Additional: not overextended
            if not self.pack.sma200.is_overextended(dt, threshold=20):
                self._enter_markup(dt, price)
                return

        # Check for MARKDOWN entry (from DCA, need strong signal)
        # 2W StochRSI exits OB + below SMA50 + sustained below BMSB
        ob_exits = stoch_2w.ob_exits(threshold=95)
        recent_ob_exit = any(0 <= (dt - d).days <= 14 for d in ob_exits.index)

        if recent_ob_exit:
            vs_sma50 = self.pack.structure.price_vs_sma50(dt)
            below_50 = vs_sma50 < 0 if not np.isnan(vs_sma50) else False
            if below_50 and self.pack.bmsb.sustained_below(dt, weeks=2):
                self._enter_markdown(dt, price)
                return

        # Simple DCA simulation: buy small amounts during ranging
        # (simplified — just track as being "in market" with small position)
        if not self.dca_active and k_2w is not None and 20 < k_2w < 80:
            self.dca_active = True
            self.dca_entry_price = price
            alloc = self.pf['t1'] * 0.5  # Half of T1 for DCA
            cost = self.capital * alloc
            self.dca_size = cost / price
            # Don't deduct from capital — DCA is a light position

    def _check_markup_signals(self, dt, price):
        """In MARKUP: check for tier additions and exit signals."""

        days_in_phase = (dt - self.phase_entry_date).days if self.phase_entry_date else 0

        # ── CORRECTION FILTER: price > SMA50 = hold ──
        vs_sma50 = self.pack.structure.price_vs_sma50(dt)
        above_sma50 = vs_sma50 > 0 if not np.isnan(vs_sma50) else True

        # ── EARLY WARNING: 1W StochRSI crosses below 97 ──
        stoch_1w = self.pack.stoch_1w
        ob_97 = stoch_1w.ob_exits(threshold=97)
        recent_1w_97 = any(0 <= (dt - d).days <= 7 for d in ob_97.index)

        if recent_1w_97 and not self.early_warning_active:
            self.early_warning_active = True
            self.early_warning_date = dt
            cfgi_declining = self.pack.cfgi.declining_from_greed(dt)
            if cfgi_declining:
                print(f"    {dt.date()}: ⚠️  EARLY WARNING + CFGI declining — prepare for exit")

        # ── PRIMARY EXIT: 2W StochRSI crosses below 95 ──
        stoch_2w = self.pack.stoch_2w
        ob_95 = stoch_2w.ob_exits(threshold=95)
        recent_2w_95 = any(0 <= (dt - d).days <= 14 for d in ob_95.index)

        if recent_2w_95:
            # Even without daily confirm, 2W 95 is 100% accurate — exit
            self._exit_markup(dt, price, 'SIGNAL_2W_95')
            return

        # ── SECONDARY EXIT: 1W 97 cross + below SMA50 ──
        if self.early_warning_active and not above_sma50:
            self._exit_markup(dt, price, 'SIGNAL_1W97_BELOW_SMA50')
            return

        # ── TIER ADDITIONS ──
        if self.position_tier == 1 and days_in_phase >= self.pf['t2_weeks'] * 7:
            # Check: still above SMA50 and no early warning
            if above_sma50 and not self.early_warning_active:
                self._add_tier(dt, price, 2)

        if self.position_tier == 2 and days_in_phase >= self.pf['t3_weeks'] * 7:
            adx = self.pack.structure.adx_at(dt)
            trending = adx > 25 if not np.isnan(adx) else False
            if above_sma50 and trending and not self.early_warning_active:
                self._add_tier(dt, price, 3)

    def _check_markdown_signals(self, dt, price):
        """In MARKDOWN: check for tier additions and exit signals."""

        days_in_phase = (dt - self.phase_entry_date).days if self.phase_entry_date else 0

        # ── EXIT: 2W StochRSI exits oversold → ranging confirmed ──
        stoch_2w = self.pack.stoch_2w
        os_exits = stoch_2w.os_exits(threshold=10)
        recent_os_exit = any(0 <= (dt - d).days <= 14 for d in os_exits.index)

        if recent_os_exit:
            self._exit_markdown(dt, price, 'SIGNAL_2W_OS_EXIT')
            return

        # ── Also exit if price reclaims SMA50 for extended period ──
        vs_sma50 = self.pack.structure.price_vs_sma50(dt)
        above_sma50 = vs_sma50 > 5 if not np.isnan(vs_sma50) else False  # 5% buffer
        if above_sma50 and days_in_phase > 14:
            sma50_rising = self.pack.structure.sma50_slope_positive(dt, window=10)
            if sma50_rising:
                self._exit_markdown(dt, price, 'SMA50_RECLAIM')
                return

        # ── TIER ADDITIONS ──
        if self.position_tier == 1 and days_in_phase >= self.pf['t2_weeks'] * 7:
            below_sma50 = (vs_sma50 < 0) if not np.isnan(vs_sma50) else False
            if below_sma50:
                self._add_tier(dt, price, 2)

        if self.position_tier == 2 and days_in_phase >= self.pf['t3_weeks'] * 7:
            adx = self.pack.structure.adx_at(dt)
            trending = adx > 25 if not np.isnan(adx) else False
            below_sma50 = (vs_sma50 < 0) if not np.isnan(vs_sma50) else False
            if below_sma50 and trending:
                self._add_tier(dt, price, 3)

    # ── Position Management ──

    def _enter_markup(self, dt, price):
        """Enter MARKUP phase with T1 long."""
        self.phase = 'MARKUP'
        self.phase_entry_date = dt
        self.early_warning_active = False

        # Close any DCA position (let TPs hit = simplified as close at current)
        if self.dca_active:
            dca_pnl = self.dca_size * (price - self.dca_entry_price)
            self.capital += dca_pnl
            self.dca_active = False
            self.dca_size = 0

        # T1 long entry
        alloc = self.pf['t1'] * self.capital
        self.position_size = alloc / price
        self.position_cost = alloc
        self.position_tier = 1
        self.tier_entry_date = dt
        self.capital -= alloc

        self.phase_history.append({'date': dt, 'phase': 'MARKUP', 'action': 'ENTER_T1',
                                   'price': price, 'size': self.position_size})
        print(f"  {dt.date()}: 📈 ENTER MARKUP T1 @ {price:.1f} (alloc ${alloc:.0f})")

    def _enter_markdown(self, dt, price):
        """Enter MARKDOWN phase with T1 short."""
        self.phase = 'MARKDOWN'
        self.phase_entry_date = dt
        self.early_warning_active = False

        if self.dca_active:
            dca_pnl = self.dca_size * (price - self.dca_entry_price)
            self.capital += dca_pnl
            self.dca_active = False
            self.dca_size = 0

        # T1 short entry (negative position)
        alloc = self.pf['t1'] * self.capital
        self.position_size = -(alloc / price)
        self.position_cost = alloc
        self.position_tier = 1
        self.tier_entry_date = dt
        # Capital stays — short doesn't require spending (simplified)

        self.phase_history.append({'date': dt, 'phase': 'MARKDOWN', 'action': 'ENTER_T1',
                                   'price': price, 'size': self.position_size})
        print(f"  {dt.date()}: 📉 ENTER MARKDOWN T1 @ {price:.1f} (alloc ${alloc:.0f})")

    def _add_tier(self, dt, price, tier):
        """Add T2 or T3 to existing position."""
        tier_key = f't{tier}'
        alloc = self.pf[tier_key] * self.capital if self.capital > 0 else 0
        if alloc <= 0:
            return

        if self.phase == 'MARKUP':
            new_size = alloc / price
            self.position_size += new_size
            self.position_cost += alloc
            self.capital -= alloc
        elif self.phase == 'MARKDOWN':
            new_size = alloc / price
            self.position_size -= new_size  # Add to short
            self.position_cost += alloc

        self.position_tier = tier
        self.tier_entry_date = dt
        self.phase_history.append({'date': dt, 'phase': self.phase, 'action': f'ADD_T{tier}',
                                   'price': price, 'size': new_size if self.phase == 'MARKUP' else -new_size})
        print(f"  {dt.date()}: {'📈' if self.phase == 'MARKUP' else '📉'} ADD T{tier} @ {price:.1f} (alloc ${alloc:.0f})")

    def _exit_markup(self, dt, price, reason):
        """Exit MARKUP: sell 100% at market."""
        pnl = self.position_size * price - self.position_cost
        pnl_pct = pnl / self.position_cost * 100 if self.position_cost > 0 else 0
        self.capital += self.position_size * price  # Sell all

        self.trades.append({
            'date': dt, 'phase': 'MARKUP', 'action': 'EXIT',
            'entry_cost': self.position_cost, 'exit_value': self.position_size * price,
            'pnl': pnl, 'pnl_pct': pnl_pct, 'reason': reason,
            'days': (dt - self.phase_entry_date).days if self.phase_entry_date else 0,
            'tier': self.position_tier,
        })

        emoji = '✅' if pnl > 0 else '❌'
        print(f"  {dt.date()}: {emoji} EXIT MARKUP @ {price:.1f} | PnL: ${pnl:.0f} ({pnl_pct:+.1f}%) | {reason}")

        self.position_size = 0
        self.position_cost = 0
        self.position_tier = 0
        self.phase = 'DCA'
        self.phase_entry_date = dt
        self.early_warning_active = False

    def _exit_markdown(self, dt, price, reason):
        """Exit MARKDOWN: cover 100% at market."""
        # Short PnL: sold high, buy back low
        exit_cost = abs(self.position_size) * price
        pnl = self.position_cost - exit_cost  # Profit if price dropped
        pnl_pct = pnl / self.position_cost * 100 if self.position_cost > 0 else 0
        self.capital += pnl  # Add profit (or subtract loss)

        self.trades.append({
            'date': dt, 'phase': 'MARKDOWN', 'action': 'EXIT',
            'entry_cost': self.position_cost, 'exit_value': exit_cost,
            'pnl': pnl, 'pnl_pct': pnl_pct, 'reason': reason,
            'days': (dt - self.phase_entry_date).days if self.phase_entry_date else 0,
            'tier': self.position_tier,
        })

        emoji = '✅' if pnl > 0 else '❌'
        print(f"  {dt.date()}: {emoji} EXIT MARKDOWN @ {price:.1f} | PnL: ${pnl:.0f} ({pnl_pct:+.1f}%) | {reason}")

        self.position_size = 0
        self.position_cost = 0
        self.position_tier = 0
        self.phase = 'DCA'
        self.phase_entry_date = dt

    def _close_position(self, dt, price, reason):
        """Force close any position at end of test."""
        if self.phase == 'MARKUP' and self.position_size > 0:
            self._exit_markup(dt, price, reason)
        elif self.phase == 'MARKDOWN' and self.position_size < 0:
            self._exit_markdown(dt, price, reason)

    def _print_results(self, dates):
        """Print backtest summary."""
        if not self.equity_curve:
            print("  No data")
            return

        eq = pd.DataFrame(self.equity_curve)
        final_equity = eq['equity'].iloc[-1]
        roi = (final_equity - self.initial_capital) / self.initial_capital * 100
        max_equity = eq['equity'].cummax()
        drawdown = (eq['equity'] - max_equity) / max_equity * 100
        max_dd = drawdown.min()

        # Buy and hold comparison
        start_price = eq['price'].iloc[0]
        end_price = eq['price'].iloc[-1]
        bnh_roi = (end_price - start_price) / start_price * 100

        # Phase stats
        n_trades = len(self.trades)
        winners = [t for t in self.trades if t['pnl'] > 0]
        losers = [t for t in self.trades if t['pnl'] <= 0]
        win_rate = len(winners) / max(n_trades, 1) * 100
        avg_win = np.mean([t['pnl_pct'] for t in winners]) if winners else 0
        avg_loss = np.mean([t['pnl_pct'] for t in losers]) if losers else 0

        # Phase time
        phase_times = {}
        for _, row in eq.iterrows():
            p = row['phase']
            phase_times[p] = phase_times.get(p, 0) + 1
        total_days = len(eq)

        print(f"\n  {'─'*60}")
        print(f"  RESULTS: {self.coin}")
        print(f"  {'─'*60}")
        print(f"  ROI:            {roi:+.1f}% (${self.initial_capital} → ${final_equity:.0f})")
        print(f"  Buy & Hold:     {bnh_roi:+.1f}%")
        print(f"  Max Drawdown:   {max_dd:.1f}%")
        print(f"  Trades:         {n_trades} ({len(winners)}W / {len(losers)}L, {win_rate:.0f}% win rate)")
        print(f"  Avg Win:        {avg_win:+.1f}%")
        print(f"  Avg Loss:       {avg_loss:+.1f}%")
        print(f"  Phase time:     ", end='')
        for p, d in sorted(phase_times.items()):
            print(f"{p}={d}d({d/total_days*100:.0f}%) ", end='')
        print()

        # Trade log
        print(f"\n  Trade Log:")
        for t in self.trades:
            emoji = '✅' if t['pnl'] > 0 else '❌'
            print(f"    {emoji} {t['date'].date()} {t['phase']} T{t['tier']} "
                  f"PnL={t['pnl_pct']:+.1f}% (${t['pnl']:.0f}) {t['days']}d | {t['reason']}")


def run_all():
    """Run backtest for all test coins."""
    print("V13 PHASE-RIDING BACKTEST")
    print("=" * 70)
    print("Signals: 2W StochRSI 95 (top), 2W OS 10 + SMA50 slope (bottom)")
    print("Correction filter: price > SMA50 = hold")
    print("Profile: High (T1=20%, T2=25%, T3=30%)")
    print()

    results = {}
    for coin in ['BTC', 'ETH', 'SOL']:
        bt = V13Backtest(coin, capital=10000, profile='high')
        bt.run(start='2024-09-01', end='2026-02-17')
        results[coin] = bt

    # Summary
    print("\n\n" + "=" * 70)
    print("PORTFOLIO SUMMARY")
    print("=" * 70)
    total_start = 30000
    total_end = 0
    for coin, bt in results.items():
        if bt.equity_curve:
            eq = bt.equity_curve[-1]['equity']
            roi = (eq - 10000) / 10000 * 100
            print(f"  {coin}: ${eq:.0f} ({roi:+.1f}%)")
            total_end += eq
        else:
            total_end += 10000
    total_roi = (total_end - total_start) / total_start * 100
    print(f"  TOTAL: ${total_end:.0f} ({total_roi:+.1f}%)")


if __name__ == '__main__':
    run_all()
