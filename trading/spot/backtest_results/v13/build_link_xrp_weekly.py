"""Build weekly candles for LINK and XRP from daily data."""
import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'candles.db'

def build_weekly(symbol):
    """Build weekly candles from daily candles."""
    conn = sqlite3.connect(DB_PATH)
    
    # Get daily candles
    df = pd.read_sql_query(
        "SELECT * FROM candles_daily WHERE symbol=? ORDER BY date", conn, params=(symbol,)
    )
    
    if df.empty:
        print(f"{symbol}: No daily candles")
        conn.close()
        return
    
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    # Resample to weekly (Sunday close)
    weekly = df['close'].resample('W-SUN').last()
    if len(weekly) == 0:
        print(f"{symbol}: No weekly data after resampling")
        conn.close()
        return
    
    # Build OHLCV
    weeks = []
    for date in weekly.index:
        week_df = df[df.index.isocalendar().week == date.isocalendar().week]
        week_df = week_df[week_df.index.isocalendar().year == date.year]
        
        if len(week_df) == 0:
            continue
        
        weeks.append({
            'symbol': symbol,
            'date': date.strftime('%Y-%m-%d'),
            'open': week_df['open'].iloc[0],
            'high': week_df['high'].max(),
            'low': week_df['low'].min(),
            'close': week_df['close'].iloc[-1],
            'volume': week_df['volume'].sum(),
        })
    
    if not weeks:
        print(f"{symbol}: No weeks built")
        conn.close()
        return
    
    # Insert into DB
    c = conn.cursor()
    for w in weeks:
        c.execute("""INSERT OR REPLACE INTO candles_weekly
                    (symbol, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                 (w['symbol'], w['date'], w['open'], w['high'], w['low'], w['close'], w['volume']))
    
    conn.commit()
    print(f"{symbol}: {len(weeks)} weekly candles built")
    
    # Verify
    count = c.execute("SELECT COUNT(*) FROM candles_weekly WHERE symbol=?", (symbol,)).fetchone()[0]
    first = c.execute("SELECT MIN(date), MAX(date) FROM candles_weekly WHERE symbol=?", (symbol,)).fetchone()
    print(f"  Stored: {count} rows, {first[0]} to {first[1]}")
    
    conn.close()


if __name__ == '__main__':
    for coin in ['LINK/USDC', 'XRP/USDC']:
        build_weekly(coin)
