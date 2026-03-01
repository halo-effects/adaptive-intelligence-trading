"""
Conviction-Weighted test WITHOUT Spring requirement.
4 signals: 2D death cross + below SMA200 + CFGI<35 + Weekly RSI(7)<30
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import numpy as np
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack
from _conviction_weighted_test import BottomStackDetector

class NoSpringConvictionV13(V13BacktestV8):
    def __init__(self, pack, config=None, min_conviction=2, graduated=False):
        super().__init__(pack, config)
        self.min_conviction = min_conviction
        self.graduated = graduated
        self.bottom_detector = BottomStackDetector(pack.coin)
        self.conviction_triggers = []

    def _get_score_no_spring(self, date):
        """Get conviction from 4 signals (no Spring required)."""
        det = self.bottom_detector
        if det.daily is None or date not in det.daily.index:
            return 0, {}
        signals = {}
        score = 0
        # 1: 2D death cross
        if hasattr(det, 'death_cross_2d') and date in det.death_cross_2d.index:
            signals['dc'] = bool(det.death_cross_2d.loc[date])
            if signals['dc']: score += 1
        # 2: below SMA200
        price = det.daily.loc[date, 'close']
        sma = det.daily.loc[date, 'sma200']
        signals['sma'] = not pd.isna(sma) and price < sma
        if signals['sma']: score += 1
        # 3: CFGI < 35
        cfgi_val = np.nan
        if det.cfgi is not None:
            cdates = det.cfgi.index[det.cfgi.index <= date]
            if len(cdates):
                cfgi_val = det.cfgi.loc[cdates[-1], 'cfgi']
        signals['cfgi'] = not pd.isna(cfgi_val) and cfgi_val < 35
        if signals['cfgi']: score += 1
        signals['cfgi_val'] = cfgi_val
        # 4: Weekly RSI(7) < 30
        rsi_val = np.nan
        if hasattr(det, 'weekly_rsi') and date in det.weekly_rsi.index:
            rsi_val = det.weekly_rsi.loc[date]
        signals['rsi'] = not pd.isna(rsi_val) and rsi_val < 30
        if signals['rsi']: score += 1
        signals['rsi_val'] = rsi_val
        signals['price'] = price
        return score, signals

    def _check_flat(self, date, price):
        score, signals = self._get_score_no_spring(date)
        if score >= self.min_conviction:
            self._deploy(date, score, signals)
            return
        super()._check_flat(date, price)

    def _deploy(self, date, score, signals):
        price = self._price(date)
        self.conviction_triggers.append({
            'date': date, 'coin': self.coin, 'score': score, 'signals': signals, 'price': price
        })
        if self.graduated:
            if score >= 4: tiers = [1, 2, 3]; tag = "T1+T2+T3"
            elif score >= 3: tiers = [1, 2]; tag = "T1+T2"
            else: tiers = [1]; tag = "T1"
        else:
            tiers = [1]; tag = "T1"
            if self.min_conviction <= 3 and score >= 4:
                tiers = [1, 2]; tag = "T1+T2"
            if self.min_conviction <= 3 and score >= 4:
                pass  # keep simple per-variant

        # For non-graduated: just deploy based on variant
        if not self.graduated:
            tag = "T1"
            tiers = [1]

        self._change_phase(date, Phase.MARKUP, f'CONVICTION {score}/4 -> {tag}')
        for t in tiers:
            pct = [0, self.cfg.TIER1_PCT, self.cfg.TIER2_PCT, self.cfg.TIER3_PCT][t]
            self._buy(date, pct, t)
        self.early_warning_date = None
        self.failsafe_armed = False
        self.peak_2w_k = 0

class GraduatedNoSpring(NoSpringConvictionV13):
    def __init__(self, pack, config=None):
        super().__init__(pack, config, min_conviction=2, graduated=True)

def main():
    coins = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']
    cap = 2500

    variants = [
        ('BASELINE', None),
        ('Conv >=2/4 -> T1', {'min_conviction': 2}),
        ('Conv >=3/4 -> T1', {'min_conviction': 3}),
        ('Conv 4/4 -> T1', {'min_conviction': 4}),
        ('Graduated (2->T1, 3->T1T2, 4->all)', {'graduated': True}),
    ]

    print("Conviction-Weighted (No Spring) Backtest")
    print("4 signals: 2D Death Cross + Below SMA200 + CFGI<35 + Weekly RSI(7)<30")
    print("="*90)

    results = []
    for vname, vopts in variants:
        print(f"\n{vname}...")
        row = {'name': vname, 'coins': {}, 'total': 0, 'triggers': []}
        for c in coins:
            try:
                pack = V13SignalPack(c)
                cfg = V13Config()
                cfg.CAPITAL = cap
                cfg.TIER1_PCT = 0.60
                cfg.TIER2_PCT = 0.20
                cfg.TIER3_PCT = 0.10

                if vopts is None:
                    bt = V13BacktestV8(pack, cfg)
                elif vopts.get('graduated'):
                    bt = GraduatedNoSpring(pack, cfg)
                else:
                    bt = NoSpringConvictionV13(pack, cfg, min_conviction=vopts['min_conviction'])

                res = bt.run()
                val = res['final_equity'] if res else cap
                row['coins'][c] = val
                row['total'] += val
                if hasattr(bt, 'conviction_triggers'):
                    row['triggers'].extend(bt.conviction_triggers)
                print(f"  {c}: ${val:,.0f}", end="")
                if hasattr(bt, 'conviction_triggers') and bt.conviction_triggers:
                    print(f"  ({len(bt.conviction_triggers)} triggers)", end="")
                print()
            except Exception as e:
                print(f"  {c}: ERROR {e}")
                row['coins'][c] = cap
                row['total'] += cap
        results.append(row)

    # Summary
    print(f"\n{'='*90}")
    print(f"{'Variant':<42} {'Total':>8} {'Delta':>8} {'Trig':>5}  ETH      SOL      BTC      LINK     XRP")
    print("-"*110)
    base = results[0]['total']
    for r in results:
        d = r['total'] - base
        ds = f"+{d:,.0f}" if d >= 0 else f"{d:,.0f}"
        if r['name'] == 'BASELINE': ds = "  BASE"
        print(f"{r['name']:<42} ${r['total']:>7,.0f} {ds:>8} {len(r['triggers']):>5}", end="")
        for c in coins:
            print(f"  ${r['coins'].get(c, cap):>6,.0f}", end="")
        print()

    # Trigger details
    all_trigs = []
    for r in results:
        if r['name'] != 'BASELINE':
            all_trigs.extend(r['triggers'])
    if all_trigs:
        print(f"\nTRIGGER EVENTS:")
        print(f"  {'Date':<12} {'Coin':<6} {'Score':<6} {'DC':>3} {'SMA':>4} {'CFGI':>5} {'RSI':>5}  CFGI_val  RSI_val  Price")
        print("  " + "-"*80)
        seen = set()
        for t in sorted(all_trigs, key=lambda x: (x['date'], x['coin'])):
            key = (str(t['date'])[:10], t['coin'])
            if key in seen: continue
            seen.add(key)
            s = t['signals']
            print(f"  {str(t['date'])[:10]:<12} {t['coin']:<6} {t['score']}/4   "
                  f"{'Y' if s.get('dc') else '-':>3} {'Y' if s.get('sma') else '-':>4} "
                  f"{'Y' if s.get('cfgi') else '-':>5} {'Y' if s.get('rsi') else '-':>5}  "
                  f"{s.get('cfgi_val', 0):>6.0f}    {s.get('rsi_val', 0):>5.1f}  ${t['price']:>9.2f}")

if __name__ == '__main__':
    main()
