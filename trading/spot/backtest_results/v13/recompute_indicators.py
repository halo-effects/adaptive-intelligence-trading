"""
Recompute indicators for backfilled daily candles.
Deletes existing rows and re-inserts with full indicators.
"""
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from build_daily_candles import compute_indicators

DB_PATH = Path(__file__).resolve().parents[2] / 'data' / 'candles.db'
SYMBOLS = ['ETH/USDT', 'SOL/USDT', 'BTC/USDT']

COLS = ['symbol', 'date', 'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'candle_count', 'sma20', 'sma50', 'sma200', 'bb_width', 'bb_pct',
        'atr14', 'atr_pct', 'adx', 'plus_di', 'minus_di', 'rsi14',
        'consec_hh_hl', 'consec_lh_ll', 'sma50_slope', 'sma200_slope',
        'price_vs_sma50', 'price_vs_sma200']

def main():
    conn = sqlite3.connect(str(DB_PATH))
    
    for symbol in SYMBOLS:
        # Load all rows — use timestamp ordering since date may be NULL
        df = pd.read_sql_query(
            "SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp, date",
            conn, params=(symbol,)
        )
        if len(df) == 0:
            print(f"  {symbol}: no data")
            continue
        
        print(f"  {symbol}: {len(df)} rows")
        
        # Ensure numeric
        for c in ['open', 'high', 'low', 'close', 'volume']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
        
        # Reconstruct date from timestamp where missing
        ts_dates = pd.to_datetime(df['timestamp'], unit='ms').dt.strftime('%Y-%m-%d')
        # Use existing date where valid, else derive from timestamp
        df['date'] = df['date'].where(df['date'].notna() & (df['date'] != ''), ts_dates)
        
        # Deduplicate by date (keep last = prefer live-collected over backfilled)
        df = df.drop_duplicates(subset='date', keep='last').sort_values('date').reset_index(drop=True)
        print(f"    After dedup: {len(df)} rows, {df['date'].iloc[0]} -> {df['date'].iloc[-1]}")
        
        # Prepare for compute_indicators (needs 'date' as datetime)
        df_comp = df[['date', 'open', 'high', 'low', 'close', 'volume']].copy()
        df_comp['date'] = pd.to_datetime(df_comp['date'])
        result = compute_indicators(df_comp)
        
        # Merge indicators back
        for col in COLS:
            if col in result.columns and col not in ('symbol', 'date', 'timestamp', 'open', 'high', 'low', 'close', 'volume'):
                df[col] = result[col].values
        
        # Set candle_count where missing
        if 'candle_count' not in df.columns or df['candle_count'].isna().all():
            df['candle_count'] = 24  # backfilled daily = full day
        df['candle_count'] = df['candle_count'].fillna(24)
        
        df['symbol'] = symbol
        
        # Verify
        adx_valid = df['adx'].notna().sum()
        sma50_valid = df['sma50'].notna().sum()
        print(f"    Indicators: ADX={adx_valid}/{len(df)}, SMA50={sma50_valid}/{len(df)}")
        
        # Delete and re-insert
        conn.execute("DELETE FROM candles_daily WHERE symbol=?", (symbol,))
        df[COLS].to_sql('candles_daily', conn, if_exists='append', index=False)
        conn.commit()
        print(f"    Written {len(df)} rows")
    
    conn.close()
    print("\nDone!")

if __name__ == '__main__':
    main()
