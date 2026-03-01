"""
Hybrid Bottom Stack: Steve's 3-Check + CFGI < 35
Post-MARKDOWN ROUTER only.

Signals (score out of 4):
  1. 2D Price below SMA200           (Steve #1)
  2. 2D RSI(14) < 26                 (Steve #2)
  3. 2D StochRSI(3,3,14,14) K&D < 20 (Steve #3)
  4. Coin-specific CFGI < 35          (our addition for sentiment)

Variants:
  - Steve pure (all 3 required)
  - Steve + CFGI (all 4 required)
  - 3/4 any combo
  - Graduated: 3/4->T1, 4/4->T1+T2
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack
from _steve_3check import Steve3CheckDetector

DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'


class HybridDetector(Steve3CheckDetector):
    """Steve's 3-Check + CFGI < 35."""
    def __init__(self, coin):
        super().__init__(coin)
        self.cfgi = self._load_cfgi()

    def _load_cfgi(self):
        try:
            db = sqlite3.connect(str(DB_PATH))
            df = pd.read_sql(
                "SELECT * FROM cfgi_daily WHERE symbol = ? ORDER BY date",
                db, params=[self.base]
            )
            db.close()
            if len(df) == 0:
                return None
            df['dt'] = pd.to_datetime(df['date'], format='mixed')
            df = df.set_index('dt')
            df.index = df.index.normalize()
            df = df[~df.index.duplicated(keep='last')]
            return df
        except:
            return None

    def check_hybrid(self, date):
        """Returns (score out of 4, details)."""
        fired_steve, details = self.check(date)
        score = 0
        if details.get('below_sma200'): score += 1
        if details.get('rsi_ok'): score += 1
        if details.get('stoch_ok'): score += 1

        # CFGI < 35
        cfgi_val = np.nan
        if self.cfgi is not None:
            cdates = self.cfgi.index[self.cfgi.index <= date]
            if len(cdates):
                cfgi_val = self.cfgi.loc[cdates[-1], 'cfgi']
        cfgi_ok = not pd.isna(cfgi_val) and cfgi_val < 35
        if cfgi_ok: score += 1
        details['cfgi'] = cfgi_val
        details['cfgi_ok'] = cfgi_ok
        details['score'] = score
        details['steve_all3'] = fired_steve
        return score, details


class HybridConvictionV13(V13BacktestV8):
    def __init__(self, pack, config=None, min_score=3, graduated=False, steve_only=False):
        super().__init__(pack, config)
        self.min_score = min_score
        self.graduated = graduated
        self.steve_only = steve_only
        self.detector = HybridDetector(pack.coin)
        self.conviction_triggers = []
        self._came_from_markdown = False

    def _change_phase(self, date, new_phase, reason=""):
        old_phase = self.phase
        super()._change_phase(date, new_phase, reason)
        flat_phase = getattr(Phase, 'ROUTER', None) or Phase.FLAT
        if new_phase == flat_phase and old_phase == Phase.MARKDOWN:
            self._came_from_markdown = True
        elif new_phase != flat_phase:
            self._came_from_markdown = False

    def _check_flat(self, date, price):
        if self._came_from_markdown and self.detector.daily is not None:
            score, details = self.detector.check_hybrid(date)

            trigger = False
            if self.steve_only:
                trigger = details.get('steve_all3', False)
            elif self.graduated:
                trigger = score >= 3
            else:
                trigger = score >= self.min_score

            if trigger:
                self.conviction_triggers.append({
                    'date': date, 'coin': self.coin, 'score': score, 'details': details
                })
                # Tier deployment
                if self.graduated and score >= 4:
                    tiers, tag = [1, 2], "T1+T2"
                else:
                    tiers, tag = [1], "T1"

                self._came_from_markdown = False
                self._change_phase(date, Phase.MARKUP, f'HYBRID {score}/4 -> {tag}')
                for t in tiers:
                    pct = [0, self.cfg.TIER1_PCT, self.cfg.TIER2_PCT, self.cfg.TIER3_PCT][t]
                    self._buy(date, pct, t)
                self.early_warning_date = None
                self.failsafe_armed = False
                self.peak_2w_k = 0
                return
        super()._check_flat(date, price)


def main():
    coins = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']
    cap = 2500

    # First show signal availability per coin
    print("HYBRID BOTTOM STACK SIGNAL SCAN")
    print("="*90)
    for c in coins:
        det = HybridDetector(c)
        if det.daily is None:
            print(f"{c}: No data")
            continue
        # Scan all dates from 2020
        df2 = det.candles_2d.dropna(subset=['sma200','rsi14','stochrsi_k','stochrsi_d'])
        hits = []
        for date in df2.index:
            if date < pd.Timestamp('2020-01-01'):
                continue
            score, details = det.check_hybrid(date)
            if score >= 3:
                hits.append((date, score, details))
        print(f"\n{c}: {len(hits)} dates with score >= 3/4")
        if hits:
            print(f"  {'Date':<12} {'Scr':>4} {'SMA':>4} {'RSI':>4} {'StRSI':>6} {'CFGI':>5}  RSI14  K      D     CFGI  Price")
            print(f"  {'-'*90}")
            for date, score, d in hits:
                print(f"  {date.strftime('%Y-%m-%d'):<12} {score}/4 "
                      f" {'Y' if d.get('below_sma200') else '-':>3} "
                      f" {'Y' if d.get('rsi_ok') else '-':>3} "
                      f" {'Y' if d.get('stoch_ok') else '-':>5} "
                      f" {'Y' if d.get('cfgi_ok') else '-':>4} "
                      f" {d.get('rsi14',0):>5.1f} {d.get('stochrsi_k',0):>5.1f} {d.get('stochrsi_d',0):>5.1f} "
                      f" {d.get('cfgi',0):>5.0f}  ${d.get('price',0):>10.2f}")

    # Backtest variants
    print(f"\n\n{'='*90}")
    print("BACKTEST: Post-MARKDOWN ROUTER triggers")
    print("="*90)

    variants = [
        ('BASELINE', {}),
        ('Steve pure (3/3)', {'steve_only': True}),
        ('Hybrid 3/4', {'min_score': 3}),
        ('Hybrid 4/4', {'min_score': 4}),
        ('Graduated 3->T1, 4->T1+T2', {'min_score': 3, 'graduated': True}),
    ]

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
                    bt = HybridConvictionV13(pack, cfg, **vopts)

                res = bt.run()
                val = res['final_equity'] if res else cap
                row['coins'][c] = val
                row['total'] += val
                trigs = getattr(bt, 'conviction_triggers', [])
                row['triggers'].extend(trigs)
                extra = f"  ({len(trigs)} trigs)" if trigs else ""
                print(f"  {c}: ${val:,.0f}{extra}")
            except Exception as e:
                print(f"  {c}: ERROR {e}")
                import traceback; traceback.print_exc()
                row['coins'][c] = cap
                row['total'] += cap
        results.append(row)

    # Summary table
    print(f"\n{'='*90}")
    print(f"{'Variant':<38} {'Total':>8} {'Delta':>8} {'Trig':>5}  ETH      SOL      BTC      LINK     XRP")
    print("-"*110)
    base = results[0]['total']
    for r in results:
        d = r['total'] - base
        ds = f"+{d:,.0f}" if d >= 0 else f"{d:,.0f}"
        if r['name'] == 'BASELINE': ds = "  BASE"
        print(f"{r['name']:<38} ${r['total']:>7,.0f} {ds:>8} {len(r['triggers']):>5}", end="")
        for c in coins:
            print(f"  ${r['coins'].get(c, cap):>6,.0f}", end="")
        print()

    # Trigger details
    all_t = []
    for r in results:
        if r['name'] != 'BASELINE':
            all_t.extend(r['triggers'])
    if all_t:
        seen = set()
        print(f"\nALL TRIGGERS:")
        print(f"  {'Date':<12} {'Coin':<6} {'Scr':<5} {'SMA':>4} {'RSI':>4} {'StRSI':>6} {'CFGI':>5}  RSI14   K      CFGI   Price")
        print(f"  {'-'*85}")
        for t in sorted(all_t, key=lambda x: (x['date'], x['coin'])):
            key = (str(t['date'])[:10], t['coin'])
            if key in seen: continue
            seen.add(key)
            d = t['details']
            print(f"  {str(t['date'])[:10]:<12} {t['coin']:<6} {t['score']}/4 "
                  f" {'Y' if d.get('below_sma200') else '-':>3} "
                  f" {'Y' if d.get('rsi_ok') else '-':>3} "
                  f" {'Y' if d.get('stoch_ok') else '-':>5} "
                  f" {'Y' if d.get('cfgi_ok') else '-':>4} "
                  f" {d.get('rsi14',0):>5.1f} {d.get('stochrsi_k',0):>5.1f} "
                  f" {d.get('cfgi',0):>5.0f}  ${d.get('price',0):>10.2f}")

if __name__ == '__main__':
    main()
