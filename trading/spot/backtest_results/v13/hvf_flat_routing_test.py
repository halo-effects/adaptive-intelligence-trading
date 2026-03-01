"""
HVF-based FLAT routing optimization — Backtest Comparison
Tests: If HVF composite > 0.3 AND price > SMA50 after 14d → route FLAT→DCA early
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack
from run_new_coins_profiles import make_config


class V13HVFRouting(V13BacktestV8):
    """Modified V13 with HVF fast-track in FLAT phase."""

    def __init__(self, pack, config=None):
        super().__init__(pack, config)
        # Precompute SMA50 from daily candles
        self.sma50 = self.daily['close'].rolling(50).mean()

    def _sma50_at(self, date):
        mask = self.sma50.index <= date
        if not mask.any():
            return np.nan
        return self.sma50.loc[mask].iloc[-1]

    def _check_flat(self, date, price):
        """Override with HVF fast-track added before timeout/ADX checks."""
        adx = self._adx(date)
        days_flat = (date - self.phase_start_date).days if self.phase_start_date else 0

        if days_flat < self.cfg.FLAT_MIN_EVAL_DAYS:
            return

        # PATH 1: From TOP SIGNAL
        if self.flat_from_top:
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

            # === HVF FAST-TRACK (PATH 1) ===
            hvf = self._hvf(date)
            sma50 = self._sma50_at(date)
            if hvf > 0.3 and not np.isnan(sma50) and price > sma50:
                self._change_phase(date, Phase.DCA,
                    f'FLAT->DCA: HVF fast-track ({hvf:.2f}>0.3, price>{sma50:.0f} SMA50, flat {days_flat}d)')
                return

            if days_flat >= self.cfg.FLAT_MAX_EVAL_DAYS:
                self._change_phase(date, Phase.DCA,
                    f'FLAT->DCA: Post-top, no markdown signal after {days_flat}d')
            return

        # PATH 2 & 3: From RANGING EXIT or MARKDOWN
        # === HVF FAST-TRACK (PATH 2/3) ===
        hvf = self._hvf(date)
        sma50 = self._sma50_at(date)
        if hvf > 0.3 and not np.isnan(sma50) and price > sma50:
            self._change_phase(date, Phase.DCA,
                f'FLAT->DCA: HVF fast-track ({hvf:.2f}>0.3, price>{sma50:.0f} SMA50, flat {days_flat}d)')
            return

        # Original ADX ranging logic
        if not np.isnan(adx) and adx < self.cfg.FLAT_ADX_RANGING:
            self.adx_below_20_streak += 1
        else:
            self.adx_below_20_streak = 0

        ranging_confirmed = self.adx_below_20_streak >= self.cfg.FLAT_ADX_SUSTAINED_DAYS
        if not ranging_confirmed:
            return

        self._change_phase(date, Phase.DCA,
            f'FLAT->DCA: Ranging confirmed (ADX<{self.cfg.FLAT_ADX_RANGING} for {self.adx_below_20_streak}d, flat {days_flat}d)')
        self.adx_below_20_streak = 0


def extract_phase_stats(result):
    """Extract FLAT/DCA phase statistics from phase log."""
    phases = result['phases']
    flat_durations = []
    dca_durations = []
    dca_count = 0
    markup_count = 0

    for i, p in enumerate(phases):
        if p['to'] == 'FLAT':
            # Find when FLAT ended
            if i + 1 < len(phases):
                duration = (phases[i+1]['date'] - p['date']).days
                flat_durations.append({'start': p['date'], 'days': duration, 'reason': p.get('reason','')})
        elif p['to'] == 'DCA':
            dca_count += 1
            if i + 1 < len(phases):
                duration = (phases[i+1]['date'] - p['date']).days
                dca_durations.append({'start': p['date'], 'days': duration})
        elif p['to'] == 'MARKUP':
            markup_count += 1

    return {
        'flat_windows': flat_durations,
        'flat_count': len(flat_durations),
        'flat_total_days': sum(f['days'] for f in flat_durations),
        'flat_avg_days': np.mean([f['days'] for f in flat_durations]) if flat_durations else 0,
        'dca_windows': dca_durations,
        'dca_count': dca_count,
        'dca_total_days': sum(d['days'] for d in dca_durations),
        'markup_entries': markup_count,
    }


def run_comparison():
    coins = ['ETH', 'BTC', 'SOL']
    cfg = make_config('high')

    print("=" * 100)
    print("  V13 HVF FLAT ROUTING OPTIMIZATION — BACKTEST COMPARISON")
    print("  Rule: HVF > 0.3 AND price > SMA50 → fast-track FLAT→DCA (after 14d min eval)")
    print("  Coins: ETH, BTC, SOL | Profile: high | Period: Oct 2020 → Feb 2026")
    print("=" * 100)

    all_baseline = {}
    all_modified = {}

    for coin in coins:
        print(f"\n{'─'*50}")
        print(f"  Running {coin}/USDC...")
        print(f"{'─'*50}")

        pack = V13SignalPack(coin)

        # Baseline
        bt_base = V13BacktestV8(pack, make_config('high'))
        r_base = bt_base.run()

        # Modified (need fresh pack since signals may have state)
        pack2 = V13SignalPack(coin)
        bt_mod = V13HVFRouting(pack2, make_config('high'))
        r_mod = bt_mod.run()

        all_baseline[coin] = r_base
        all_modified[coin] = r_mod

    # ── COMPARISON TABLES ──
    print("\n" + "=" * 100)
    print("  RESULTS COMPARISON")
    print("=" * 100)

    # Per-coin summary
    header = f"{'Coin':<6} {'Metric':<20} {'Baseline':>12} {'Modified':>12} {'Delta':>10}"
    print(f"\n{header}")
    print("─" * 62)

    for coin in coins:
        rb = all_baseline[coin]
        rm = all_modified[coin]
        if not rb or not rm:
            print(f"  {coin}: SKIP")
            continue

        metrics = [
            ('Closed ROI %', rb['closed_roi'], rm['closed_roi']),
            ('Total ROI %', rb['roi'], rm['roi']),
            ('Final Equity $', rb['final_equity'], rm['final_equity']),
            ('Max Drawdown %', rb['max_drawdown'], rm['max_drawdown']),
            ('Closed Trades', rb['closed_trades'], rm['closed_trades']),
            ('Markup Cycles', rb['markup_cycles'], rm['markup_cycles']),
            ('DCA Trades', rb['dca_trades'], rm['dca_trades']),
            ('Win Rate %', rb['win_rate'], rm['win_rate']),
            ('Time FLAT %', rb['time_flat_pct'], rm['time_flat_pct']),
            ('Time DCA %', rb['time_dca_pct'], rm['time_dca_pct']),
            ('Time MARKUP %', rb['time_markup_pct'], rm['time_markup_pct']),
        ]

        for i, (name, vb, vm) in enumerate(metrics):
            delta = vm - vb
            sign = '+' if delta > 0 else ''
            c = coin if i == 0 else ''
            if isinstance(vb, float):
                print(f"{c:<6} {name:<20} {vb:>12.1f} {vm:>12.1f} {sign}{delta:>9.1f}")
            else:
                print(f"{c:<6} {name:<20} {vb:>12} {vm:>12} {sign}{delta:>9}")
        print()

    # ── FLAT PHASE DETAILS ──
    print("\n" + "=" * 100)
    print("  FLAT PHASE ANALYSIS")
    print("=" * 100)

    for coin in coins:
        rb = all_baseline[coin]
        rm = all_modified[coin]
        if not rb or not rm:
            continue

        sb = extract_phase_stats(rb)
        sm = extract_phase_stats(rm)

        print(f"\n  {coin}:")
        print(f"    FLAT windows:     {sb['flat_count']} baseline → {sm['flat_count']} modified")
        print(f"    FLAT total days:  {sb['flat_total_days']} baseline → {sm['flat_total_days']} modified  (saved {sb['flat_total_days'] - sm['flat_total_days']}d)")
        print(f"    FLAT avg days:    {sb['flat_avg_days']:.1f} baseline → {sm['flat_avg_days']:.1f} modified")
        print(f"    DCA windows:      {sb['dca_count']} baseline → {sm['dca_count']} modified")
        print(f"    DCA total days:   {sb['dca_total_days']} baseline → {sm['dca_total_days']} modified")
        print(f"    MARKUP entries:   {sb['markup_entries']} baseline → {sm['markup_entries']} modified")

        # Show each FLAT window side-by-side
        print(f"\n    FLAT window details:")
        print(f"    {'#':<4} {'Baseline':^30} {'Modified':^30}")
        max_windows = max(len(sb['flat_windows']), len(sm['flat_windows']))
        for i in range(max_windows):
            bw = sb['flat_windows'][i] if i < len(sb['flat_windows']) else None
            mw = sm['flat_windows'][i] if i < len(sm['flat_windows']) else None
            bs = f"{bw['start'].strftime('%Y-%m-%d')} ({bw['days']}d)" if bw else "—"
            ms = f"{mw['start'].strftime('%Y-%m-%d')} ({mw['days']}d)" if mw else "—"
            print(f"    {i+1:<4} {bs:^30} {ms:^30}")

    # ── PHASE TIMELINE DIFF ──
    print("\n" + "=" * 100)
    print("  PHASE TIMELINE — WHERE ROUTING CHANGED")
    print("=" * 100)

    for coin in coins:
        rb = all_baseline[coin]
        rm = all_modified[coin]
        if not rb or not rm:
            continue

        print(f"\n  {coin}:")
        # Find HVF fast-track transitions in modified
        hvf_transitions = [p for p in rm['phases'] if 'HVF fast-track' in p.get('reason', '')]
        if hvf_transitions:
            for t in hvf_transitions:
                print(f"    ★ {t['date'].strftime('%Y-%m-%d')}: {t['reason']}")
                # Find what baseline did at that time
                for bp in rb['phases']:
                    if abs((bp['date'] - t['date']).days) < 60 and bp['to'] == 'DCA' and 'FLAT' in bp.get('reason', ''):
                        print(f"      Baseline: {bp['date'].strftime('%Y-%m-%d')}: {bp['reason']}")
                        days_saved = (bp['date'] - t['date']).days
                        if days_saved > 0:
                            print(f"      → Saved {days_saved} days")
                        break
        else:
            print("    No HVF fast-track triggers")

    # ── REGRESSION CHECK ──
    print("\n" + "=" * 100)
    print("  REGRESSION CHECK")
    print("=" * 100)

    regressions = []
    for coin in coins:
        rb = all_baseline[coin]
        rm = all_modified[coin]
        if not rb or not rm:
            continue
        delta_roi = rm['closed_roi'] - rb['closed_roi']
        if delta_roi < -1.0:  # More than 1% worse
            regressions.append((coin, delta_roi))
            print(f"  ⚠️  {coin}: REGRESSION — closed ROI {delta_roi:+.1f}%")
        else:
            print(f"  ✅ {coin}: OK (delta {delta_roi:+.1f}%)")

    # ── RECOMMENDATION ──
    print("\n" + "=" * 100)
    print("  RECOMMENDATION")
    print("=" * 100)

    total_flat_saved = sum(
        extract_phase_stats(all_baseline[c])['flat_total_days'] - extract_phase_stats(all_modified[c])['flat_total_days']
        for c in coins if all_baseline[c] and all_modified[c]
    )
    avg_roi_delta = np.mean([
        all_modified[c]['closed_roi'] - all_baseline[c]['closed_roi']
        for c in coins if all_baseline[c] and all_modified[c]
    ])

    print(f"\n  Total FLAT days saved across all coins: {total_flat_saved}")
    print(f"  Average closed ROI change: {avg_roi_delta:+.1f}%")

    if regressions:
        print(f"\n  ⚠️  REGRESSIONS found in {len(regressions)} coin(s). Review before implementing.")
    elif total_flat_saved > 0 and avg_roi_delta >= 0:
        print(f"\n  ✅ RECOMMEND: HVF fast-track is a net positive.")
        print(f"     Saves {total_flat_saved} days of idle FLAT time with no ROI regression.")
    elif total_flat_saved > 0 and avg_roi_delta > -1:
        print(f"\n  🟡 MARGINAL: Saves time but small ROI impact. Consider implementing with monitoring.")
    else:
        print(f"\n  ❌ NOT RECOMMENDED: No clear benefit or negative ROI impact.")


if __name__ == '__main__':
    run_comparison()
