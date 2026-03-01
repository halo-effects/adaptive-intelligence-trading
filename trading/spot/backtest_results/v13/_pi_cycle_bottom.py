"""
Pi Cycle Bottom Indicator + Steve's 3-Check Hybrid

Pi Cycle Bottom:
  - 150-day SMA
  - 471-day SMA * 0.745
  - Bottom signal: 150 SMA crosses below 471*0.745 SMA
  (Some versions use the crossover itself; others use when price is in the zone between them)

Test as standalone signal and combined with Steve's 3-Check + CFGI.

Also test DURING MARKDOWN (not just post-MARKDOWN ROUTER) per Brett's directive
that current shorts won't close in time.
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


class PiCycleDetector:
    """Pi Cycle Bottom indicator on daily candles."""
    def __init__(self, coin):
        self.coin = coin
        self.base = coin.split('/')[0] if '/' in coin else coin
        self.daily = self._load_daily()
        if self.daily is not None:
            self._compute()

    def _load_daily(self):
        db = sqlite3.connect(str(DB_PATH))
        syms = db.execute(
            "SELECT DISTINCT symbol FROM candles_daily WHERE symbol LIKE ?",
            (f'{self.base}%',)
        ).fetchall()
        if not syms:
            db.close()
            return None
        df = pd.read_sql(
            "SELECT timestamp, close FROM candles_daily WHERE symbol=? ORDER BY timestamp",
            db, params=[syms[0][0]]
        )
        db.close()
        df['dt'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('dt').sort_index()
        df = df[~df.index.duplicated(keep='last')]
        return df

    def _compute(self):
        df = self.daily
        df['sma150'] = df['close'].rolling(150).mean()
        df['sma471'] = df['close'].rolling(471).mean()
        df['sma471_scaled'] = df['sma471'] * 0.745

        # Pi cycle bottom zone: 150 SMA < 471*0.745 SMA
        df['pi_bottom_zone'] = df['sma150'] < df['sma471_scaled']

        # Cross signal: 150 SMA crosses below 471*0.745
        prev = df['sma150'].shift(1) >= df['sma471_scaled'].shift(1)
        curr = df['sma150'] < df['sma471_scaled']
        df['pi_cross_below'] = prev & curr

    def in_bottom_zone(self, date):
        if self.daily is None or date not in self.daily.index:
            return False, {}
        row = self.daily.loc[date]
        in_zone = bool(row.get('pi_bottom_zone', False))
        return in_zone, {
            'sma150': row.get('sma150', np.nan),
            'sma471_scaled': row.get('sma471_scaled', np.nan),
            'price': row['close'],
            'in_zone': in_zone,
        }

    def find_all_signals(self, start='2015-01-01'):
        """Find all dates where Pi Cycle bottom zone is active."""
        df = self.daily.dropna(subset=['sma150', 'sma471_scaled'])
        zones = []
        in_zone = False
        zone_start = None
        for date in df.index:
            if date < pd.Timestamp(start):
                continue
            if df.loc[date, 'pi_bottom_zone']:
                if not in_zone:
                    zone_start = date
                    in_zone = True
            else:
                if in_zone:
                    zones.append({
                        'start': zone_start, 'end': date,
                        'days': (date - zone_start).days,
                        'price_at_start': df.loc[zone_start, 'close'],
                    })
                    in_zone = False
        if in_zone:
            zones.append({
                'start': zone_start, 'end': 'ONGOING',
                'days': (df.index[-1] - zone_start).days,
                'price_at_start': df.loc[zone_start, 'close'],
            })
        return zones


class FullStackConvictionV13(V13BacktestV8):
    """
    Conviction stack that fires DURING MARKDOWN too (not just ROUTER).
    On signal: close shorts, flip to MARKUP.
    
    Signals (score /5):
      1. 2D below SMA200 (Steve #1)
      2. 2D RSI(14) < 26 (Steve #2)
      3. 2D StochRSI K&D < 20 (Steve #3)
      4. CFGI < 35
      5. Pi Cycle bottom zone active
    """
    def __init__(self, pack, config=None, min_score=3, graduated=False):
        super().__init__(pack, config)
        self.min_score = min_score
        self.graduated = graduated
        self.steve = Steve3CheckDetector(pack.coin)
        self.pi = PiCycleDetector(pack.coin)
        self.cfgi = self._load_cfgi()
        self.conviction_triggers = []
        self._no_reshort = False  # once conviction flips to MARKUP, never re-short

    def _open_short(self, date, pct, tier):
        """Override: block shorting after conviction flip."""
        if self._no_reshort:
            return
        super()._open_short(date, pct, tier)

    def _load_cfgi(self):
        try:
            base = self.coin.split('/')[0]
            db = sqlite3.connect(str(DB_PATH))
            df = pd.read_sql("SELECT * FROM cfgi_daily WHERE symbol = ? ORDER BY date", db, params=[base])
            db.close()
            if len(df) == 0: return None
            df['dt'] = pd.to_datetime(df['date'], format='mixed')
            df = df.set_index('dt')
            df.index = df.index.normalize()
            df = df[~df.index.duplicated(keep='last')]
            return df
        except:
            return None

    def _get_score(self, date):
        score = 0
        details = {}

        # Steve signals (2D chart)
        if self.steve.daily is not None:
            _, sd = self.steve.check(date)
            details.update(sd)
            if sd.get('below_sma200'): score += 1
            if sd.get('rsi_ok'): score += 1
            if sd.get('stoch_ok'): score += 1

        # CFGI < 35
        cfgi_val = np.nan
        if self.cfgi is not None:
            cdates = self.cfgi.index[self.cfgi.index <= date]
            if len(cdates):
                cfgi_val = self.cfgi.loc[cdates[-1], 'cfgi']
        details['cfgi'] = cfgi_val
        details['cfgi_ok'] = not pd.isna(cfgi_val) and cfgi_val < 35
        if details['cfgi_ok']: score += 1

        # Pi Cycle bottom zone
        pi_active, pi_details = self.pi.in_bottom_zone(date)
        details['pi_bottom'] = pi_active
        details.update({f'pi_{k}': v for k, v in pi_details.items()})
        if pi_active: score += 1

        details['score'] = score
        return score, details

    def _check_markdown(self, date, price):
        """Override: check conviction during MARKDOWN. If fires, close shorts and go MARKUP."""
        score, details = self._get_score(date)
        if score >= self.min_score:
            # Close short position first using engine's own method
            self._close_short(date, f'CONVICTION {score}/5')

            self.conviction_triggers.append({
                'date': date, 'coin': self.coin, 'score': score, 'details': details,
                'from_phase': 'MARKDOWN'
            })

            # Determine tiers
            if self.graduated:
                if score >= 5: tiers, tag = [1,2,3], "T1+T2+T3"
                elif score >= 4: tiers, tag = [1,2], "T1+T2"
                else: tiers, tag = [1], "T1"
            else:
                tiers, tag = [1], "T1"

            # Disable shorts after conviction flip — hold spot longs, no re-shorting
            self._no_reshort = True

            self._change_phase(date, Phase.MARKUP, f'CONVICTION {score}/5 -> {tag} (from MARKDOWN)')
            for t in tiers:
                pct = [0, self.cfg.TIER1_PCT, self.cfg.TIER2_PCT, self.cfg.TIER3_PCT][t]
                self._buy(date, pct, t)
            self.early_warning_date = None
            self.failsafe_armed = False
            self.peak_2w_k = 0
            return

        # Standard markdown check
        super()._check_markdown(date, price)

    def _check_flat(self, date, price):
        """Also check during ROUTER/FLAT phase."""
        score, details = self._get_score(date)
        if score >= self.min_score:
            self.conviction_triggers.append({
                'date': date, 'coin': self.coin, 'score': score, 'details': details
            })
            if self.graduated:
                if score >= 5: tiers, tag = [1,2,3], "T1+T2+T3"
                elif score >= 4: tiers, tag = [1,2], "T1+T2"
                else: tiers, tag = [1], "T1"
            else:
                tiers, tag = [1], "T1"

            self._change_phase(date, Phase.MARKUP, f'CONVICTION {score}/5 -> {tag} (from ROUTER)')
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

    # Part 1: Pi Cycle bottom zones
    print("PI CYCLE BOTTOM ZONES (150 SMA < 471*0.745 SMA)")
    print("="*80)
    for c in coins:
        pi = PiCycleDetector(c)
        if pi.daily is None:
            print(f"{c}: No data")
            continue
        zones = pi.find_all_signals('2018-01-01')
        print(f"\n{c}: {len(zones)} bottom zones")
        for z in zones:
            end = z['end'] if isinstance(z['end'], str) else z['end'].strftime('%Y-%m-%d')
            print(f"  {z['start'].strftime('%Y-%m-%d')} to {end}  ({z['days']}d)  entry=${z['price_at_start']:,.2f}")

    # Part 2: Backtest (fires during MARKDOWN + ROUTER)
    print(f"\n\n{'='*80}")
    print("BACKTEST: Conviction fires during MARKDOWN AND ROUTER")
    print("5 signals: Steve 3-Check + CFGI<35 + Pi Cycle Bottom")
    print("="*80)

    variants = [
        ('BASELINE', {}),
        ('>=3/5 T1 (MD+ROUTER)', {'min_score': 3}),
        ('>=4/5 T1 (MD+ROUTER)', {'min_score': 4}),
        ('5/5 T1 (MD+ROUTER)', {'min_score': 5}),
        ('Graduated 3->T1, 4->T1T2, 5->all', {'min_score': 3, 'graduated': True}),
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
                    bt = FullStackConvictionV13(pack, cfg, **vopts)

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

    # Summary
    print(f"\n{'='*80}")
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
    all_t = []
    seen = set()
    for r in results:
        if r['name'] != 'BASELINE':
            for t in r['triggers']:
                key = (str(t['date'])[:10], t['coin'], t['score'])
                if key not in seen:
                    seen.add(key)
                    all_t.append(t)

    if all_t:
        print(f"\nALL UNIQUE TRIGGERS:")
        print(f"  {'Date':<12} {'Coin':<6} {'Scr':<5} {'SMA':>4} {'RSI':>4} {'StRSI':>6} {'CFGI':>5} {'Pi':>3}  RSI14   CFGI   Phase      Price")
        print(f"  {'-'*100}")
        for t in sorted(all_t, key=lambda x: (x['date'], x['coin'])):
            d = t['details']
            phase = "MD" if "MARKDOWN" in str(t.get('details', {}).get('score', '')) else "?"
            print(f"  {str(t['date'])[:10]:<12} {t['coin']:<6} {t['score']}/5 "
                  f" {'Y' if d.get('below_sma200') else '-':>3} "
                  f" {'Y' if d.get('rsi_ok') else '-':>3} "
                  f" {'Y' if d.get('stoch_ok') else '-':>5} "
                  f" {'Y' if d.get('cfgi_ok') else '-':>4} "
                  f" {'Y' if d.get('pi_bottom') else '-':>2} "
                  f" {d.get('rsi14',0):>5.1f}  {d.get('cfgi',0):>5.0f}  "
                  f"${d.get('price',0):>10.2f}")


if __name__ == '__main__':
    main()
