"""
Steve Courtney (CCU) "3-Checkmark" Bottom Stack on 2D candles.
All indicators computed on 2-day resampled candles:
  1. Price below 2D SMA(200)
  2. 2D RSI(14) < 26
  3. 2D StochRSI(3,3,14,14) both K AND D < 20

Test as conviction trigger in post-MARKDOWN ROUTER phase.
Also show standalone signal firing dates for reference.
"""
import sys, os
import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path
from .v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from .v13_signals import V13SignalPack

# Use AIT_CANDLES_DB env var if set; fall back to default
_default_path = Path(__file__).resolve().parent.parent / 'data' / 'candles.db'
DB_PATH = Path(os.environ.get('AIT_CANDLES_DB', str(_default_path)))


class Steve3CheckDetector:
    """Steve Courtney's 3-Checkmark bottom detection on 2D candles."""

    def __init__(self, coin):
        self.coin = coin
        self.base = coin.split('/')[0] if '/' in coin else coin
        self.daily = self._load_daily()
        if self.daily is not None:
            self.candles_2d = self._resample_2d()
            self._compute_indicators()
            self._align_to_daily()

    def _load_daily(self):
        db = sqlite3.connect(str(DB_PATH))
        syms = db.execute(
            "SELECT DISTINCT symbol FROM candles_daily WHERE symbol LIKE ?",
            (f'{self.base}%',)
        ).fetchall()
        if not syms:
            db.close()
            return None
        # Pick best symbol: prefer symbols with indicators, then widest range
        # (matches load_daily logic in v13_signals.py — Finding #12 fix)
        def _score(s):
            r = db.execute(
                'SELECT MAX(timestamp) - MIN(timestamp), '
                'SUM(CASE WHEN sma50 IS NOT NULL AND sma50 != 0 THEN 1 ELSE 0 END) '
                'FROM candles_daily '
                'WHERE symbol=? AND timestamp IS NOT NULL AND timestamp > 0', (s,)).fetchone()
            date_range = r[0] or 0
            has_indicators = 1 if (r[1] or 0) > 0 else 0
            return (has_indicators * 10**15) + date_range
        sym = max([s[0] for s in syms], key=_score)
        df = pd.read_sql(
            "SELECT timestamp, open, high, low, close, volume FROM candles_daily WHERE symbol=? ORDER BY timestamp",
            db, params=[sym]
        )
        db.close()
        df['dt'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('dt').sort_index()
        df = df[~df.index.duplicated(keep='last')]
        df = df[df.index.notna()]
        return df

    def _resample_2d(self):
        return self.daily.resample('2D').agg({
            'open': 'first', 'high': 'max', 'low': 'min',
            'close': 'last', 'volume': 'sum'
        }).dropna()

    def _compute_indicators(self):
        df = self.candles_2d
        # SMA200
        df['sma200'] = df['close'].rolling(200).mean()

        # RSI(14)
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
        rs = avg_gain / avg_loss
        df['rsi14'] = 100 - (100 / (1 + rs))

        # StochRSI(3, 3, 14, 14) = StochRSI of RSI(14) over 14 periods, K smooth=3, D smooth=3
        rsi = df['rsi14']
        rsi_low = rsi.rolling(14).min()
        rsi_high = rsi.rolling(14).max()
        denom = rsi_high - rsi_low
        stoch_raw = ((rsi - rsi_low) / denom.replace(0, np.nan)) * 100
        df['stochrsi_k'] = stoch_raw.rolling(3).mean()
        df['stochrsi_d'] = df['stochrsi_k'].rolling(3).mean()

        self.candles_2d = df

    def _align_to_daily(self):
        """Forward-fill 2D indicators to daily index."""
        df2 = self.candles_2d
        idx = self.daily.index
        self.below_sma200 = (df2['close'] < df2['sma200']).reindex(idx, method='ffill').fillna(False)
        self.rsi14 = df2['rsi14'].reindex(idx, method='ffill')
        self.stochrsi_k = df2['stochrsi_k'].reindex(idx, method='ffill')
        self.stochrsi_d = df2['stochrsi_d'].reindex(idx, method='ffill')

    def check(self, date):
        """Returns (all_3_fire, details_dict)."""
        if self.daily is None or date not in self.daily.index:
            return False, {}
        below = bool(self.below_sma200.get(date, False))
        rsi = self.rsi14.get(date, np.nan)
        k = self.stochrsi_k.get(date, np.nan)
        d = self.stochrsi_d.get(date, np.nan)

        rsi_ok = not pd.isna(rsi) and rsi < 26
        stoch_ok = not pd.isna(k) and not pd.isna(d) and k < 20 and d < 20

        fired = below and rsi_ok and stoch_ok
        return fired, {
            'below_sma200': below, 'rsi14': rsi, 'rsi_ok': rsi_ok,
            'stochrsi_k': k, 'stochrsi_d': d, 'stoch_ok': stoch_ok,
            'price': self.daily.loc[date, 'close'] if date in self.daily.index else np.nan,
        }

    def find_all_signals(self, start='2020-01-01'):
        """Find all dates where all 3 checks fire."""
        signals = []
        df2 = self.candles_2d.dropna(subset=['sma200', 'rsi14', 'stochrsi_k', 'stochrsi_d'])
        for date in df2.index:
            if date < pd.Timestamp(start):
                continue
            below = df2.loc[date, 'close'] < df2.loc[date, 'sma200']
            rsi_ok = df2.loc[date, 'rsi14'] < 26
            stoch_ok = df2.loc[date, 'stochrsi_k'] < 20 and df2.loc[date, 'stochrsi_d'] < 20
            if below and rsi_ok and stoch_ok:
                signals.append({
                    'date': date,
                    'price': df2.loc[date, 'close'],
                    'rsi14': df2.loc[date, 'rsi14'],
                    'stochrsi_k': df2.loc[date, 'stochrsi_k'],
                    'stochrsi_d': df2.loc[date, 'stochrsi_d'],
                })
        return signals


class Steve3CheckV13(V13BacktestV8):
    def __init__(self, pack, config=None):
        super().__init__(pack, config)
        self.steve = Steve3CheckDetector(pack.coin)
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
        if self._came_from_markdown and self.steve.daily is not None:
            fired, details = self.steve.check(date)
            if fired:
                self.conviction_triggers.append({
                    'date': date, 'coin': self.coin, 'details': details
                })
                self._came_from_markdown = False
                self._change_phase(date, Phase.MARKUP, 'STEVE 3-CHECK bottom')
                self._buy(date, self.cfg.TIER1_PCT, 1)
                self.early_warning_date = None
                self.failsafe_armed = False
                self.peak_2w_k = 0
                return
        super()._check_flat(date, price)


def main():
    coins = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']
    cap = 2500

    # Part 1: Show all signal dates per coin
    print("STEVE COURTNEY 3-CHECKMARK BOTTOM SIGNALS")
    print("2D chart: Below SMA200 + RSI(14)<26 + StochRSI(3,3,14,14) K&D<20")
    print("="*90)

    for c in coins:
        det = Steve3CheckDetector(c)
        if det.daily is None:
            print(f"\n{c}: No data")
            continue
        sigs = det.find_all_signals('2020-01-01')
        print(f"\n{c}: {len(sigs)} signals found (2020+)")
        if sigs:
            print(f"  {'Date':<12} {'Price':>10} {'RSI14':>6} {'K':>6} {'D':>6}")
            print(f"  {'-'*45}")
            for s in sigs:
                print(f"  {s['date'].strftime('%Y-%m-%d'):<12} ${s['price']:>9.2f} {s['rsi14']:>6.1f} {s['stochrsi_k']:>6.1f} {s['stochrsi_d']:>6.1f}")

    # Part 2: Post-MARKDOWN backtest
    print(f"\n\n{'='*90}")
    print("BACKTEST: Steve 3-Check as Post-MARKDOWN ROUTER trigger")
    print("Deploys T1 (60%) immediately on signal")
    print("="*90)

    variants = [
        ('BASELINE', False),
        ('Steve 3-Check T1', True),
    ]
    results = []
    for vname, use_steve in variants:
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

                if use_steve:
                    bt = Steve3CheckV13(pack, cfg)
                else:
                    bt = V13BacktestV8(pack, cfg)

                res = bt.run()
                val = res['final_equity'] if res else cap
                row['coins'][c] = val
                row['total'] += val
                trigs = getattr(bt, 'conviction_triggers', [])
                row['triggers'].extend(trigs)
                extra = f"  ({len(trigs)} triggers)" if trigs else ""
                print(f"  {c}: ${val:,.0f}{extra}")
            except Exception as e:
                print(f"  {c}: ERROR {e}")
                row['coins'][c] = cap
                row['total'] += cap
        results.append(row)

    # Summary
    print(f"\n{'='*90}")
    base = results[0]['total']
    for r in results:
        d = r['total'] - base
        ds = f"+{d:,.0f}" if d >= 0 else f"{d:,.0f}"
        if r['name'] == 'BASELINE': ds = "BASE"
        print(f"{r['name']:<35} ${r['total']:>7,.0f} {ds:>8}  ", end="")
        for c in coins:
            print(f" {c}=${r['coins'].get(c,cap):>6,.0f}", end="")
        print()

    # Trigger details
    all_t = [t for r in results for t in r['triggers']]
    if all_t:
        print(f"\nTRIGGER DETAILS:")
        for t in sorted(all_t, key=lambda x: x['date']):
            d = t['details']
            print(f"  {str(t['date'])[:10]} {t['coin']:<5} "
                  f"RSI={d['rsi14']:.1f} K={d['stochrsi_k']:.1f} D={d['stochrsi_d']:.1f} "
                  f"${d['price']:.2f}")

if __name__ == '__main__':
    main()
