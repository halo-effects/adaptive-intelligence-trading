"""
Build daily candles from 1h candles in the candle DB.
Aggregates: first open, max high, min low, last close, sum volume.
Also precomputes daily indicators: SMA50, SMA200, BB(20), ADX(14), ATR(14).
"""
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'

COINS = [
    "AAVE/USDT", "ADA/USDT", "ALGO/USDT", "ARB/USDT", "ASTER/USDT",
    "ATOM/USDT", "AVAX/USDT", "AXS/USDT", "BCH/USDT", "BNB/USDT",
    "BONK/USDT", "BTC/USDT", "CRV/USDT", "DOGE/USDT", "DOT/USDT",
    "ETH/USDT", "FET/USDT", "FIL/USDT", "FLOKI/USDT", "FTM/USDT",
    "GALA/USDT", "GRT/USDT", "HYPE/USDC", "INJ/USDT", "JUP/USDT",
    "LINK/USDT", "LTC/USDT", "MANA/USDT", "MATIC/USDT", "NEAR/USDT",
    "PEPE/USDC", "RUNE/USDT", "SAND/USDT", "SEI/USDT", "SHIB/USDT",
    "SOL/USDT", "SUI/USDT", "TAO/USDT", "TON/USDT", "TRUMP/USDC",
    "UNI/USDT", "WIF/USDT", "XRP/USDT", "ZEC/USDT",
]


def aggregate_daily(df_1h):
    """Aggregate 1h OHLCV to daily OHLCV."""
    df = df_1h.copy()
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.floor('D')
    daily = df.groupby('date').agg(
        timestamp=('timestamp', 'first'),
        open=('open', 'first'),
        high=('high', 'max'),
        low=('low', 'min'),
        close=('close', 'last'),
        volume=('volume', 'sum'),
        candle_count=('timestamp', 'count'),
    ).reset_index()

    # Keep rows with >=20 candles (full days) OR the last row (current partial day)
    daily['is_last'] = daily.index == len(daily) - 1
    daily = daily[(daily['candle_count'] >= 20) | daily['is_last']].reset_index(drop=True)
    daily = daily.drop(columns=['is_last'])
    return daily


def compute_indicators(daily):
    """Compute daily indicators for phase detection."""
    df = daily.copy()

    # SMAs
    df['sma20'] = df['close'].rolling(20).mean()
    df['sma50'] = df['close'].rolling(50).mean()
    df['sma200'] = df['close'].rolling(200).mean()

    # Bollinger Bands (20)
    df['bb_mid'] = df['sma20']
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid'] * 100
    df['bb_pct'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower']) * 100

    # ATR(14)
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            np.abs(df['high'] - df['close'].shift(1)),
            np.abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr14'] = df['tr'].ewm(alpha=1/14, adjust=False).mean()
    df['atr_pct'] = df['atr14'] / df['close'] * 100

    # Directional Movement for ADX(14)
    df['plus_dm'] = np.where(
        (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
        np.maximum(df['high'] - df['high'].shift(1), 0),
        0
    )
    df['minus_dm'] = np.where(
        (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
        np.maximum(df['low'].shift(1) - df['low'], 0),
        0
    )
    df['smooth_plus_dm'] = df['plus_dm'].ewm(alpha=1/14, adjust=False).mean()
    df['smooth_minus_dm'] = df['minus_dm'].ewm(alpha=1/14, adjust=False).mean()
    df['smooth_tr'] = df['tr'].ewm(alpha=1/14, adjust=False).mean()
    df['plus_di'] = df['smooth_plus_dm'] / df['smooth_tr'] * 100
    df['minus_di'] = df['smooth_minus_dm'] / df['smooth_tr'] * 100
    df['dx'] = np.abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di']) * 100
    df['adx'] = df['dx'].ewm(alpha=1/14, adjust=False).mean()

    # RSI(14)
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    rs = gain.ewm(alpha=1/14, adjust=False).mean() / loss.ewm(alpha=1/14, adjust=False).mean()
    df['rsi14'] = 100 - (100 / (1 + rs))

    # Consecutive HH/HL and LH/LL structure
    count = len(df)
    consec_hh_hl = [0] * count
    consec_lh_ll = [0] * count
    for i in range(1, count):
        hh = df['high'].iloc[i] > df['high'].iloc[i - 1]
        hl = df['low'].iloc[i] > df['low'].iloc[i - 1]
        lh = df['high'].iloc[i] < df['high'].iloc[i - 1]
        ll = df['low'].iloc[i] < df['low'].iloc[i - 1]
        if hh and hl:
            consec_hh_hl[i] = consec_hh_hl[i - 1] + 1
        if lh and ll:
            consec_lh_ll[i] = consec_lh_ll[i - 1] + 1
    df['consec_hh_hl'] = consec_hh_hl
    df['consec_lh_ll'] = consec_lh_ll

    # Slopes and price vs SMA
    df['sma50_slope'] = df['sma50'].diff(5)
    df['sma200_slope'] = df['sma200'].diff(5)
    df['price_vs_sma50'] = (df['close'] - df['sma50']) / df['sma50'] * 100
    df['price_vs_sma200'] = (df['close'] - df['sma200']) / df['sma200'] * 100

    return df


def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute('DROP TABLE IF EXISTS candles_daily')
    conn.execute('''
        CREATE TABLE candles_daily (
            symbol TEXT,
            date TEXT,
            timestamp INTEGER,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            candle_count INTEGER,
            sma20 REAL, sma50 REAL, sma200 REAL,
            bb_width REAL, bb_pct REAL,
            atr14 REAL, atr_pct REAL,
            adx REAL, plus_di REAL, minus_di REAL,
            rsi14 REAL,
            consec_hh_hl INTEGER, consec_lh_ll INTEGER,
            sma50_slope REAL, sma200_slope REAL,
            price_vs_sma50 REAL, price_vs_sma200 REAL
        )
    ''')

    total_days = 0
    for symbol in COINS:
        df_1h = pd.read_sql_query(
            'SELECT timestamp, open, high, low, close, volume FROM candles WHERE symbol=? ORDER BY timestamp',
            conn, params=(symbol,)
        )
        if len(df_1h) == 0:
            print(f'  {symbol}: NO DATA — skipping')
            continue

        for col in ('open', 'high', 'low', 'close', 'volume'):
            df_1h[col] = pd.to_numeric(df_1h[col], errors='coerce')
        df_1h['timestamp'] = df_1h['timestamp'].astype(int)

        daily = aggregate_daily(df_1h)
        daily = compute_indicators(daily)
        daily['date'] = daily['date'].dt.strftime('%Y-%m-%d')
        daily['symbol'] = symbol

        cols = ('symbol', 'date', 'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'candle_count', 'sma20', 'sma50', 'sma200', 'bb_width', 'bb_pct',
                'atr14', 'atr_pct', 'adx', 'plus_di', 'minus_di', 'rsi14',
                'consec_hh_hl', 'consec_lh_ll', 'sma50_slope', 'sma200_slope',
                'price_vs_sma50', 'price_vs_sma200')
        daily[list(cols)].to_sql('candles_daily', conn, if_exists='append', index=False)

        n = len(daily)
        first_date = daily['date'].iloc[0]
        last_date = daily['date'].iloc[-1]
        flag = '<15' if n < 15 else ('>5' if n > 5 else '   ')
        print(f'  {symbol:<15} {n:>4} daily candles   {first_date} -> {last_date}')
        total_days += n

    conn.execute('CREATE INDEX IF NOT EXISTS idx_daily_symbol_date ON candles_daily(symbol, date)')
    conn.commit()
    conn.close()
    print(f'\nTotal: {total_days} daily candles across {len(COINS)} coins')
    print(f'DB: {DB_PATH}')


if __name__ == '__main__':
    main()
