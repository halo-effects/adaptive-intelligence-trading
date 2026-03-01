"""
Build daily candles from 1h candles in the candle DB.
Aggregates: first open, max high, min low, last close, sum volume.
Also precomputes daily indicators: SMA50, SMA200, BB(20), ADX(14), ATR(14).
"""
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "candles.db"

# Coins to process
COINS = [
    "BTC/USDC", "ETH/USDC", "SOL/USDC",
    "BTC/USDT", "ETH/USDT", "SOL/USDT",
    "BNB/USDT", "XRP/USDT", "DOGE/USDT",
    "HYPE/USDC", "ASTER/USDT", "PEPE/USDT",
    "ZEC/USDT",
    "NEAR/USDT",
    "LINK/USDT",
    "LINK/USDC",
    "XRP/USDC",
]


def aggregate_daily(df_1h: pd.DataFrame) -> pd.DataFrame:
    """Aggregate 1h OHLCV to daily OHLCV."""
    df = df_1h.copy()
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.floor('D')
    
    daily = df.groupby('date').agg(
        timestamp=('timestamp', 'first'),  # First timestamp of the day
        open=('open', 'first'),
        high=('high', 'max'),
        low=('low', 'min'),
        close=('close', 'last'),
        volume=('volume', 'sum'),
        candle_count=('timestamp', 'count'),
    ).reset_index()
    
    # Only keep full days (at least 20 of 24 candles) except last day
    daily['is_last'] = daily.index == len(daily) - 1
    daily = daily[(daily['candle_count'] >= 20) | daily['is_last']].reset_index(drop=True)
    daily = daily.drop(columns=['is_last'])
    
    return daily


def compute_indicators(daily: pd.DataFrame) -> pd.DataFrame:
    """Compute daily indicators for phase detection."""
    df = daily.copy()
    
    # SMAs
    df['sma20'] = df['close'].rolling(20).mean()
    df['sma50'] = df['close'].rolling(50).mean()
    df['sma200'] = df['close'].rolling(200).mean()
    
    # Bollinger Bands (20-period, 2 std)
    df['bb_mid'] = df['sma20']
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid'] * 100  # As percentage
    df['bb_pct'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])  # 0-1 position
    
    # ATR (14-period)
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr14'] = df['tr'].rolling(14).mean()
    df['atr_pct'] = df['atr14'] / df['close'] * 100  # ATR as % of price
    
    # ADX (14-period)
    df['plus_dm'] = np.where(
        (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
        np.maximum(df['high'] - df['high'].shift(1), 0), 0
    )
    df['minus_dm'] = np.where(
        (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
        np.maximum(df['low'].shift(1) - df['low'], 0), 0
    )
    
    # Smoothed DM and TR (Wilder's smoothing = EMA with alpha=1/14)
    alpha = 1 / 14
    df['smooth_plus_dm'] = df['plus_dm'].ewm(alpha=alpha, adjust=False).mean()
    df['smooth_minus_dm'] = df['minus_dm'].ewm(alpha=alpha, adjust=False).mean()
    df['smooth_tr'] = df['tr'].ewm(alpha=alpha, adjust=False).mean()
    
    df['plus_di'] = (df['smooth_plus_dm'] / df['smooth_tr']) * 100
    df['minus_di'] = (df['smooth_minus_dm'] / df['smooth_tr']) * 100
    df['dx'] = abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di']) * 100
    df['adx'] = df['dx'].rolling(14).mean()
    
    # RSI (14-period)
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi14'] = 100 - (100 / (1 + rs))
    
    # Daily structure: higher highs / higher lows
    df['hh'] = df['high'] > df['high'].shift(1)  # Higher high
    df['hl'] = df['low'] > df['low'].shift(1)    # Higher low
    df['lh'] = df['high'] < df['high'].shift(1)  # Lower high
    df['ll'] = df['low'] < df['low'].shift(1)    # Lower low
    
    # Consecutive HH/HL count (markup structure)
    df['consec_hh_hl'] = 0
    count = 0
    for i in range(len(df)):
        if df.iloc[i]['hh'] and df.iloc[i]['hl']:
            count += 1
        else:
            count = 0
        df.iloc[i, df.columns.get_loc('consec_hh_hl')] = count
    
    # Consecutive LH/LL count (markdown structure)
    df['consec_lh_ll'] = 0
    count = 0
    for i in range(len(df)):
        if df.iloc[i]['lh'] and df.iloc[i]['ll']:
            count += 1
        else:
            count = 0
        df.iloc[i, df.columns.get_loc('consec_lh_ll')] = count
    
    # SMA slopes (5-day lookback)
    df['sma50_slope'] = (df['sma50'] - df['sma50'].shift(5)) / df['sma50'].shift(5) * 100
    df['sma200_slope'] = (df['sma200'] - df['sma200'].shift(5)) / df['sma200'].shift(5) * 100
    
    # Price relative to SMAs
    df['price_vs_sma50'] = (df['close'] - df['sma50']) / df['sma50'] * 100
    df['price_vs_sma200'] = (df['close'] - df['sma200']) / df['sma200'] * 100
    
    return df


def main():
    conn = sqlite3.connect(str(DB_PATH))
    
    # Create daily table
    conn.execute("DROP TABLE IF EXISTS candles_daily")
    conn.execute("""
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
    """)
    
    total_days = 0
    for symbol in COINS:
        # Load 1h candles
        df_1h = pd.read_sql_query(
            "SELECT timestamp, open, high, low, close, volume FROM candles "
            "WHERE symbol=? ORDER BY timestamp",
            conn, params=(symbol,)
        )
        if len(df_1h) == 0:
            print(f"  {symbol}: NO DATA — skipping")
            continue
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df_1h[col] = pd.to_numeric(df_1h[col], errors='coerce')
        df_1h['timestamp'] = df_1h['timestamp'].astype(int)
        
        # Aggregate to daily
        daily = aggregate_daily(df_1h)
        
        # Compute indicators
        daily = compute_indicators(daily)
        
        # Store date as string for readability
        daily['date'] = daily['date'].dt.strftime('%Y-%m-%d')
        daily['symbol'] = symbol
        
        # Select columns matching table schema
        cols = ['symbol', 'date', 'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'candle_count', 'sma20', 'sma50', 'sma200', 'bb_width', 'bb_pct',
                'atr14', 'atr_pct', 'adx', 'plus_di', 'minus_di', 'rsi14',
                'consec_hh_hl', 'consec_lh_ll', 'sma50_slope', 'sma200_slope',
                'price_vs_sma50', 'price_vs_sma200']
        
        daily[cols].to_sql('candles_daily', conn, if_exists='append', index=False)
        
        first_date = daily['date'].iloc[0]
        last_date = daily['date'].iloc[-1]
        total_days += len(daily)
        print(f"  {symbol:<15} {len(daily):>5} daily candles  {first_date} -> {last_date}")
    
    # Create index for fast lookups
    conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_symbol_date ON candles_daily(symbol, date)")
    conn.commit()
    
    print(f"\nTotal: {total_days} daily candles across {len(COINS)} coins")
    print(f"DB: {DB_PATH}")
    conn.close()


if __name__ == "__main__":
    main()
