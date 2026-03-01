"""
ROUTER Phase 4: Direct ROUTER->MARKUP path.
Currently ROUTER can only exit to DCA or MARKDOWN.
Add MARKUP exit using HH_HL + Fib_support (same gate as DCA->MARKUP).

Key risk: must not fire on bear market rallies.
Test with various confirmation requirements.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase, price_near_fib_support
from v13_signals import V13SignalPack


class V13RouterDirectMarkup(V13BacktestV8):
    """V13 with ROUTER->MARKUP direct path."""

    def __init__(self, pack, cfg, direct_cfg=None):
        super().__init__(pack, cfg)
        self.direct_cfg = direct_cfg or {}
        self.direct_markup_count = 0
        self.direct_markup_details = []

    def _check_flat(self, date, price):
        """Override: add ROUTER->MARKUP check before existing logic."""
        if self.phase_start_date is None:
            return

        adx = self._adx(date)
        days_flat = (date - self.phase_start_date).days

        min_eval = self.cfg.FLAT_MIN_EVAL_DAYS
        if days_flat < min_eval:
            return

        # --- Existing PATH 1: From TOP SIGNAL ---
        if self.flat_from_top:
            # Check MARKDOWN first (highest priority)
            fib = self._fib_levels(date)
            from v13_phase_backtest_v8 import price_broke_fib_support
            lh_ll = self.pack.structure.lh_ll_streak(date, self.cfg.HH_HL_LOOKBACK)
            if lh_ll and not np.isnan(adx) and adx > self.cfg.ADX_THRESHOLD:
                if price_broke_fib_support(price, fib):
                    overext = self.pack.sma200.overextension_at(date)
                    note = f'FLAT->MARKDOWN: Post-top, LH_LL+ADX={adx:.0f}+Fib_break'
                    if not np.isnan(overext):
                        note += f' (SMA200={overext*100:+.0f}%)'
                    note += f' (flat {days_flat}d)'
                    self._change_phase(date, Phase.MARKDOWN, note)
                    return

            # --- NEW: Check MARKUP (V-bottom recovery) ---
            min_markup_days = self.direct_cfg.get('min_markup_days', 14)
            if days_flat >= min_markup_days:
                if self._check_direct_markup(date, price, days_flat):
                    return

            # Timeout
            if days_flat >= self.cfg.FLAT_MAX_EVAL_DAYS:
                self._change_phase(date, Phase.DCA,
                    f'FLAT->DCA: Post-top, no markdown signal after {days_flat}d')
            return

        # --- PATH 2 & 3: From RANGING EXIT or MARKDOWN ---
        # --- NEW: Check MARKUP here too ---
        min_markup_days = self.direct_cfg.get('min_markup_days_nontop', 
                                               self.direct_cfg.get('min_markup_days', 14))
        if days_flat >= min_markup_days:
            if self._check_direct_markup(date, price, days_flat):
                return

        # ADX ranging confirmation (existing)
        if not np.isnan(adx) and adx < self.cfg.FLAT_ADX_RANGING:
            self.adx_below_20_streak += 1
        else:
            self.adx_below_20_streak = 0

        if self.adx_below_20_streak >= self.cfg.FLAT_ADX_SUSTAINED_DAYS:
            self._change_phase(date, Phase.DCA,
                f'FLAT->DCA: Ranging confirmed (ADX<{self.cfg.FLAT_ADX_RANGING} for {self.adx_below_20_streak}d, flat {days_flat}d)')
            self.adx_below_20_streak = 0

    def _check_direct_markup(self, date, price, days_flat):
        """Check if conditions are met for direct ROUTER->MARKUP transition."""
        cfg = self.direct_cfg

        # Gate 1: HH_HL structure (required)
        hh_hl_min = cfg.get('hh_hl_min', 2)
        hh_hl = self.pack.structure.hh_hl_streak(date, self.cfg.HH_HL_LOOKBACK)
        if hh_hl < hh_hl_min:
            return False

        # Gate 2: Fib support (optional but default on)
        if cfg.get('require_fib', True):
            fib = self._fib_levels(date)
            if not price_near_fib_support(price, fib):
                return False

        # Gate 3: ADX trend strength (optional)
        adx_min = cfg.get('adx_min', 0)
        if adx_min > 0:
            adx = self._adx(date)
            if np.isnan(adx) or adx < adx_min:
                return False

        # Gate 4: SMA200 overextension check (optional — block if too extended)
        max_overext = cfg.get('max_sma200_overext', 0)
        if max_overext > 0:
            overext = self.pack.sma200.overextension_at(date)
            if not np.isnan(overext) and overext * 100 > max_overext:
                return False

        # Gate 5: CFGI sentiment (optional — require not in extreme fear)
        cfgi_min = cfg.get('cfgi_min', 0)
        if cfgi_min > 0:
            cfgi = self._cfgi(date)
            if np.isnan(cfgi) or cfgi < cfgi_min:
                return False

        # Gate 6: Bear bias check (optional — block during bear)
        if cfg.get('check_bear_bias', False):
            if self.shorts_enabled:
                return False

        # Gate 7: SMA50 above (optional — price must be above SMA50)
        if cfg.get('require_sma50_above', False):
            try:
                sma50 = self.pack.daily.loc[:date, 'sma50'].iloc[-1]
                close = self.pack.daily.loc[:date, 'close'].iloc[-1]
                if np.isnan(sma50) or close <= sma50:
                    return False
            except:
                return False

        # All gates passed — transition to MARKUP
        note = f'ROUTER->MARKUP: HH_HL={hh_hl}+Fib_support (direct, {days_flat}d in router)'
        self.direct_markup_count += 1
        self.direct_markup_details.append({
            'date': date, 'days_flat': days_flat, 'hh_hl': hh_hl
        })
        self._change_phase(date, Phase.MARKUP, note)
        return True


def run_variant(coins, direct_cfg, label):
    results = {}
    total_equity = 0
    total_direct = 0

    for coin in coins:
        pack = V13SignalPack(coin)
        cfg = V13Config()
        cfg.START_DATE = '2023-01-01'
        cfg.END_DATE = '2026-02-25'
        cfg.CAPITAL = 2500

        bt = V13RouterDirectMarkup(pack, cfg, direct_cfg=direct_cfg.copy())
        result = bt.run()
        if result is None:
            continue

        router_days = sum(1 for e in bt.equity_curve if e.get('phase') == Phase.FLAT)

        results[coin] = {
            'equity': result['final_equity'],
            'roi': result['roi'],
            'trades': result['total_trades'],
            'direct_markups': bt.direct_markup_count,
            'router_days': router_days,
        }
        total_equity += result['final_equity']
        total_direct += bt.direct_markup_count

    return results, total_equity, total_direct


def main():
    coins = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']

    variants = [
        ('BASELINE (no direct markup)', {}),
        # Basic: HH_HL + Fib
        ('HH_HL>=2 + Fib @14d', {'hh_hl_min': 2, 'min_markup_days': 14}),
        ('HH_HL>=1 + Fib @14d', {'hh_hl_min': 1, 'min_markup_days': 14}),
        ('HH_HL>=2 + Fib @7d', {'hh_hl_min': 2, 'min_markup_days': 7}),
        ('HH_HL>=2 + Fib @21d', {'hh_hl_min': 2, 'min_markup_days': 21}),
        # With ADX confirmation
        ('HH_HL>=2 + Fib + ADX>20 @14d', {'hh_hl_min': 2, 'adx_min': 20, 'min_markup_days': 14}),
        ('HH_HL>=2 + Fib + ADX>25 @14d', {'hh_hl_min': 2, 'adx_min': 25, 'min_markup_days': 14}),
        # With SMA200 overextension cap
        ('HH_HL>=2 + Fib + SMA200<20% @14d', {'hh_hl_min': 2, 'max_sma200_overext': 20, 'min_markup_days': 14}),
        ('HH_HL>=2 + Fib + SMA200<30% @14d', {'hh_hl_min': 2, 'max_sma200_overext': 30, 'min_markup_days': 14}),
        # With SMA50 above
        ('HH_HL>=2 + Fib + SMA50above @14d', {'hh_hl_min': 2, 'require_sma50_above': True, 'min_markup_days': 14}),
        # With CFGI
        ('HH_HL>=2 + Fib + CFGI>40 @14d', {'hh_hl_min': 2, 'cfgi_min': 40, 'min_markup_days': 14}),
        ('HH_HL>=2 + Fib + CFGI>50 @14d', {'hh_hl_min': 2, 'cfgi_min': 50, 'min_markup_days': 14}),
        # Combined best candidates
        ('HH_HL>=2 + Fib + ADX>20 + SMA200<20%', {'hh_hl_min': 2, 'adx_min': 20, 'max_sma200_overext': 20, 'min_markup_days': 14}),
        ('HH_HL>=2 + Fib + SMA50 + CFGI>40', {'hh_hl_min': 2, 'require_sma50_above': True, 'cfgi_min': 40, 'min_markup_days': 14}),
        # No Fib requirement
        ('HH_HL>=2 only @14d', {'hh_hl_min': 2, 'require_fib': False, 'min_markup_days': 14}),
        ('HH_HL>=2 + SMA50above @14d (no Fib)', {'hh_hl_min': 2, 'require_fib': False, 'require_sma50_above': True, 'min_markup_days': 14}),
        # Top-only vs all entries
        ('HH_HL>=2 + Fib @14d (nontop@21d)', {'hh_hl_min': 2, 'min_markup_days': 14, 'min_markup_days_nontop': 21}),
        # Bear bias block
        ('HH_HL>=2 + Fib + NoBear @14d', {'hh_hl_min': 2, 'check_bear_bias': True, 'min_markup_days': 14}),
    ]

    print("=" * 140)
    print("  ROUTER PHASE 4: Direct ROUTER->MARKUP Path Sweep")
    print("=" * 140)

    baseline_equity = None
    baseline_router = None
    all_results = []

    for label, direct_cfg in variants:
        results, total_eq, total_direct = run_variant(coins, direct_cfg, label)
        total_router = sum(r['router_days'] for r in results.values())

        if baseline_equity is None:
            baseline_equity = total_eq
            baseline_router = total_router

        delta = total_eq - baseline_equity
        days_saved = baseline_router - total_router
        all_results.append((label, results, total_eq, delta, total_direct, total_router, days_saved))

    print(f"\n{'Variant':<45} {'Total$':>10} {'Delta':>8} {'DM#':>4} {'RtrDays':>8} {'Saved':>6}  ", end="")
    for c in coins:
        print(f" {c:>7}", end="")
    print()
    print("-" * 140)

    for label, results, total_eq, delta, total_dm, router_d, days_saved in all_results:
        d_str = f"{delta:+,.0f}" if delta != 0 else "BASE"
        print(f"{label:<45} ${total_eq:>9,.0f} {d_str:>8} {total_dm:>4} {router_d:>8} {days_saved:>+6}  ", end="")
        for c in coins:
            if c in results:
                coin_delta = results[c]['equity'] - all_results[0][1].get(c, {}).get('equity', 0)
                print(f" {coin_delta:>+7,.0f}", end="")
            else:
                print(f" {'N/A':>7}", end="")
        print()


if __name__ == '__main__':
    main()
