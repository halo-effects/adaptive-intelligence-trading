"""
ROUTER Phase 3: Fast-track DCA routing test.
Test HH_HL-based early exit from ROUTER to DCA.

Variants:
  - Baseline (current: 14d min + ADX sustained 14d OR 42d timeout)
  - HH_HL >= 1 at 7d  -> fast-track to DCA
  - HH_HL >= 1 at 5d  -> faster
  - HH_HL >= 1 at 3d  -> fastest
  - SMA50 above at 7d -> fast-track to DCA
  - Combined: HH_HL>=1 OR SMA50_above at 7d
  - Also test reducing timeout from 42d to 28d alongside fast-track
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack


class V13RouterFastTrack(V13BacktestV8):
    """V13 with ROUTER fast-track to DCA."""

    def __init__(self, pack, cfg, fast_cfg=None):
        super().__init__(pack, cfg)
        self.fast_cfg = fast_cfg or {}
        self.fast_track_count = 0
        self.fast_track_details = []

    def _check_flat(self, date, price):
        """Override FLAT/ROUTER check to add fast-track logic.
        MUST match v8 exactly for baseline (empty fast_cfg)."""
        if self.phase_start_date is None:
            return

        adx = self._adx(date)
        days_in = (date - self.phase_start_date).days

        # Minimum eval period for all FLAT exits
        min_eval = self.fast_cfg.get('min_eval_days', self.cfg.FLAT_MIN_EVAL_DAYS)
        if days_in < min_eval:
            return

        # PATH 1: Entered from TOP SIGNAL
        if self.flat_from_top:
            # Check for MARKDOWN: LH_LL + ADX>20 + Fib_break
            from v13_phase_backtest_v8 import price_broke_fib_support
            fib = self._fib_levels(date)
            lh_ll = self.pack.structure.lh_ll_streak(date, self.cfg.HH_HL_LOOKBACK)
            if lh_ll and not np.isnan(adx) and adx > self.cfg.ADX_THRESHOLD:
                if price_broke_fib_support(price, fib):
                    overext = self.pack.sma200.overextension_at(date)
                    note = f'FLAT->MARKDOWN: Post-top, LH_LL+ADX={adx:.0f}+Fib_break'
                    if not np.isnan(overext):
                        note += f' (SMA200={overext*100:+.0f}%)'
                    note += f' (flat {days_in}d)'
                    self._change_phase(date, Phase.MARKDOWN, note)
                    return

            # --- NEW: Fast-track to DCA (only during from_top, before timeout) ---
            ft_check_day = self.fast_cfg.get('ft_check_day', 0)
            if ft_check_day > 0 and days_in >= ft_check_day:
                if self._should_fast_track(date, days_in):
                    return

            # Timeout
            max_eval = self.fast_cfg.get('max_eval_days', self.cfg.FLAT_MAX_EVAL_DAYS)
            if days_in >= max_eval:
                self._change_phase(date, Phase.DCA,
                    f'FLAT->DCA: Post-top, no markdown signal after {days_in}d')
            return

        # PATH 2 & 3: From RANGING EXIT or MARKDOWN
        # --- NEW: Fast-track to DCA (non-top entries too) ---
        ft_check_day = self.fast_cfg.get('ft_check_day', 0)
        if ft_check_day > 0 and days_in >= ft_check_day:
            if self._should_fast_track(date, days_in):
                return

        # ADX ranging confirmation
        if not np.isnan(adx) and adx < self.cfg.FLAT_ADX_RANGING:
            self.adx_below_20_streak += 1
        else:
            self.adx_below_20_streak = 0

        ranging = self.adx_below_20_streak >= self.fast_cfg.get(
            'adx_sustained_days', self.cfg.FLAT_ADX_SUSTAINED_DAYS)
        if ranging:
            self._change_phase(date, Phase.DCA,
                f'FLAT->DCA: Ranging confirmed (ADX<{self.cfg.FLAT_ADX_RANGING} for {self.adx_below_20_streak}d)')
            self.adx_below_20_streak = 0

    def _should_fast_track(self, date, days_in):
        """Check fast-track signals and transition if met. Returns True if transitioned."""
        should_fast_track = False
        reason_parts = []

        if self.fast_cfg.get('ft_hh_hl', False):
            hh_hl = self.pack.structure.hh_hl_streak(date, self.cfg.HH_HL_LOOKBACK)
            if hh_hl >= self.fast_cfg.get('ft_hh_hl_min', 1):
                should_fast_track = True
                reason_parts.append(f'HH_HL={hh_hl}')

        if self.fast_cfg.get('ft_sma50', False) or self.fast_cfg.get('ft_sma50_only', False):
            try:
                sma50 = self.pack.daily.loc[:date, 'sma50'].iloc[-1]
                close = self.pack.daily.loc[:date, 'close'].iloc[-1]
                if not np.isnan(sma50) and close > sma50:
                    if self.fast_cfg.get('ft_sma50_only', False):
                        should_fast_track = True
                    elif self.fast_cfg.get('ft_sma50_or', False):
                        should_fast_track = True
                    reason_parts.append('SMA50_above')
            except:
                pass

        if self.fast_cfg.get('ft_cfgi', False):
            cfgi = self._cfgi(date)
            cfgi_thresh = self.fast_cfg.get('ft_cfgi_min', 50)
            if not np.isnan(cfgi) and cfgi >= cfgi_thresh:
                if self.fast_cfg.get('ft_cfgi_or', False):
                    should_fast_track = True
                    reason_parts.append(f'CFGI={cfgi:.0f}')

        if should_fast_track:
            reason = f'FAST_TRACK->DCA: {"+".join(reason_parts)} @{days_in}d'
            self.fast_track_count += 1
            self.fast_track_details.append({'date': date, 'days_in': days_in, 'reason': reason})
            self._change_phase(date, Phase.DCA, reason)
            return True
        return False


def run_variant(coins, fast_cfg, label):
    results = {}
    total_equity = 0
    total_ft = 0

    for coin in coins:
        pack = V13SignalPack(coin)
        cfg = V13Config()
        cfg.START_DATE = '2023-01-01'
        cfg.END_DATE = '2026-02-25'
        cfg.CAPITAL = 2500

        bt = V13RouterFastTrack(pack, cfg, fast_cfg=fast_cfg.copy())
        result = bt.run()
        if result is None:
            continue

        # Calculate time in ROUTER
        router_days = sum(1 for e in bt.equity_curve if e.get('phase') == Phase.FLAT)

        results[coin] = {
            'equity': result['final_equity'],
            'roi': result['roi'],
            'trades': result['total_trades'],
            'fast_tracks': bt.fast_track_count,
            'router_days': router_days,
        }
        total_equity += result['final_equity']
        total_ft += bt.fast_track_count

    return results, total_equity, total_ft


def main():
    coins = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']

    variants = [
        ('BASELINE (14d min, 42d timeout)', {}),
        # HH_HL fast-track variants
        ('HH_HL>=1 @7d', {'ft_check_day': 7, 'ft_hh_hl': True, 'ft_hh_hl_min': 1}),
        ('HH_HL>=1 @5d', {'ft_check_day': 5, 'ft_hh_hl': True, 'ft_hh_hl_min': 1}),
        ('HH_HL>=1 @3d', {'ft_check_day': 3, 'ft_hh_hl': True, 'ft_hh_hl_min': 1}),
        ('HH_HL>=1 @10d', {'ft_check_day': 10, 'ft_hh_hl': True, 'ft_hh_hl_min': 1}),
        ('HH_HL>=1 @14d', {'ft_check_day': 14, 'ft_hh_hl': True, 'ft_hh_hl_min': 1}),
        # SMA50 variants
        ('SMA50_above @7d', {'ft_check_day': 7, 'ft_sma50': True, 'ft_sma50_only': True}),
        ('SMA50_above @14d', {'ft_check_day': 14, 'ft_sma50': True, 'ft_sma50_only': True}),
        # Combined
        ('HH_HL>=1 OR SMA50 @7d', {'ft_check_day': 7, 'ft_hh_hl': True, 'ft_sma50': True, 'ft_sma50_or': True}),
        ('HH_HL>=1 + CFGI>=50 @7d', {'ft_check_day': 7, 'ft_hh_hl': True, 'ft_cfgi': True, 'ft_cfgi_or': True, 'ft_cfgi_min': 50}),
        # HH_HL + reduced timeout
        ('HH_HL>=1 @7d + 28d timeout', {'ft_check_day': 7, 'ft_hh_hl': True, 'max_eval_days': 28}),
        ('HH_HL>=1 @7d + 21d timeout', {'ft_check_day': 7, 'ft_hh_hl': True, 'max_eval_days': 21}),
        ('HH_HL>=1 @5d + 28d timeout', {'ft_check_day': 5, 'ft_hh_hl': True, 'max_eval_days': 28}),
        # Reduced min eval
        ('HH_HL>=1 @7d, min_eval=7', {'ft_check_day': 7, 'ft_hh_hl': True, 'min_eval_days': 7}),
        ('HH_HL>=1 @5d, min_eval=5', {'ft_check_day': 5, 'ft_hh_hl': True, 'min_eval_days': 5}),
        # Just timeout reduction (no fast-track)
        ('No FT, timeout=28d', {'max_eval_days': 28}),
        ('No FT, timeout=21d', {'max_eval_days': 21}),
    ]

    print("=" * 130)
    print("  ROUTER PHASE 3: Fast-Track DCA Routing Sweep")
    print("=" * 130)

    baseline_equity = None
    baseline_router_days = None
    all_results = []

    for label, fast_cfg in variants:
        results, total_eq, total_ft = run_variant(coins, fast_cfg, label)
        total_router = sum(r['router_days'] for r in results.values())

        if baseline_equity is None:
            baseline_equity = total_eq
            baseline_router_days = total_router

        delta = total_eq - baseline_equity
        days_saved = baseline_router_days - total_router
        all_results.append((label, results, total_eq, delta, total_ft, total_router, days_saved))

    # Print results
    print(f"\n{'Variant':<40} {'Total$':>10} {'Delta':>8} {'FT#':>4} {'RtrDays':>8} {'Saved':>6}  ", end="")
    for c in coins:
        print(f" {c:>7}", end="")
    print()
    print("-" * 130)

    for label, results, total_eq, delta, total_ft, router_d, days_saved in all_results:
        d_str = f"{delta:+,.0f}" if delta != 0 else "BASE"
        print(f"{label:<40} ${total_eq:>9,.0f} {d_str:>8} {total_ft:>4} {router_d:>8} {days_saved:>+6}  ", end="")
        for c in coins:
            if c in results:
                coin_delta = results[c]['equity'] - all_results[0][1].get(c, {}).get('equity', 0)
                print(f" {coin_delta:>+7,.0f}", end="")
            else:
                print(f" {'N/A':>7}", end="")
        print()


if __name__ == '__main__':
    main()
