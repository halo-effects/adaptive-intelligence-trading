"""Build 3-day candles from daily data and compute key signals.

Signals computed:
- SMA50/SMA200 (death cross / golden cross)
- HH_HL / LH_LL streaks (structure confirmation)
- ADX (trend strength)
- RSI14
- Price vs SMA200 (overextension)

Usage:
    from build_3d_signals import build_3d_signals
    df_3d = build_3d_signals('ETH/USDC')
"""
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'candles.db'


def _compute_adx(df, period=14):
    """Compute ADX from OHLC data."""
    high = df['high']
    low = df['low']
    close = df['close']
    
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    
    atr = tr.ewm(alpha=1/period, min_periods=period).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr)
    
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1/period, min_periods=period).mean()
    return adx, plus_di, minus_di


def _compute_streaks(df):
    """Compute HH_HL and LH_LL consecutive streaks from 3D candles."""
    highs = df['high']
    lows = df['low']
    
    hh = highs > highs.shift(1)  # Higher high
    hl = lows > lows.shift(1)    # Higher low
    lh = highs < highs.shift(1)  # Lower high
    ll = lows < lows.shift(1)    # Lower low
    
    hh_hl = hh & hl  # Bullish candle (higher high AND higher low)
    lh_ll = lh & ll  # Bearish candle (lower high AND lower low)
    
    # Compute consecutive streaks
    hh_hl_streak = pd.Series(0, index=df.index, dtype=int)
    lh_ll_streak = pd.Series(0, index=df.index, dtype=int)
    
    for i in range(1, len(df)):
        if hh_hl.iloc[i]:
            hh_hl_streak.iloc[i] = hh_hl_streak.iloc[i-1] + 1
        if lh_ll.iloc[i]:
            lh_ll_streak.iloc[i] = lh_ll_streak.iloc[i-1] + 1
    
    return hh_hl_streak, lh_ll_streak


def build_3d_candles(symbol):
    """Aggregate daily candles into 3-day candles."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT date, open, high, low, close, volume FROM candles_daily WHERE symbol=? ORDER BY date",
        conn, params=(symbol,)
    )
    conn.close()
    
    if df.empty:
        raise ValueError(f"No daily data for {symbol}")
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    
    # Group into 3-day periods from the start
    # Use integer division to assign group IDs
    df['group'] = np.arange(len(df)) // 3
    
    agg = df.groupby('group').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })
    
    # Use the last date of each group as the index
    dates = df.groupby('group').apply(lambda x: x.index[-1])
    agg.index = dates.values
    agg.index.name = 'date'
    
    return agg


def build_3d_signals(symbol):
    """Build 3-day candles with all signals."""
    df = build_3d_candles(symbol)
    
    # SMAs
    df['sma20'] = df['close'].rolling(20).mean()
    df['sma50'] = df['close'].rolling(50).mean()
    df['sma200'] = df['close'].rolling(200).mean()
    
    # Death cross / Golden cross
    df['death_cross'] = (df['sma50'] < df['sma200']).astype(int)
    df['golden_cross'] = (df['sma50'] > df['sma200']).astype(int)
    
    # Detect transitions
    df['death_cross_signal'] = (df['death_cross'].diff() == 1).astype(int)
    df['golden_cross_signal'] = (df['golden_cross'].diff() == 1).astype(int)
    
    # ADX
    df['adx'], df['plus_di'], df['minus_di'] = _compute_adx(df)
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0.0).ewm(alpha=1/14, min_periods=14).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/14, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi14'] = 100 - (100 / (1 + rs))
    
    # Structure streaks
    df['hh_hl_streak'], df['lh_ll_streak'] = _compute_streaks(df)
    
    # Price vs SMA200
    df['price_vs_sma200'] = ((df['close'] - df['sma200']) / df['sma200'] * 100)
    
    # SMA50 slope (% change over 5 periods = 15 days)
    df['sma50_slope'] = df['sma50'].pct_change(5) * 100
    
    return df


if __name__ == '__main__':
    for coin in ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']:
        df = build_3d_signals(coin)
        print(f"\n{'='*70}")
        print(f"{coin}: {len(df)} 3D candles ({df.index[0].date()} to {df.index[-1].date()})")
        print(f"{'='*70}")
        
        # Death cross transitions
        dc_dates = df[df['death_cross_signal'] == 1].index
        gc_dates = df[df['golden_cross_signal'] == 1].index
        print(f"\n  Death Crosses ({len(dc_dates)}):")
        for d in dc_dates:
            price = df.loc[d, 'close']
            adx = df.loc[d, 'adx']
            lh_ll = df.loc[d, 'lh_ll_streak']
            print(f"    {d.date()}: price=${price:,.0f}, ADX={adx:.0f}, LH_LL={lh_ll}")
        
        print(f"\n  Golden Crosses ({len(gc_dates)}):")
        for d in gc_dates:
            price = df.loc[d, 'close']
            adx = df.loc[d, 'adx']
            hh_hl = df.loc[d, 'hh_hl_streak']
            print(f"    {d.date()}: price=${price:,.0f}, ADX={adx:.0f}, HH_HL={hh_hl}")
        
        # Count chattering (how many transitions total)
        total_transitions = len(dc_dates) + len(gc_dates)
        years = (df.index[-1] - df.index[0]).days / 365.25
        print(f"\n  Total transitions: {total_transitions} over {years:.1f} years = {total_transitions/years:.1f}/year")
        
        # Current state
        last = df.iloc[-1]
        state = "BEAR (death cross)" if last['death_cross'] else "BULL (golden cross)"
        print(f"\n  Current: {state}, ADX={last['adx']:.0f}, HH_HL={last['hh_hl_streak']}, LH_LL={last['lh_ll_streak']}")
