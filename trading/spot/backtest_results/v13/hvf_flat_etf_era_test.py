"""
HVF FLAT routing — ETF ERA ONLY (Jan 2023 → Feb 2026)
Tests multiple filter combos: baseline vs HVF fast-track variants
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack
from run_new_coins_profiles import make_config

ETF_START = pd.Timestamp('2023-01-01')


class V13HVF_SMA50(V13BacktestV8):
    """HVF>0.3 + SMA50_ABOVE"""
    HVF_THRESH = 0.3

    def __init__(self, pack, config=None):
        super().__init__(pack, config)
        self.sma50 = self.daily['close'].rolling(50).mean()

    def _sma_at(self, sma_series, date):
        mask = sma_series.index <= date
        return sma_series.loc[mask].iloc[-1] if mask.any() else np.nan

    def _check_flat(self, date, price):
        adx = self._adx(date)
        days_flat = (date - self.phase_start_date).days if self.phase_start_date else 0
        if days_flat < self.cfg.FLAT_MIN_EVAL_DAYS:
            return

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

            # HVF fast-track
            if self._hvf_pass(date, price, days_flat):
                return

            if days_flat >= self.cfg.FLAT_MAX_EVAL_DAYS:
                self._change_phase(date, Phase.DCA,
                    f'FLAT->DCA: Post-top, no markdown signal after {days_flat}d')
            return

        # PATH 2/3
        if self._hvf_pass(date, price, days_flat):
            return

        if not np.isnan(adx) and adx < self.cfg.FLAT_ADX_RANGING:
            self.adx_below_20_streak += 1
        else:
            self.adx_below_20_streak = 0

        if self.adx_below_20_streak >= self.cfg.FLAT_ADX_SUSTAINED_DAYS:
            self._change_phase(date, Phase.DCA,
                f'FLAT->DCA: Ranging confirmed (ADX<{self.cfg.FLAT_ADX_RANGING} for {self.adx_below_20_streak}d, flat {days_flat}d)')
            self.adx_below_20_streak = 0

    def _hvf_pass(self, date, price, days_flat):
        hvf = self._hvf(date)
        sma = self._sma_at(self.sma50, date)
        if hvf > self.HVF_THRESH and not np.isnan(sma) and price > sma:
            self._change_phase(date, Phase.DCA,
                f'FLAT->DCA: HVF fast-track ({hvf:.2f}>{self.HVF_THRESH}, price>{sma:.0f} SMA50, flat {days_flat}d)')
            return True
        return False


class V13HVF_SMA200(V13HVF_SMA50):
    """HVF>0.3 + SMA200_ABOVE"""
    def __init__(self, pack, config=None):
        super().__init__(pack, config)
        self.sma200 = self.daily['close'].rolling(200).mean()

    def _hvf_pass(self, date, price, days_flat):
        hvf = self._hvf(date)
        sma = self._sma_at(self.sma200, date)
        if hvf > self.HVF_THRESH and not np.isnan(sma) and price > sma:
            self._change_phase(date, Phase.DCA,
                f'FLAT->DCA: HVF fast-track ({hvf:.2f}>{self.HVF_THRESH}, price>{sma:.0f} SMA200, flat {days_flat}d)')
            return True
        return False


class V13HVF_SMA50_CFGI(V13HVF_SMA50):
    """HVF>0.3 + SMA50_ABOVE + CFGI>40"""
    def _hvf_pass(self, date, price, days_flat):
        hvf = self._hvf(date)
        sma = self._sma_at(self.sma50, date)
        cfgi = self._cfgi(date)
        if (hvf > self.HVF_THRESH and not np.isnan(sma) and price > sma
                and not np.isnan(cfgi) and cfgi > 40):
            self._change_phase(date, Phase.DCA,
                f'FLAT->DCA: HVF fast-track ({hvf:.2f}>{self.HVF_THRESH}, price>{sma:.0f} SMA50, CFGI={cfgi:.0f}>40, flat {days_flat}d)')
            return True
        return False


class V13HVF04_SMA50(V13HVF_SMA50):
    """HVF>0.4 + SMA50_ABOVE"""
    HVF_THRESH = 0.4


def filter_result_to_era(result, start=ETF_START):
    """Filter results to only count from start date. Uses equity curve for ROI."""
    # ROI from equity curve
    ec = result['equity_curve']
    mask = ec.index >= start
    if mask.any():
        eq_start = ec.loc[mask].iloc[0]['equity']
        eq_end = ec.iloc[-1]['equity']
        era_roi = (eq_end / eq_start - 1) * 100
    else:
        era_roi = 0.0

    # Trades from era
    trades_era = [t for t in result.get('trades', []) if t['date'] >= start]
    buys_era = [t for t in trades_era if 'BUY' in t.get('action', '')]
    sells_era = [t for t in trades_era if 'SELL' in t.get('action', '') or 'CLOSE' in t.get('action', '')]

    phases = [p for p in result['phases'] if p['date'] >= start]
    all_phases = result['phases']
    end_date = result.get('end', ec.index[-1])
    phase_days = {'FLAT': 0, 'DCA': 0, 'MARKUP': 0, 'MARKDOWN': 0}
    for i, p in enumerate(all_phases):
        next_date = all_phases[i+1]['date'] if i+1 < len(all_phases) else end_date
        seg_start = max(p['date'], start)
        seg_end = next_date
        if seg_end <= start:
            continue
        days = (seg_end - seg_start).days
        if days > 0:
            phase_days[p['to']] = phase_days.get(p['to'], 0) + days

    total_days = sum(phase_days.values()) or 1
    return {
        'era_roi': era_roi,
        'era_equity_start': eq_start if mask.any() else 0,
        'era_equity_end': eq_end if mask.any() else 0,
        'total_roi': result['roi'],
        'closed_roi': result['closed_roi'],
        'era_buys': len(buys_era),
        'era_sells': len(sells_era),
        'era_trades': len(trades_era),
        'phases': phases,
        'all_phases': all_phases,
        'phase_days': phase_days,
        'total_days': total_days,
        'time_flat_pct': 100 * phase_days.get('FLAT', 0) / total_days,
        'time_dca_pct': 100 * phase_days.get('DCA', 0) / total_days,
        'time_markup_pct': 100 * phase_days.get('MARKUP', 0) / total_days,
        'time_markdown_pct': 100 * phase_days.get('MARKDOWN', 0) / total_days,
        'final_equity': result['final_equity'],
        'max_drawdown': result['max_drawdown'],
    }


def flat_stats_from_era(result, start=ETF_START):
    """FLAT window stats from era start."""
    all_phases = result.get('all_phases', result['phases'])
    end_date = pd.Timestamp.now()
    flat_windows = []
    for i, p in enumerate(all_phases):
        if p['to'] != 'FLAT':
            continue
        next_date = all_phases[i+1]['date'] if i+1 < len(all_phases) else end_date
        if next_date <= start:
            continue
        seg_start = max(p['date'], start)
        days = (next_date - seg_start).days
        if days > 0:
            flat_windows.append({
                'start': seg_start,
                'end': next_date,
                'days': days,
                'reason': p.get('reason', ''),
                # Find exit reason
                'exit': all_phases[i+1].get('reason', '') if i+1 < len(all_phases) else ''
            })
    return flat_windows


def run_all():
    coins = ['ETH', 'BTC', 'SOL']
    variants = {
        'BASELINE': V13BacktestV8,
        'HVF>0.3+SMA50': V13HVF_SMA50,
        'HVF>0.3+SMA200': V13HVF_SMA200,
        'HVF>0.3+SMA50+CFGI>40': V13HVF_SMA50_CFGI,
        'HVF>0.4+SMA50': V13HVF04_SMA50,
    }

    print("=" * 110)
    print("  V13 HVF FLAT ROUTING — ETF ERA (Jan 2023 → Feb 2026)")
    print("  Coins: ETH, BTC, SOL | Profile: high")
    print("=" * 110)

    # Run all
    results = {}  # {(coin, variant_name): filtered_result}
    raw_results = {}
    for coin in coins:
        for vname, vcls in variants.items():
            print(f"  Running {coin} / {vname}...", flush=True)
            pack = V13SignalPack(coin)
            cfg = make_config('high')
            bt = vcls(pack, cfg)
            raw = bt.run()
            raw_results[(coin, vname)] = raw
            results[(coin, vname)] = filter_result_to_era(raw)
    print()

    # ── TABLE 1: ROI & TRADES ──
    print("=" * 110)
    print("  ETF ERA ROI & TRADES (Jan 2023+)")
    print("=" * 110)
    vnames = list(variants.keys())
    header = f"{'Coin':<6}" + "".join(f" {v:>22}" for v in vnames)
    print(f"\n  ERA ROI % (equity-based, Jan 2023 →):")
    print(f"  {header}")
    print(f"  {'─'*6}" + "─"*22*len(vnames))
    for coin in coins:
        row = f"  {coin:<6}"
        base_roi = results[(coin, 'BASELINE')]['era_roi']
        for v in vnames:
            r = results[(coin, v)]['era_roi']
            delta = r - base_roi
            if v == 'BASELINE':
                row += f" {r:>22.1f}"
            else:
                row += f" {r:>14.1f} ({delta:+.1f})"
        print(row)

    print(f"\n  Full-period Closed ROI %:")
    print(f"  {header}")
    print(f"  {'─'*6}" + "─"*22*len(vnames))
    for coin in coins:
        row = f"  {coin:<6}"
        base_roi = results[(coin, 'BASELINE')]['closed_roi']
        for v in vnames:
            r = results[(coin, v)]['closed_roi']
            delta = r - base_roi
            if v == 'BASELINE':
                row += f" {r:>22.1f}"
            else:
                row += f" {r:>14.1f} ({delta:+.1f})"
        print(row)

    print(f"\n  Era Trades (buys/sells from 2023+):")
    print(f"  {header}")
    print(f"  {'─'*6}" + "─"*22*len(vnames))
    for coin in coins:
        row = f"  {coin:<6}"
        for v in vnames:
            r = results[(coin, v)]
            row += f" {r['era_buys']:>9}b/{r['era_sells']}s"
        print(row)

    # ── TABLE 2: TIME IN PHASE ──
    print(f"\n  Time in FLAT % (2023+):")
    print(f"  {header}")
    print(f"  {'─'*6}" + "─"*22*len(vnames))
    for coin in coins:
        row = f"  {coin:<6}"
        base_flat = results[(coin, 'BASELINE')]['time_flat_pct']
        for v in vnames:
            r = results[(coin, v)]['time_flat_pct']
            delta = r - base_flat
            if v == 'BASELINE':
                row += f" {r:>22.1f}"
            else:
                row += f" {r:>14.1f} ({delta:+.1f})"
        print(row)

    print(f"\n  Time in DCA % (2023+):")
    print(f"  {header}")
    print(f"  {'─'*6}" + "─"*22*len(vnames))
    for coin in coins:
        row = f"  {coin:<6}"
        for v in vnames:
            r = results[(coin, v)]['time_dca_pct']
            row += f" {r:>22.1f}"
        print(row)

    # ── TABLE 3: FLAT DAYS SAVED ──
    print(f"\n\n  FLAT Days (2023+):")
    print(f"  {'Coin':<6} {'BASELINE':>10}" + "".join(f" {v:>22}" for v in vnames[1:]))
    print(f"  {'─'*6}{'─'*10}" + "─"*22*(len(vnames)-1))
    for coin in coins:
        base_days = results[(coin, 'BASELINE')]['phase_days'].get('FLAT', 0)
        row = f"  {coin:<6} {base_days:>10}"
        for v in vnames[1:]:
            d = results[(coin, v)]['phase_days'].get('FLAT', 0)
            saved = base_days - d
            row += f" {d:>12} (save {saved:>3}d)"
        print(row)

    # ── FLAT WINDOW DETAILS ──
    print(f"\n\n{'='*110}")
    print("  FLAT WINDOW DETAILS (2023+) — Baseline vs Each Variant")
    print(f"{'='*110}")
    for coin in coins:
        print(f"\n  {coin}:")
        base_flats = flat_stats_from_era(results[(coin, 'BASELINE')])
        print(f"    BASELINE flat windows: {len(base_flats)}")
        for i, fw in enumerate(base_flats):
            print(f"      #{i+1}: {fw['start'].strftime('%Y-%m-%d')} → {fw['end'].strftime('%Y-%m-%d')} ({fw['days']}d)")

        for v in vnames[1:]:
            mod_flats = flat_stats_from_era(results[(coin, v)])
            print(f"    {v} flat windows: {len(mod_flats)}")
            for i, fw in enumerate(mod_flats):
                marker = " ★HVF" if 'HVF' in fw.get('exit', '') else ""
                print(f"      #{i+1}: {fw['start'].strftime('%Y-%m-%d')} → {fw['end'].strftime('%Y-%m-%d')} ({fw['days']}d){marker}")

    # ── HVF TRIGGERS TIMELINE ──
    print(f"\n\n{'='*110}")
    print("  HVF FAST-TRACK TRIGGERS (2023+)")
    print(f"{'='*110}")
    for coin in coins:
        print(f"\n  {coin}:")
        for v in vnames[1:]:
            raw = raw_results[(coin, v)]
            hvf_triggers = [p for p in raw['phases'] if p['date'] >= ETF_START and 'HVF fast-track' in p.get('reason', '')]
            if hvf_triggers:
                print(f"    {v}:")
                for t in hvf_triggers:
                    print(f"      {t['date'].strftime('%Y-%m-%d')}: {t['reason']}")
            else:
                print(f"    {v}: No triggers")

    # ── REGRESSION CHECK ──
    print(f"\n\n{'='*110}")
    print("  REGRESSION CHECK (vs BASELINE, 2023+)")
    print(f"{'='*110}")
    for v in vnames[1:]:
        print(f"\n  {v}:")
        any_reg = False
        for coin in coins:
            delta = results[(coin, v)]['era_roi'] - results[(coin, 'BASELINE')]['era_roi']
            if delta < -1.0:
                print(f"    ⚠️  {coin}: REGRESSION {delta:+.1f}%")
                any_reg = True
            else:
                print(f"    ✅ {coin}: {delta:+.1f}%")
        if not any_reg:
            print(f"    → No regressions!")

    # ── SUMMARY / RECOMMENDATION ──
    print(f"\n\n{'='*110}")
    print("  SUMMARY — BEST FILTER COMBO")
    print(f"{'='*110}")
    print(f"\n  {'Variant':<28} {'Avg ROI Δ':>10} {'Total FLAT saved':>18} {'Regressions':>12}")
    print(f"  {'─'*28} {'─'*10} {'─'*18} {'─'*12}")
    for v in vnames[1:]:
        avg_delta = np.mean([results[(c,v)]['era_roi'] - results[(c,'BASELINE')]['era_roi'] for c in coins])
        flat_saved = sum(
            results[(c,'BASELINE')]['phase_days'].get('FLAT',0) - results[(c,v)]['phase_days'].get('FLAT',0)
            for c in coins
        )
        regs = sum(1 for c in coins if results[(c,v)]['era_roi'] - results[(c,'BASELINE')]['era_roi'] < -1.0)
        print(f"  {v:<28} {avg_delta:>+10.1f}% {flat_saved:>15}d {regs:>12}")

    print()


if __name__ == '__main__':
    run_all()
