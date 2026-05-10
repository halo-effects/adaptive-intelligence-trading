import os
"""
V13 Signal Library — All phase transition signals in one module.

Signals:
  S1: StochRSI OB exit (1W/2W/3W, configurable threshold)
  S2: StochRSI OS exit (1W/2W/3W, configurable threshold)
  S3: StochRSI divergence (bullish/bearish)
  S4: Bull Market Support Band (20W SMA + 21W EMA)
  S5: Daily SMA50 slope
  S6: Daily HH/HL and LH/LL streaks
  S7: Daily ADX (trending vs ranging)
  S8: CFGI level (fear/greed zones)
  S9: CFGI direction (ROC)
  S10: SMA200 overextension
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import timedelta
from pathlib import Path

DB_PATH = Path(os.environ.get('AIT_CANDLES_DB', str(Path(__file__).resolve().parent.parent / 'data' / 'candles.db')))


# ── Helpers ─────────────────────────────────────────────────────────────

def _stoch_rsi(close, rsi_period=14, stoch_period=14, k_smooth=3, d_smooth=3):
    """Compute Stochastic RSI returning K, D, RSI series."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/rsi_period, min_periods=rsi_period).mean()
    avg_loss = loss.ewm(alpha=1/rsi_period, min_periods=rsi_period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi_low = rsi.rolling(stoch_period).min()
    rsi_high = rsi.rolling(stoch_period).max()
    denom = rsi_high - rsi_low
    denom = denom.replace(0, np.nan)
    stoch_k = 100 * (rsi - rsi_low) / denom
    stoch_k = stoch_k.rolling(k_smooth).mean()
    stoch_d = stoch_k.rolling(d_smooth).mean()
    return stoch_k, stoch_d, rsi


def resample_nweek(daily_close, n_weeks):
    """Resample daily closes to n-week periods. Returns Series."""
    start = daily_close.index[0]
    days = (daily_close.index - start).days
    period = days // (n_weeks * 7)
    grouped = daily_close.groupby(period)
    result = grouped.last()
    # Use last date in each group as index
    dates = daily_close.groupby(period).apply(lambda x: x.index[-1])
    result.index = dates.values
    return result


def resample_nweek_ohlc(daily_df, n_weeks):
    """Resample daily OHLCV to n-week OHLCV. Returns DataFrame."""
    start = daily_df.index[0]
    days = (daily_df.index - start).days
    period = days // (n_weeks * 7)
    grouped = daily_df.groupby(period)
    result = grouped.agg({
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'volume': 'sum'
    })
    dates = daily_df.groupby(period).apply(lambda x: x.index[-1])
    result.index = dates.values
    return result


# ── Data Loading ────────────────────────────────────────────────────────

def load_daily(coin, db_path=None):
    """Load daily candles for a coin from the DB."""
    db = sqlite3.connect(str(db_path or DB_PATH))
    # Search by base coin (e.g., LINK/USDC → LINK/%) to find all quote pairs
    base = coin.split('/')[0] if '/' in coin else coin
    syms = [r[0] for r in db.execute(
        'SELECT DISTINCT symbol FROM candles_daily WHERE symbol LIKE ?',
        (f'{base}/%',)).fetchall()]
    if not syms:
        db.close()
        return None
    # Pick the best symbol: prefer symbols WITH indicators (sma50 populated),
    # then by widest valid date range. This fixes BTC/ETH where the USDC pair
    # has wider range (from Binance backfill) but no indicators, while the
    # USDT pair has indicators.
    def _score(s):
        r = db.execute(
            'SELECT MAX(timestamp) - MIN(timestamp), '
            'SUM(CASE WHEN sma50 IS NOT NULL AND sma50 != 0 THEN 1 ELSE 0 END) '
            'FROM candles_daily '
            'WHERE symbol=? AND timestamp IS NOT NULL AND timestamp > 0', (s,)).fetchone()
        date_range = r[0] or 0
        has_indicators = 1 if (r[1] or 0) > 0 else 0
        # Prefer symbols with indicators (1e15 bonus), then by date range
        return (has_indicators * 10**15) + date_range
    best = max(syms, key=_score)
    df = pd.read_sql(
        'SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp',
        db, params=[best])
    db.close()
    df['dt'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('dt', inplace=True)
    # Deduplicate index — duplicate timestamps cause InvalidIndexError downstream
    if not df.index.is_unique:
        df = df[~df.index.duplicated(keep='last')]
    df.attrs['symbol'] = best
    return df


def load_cfgi(coin, db_path=None):
    """Load CFGI history for a coin from the DB (cfgi_daily table)."""
    db = sqlite3.connect(str(db_path or DB_PATH))
    # Extract base coin (e.g., XRP/USDC → XRP) for consistent matching
    base = coin.split('/')[0].upper() if '/' in coin else coin.upper()
    try:
        # cfgi_daily has symbol column like 'BTC/USDC' or 'BTC'
        df = pd.read_sql(
            "SELECT * FROM cfgi_daily WHERE symbol LIKE ? ORDER BY date",
            db, params=[f'{base}%'])
    except Exception:
        db.close()
        return None
    db.close()
    if len(df) == 0:
        return None
    df['dt'] = pd.to_datetime(df['date'], format='mixed')
    df.set_index('dt', inplace=True)
    # Normalize to date only (remove time component)
    df.index = df.index.normalize()
    # Rename cfgi column to value for consistency
    if 'cfgi' in df.columns:
        df['value'] = pd.to_numeric(df['cfgi'], errors='coerce')
    # Deduplicate
    df = df[~df.index.duplicated(keep='last')]
    return df


# ── Signal Computers ────────────────────────────────────────────────────

class StochRSISignal:
    """S1/S2: StochRSI OB/OS exit signals at various timeframes and thresholds."""

    def __init__(self, daily, n_weeks=2):
        self.n_weeks = n_weeks
        if n_weeks == 1:
            resampled = daily['close'].resample('W').last().dropna()
        else:
            resampled = resample_nweek(daily['close'], n_weeks)
        self.k, self.d, self.rsi = _stoch_rsi(resampled)
        self.close = resampled
        self.df = pd.DataFrame({
            'close': resampled, 'K': self.k, 'D': self.d, 'rsi': self.rsi
        })

    def ob_exits(self, threshold=80):
        """Find dates where K crosses below threshold from above."""
        prev_k = self.df['K'].shift(1)
        mask = (prev_k >= threshold) & (self.df['K'] < threshold)
        return self.df[mask].copy()

    def os_exits(self, threshold=20):
        """Find dates where K crosses above threshold from below."""
        prev_k = self.df['K'].shift(1)
        mask = (prev_k <= threshold) & (self.df['K'] > threshold)
        return self.df[mask].copy()

    def is_ob(self, date, threshold=80):
        """Was StochRSI overbought at or near this date?"""
        nearby = self.df[self.df.index <= date].tail(1)
        if len(nearby) == 0:
            return False
        return nearby['K'].iloc[0] > threshold

    def is_os(self, date, threshold=20):
        """Was StochRSI oversold at or near this date?"""
        nearby = self.df[self.df.index <= date].tail(1)
        if len(nearby) == 0:
            return False
        return nearby['K'].iloc[0] < threshold

    def was_ob_recently(self, date, lookback_weeks=4, threshold=80):
        """Was StochRSI OB at any point in the last N weeks?"""
        start = date - timedelta(weeks=lookback_weeks)
        window = self.df[(self.df.index >= start) & (self.df.index <= date)]
        return (window['K'] > threshold).any() if len(window) > 0 else False

    def get_k_at(self, date):
        """Get K value at or just before a date."""
        nearby = self.df[self.df.index <= date].tail(1)
        return nearby['K'].iloc[0] if len(nearby) > 0 else np.nan


class StochRSIDivergence:
    """S3: StochRSI divergence detection (bullish/bearish)."""

    def __init__(self, daily, n_weeks=1):
        if n_weeks == 1:
            resampled_close = daily['close'].resample('W').last().dropna()
            resampled_low = daily['low'].resample('W').min().dropna()
            resampled_high = daily['high'].resample('W').max().dropna()
        else:
            ohlc = resample_nweek_ohlc(daily[['open','high','low','close','volume']], n_weeks)
            resampled_close = ohlc['close']
            resampled_low = ohlc['low']
            resampled_high = ohlc['high']

        self.k, self.d, _ = _stoch_rsi(resampled_close)
        self.close = resampled_close
        self.low = resampled_low
        self.high = resampled_high

    def _find_extremes(self, series, order=2):
        mins, maxs = [], []
        vals = series.values
        idx = series.index
        for i in range(order, len(vals) - order):
            if np.isnan(vals[i]):
                continue
            if all(vals[i] <= vals[i-j] for j in range(1, order+1) if not np.isnan(vals[i-j])) and \
               all(vals[i] <= vals[i+j] for j in range(1, order+1) if not np.isnan(vals[i+j])):
                mins.append((idx[i], vals[i]))
            if all(vals[i] >= vals[i-j] for j in range(1, order+1) if not np.isnan(vals[i-j])) and \
               all(vals[i] >= vals[i+j] for j in range(1, order+1) if not np.isnan(vals[i+j])):
                maxs.append((idx[i], vals[i]))
        return mins, maxs

    def find(self, lookback_weeks=20, since='2024-01-01'):
        """Find bullish and bearish divergences."""
        price_mins, price_maxs = self._find_extremes(self.low, order=2)
        stoch_mins, stoch_maxs = self._find_extremes(self.k, order=2)

        bullish, bearish = [], []

        # Bullish: consecutive price lows going lower, StochRSI lows going higher
        for i in range(1, len(price_mins)):
            d1, p1 = price_mins[i-1]
            d2, p2 = price_mins[i]
            if p2 >= p1 or (d2 - d1).days > lookback_weeks * 7:
                continue
            if d2 < pd.Timestamp(since):
                continue
            s1 = s2 = None
            for sd, sv in stoch_mins:
                if abs((sd - d1).days) <= 14:
                    s1 = sv
                if abs((sd - d2).days) <= 14:
                    s2 = sv
            if s1 is not None and s2 is not None and s2 > s1:
                bullish.append({'date': d2, 'type': 'bullish',
                               'price1': p1, 'price2': p2,
                               'stoch1': s1, 'stoch2': s2})

        # Bearish: consecutive price highs going higher, StochRSI highs going lower
        for i in range(1, len(price_maxs)):
            d1, p1 = price_maxs[i-1]
            d2, p2 = price_maxs[i]
            if p2 <= p1 or (d2 - d1).days > lookback_weeks * 7:
                continue
            if d2 < pd.Timestamp(since):
                continue
            s1 = s2 = None
            for sd, sv in stoch_maxs:
                if abs((sd - d1).days) <= 14:
                    s1 = sv
                if abs((sd - d2).days) <= 14:
                    s2 = sv
            if s1 is not None and s2 is not None and s2 < s1:
                bearish.append({'date': d2, 'type': 'bearish',
                               'price1': p1, 'price2': p2,
                               'stoch1': s1, 'stoch2': s2})

        return bullish, bearish


class BullMarketSupportBand:
    """S4: Bull Market Support Band (20-week SMA + 21-week EMA)."""

    def __init__(self, daily):
        self.sma_20w = daily['close'].rolling(140).mean()
        self.ema_21w = daily['close'].ewm(span=147).mean()
        self.close = daily['close']
        self.band_top = pd.concat([self.sma_20w, self.ema_21w], axis=1).max(axis=1)
        self.band_bot = pd.concat([self.sma_20w, self.ema_21w], axis=1).min(axis=1)

    def status_at(self, date):
        """Returns 'ABOVE', 'BELOW', or 'IN_BAND' at a date."""
        if date not in self.close.index:
            # Find nearest
            mask = self.close.index <= date
            if not mask.any():
                return 'UNKNOWN'
            date = self.close.index[mask][-1]
        c = self.close.loc[date]
        bt = self.band_top.loc[date]
        bb = self.band_bot.loc[date]
        if pd.isna(bt):
            return 'UNKNOWN'
        if c > bt:
            return 'ABOVE'
        elif c < bb:
            return 'BELOW'
        return 'IN_BAND'

    def sustained_below(self, date, weeks=2):
        """Has price been below the band for N weeks sustained?"""
        days = weeks * 7
        start = date - timedelta(days=days)
        window = self.close[(self.close.index >= start) & (self.close.index <= date)]
        band = self.band_bot[(self.band_bot.index >= start) & (self.band_bot.index <= date)]
        if len(window) < days * 0.5:
            return False
        common = window.index.intersection(band.index)
        if len(common) == 0:
            return False
        return (window[common] < band[common]).all()

    def lost_support(self, since='2024-01-01'):
        """Find dates where price crossed below band."""
        valid = self.close.index.intersection(self.band_top.dropna().index)
        above = self.close[valid] > self.band_top[valid]
        prev = above.shift(1)
        lost = valid[(prev == True) & (above == False)]
        return [d for d in lost if d >= pd.Timestamp(since)]


class DailyStructure:
    """S5/S6/S7: Daily SMA50 slope, HH/HL streaks, ADX."""

    def __init__(self, daily):
        self.daily = daily

    @staticmethod
    def _safe_float(val):
        """Convert value to float, returning np.nan for None/invalid."""
        if val is None:
            return np.nan
        try:
            return float(val)
        except (TypeError, ValueError):
            return np.nan

    def sma50_slope_at(self, date, window=10):
        """SMA50 slope over N days ending at date."""
        end = self.daily[self.daily.index <= date]
        if len(end) < window or 'sma50' not in end.columns:
            return np.nan
        vals = end['sma50'].tail(window).apply(self._safe_float)
        if vals.isna().any():
            return np.nan
        # Slope as % change over window
        return (vals.iloc[-1] - vals.iloc[0]) / vals.iloc[0] * 100

    def sma50_slope_positive(self, date, window=10):
        return self.sma50_slope_at(date, window) > 0

    def sma50_slope_negative(self, date, window=10):
        return self.sma50_slope_at(date, window) < 0

    def hh_hl_streak(self, date, min_streak=2):
        """Check if there are min_streak consecutive HH/HL days at date."""
        end = self.daily[self.daily.index <= date]
        if 'consec_hh_hl' not in end.columns or len(end) == 0:
            return False
        val = end['consec_hh_hl'].iloc[-1]
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return False
        return val >= min_streak

    def lh_ll_streak(self, date, min_streak=2):
        """Check if there are min_streak consecutive LH/LL days at date."""
        end = self.daily[self.daily.index <= date]
        if 'consec_lh_ll' not in end.columns or len(end) == 0:
            return False
        val = end['consec_lh_ll'].iloc[-1]
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return False
        return val >= min_streak

    def adx_at(self, date):
        end = self.daily[self.daily.index <= date]
        if 'adx' not in end.columns or len(end) == 0:
            return np.nan
        return self._safe_float(end['adx'].iloc[-1])

    def is_ranging(self, date, threshold=20):
        adx = self.adx_at(date)
        return adx < threshold if not np.isnan(adx) else False

    def is_trending(self, date, threshold=25):
        adx = self.adx_at(date)
        return adx > threshold if not np.isnan(adx) else False

    def price_vs_sma50(self, date):
        end = self.daily[self.daily.index <= date]
        if 'price_vs_sma50' not in end.columns or len(end) == 0:
            return np.nan
        return self._safe_float(end['price_vs_sma50'].iloc[-1])

    def price_vs_sma200(self, date):
        end = self.daily[self.daily.index <= date]
        if 'price_vs_sma200' not in end.columns or len(end) == 0:
            return np.nan
        return self._safe_float(end['price_vs_sma200'].iloc[-1])

    def bb_width_at(self, date):
        end = self.daily[self.daily.index <= date]
        if 'bb_width' not in end.columns or len(end) == 0:
            return np.nan
        return self._safe_float(end['bb_width'].iloc[-1])


class CFGISignal:
    """S8/S9: CFGI level and direction signals."""

    def __init__(self, cfgi_df):
        self.cfgi = cfgi_df

    def value_at(self, date):
        """Get CFGI value at date."""
        if self.cfgi is None:
            return np.nan
        nearby = self.cfgi[self.cfgi.index <= date].tail(1)
        if len(nearby) == 0:
            return np.nan
        val = nearby['value'].iloc[0] if 'value' in nearby.columns else np.nan
        return float(val) if not pd.isna(val) else np.nan

    def in_fear(self, date, threshold=30):
        v = self.value_at(date)
        return v < threshold if not np.isnan(v) else False

    def in_greed(self, date, threshold=70):
        v = self.value_at(date)
        return v > threshold if not np.isnan(v) else False

    def roc(self, date, period=7):
        """CFGI rate of change over N days."""
        if self.cfgi is None or 'value' not in self.cfgi.columns:
            return np.nan
        end = self.cfgi[self.cfgi.index <= date].tail(period + 1)
        if len(end) < period + 1:
            return np.nan
        v_now = float(end['value'].iloc[-1])
        v_prev = float(end['value'].iloc[0])
        return v_now - v_prev

    def declining_from_greed(self, date, greed_threshold=70, drop_to=50, lookback_days=30):
        """Was CFGI above greed_threshold recently and now below drop_to?"""
        if self.cfgi is None or 'value' not in self.cfgi.columns:
            return False
        start = date - timedelta(days=lookback_days)
        window = self.cfgi[(self.cfgi.index >= start) & (self.cfgi.index <= date)]
        if len(window) < 5:
            return False
        was_greedy = (window['value'].astype(float) > greed_threshold).any()
        current = float(window['value'].iloc[-1])
        return was_greedy and current < drop_to

    def rising_from_fear(self, date, fear_threshold=25, rise_to=40, lookback_days=30):
        """Was CFGI below fear_threshold recently and now above rise_to?"""
        if self.cfgi is None or 'value' not in self.cfgi.columns:
            return False
        start = date - timedelta(days=lookback_days)
        window = self.cfgi[(self.cfgi.index >= start) & (self.cfgi.index <= date)]
        if len(window) < 5:
            return False
        was_fearful = (window['value'].astype(float) < fear_threshold).any()
        current = float(window['value'].iloc[-1])
        return was_fearful and current > rise_to


class SMA200Overextension:
    """S10: SMA200 overextension filter."""

    def __init__(self, daily):
        self.daily = daily

    def overextension_at(self, date):
        """Price vs SMA200 as %."""
        end = self.daily[self.daily.index <= date]
        if 'price_vs_sma200' not in end.columns or len(end) == 0:
            return np.nan
        return end['price_vs_sma200'].iloc[-1]

    def is_overextended(self, date, threshold=20):
        """Is price >threshold% above SMA200?"""
        v = self.overextension_at(date)
        return v > threshold if not np.isnan(v) else False


# ── Composite Signal Pack ───────────────────────────────────────────────

class V13SignalPack:
    """All V13 signals for a single coin, ready for matrix testing."""

    def __init__(self, coin, db_path=None):
        self.coin = coin
        self.daily = load_daily(coin, db_path)
        if self.daily is None:
            raise ValueError(f"No daily data for {coin}")
        self.cfgi_df = load_cfgi(coin, db_path)

        # Build all signal objects
        self.stoch_1w = StochRSISignal(self.daily, n_weeks=1)
        self.stoch_2w = StochRSISignal(self.daily, n_weeks=2)
        self.stoch_3w = StochRSISignal(self.daily, n_weeks=3)

        self.div_1w = StochRSIDivergence(self.daily, n_weeks=1)
        self.div_2w = StochRSIDivergence(self.daily, n_weeks=2)

        self.bmsb = BullMarketSupportBand(self.daily)
        self.structure = DailyStructure(self.daily)
        self.cfgi = CFGISignal(self.cfgi_df)
        self.sma200 = SMA200Overextension(self.daily)

    def get_stoch(self, n_weeks):
        if n_weeks == 1: return self.stoch_1w
        if n_weeks == 2: return self.stoch_2w
        if n_weeks == 3: return self.stoch_3w
        raise ValueError(f"Unsupported n_weeks={n_weeks}")

    def snapshot_at(self, date):
        """Get all signal values at a specific date. Useful for debugging."""
        return {
            'date': date,
            'coin': self.coin,
            'stoch_1w_K': self.stoch_1w.get_k_at(date),
            'stoch_2w_K': self.stoch_2w.get_k_at(date),
            'stoch_3w_K': self.stoch_3w.get_k_at(date),
            'bmsb': self.bmsb.status_at(date),
            'sma50_slope': self.structure.sma50_slope_at(date),
            'hh_hl': self.structure.hh_hl_streak(date),
            'lh_ll': self.structure.lh_ll_streak(date),
            'adx': self.structure.adx_at(date),
            'cfgi': self.cfgi.value_at(date),
            'cfgi_roc7': self.cfgi.roc(date, 7),
            'sma200_overext': self.sma200.overextension_at(date),
            'price_vs_sma50': self.structure.price_vs_sma50(date),
        }

    def measure_outcome(self, date, days_forward=60, direction='down'):
        """Measure price outcome after a signal date."""
        future = self.daily[self.daily.index >= date].head(days_forward)
        if len(future) < 5:
            return {'max_up': np.nan, 'max_down': np.nan, 'end_pct': np.nan}
        entry = future['close'].iloc[0]
        return {
            'max_up': (future['high'].max() - entry) / entry * 100,
            'max_down': (future['low'].min() - entry) / entry * 100,
            'end_pct': (future['close'].iloc[-1] - entry) / entry * 100,
        }


# ── Quick test ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    for coin in ['BTC', 'ETH', 'SOL']:
        try:
            pack = V13SignalPack(coin)
        except ValueError as e:
            print(f"Skip {coin}: {e}")
            continue

        print(f"\n{'='*60}")
        print(f"  {coin} — Signal Pack Loaded")
        print(f"{'='*60}")

        # 2W StochRSI top signals
        tops = pack.stoch_2w.ob_exits(threshold=80)
        tops = tops[tops.index >= '2024-01-01']
        print(f"\n  2W StochRSI OB exits (>80): {len(tops)}")
        for dt, row in tops.iterrows():
            snap = pack.snapshot_at(dt)
            out = pack.measure_outcome(dt, 60)
            print(f"    {dt.date()}: K={row['K']:.0f}, BMSB={snap['bmsb']}, "
                  f"SMA50slope={snap['sma50_slope']:.2f}%, CFGI={snap['cfgi']}, "
                  f"60d_dd={out['max_down']:.1f}%")

        # 2W bottom signals
        bots = pack.stoch_2w.os_exits(threshold=20)
        bots = bots[bots.index >= '2024-01-01']
        print(f"\n  2W StochRSI OS exits (<20): {len(bots)}")
        for dt, row in bots.iterrows():
            snap = pack.snapshot_at(dt)
            out = pack.measure_outcome(dt, 90)
            print(f"    {dt.date()}: K={row['K']:.0f}, BMSB={snap['bmsb']}, "
                  f"SMA50slope={snap['sma50_slope']:.2f}%, CFGI={snap['cfgi']}, "
                  f"90d_up={out['max_up']:.1f}%")

        # Current snapshot
        last_date = pack.daily.index[-1]
        snap = pack.snapshot_at(last_date)
        print(f"\n  Current ({last_date.date()}):")
        for k, v in snap.items():
            if k not in ('date', 'coin'):
                print(f"    {k}: {v}")
