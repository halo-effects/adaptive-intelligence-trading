"""
Conviction-Weighted test - ONLY fires after MARKDOWN -> ROUTER transition.
4 signals: 2D death cross + below SMA200 + CFGI<35 + Weekly RSI(7)<30
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import numpy as np
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack
from _conviction_weighted_test import BottomStackDetector


class PostMarkdownConvictionV13(V13BacktestV8):
    def __init__(self, pack, config=None, min_conviction=2, graduated=False):
        super().__init__(pack, config)
        self.min_conviction = min_conviction
        self.graduated = graduated
        self.bottom_detector = BottomStackDetector(pack.coin)
        self.conviction_triggers = []
        self._prev_phase = None  # track what phase we came from
        self._came_from_markdown = False

    def _change_phase(self, date, new_phase, reason=""):
        """Override to track phase transitions."""
        old_phase = self.phase
        super()._change_phase(date, new_phase, reason)
        # If we just entered ROUTER from MARKDOWN, flag it
        # v8 uses FLAT, router_v1 uses ROUTER
        flat_phase = getattr(Phase, 'ROUTER', None) or Phase.FLAT
        if new_phase == flat_phase and old_phase == Phase.MARKDOWN:
            self._came_from_markdown = True
        elif new_phase != flat_phase:
            self._came_from_markdown = False

    def _get_score(self, date):
        det = self.bottom_detector
        if det.daily is None or date not in det.daily.index:
            return 0, {}
        signals = {}
        score = 0
        # 1: 2D death cross
        if hasattr(det, 'death_cross_2d') and date in det.death_cross_2d.index:
            signals['dc'] = bool(det.death_cross_2d.loc[date])
            if signals['dc']: score += 1
        else:
            signals['dc'] = False
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
        # ONLY check conviction if we came from MARKDOWN
        if self._came_from_markdown:
            score, signals = self._get_score(date)
            if score >= self.min_conviction:
                self._deploy(date, score, signals)
                return
        # Standard FLAT/ROUTER logic
        super()._check_flat(date, price)

    def _deploy(self, date, score, signals):
        price = self._price(date)
        self.conviction_triggers.append({
            'date': date, 'coin': self.coin, 'score': score,
            'signals': signals, 'price': price
        })
        if self.graduated:
            if score >= 4: tiers, tag = [1,2,3], "T1+T2+T3"
            elif score >= 3: tiers, tag = [1,2], "T1+T2"
            else: tiers, tag = [1], "T1"
        else:
            tiers, tag = [1], "T1"

        self._came_from_markdown = False  # consumed the signal
        self._change_phase(date, Phase.MARKUP, f'CONVICTION {score}/4 -> {tag} (post-MARKDOWN)')
        for t in tiers:
            pct = [0, self.cfg.TIER1_PCT, self.cfg.TIER2_PCT, self.cfg.TIER3_PCT][t]
            self._buy(date, pct, t)
        self.early_warning_date = None
        self.failsafe_armed = False
        self.peak_2w_k = 0


def main():
    coins = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']
    cap = 2500

    variants = [
        ('BASELINE', {}),
        ('>=2/4 T1 (post-MD only)', {'min_conviction': 2}),
        ('>=3/4 T1 (post-MD only)', {'min_conviction': 3}),
        ('4/4 T1 (post-MD only)', {'min_conviction': 4}),
        ('Graduated 2->T1, 3->T1T2, 4->all', {'min_conviction': 2, 'graduated': True}),
    ]

    print("Conviction-Weighted (Post-MARKDOWN only)")
    print("Only fires during ROUTER phases that follow a MARKDOWN")
    print("4 signals: 2D Death Cross + Below SMA200 + CFGI<35 + Weekly RSI(7)<30")
    print("="*100)

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

                if not vopts:
                    bt = V13BacktestV8(pack, cfg)
                else:
                    bt = PostMarkdownConvictionV13(pack, cfg, **vopts)

                res = bt.run()
                val = res['final_equity'] if res else cap
                row['coins'][c] = val
                row['total'] += val
                if hasattr(bt, 'conviction_triggers') and bt.conviction_triggers:
                    row['triggers'].extend(bt.conviction_triggers)
                    print(f"  {c}: ${val:,.0f}  ({len(bt.conviction_triggers)} triggers)")
                else:
                    print(f"  {c}: ${val:,.0f}")
            except Exception as e:
                print(f"  {c}: ERROR {e}")
                import traceback; traceback.print_exc()
                row['coins'][c] = cap
                row['total'] += cap
        results.append(row)

    # Summary
    print(f"\n{'='*100}")
    print(f"{'Variant':<45} {'Total':>8} {'Delta':>8} {'Trig':>5}  ETH      SOL      BTC      LINK     XRP")
    print("-"*115)
    base = results[0]['total']
    for r in results:
        d = r['total'] - base
        ds = f"+{d:,.0f}" if d >= 0 else f"{d:,.0f}"
        if r['name'] == 'BASELINE': ds = "  BASE"
        print(f"{r['name']:<45} ${r['total']:>7,.0f} {ds:>8} {len(r['triggers']):>5}", end="")
        for c in coins:
            print(f"  ${r['coins'].get(c, cap):>6,.0f}", end="")
        print()

    # Trigger details
    all_trigs = set()
    for r in results:
        for t in r['triggers']:
            all_trigs.add((str(t['date'])[:10], t['coin'], t['score'],
                          t['signals'].get('dc', False), t['signals'].get('sma', False),
                          t['signals'].get('cfgi', False), t['signals'].get('rsi', False),
                          t['signals'].get('cfgi_val', 0), t['signals'].get('rsi_val', 0),
                          t['price']))

    if all_trigs:
        print(f"\nALL TRIGGER EVENTS (post-MARKDOWN ROUTER only):")
        print(f"  {'Date':<12} {'Coin':<6} {'Score':<6} {'DC':>3} {'SMA':>4} {'CFGI':>5} {'RSI':>5}  CFGI_v  RSI_v    Price")
        print("  " + "-"*85)
        for t in sorted(all_trigs):
            date, coin, score, dc, sma, cfgi, rsi, cfgi_v, rsi_v, price = t
            print(f"  {date:<12} {coin:<6} {score}/4   "
                  f"{'Y' if dc else '-':>3} {'Y' if sma else '-':>4} "
                  f"{'Y' if cfgi else '-':>5} {'Y' if rsi else '-':>5}  "
                  f"{cfgi_v:>5.0f}   {rsi_v:>5.1f}  ${price:>10.2f}")

if __name__ == '__main__':
    main()
