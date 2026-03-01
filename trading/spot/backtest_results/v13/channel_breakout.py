"""
Channel Breakout + Retest detector for V13 cold start fallback.

Detects when price breaks out of a long-established range and retests:
- BULLISH: Break above channel top → retest → hold = MARKUP entry
- BEARISH: Break below channel bottom → retest → reject = MARKDOWN entry

Uses Bollinger Band width squeeze (< threshold) + ADX < 20 to identify channels,
then tracks breakout + retest confirmation.

Brett's rule: "If it re-enters the channel, the breakout is invalidated."
"""
import pandas as pd
import numpy as np


class ChannelBreakout:
    """Detect channel breakouts with retest confirmation."""

    def __init__(self, daily_df: pd.DataFrame,
                 squeeze_bb_width=15.0,     # BB width % below this = squeeze
                 squeeze_adx=20.0,          # ADX below this = no trend (ranging)
                 min_channel_days=14,        # Minimum days in channel before breakout counts
                 retest_window_days=14,      # How many days after breakout to look for retest
                 retest_tolerance=0.02):     # How close to channel edge = retest (2%)
        self.df = daily_df.copy()
        self.squeeze_bb = squeeze_bb_width
        self.squeeze_adx = squeeze_adx
        self.min_channel_days = min_channel_days
        self.retest_window = retest_window_days
        self.retest_tol = retest_tolerance

        self._detect_channels()
        self._detect_breakouts()

    def _detect_channels(self):
        """Identify channel/range periods from tight rolling price range."""
        df = self.df
        # Method: rolling 20-day high-low range as % of low
        # Channel = rolling range below threshold OR (BB squeeze AND low ADX)
        roll_high = df['high'].rolling(20).max()
        roll_low = df['low'].rolling(20).min()
        roll_range = (roll_high - roll_low) / roll_low * 100
        df['roll_range'] = roll_range
        # Channel = rolling range < 20% (tight consolidation)
        # OR classic BB squeeze + low ADX
        df['in_channel'] = (roll_range < 20) | ((df['bb_width'] < self.squeeze_bb) & (df['adx'] < self.squeeze_adx))

        # Find channel periods (start, end, high, low)
        self.channels = []
        in_ch = False
        ch_start = None
        ch_high = 0
        ch_low = float('inf')

        for date, row in df.iterrows():
            if row['in_channel']:
                if not in_ch:
                    ch_start = date
                    ch_high = row['high']
                    ch_low = row['low']
                    in_ch = True
                else:
                    ch_high = max(ch_high, row['high'])
                    ch_low = min(ch_low, row['low'])
            else:
                if in_ch:
                    days = (date - ch_start).days
                    if days >= self.min_channel_days:
                        self.channels.append({
                            'start': ch_start,
                            'end': date,
                            'days': days,
                            'high': ch_high,
                            'low': ch_low,
                            'mid': (ch_high + ch_low) / 2,
                            'width_pct': (ch_high - ch_low) / ch_low * 100
                        })
                    in_ch = False

        # Handle channel still active at end
        if in_ch and ch_start is not None:
            days = (df.index[-1] - ch_start).days
            if days >= self.min_channel_days:
                self.channels.append({
                    'start': ch_start,
                    'end': df.index[-1],
                    'days': days,
                    'high': ch_high,
                    'low': ch_low,
                    'mid': (ch_high + ch_low) / 2,
                    'width_pct': (ch_high - ch_low) / ch_low * 100
                })

    def _detect_breakouts(self):
        """Detect breakouts from channels with retest confirmation."""
        df = self.df
        self.breakouts = []

        for ch in self.channels:
            ch_end = ch['end']
            ch_high = ch['high']
            ch_low = ch['low']

            # Look at candles after channel ends
            post = df[df.index > ch_end]
            if len(post) == 0:
                continue

            # Check first candle after channel — did it break up or down?
            breakout_detected = False
            breakout_dir = None
            breakout_date = None
            breakout_price = None

            for date, row in post.iterrows():
                # Bullish breakout: close above channel high
                if not breakout_detected and row['close'] > ch_high:
                    breakout_detected = True
                    breakout_dir = 'BULLISH'
                    breakout_date = date
                    breakout_price = row['close']
                    break
                # Bearish breakout: close below channel low
                elif not breakout_detected and row['close'] < ch_low:
                    breakout_detected = True
                    breakout_dir = 'BEARISH'
                    breakout_date = date
                    breakout_price = row['close']
                    break

            if not breakout_detected:
                continue

            # Now look for retests (can retest multiple times — each hold = stronger)
            retest_start = df[df.index > breakout_date]
            retest_count = 0       # Number of successful retests
            retest_found = False
            retest_held = False
            retest_date = None      # Date of first confirmed retest
            last_retest_date = None # Date of most recent retest
            invalidated = False
            in_retest = False       # Currently in a retest pullback

            for date, row in retest_start.iterrows():
                days_since = (date - breakout_date).days
                if days_since > self.retest_window * 3:  # Extended window for multiple retests
                    break

                if breakout_dir == 'BULLISH':
                    near_top = ch_high * (1 + self.retest_tol)
                    # Detect start of a retest (price pulls back near channel top)
                    if not in_retest and row['low'] <= near_top:
                        in_retest = True
                        # Did it re-enter the channel? (close below ch_high)
                        if row['close'] < ch_high:
                            invalidated = True
                            break
                    # During retest, check if it re-enters channel
                    elif in_retest and row['close'] < ch_high:
                        invalidated = True
                        break
                    # After retest touch, check if it held (bounced back above)
                    elif in_retest and row['close'] > ch_high * (1 + self.retest_tol):
                        # Retest held — count it
                        retest_count += 1
                        retest_found = True
                        retest_held = True
                        if retest_date is None:
                            retest_date = date
                        last_retest_date = date
                        in_retest = False  # Reset for potential next retest

                elif breakout_dir == 'BEARISH':
                    near_bottom = ch_low * (1 - self.retest_tol)
                    if not in_retest and row['high'] >= near_bottom:
                        in_retest = True
                        if row['close'] > ch_low:
                            invalidated = True
                            break
                    elif in_retest and row['close'] > ch_low:
                        invalidated = True
                        break
                    elif in_retest and row['close'] < ch_low * (1 - self.retest_tol):
                        retest_count += 1
                        retest_found = True
                        retest_held = True
                        if retest_date is None:
                            retest_date = date
                        last_retest_date = date
                        in_retest = False

            # Also count breakouts that just run (no retest) — strong momentum
            # If price moves >10% from breakout without retest, confirm anyway
            no_retest_confirm = False
            if not retest_found:
                for date, row in retest_start.iterrows():
                    days_since = (date - breakout_date).days
                    if days_since > self.retest_window:
                        break
                    if breakout_dir == 'BULLISH':
                        move = (row['close'] - breakout_price) / breakout_price
                        if move > 0.10:  # 10% run without retest = confirmed
                            no_retest_confirm = True
                            retest_date = date
                            retest_held = True
                            break
                    elif breakout_dir == 'BEARISH':
                        move = (breakout_price - row['close']) / breakout_price
                        if move > 0.10:
                            no_retest_confirm = True
                            retest_date = date
                            retest_held = True
                            break

            confirmed = (retest_found and retest_held and not invalidated) or no_retest_confirm

            self.breakouts.append({
                'channel_start': ch['start'],
                'channel_end': ch['end'],
                'channel_days': ch['days'],
                'channel_high': ch_high,
                'channel_low': ch_low,
                'direction': breakout_dir,
                'breakout_date': breakout_date,
                'breakout_price': breakout_price,
                'retest_date': retest_date,
                'retest_found': retest_found,
                'retest_held': retest_held,
                'retest_count': retest_count,
                'invalidated': invalidated,
                'no_retest_run': no_retest_confirm,
                'confirmed': confirmed,
            })

    def confirmed_at(self, date):
        """Check if there's a confirmed breakout signal on exactly this date.
        Returns: 'MARKUP', 'MARKDOWN', or None.
        Signal fires only on the confirmation date (retest hold or run-away date)."""
        for bo in self.breakouts:
            if not bo['confirmed']:
                continue
            # Signal fires on the specific confirmation date only
            confirm_date = bo['retest_date'] or bo['breakout_date']
            if confirm_date and confirm_date == date:
                if bo['direction'] == 'BULLISH':
                    return 'MARKUP'
                elif bo['direction'] == 'BEARISH':
                    return 'MARKDOWN'
        return None

    def first_confirmed_after(self, start_date):
        """Get the first confirmed breakout after start_date.
        Returns: (date, 'MARKUP'/'MARKDOWN') or (None, None)."""
        best_date = None
        best_dir = None
        for bo in self.breakouts:
            if not bo['confirmed']:
                continue
            confirm_date = bo['retest_date'] or bo['breakout_date']
            if confirm_date and confirm_date > start_date:
                if best_date is None or confirm_date < best_date:
                    best_date = confirm_date
                    best_dir = 'MARKUP' if bo['direction'] == 'BULLISH' else 'MARKDOWN'
        return best_date, best_dir

    def print_summary(self):
        """Print detected channels and breakouts."""
        print(f"\n  Channels detected: {len(self.channels)}")
        for ch in self.channels:
            print(f"    {ch['start'].date()} -> {ch['end'].date()} ({ch['days']}d) "
                  f"H=${ch['high']:.4f} L=${ch['low']:.4f} W={ch['width_pct']:.1f}%")

        print(f"\n  Breakouts detected: {len(self.breakouts)}")
        for bo in self.breakouts:
            status = "✅ CONFIRMED" if bo['confirmed'] else ("❌ INVALIDATED" if bo['invalidated'] else "⏳ UNCONFIRMED")
            retest_info = ""
            if bo['retest_found']:
                count = bo.get('retest_count', 1)
                retest_info = f" retest={bo['retest_date'].date() if bo['retest_date'] else '?'} ({count}x)"
            elif bo['no_retest_run']:
                retest_info = " (run without retest)"
            print(f"    {bo['breakout_date'].date()} {bo['direction']} @ ${bo['breakout_price']:.4f} "
                  f"from {bo['channel_days']}d channel [{bo['channel_low']:.4f}-{bo['channel_high']:.4f}]"
                  f"{retest_info} {status}")


def test_coins():
    """Test channel detection on BNB and XRP."""
    import sqlite3
    from pathlib import Path

    DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "candles.db"
    db = sqlite3.connect(str(DB_PATH))

    for coin in ['XRP/USDT', 'BNB/USDT', 'BTC/USDC', 'ETH/USDC', 'SOL/USDC']:
        print(f"\n{'='*60}")
        print(f"  {coin}")
        print(f"{'='*60}")

        df = pd.read_sql(
            'SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp',
            db, params=(coin,))
        if len(df) == 0:
            print("  No data")
            continue

        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('date', inplace=True)

        cb = ChannelBreakout(df)
        cb.print_summary()

    db.close()


if __name__ == '__main__':
    test_coins()
