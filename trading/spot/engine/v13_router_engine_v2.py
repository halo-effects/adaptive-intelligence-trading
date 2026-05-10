"""
V13 ROUTER Engine v2 -- Conviction Bottom + Top Detection

Extends ROUTER v1 with:

BOTTOM CONVICTION (during MARKDOWN):
  - Hybrid 3/4 conviction stack (Steve 3-Check + CFGI<35)
  - Triple-gate prerequisite:
      Gate 1: Top detected (MARKUP->ROUTER transition confirms cycle)
      Gate 2: 3D death cross active (SMA50 < SMA200 on 3D candles)
      Gate 3: 2W StochRSI exhaustion lift-off (K >= 5 after pinned < 5)
  - One-trigger-per-cycle lock, no-reshort flag
  - Action: Close ALL shorts, flip MARKUP T1 (60%)
  - Backtest: +$9,847 (+98.5%)

TOP DETECTION (during MARKUP, Layer 2 modification):
  - OB93 fires -> ARM (don't sell immediately)
  - Wait for 2D RSI bearish divergence confirmation
  - 35d timeout if divergence never comes -> sell anyway
  - Layers 2b-5 only fire if NOT armed (OB93 takes priority when armed)
  - Divergence config: 30-bar 2D lookback, RSI gap>=8, price within 3%
    of high, RSI>60, RSI peak>75
  - Backtest: +$15,160 at 35d timeout

With conviction+top DISABLED: must produce 100% identical results to v1.

Locked parameters (2026-02-28):
  Bottom: 3D DX + 2W K>=5 + score>=3/4 + close shorts + no reshort
  Top: OB93 arm + 2D divergence confirm + 35d timeout
"""

import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict

from .v13_router_engine_v1 import V13RouterV1, V13Config, Phase, V13SignalPack
from .v13_router_engine_v1 import compute_fib_levels, FIB_RATIOS, FIB_TOLERANCE
from .v13_router_engine_v1 import print_results
from ._steve_3check import Steve3CheckDetector

import sqlite3

# Use AIT_CANDLES_DB env var if set; fall back to default
_default_path = Path(__file__).resolve().parent.parent / 'data' / 'candles.db'
DB_PATH = Path(os.environ.get('AIT_CANDLES_DB', str(_default_path)))


class HybridDetector2D:
    """Steve's 3-Check (2D) + CFGI<35 + 2D death cross gate."""

    def __init__(self, coin, exhaustion_k_min=5.0, exhaustion_tf='2W', exhaustion_mode='cross'):
        self.coin = coin
        self.base = coin.split('/')[0] if '/' in coin else coin
        self._exhaustion_k_min = exhaustion_k_min
        self._exhaustion_tf = exhaustion_tf
        self._exhaustion_mode = exhaustion_mode  # 'cross' = K×D, 'k_lift' = K >= threshold
        self._steve = Steve3CheckDetector(self.base)
        self._cfgi = self._load_cfgi()
        self._2d_death_cross = self._compute_2d_death_cross()

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
        except Exception:
            return None

    def _load_full_daily(self):
        """Load best available daily history.
        Uses same symbol selection as load_daily(): prefer symbols with
        indicators, then widest range. (Finding #13 fix)"""
        try:
            db = sqlite3.connect(str(DB_PATH))
            syms = [r[0] for r in db.execute(
                'SELECT DISTINCT symbol FROM candles_daily WHERE symbol LIKE ?',
                (f'{self.base}/%',)).fetchall()]
            if not syms:
                db.close()
                return None
            def _score(s):
                r = db.execute(
                    'SELECT MAX(timestamp) - MIN(timestamp), '
                    'SUM(CASE WHEN sma50 IS NOT NULL AND sma50 != 0 THEN 1 ELSE 0 END) '
                    'FROM candles_daily '
                    'WHERE symbol=? AND timestamp IS NOT NULL AND timestamp > 0', (s,)).fetchone()
                date_range = r[0] or 0
                has_indicators = 1 if (r[1] or 0) > 0 else 0
                return (has_indicators * 10**15) + date_range
            best_sym = max(syms, key=_score)
            best_df = pd.read_sql(
                "SELECT timestamp, open, high, low, close, volume FROM candles_daily WHERE symbol=? ORDER BY timestamp",
                db, params=[best_sym]
            )
            db.close()
            if len(best_df) == 0:
                return None
            best_df['dt'] = pd.to_datetime(best_df['timestamp'], unit='ms')
            best_df = best_df.set_index('dt').sort_index()
            best_df = best_df[~best_df.index.duplicated(keep='last')]
            return best_df
        except Exception:
            return None

    def compute_2d_divergence_dates(self):
        """Compute dates where 2D RSI bearish divergence fires.
        Config: 30-bar lookback, RSI gap>=8, price within 3% of high, RSI>60, peak>75."""
        df = self._load_full_daily()
        if df is None:
            return set()
        d2 = df['close'].resample('2D').last().dropna()
        period = 14
        delta = d2.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        dates = set()
        lookback = 30
        for i in range(lookback, len(d2)):
            cr = rsi.iloc[i]
            cp = d2.iloc[i]
            if pd.isna(cr) or cr < 60:
                continue
            wp = d2.iloc[i-lookback:i+1]
            wr = rsi.iloc[i-lookback:i+1]
            if cp < wp.max() * 0.97:
                continue
            rp = wr.max()
            if rp < 75:
                continue
            if rp - cr >= 8:
                dt = d2.index[i]
                dates.add(dt.strftime('%Y-%m-%d'))
                dates.add((dt + pd.Timedelta(days=1)).strftime('%Y-%m-%d'))
        return dates

    def _compute_2d_death_cross(self):
        """Compute death cross states + 2W StochRSI exhaustion crossover."""
        df = self._load_full_daily()
        if df is None:
            return None

        daily_idx = df.index

        # 3D death cross (SMA50 < SMA200)
        d3 = df['close'].resample('3D').last().dropna()
        s50_3 = d3.rolling(50).mean()
        s200_3 = d3.rolling(200).mean()
        in_dx_3d = s50_3 < s200_3
        self._in_dx_3d = in_dx_3d.reindex(daily_idx, method='ffill')

        # StochRSI exhaustion crossover (configurable timeframe)
        w2 = df.resample(self._exhaustion_tf).agg({
            'open': 'first', 'high': 'max', 'low': 'min',
            'close': 'last', 'volume': 'sum'
        }).dropna()

        # RSI(14) on 2W
        delta = w2['close'].diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
        rs = avg_gain / avg_loss
        w2['rsi14'] = 100 - (100 / (1 + rs))

        # StochRSI(3,3,14,14)
        rsi = w2['rsi14']
        rsi_low = rsi.rolling(14).min()
        rsi_high = rsi.rolling(14).max()
        denom = rsi_high - rsi_low
        stoch_raw = ((rsi - rsi_low) / denom.replace(0, np.nan)) * 100
        w2['k'] = stoch_raw.rolling(3).mean()
        w2['d'] = w2['k'].rolling(3).mean()

        # Method A: K×D crossover after pinned (original)
        w2['was_pinned'] = w2['k'].rolling(3).min() < 5
        w2['k_above_d'] = w2['k'] > w2['d']
        w2['cross_up'] = w2['k_above_d'] & ~w2['k_above_d'].shift(1).fillna(False)
        w2['exhaustion_cross'] = w2['cross_up'] & w2['was_pinned'] & (w2['k'] >= self._exhaustion_k_min)

        # Method B: K >= threshold after being pinned < 5 (faster, no D cross needed)
        w2['k_lifted'] = (w2['k'] >= self._exhaustion_k_min) & (w2['k'].shift(1) < self._exhaustion_k_min) & w2['was_pinned']

        # Use configured method
        signal_col = 'k_lifted' if self._exhaustion_mode == 'k_lift' else 'exhaustion_cross'

        # Once fired, stays True until K enters overbought (K > 90 = new cycle top)
        cross_active = pd.Series(False, index=w2.index)
        active = False
        for dt, row in w2.iterrows():
            if row[signal_col]:
                active = True
            if active and row['k'] > 90:
                active = False
            cross_active.loc[dt] = active

        self._2w_exhaustion_cross = cross_active.reindex(daily_idx, method='ffill').fillna(False)

        # Also keep 2D for reference
        d2 = df['close'].resample('2D').last().dropna()
        s50_2 = d2.rolling(50).mean()
        s200_2 = d2.rolling(200).mean()
        in_dx_2d = s50_2 < s200_2
        self._in_dx_2d = in_dx_2d.reindex(daily_idx, method='ffill')

        return self._in_dx_2d

    def in_death_cross(self, date, timeframe='3D'):
        """Check if coin is in death cross at given date."""
        if self._2d_death_cross is None:
            return False
        series = self._in_dx_3d if timeframe == '3D' else self._in_dx_2d
        if series is None:
            return False
        if date in series.index:
            return bool(series.loc[date])
        prior = series.index[series.index <= date]
        if len(prior):
            return bool(series.loc[prior[-1]])
        return False

    def has_2w_exhaustion_cross(self, date):
        """Check if 2W StochRSI exhaustion crossover has fired (K crossed above D after being pinned < 5)."""
        if not hasattr(self, '_2w_exhaustion_cross') or self._2w_exhaustion_cross is None:
            return False
        if date in self._2w_exhaustion_cross.index:
            return bool(self._2w_exhaustion_cross.loc[date])
        prior = self._2w_exhaustion_cross.index[self._2w_exhaustion_cross.index <= date]
        if len(prior):
            return bool(self._2w_exhaustion_cross.loc[prior[-1]])
        return False

    def check(self, date):
        """Returns (score out of 4, details_dict)."""
        if self._steve.daily is None:
            return 0, {}

        _, details = self._steve.check(date)
        score = 0
        if details.get('below_sma200'):
            score += 1
        if details.get('rsi_ok'):
            score += 1
        if details.get('stoch_ok'):
            score += 1

        # CFGI < 35
        cfgi_val = np.nan
        if self._cfgi is not None:
            cdates = self._cfgi.index[self._cfgi.index <= date]
            if len(cdates):
                cfgi_val = self._cfgi.loc[cdates[-1], 'cfgi']
        cfgi_ok = not pd.isna(cfgi_val) and cfgi_val < 35
        if cfgi_ok:
            score += 1

        details['cfgi'] = cfgi_val
        details['cfgi_ok'] = cfgi_ok
        details['score'] = score
        return score, details


class V13RouterV2(V13RouterV1):
    """V13 Router v2 -- Conviction bottom override during MARKDOWN.

    Args:
        conviction_enabled: If False, behaves identically to v1.
        min_score: Minimum conviction score to trigger (default 3 of 4).
    """

    def __init__(self, pack: V13SignalPack, config: V13Config = None,
                 conviction_enabled: bool = True, min_score: int = 3,
                 exhaustion_tf: str = '2W', exhaustion_k_min: float = 5.0,
                 exhaustion_mode: str = 'k_lift',
                 top_detection_enabled: bool = True,
                 top_divergence_timeout: int = 35):
        super().__init__(pack, config)
        self.conviction_enabled = conviction_enabled
        self.top_detection_enabled = top_detection_enabled
        self.top_divergence_timeout = top_divergence_timeout
        self.min_score = min_score

        # Conviction state (bottom)
        self._top_detected = False        # Gate: top must fire before bottom allowed
        self._conviction_fired = False     # One per cycle lock
        self._no_reshort = False           # Block shorts after conviction flip

        # Top detection state (OB93 arm → divergence confirm)
        self._ob93_armed = False           # OB93 fired, waiting for divergence
        self._ob93_armed_date = None       # Date OB93 armed

        self._detector = HybridDetector2D(
            pack.coin, exhaustion_k_min=exhaustion_k_min,
            exhaustion_tf=exhaustion_tf, exhaustion_mode=exhaustion_mode
        ) if (conviction_enabled or top_detection_enabled) else None

        # Precompute divergence dates for top detection
        self._div_dates = (self._detector.compute_2d_divergence_dates()
                          if self._detector and top_detection_enabled else set())

        self.conviction_triggers = []      # Log of bottom triggers
        self.top_triggers = []             # Log of top triggers

    def _open_short(self, date, pct, tier):
        """Block shorts if no-reshort flag is set."""
        if self._no_reshort:
            return
        super()._open_short(date, pct, tier)

    def _router_check_markup(self, date, price, signals):
        """Override: OB93 arm→divergence top detection + conviction gate arming."""
        # DCA graceful exit + 2W K tracking (same as parent)
        if self.dca_coins > 0:
            self._dca_tick(date, price)

        k_2w = self.pack.stoch_2w.get_k_at(date)
        if not np.isnan(k_2w) and k_2w > self.peak_2w_k:
            self.peak_2w_k = k_2w

        # Layer 1: Early warning (same as parent)
        if signals['early_warning_1w'] and self.early_warning_date is None:
            self.early_warning_date = date
            self.trades.append({
                'date': date, 'action': f'EARLY_WARNING_1W_97 (2W_peak={self.peak_2w_k:.0f})',
                'price': price, 'amount': 0, 'coins': 0, 'phase': self.phase
            })

        # Layer 2: OB93 — ARM if top detection enabled, else immediate sell
        if self.top_detection_enabled and not self._ob93_armed and signals['ob_2w_93']:
            self._ob93_armed = True
            self._ob93_armed_date = date
            self.trades.append({
                'date': date, 'action': f'OB93_ARMED (waiting for divergence, {self.top_divergence_timeout}d timeout)',
                'price': price, 'amount': 0, 'coins': 0, 'phase': self.phase
            })
        elif not self.top_detection_enabled and signals['ob_2w_93']:
            # Original behavior: immediate sell
            pnl = self._sell_all(date, 'PRIMARY_2W_OB93')
            if self.dca_coins > 0:
                self._dca_close(date, 'TOP_EXIT')
            self._change_phase(date, Phase.ROUTER, f'2W OB93 exit, pnl={pnl:+.1f}%')
            self._reset_top_state()
            self._mark_top_detected()
            return

        # Layer 2 continued: check divergence or timeout while armed
        if self._ob93_armed:
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            days_armed = (date - self._ob93_armed_date).days
            has_div = date_str in self._div_dates
            timeout = days_armed >= self.top_divergence_timeout

            if has_div or timeout:
                reason = 'DIVERGENCE' if has_div else f'TIMEOUT_{days_armed}d'
                pnl = self._sell_all(date, f'OB93+{reason}')
                if self.dca_coins > 0:
                    self._dca_close(date, 'TOP_EXIT')
                self._change_phase(date, Phase.ROUTER, f'OB93 armed -> {reason}, pnl={pnl:+.1f}%')
                self._reset_top_state()
                self._ob93_armed = False
                self._ob93_armed_date = None
                self.top_triggers.append({
                    'date': date, 'coin': self.coin, 'reason': reason,
                    'days_armed': days_armed, 'price': price
                })
                self._mark_top_detected()
                return

        # Layers 2b-5: only fire if NOT armed (OB93 takes priority)
        if not self._ob93_armed:
            # Layer 2b: Fallback -- 1W OB85 when 2W never reached OB
            if self.peak_2w_k < self.cfg.OB_THRESHOLD_2W and self.early_warning_date:
                if signals['ob_1w_85']:
                    pnl = self._sell_all(date, f'FALLBACK_1W_OB85 (2W_peak={self.peak_2w_k:.0f})')
                    if self.dca_coins > 0:
                        self._dca_close(date, 'TOP_EXIT')
                    self._change_phase(date, Phase.ROUTER,
                        f'1W OB85 fallback (2W peak={self.peak_2w_k:.0f}<93), pnl={pnl:+.1f}%')
                    self._reset_top_state()
                    self._mark_top_detected()
                    return

            # Layer 3: Failsafe -- 1W K<50 after armed
            if self.early_warning_date and not self.failsafe_armed:
                if (date - self.early_warning_date).days >= self.cfg.FAILSAFE_WINDOW_WEEKS * 7:
                    self.failsafe_armed = True
            if self.failsafe_armed and signals['failsafe_1w']:
                pnl = self._sell_all(date, 'FAILSAFE_1W_K50')
                if self.dca_coins > 0:
                    self._dca_close(date, 'TOP_EXIT')
                self._change_phase(date, Phase.ROUTER, f'Failsafe 1W K<50, pnl={pnl:+.1f}%')
                self._reset_top_state()
                self._mark_top_detected()
                return

        # Layer 4: Ranging exit (fires even if armed — trend is dead)
        days_in = signals['days_in_phase']
        if days_in >= 14:
            adx = signals['adx']
            if not np.isnan(adx) and adx < self.cfg.PHASE_ADX_RANGING:
                self.adx_below_20_streak += 1
                if self.adx_below_20_streak >= self.cfg.PHASE_ADX_SUSTAINED_DAYS:
                    pnl = self._sell_all(date, f'MARKUP_RANGING (ADX<{self.cfg.PHASE_ADX_RANGING} for {self.adx_below_20_streak}d)')
                    if self.dca_coins > 0:
                        self._dca_close(date, 'RANGING_EXIT')
                    self._change_phase(date, Phase.ROUTER,
                        f'Markup ranging: ADX<{self.cfg.PHASE_ADX_RANGING} for {self.adx_below_20_streak}d')
                    self._reset_top_state()
                    self._ob93_armed = False
                    self._ob93_armed_date = None
                    self._mark_top_detected()
                    return
            else:
                self.adx_below_20_streak = 0

        # Layer 5: Markup failure (fires even if armed — capital protection)
        if self.entry_price > 0:
            dd_from_entry = (price - self.entry_price) / self.entry_price
            if dd_from_entry < -self.cfg.MARKUP_FAIL_DD_PCT:
                adx = signals['adx']
                if not np.isnan(adx) and adx > self.cfg.MARKUP_FAIL_ADX:
                    pnl = self._sell_all(date, f'MARKUP_FAIL (dd={dd_from_entry*100:.0f}%, ADX={adx:.0f})')
                    if self.dca_coins > 0:
                        self._dca_close(date, 'MARKUP_FAIL')
                    self._change_phase(date, Phase.ROUTER,
                        f'Markup failed: {dd_from_entry*100:.0f}% below entry, ADX={adx:.0f}')
                    self._reset_top_state()
                    self._ob93_armed = False
                    self._ob93_armed_date = None
                    self._mark_top_detected()
                    return

        # Tier adds
        self._router_check_markup_tiers(date, price, signals)

    def _mark_top_detected(self):
        """Set conviction gates when MARKUP exits to ROUTER."""
        if self.conviction_enabled:
            self._top_detected = True
            self._conviction_fired = False
            self._no_reshort = False

    def _router_check_markdown(self, date, price, signals):
        """Override: check conviction stack before normal markdown logic."""
        if (self.conviction_enabled and
            self._top_detected and
            not self._conviction_fired and
            self.phase == Phase.MARKDOWN):

            # Gate 1: Must be in 3D death cross (filters corrections vs real bears)
            if not self._detector.in_death_cross(date, '3D'):
                super()._router_check_markdown(date, price, signals)
                return

            # Gate 2: Must have 2W StochRSI exhaustion crossover (confirms actual turn)
            if not self._detector.has_2w_exhaustion_cross(date):
                super()._router_check_markdown(date, price, signals)
                return

            score, details = self._detector.check(date)
            if score >= self.min_score:
                # CONVICTION TRIGGER: close shorts and flip to markup
                self._conviction_fired = True
                self._no_reshort = True

                # Close any open shorts
                short_pnl = 0
                if self.short_coins > 0:
                    short_pnl = self._close_short(date, f'CONVICTION_{score}/4')

                self.conviction_triggers.append({
                    'date': date,
                    'coin': self.coin,
                    'score': score,
                    'details': details,
                    'short_pnl_pct': short_pnl,
                })

                # Flip to MARKUP (buy spot T1)
                self._change_phase(date, Phase.MARKUP,
                    f'CONVICTION_{score}/4: bottom detected, T1 markup entry')
                alloc = self.cfg.TIER1_PCT
                self._buy(date, alloc, 1)
                return

        # Normal markdown logic
        super()._router_check_markdown(date, price, signals)

    def _change_phase(self, date, new_phase, reason=''):
        """Reset OB93 armed state when entering MARKUP (new cycle)."""
        super()._change_phase(date, new_phase, reason)
        if new_phase == Phase.MARKUP:
            self._ob93_armed = False
            self._ob93_armed_date = None

    def _results(self):
        """Extend results with conviction + top detection data."""
        r = super()._results()
        if r is not None:
            r['conviction_triggers'] = self.conviction_triggers
            r['top_triggers'] = self.top_triggers
            r['conviction_enabled'] = self.conviction_enabled
            r['top_detection_enabled'] = self.top_detection_enabled
            r['top_detected'] = self._top_detected
            r['conviction_fired'] = self._conviction_fired
        return r


# -- Runner ------------------------------------------------------------------

def run_combined(coins=None, start='2024-10-01', capital=10000):
    """Run 3-way comparison: baseline vs top-only vs combined (top+bottom)."""
    if coins is None:
        coins = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']

    per_coin = capital / len(coins)

    print("=" * 80)
    print("ROUTER v2 COMBINED BACKTEST — Bottom Conviction + Top Detection")
    print(f"Start: {start}, Capital: ${capital:,} (${per_coin:,.0f}/coin)")
    print(f"Coins: {', '.join(coins)}")
    print(f"Bottom: 3D DX + 2W K>=5 + score>=3/4 + close shorts + no reshort")
    print(f"Top: OB93 arm + 2D divergence confirm + 35d timeout")
    print("=" * 80)

    configs = {
        'baseline': dict(conviction_enabled=False, top_detection_enabled=False),
        'top_only': dict(conviction_enabled=False, top_detection_enabled=True, top_divergence_timeout=35),
        'bottom_only': dict(conviction_enabled=True, top_detection_enabled=False,
                           exhaustion_mode='k_lift', exhaustion_tf='2W', min_score=3),
        'combined': dict(conviction_enabled=True, top_detection_enabled=True,
                        top_divergence_timeout=35, exhaustion_mode='k_lift',
                        exhaustion_tf='2W', min_score=3),
    }

    all_results = {k: {} for k in configs}

    for coin in coins:
        base = coin.split('/')[0]
        print(f"\n{'='*50}")
        print(f"  {coin}")
        print(f"{'='*50}")

        try:
            pack_cache = V13SignalPack(coin)
        except Exception as e:
            print(f"  ERROR loading pack: {e}")
            continue

        for label, kwargs in configs.items():
            pack = V13SignalPack(coin)
            eng = V13RouterV2(pack, V13Config(), **kwargs)
            eng.cfg.CAPITAL = per_coin
            eng.cfg.START_DATE = start
            r = eng.run()
            if r:
                all_results[label][coin] = r

        # Print per-coin comparison
        for label in configs:
            r = all_results[label].get(coin)
            if r:
                print(f"  {label:>12}: ${r['final_equity']:,.2f} ({r['roi']:+.1f}%)")
                if r.get('top_triggers'):
                    for t in r['top_triggers']:
                        print(f"    TOP: {t['date'].strftime('%Y-%m-%d')} {t['reason']} ({t['days_armed']}d armed) @ ${t['price']:.2f}")
                if r.get('conviction_triggers'):
                    for t in r['conviction_triggers']:
                        d = t['details']
                        print(f"    BOTTOM: {t['date'].strftime('%Y-%m-%d')} score={t['score']}/4 short_pnl={t['short_pnl_pct']:+.1f}%")

    # Portfolio summary
    print(f"\n{'='*80}")
    print(f"PORTFOLIO SUMMARY")
    print(f"{'='*80}")
    print(f"  {'Coin':<12} {'Baseline':>10} {'Top Only':>10} {'Bot Only':>10} {'Combined':>10} {'Delta':>10}")
    print(f"  {'-'*65}")

    totals = {k: 0 for k in configs}
    for coin in coins:
        vals = {}
        for label in configs:
            r = all_results[label].get(coin)
            vals[label] = r['final_equity'] if r else 0
            totals[label] += vals[label]
        delta = vals['combined'] - vals['baseline']
        print(f"  {coin:<12} ${vals['baseline']:>8,.0f} ${vals['top_only']:>8,.0f} ${vals['bottom_only']:>8,.0f} ${vals['combined']:>8,.0f} ${delta:>+8,.0f}")

    print(f"  {'-'*65}")
    delta_total = totals['combined'] - totals['baseline']
    for label in configs:
        roi = (totals[label] - capital) / capital * 100
        delta = totals[label] - totals['baseline']
        print(f"  {label:>12}: ${totals[label]:>10,.2f} ({roi:+.1f}%) delta=${delta:+,.0f}")

    print(f"\n  Paper bot baseline: ${totals['baseline']:,.0f}")
    print(f"  Combined (top+bottom): ${totals['combined']:,.0f}")
    print(f"  Net improvement: ${delta_total:+,.0f} ({delta_total/totals['baseline']*100:+.1f}%)")

    return all_results


if __name__ == '__main__':
    run_combined()
