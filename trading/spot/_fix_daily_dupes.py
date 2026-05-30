#!/usr/bin/env python3
"""
One-time fix: Deduplicate candles_daily table.

The table accumulated ~250K+ duplicate rows because it was initially created
without a proper PRIMARY KEY constraint. resample_daily.py's INSERT OR IGNORE
couldn't prevent duplicates on a table without unique constraints.

Strategy:
1. Create a clean table with proper PK
2. Copy distinct rows (keep latest candle_count per symbol+timestamp)
3. Drop old table, rename clean table
4. Also drop the redundant idx_candles_sym_tf_ts index on candles table
"""
import sqlite3
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_PATH = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'

db = sqlite3.connect(DB_PATH)

# Count before
before = db.execute('SELECT COUNT(*) FROM candles_daily').fetchone()[0]
distinct = db.execute('SELECT COUNT(*) FROM (SELECT DISTINCT symbol, timestamp FROM candles_daily)').fetchone()[0]
print(f'Before: {before:,} rows, {distinct:,} unique (symbol, timestamp) pairs')
print(f'Duplicates to remove: {before - distinct:,}')

# Step 1: Create clean table
db.execute('DROP TABLE IF EXISTS candles_daily_clean')
db.execute("""
    CREATE TABLE candles_daily_clean (
        symbol TEXT,
        date TEXT,
        timestamp INTEGER,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume REAL,
        candle_count INTEGER DEFAULT 0,
        sma20 REAL,
        sma50 REAL,
        sma200 REAL,
        bb_width REAL,
        bb_pct REAL,
        atr14 REAL,
        atr_pct REAL,
        adx REAL,
        plus_di REAL,
        minus_di REAL,
        rsi14 REAL,
        consec_hh_hl INTEGER,
        consec_lh_ll INTEGER,
        sma50_slope REAL,
        sma200_slope REAL,
        price_vs_sma50 REAL,
        price_vs_sma200 REAL,
        PRIMARY KEY (symbol, timestamp)
    )
""")

# Step 2: Copy deduped rows (keep the row with highest candle_count per key)
db.execute("""
    INSERT INTO candles_daily_clean
    SELECT symbol, date, timestamp, open, high, low, close, volume, candle_count,
           sma20, sma50, sma200, bb_width, bb_pct, atr14, atr_pct,
           adx, plus_di, minus_di, rsi14,
           consec_hh_hl, consec_lh_ll, sma50_slope, sma200_slope,
           price_vs_sma50, price_vs_sma200
    FROM candles_daily
    GROUP BY symbol, timestamp
    HAVING candle_count = MAX(candle_count)
""")

clean_count = db.execute('SELECT COUNT(*) FROM candles_daily_clean').fetchone()[0]
print(f'Clean table: {clean_count:,} rows')

# Step 3: Swap tables
db.execute('DROP TABLE candles_daily')
db.execute('ALTER TABLE candles_daily_clean RENAME TO candles_daily')

# Recreate the date index
db.execute('CREATE INDEX IF NOT EXISTS idx_daily_symbol_date ON candles_daily(symbol, date)')

db.commit()

# Step 4: Drop redundant index on candles table
try:
    db.execute('DROP INDEX IF EXISTS idx_candles_sym_tf_ts')
    db.commit()
    print('Dropped redundant idx_candles_sym_tf_ts index')
except Exception as e:
    print(f'Could not drop index: {e}')

# Verify
after = db.execute('SELECT COUNT(*) FROM candles_daily').fetchone()[0]
print(f'After: {after:,} rows')
print(f'Removed: {before - after:,} duplicate rows')

# VACUUM to reclaim space
print('Running VACUUM...')
db.execute('VACUUM')
print('Done.')

db.close()
