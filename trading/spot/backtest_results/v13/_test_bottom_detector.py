"""Test bottom stack detector."""

import sys, os
import sqlite3
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Just test the database loading parts
DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'
print(f"Database path: {DB_PATH}")

coin = 'BTC'
base_coin = coin.split('/')[0] if '/' in coin else coin

# Test candles loading
print(f"Testing candles loading for {base_coin}...")
try:
    db = sqlite3.connect(str(DB_PATH))
    
    # Check candles_daily table
    symbols = db.execute(
        "SELECT DISTINCT symbol FROM candles_daily WHERE symbol LIKE ? LIMIT 5",
        (f'{base_coin}%',)
    ).fetchall()
    print(f"Found symbols in candles_daily: {[s[0] for s in symbols]}")
    
    if symbols:
        symbol = symbols[0][0]
        count = db.execute(
            "SELECT COUNT(*) FROM candles_daily WHERE symbol=?", (symbol,)
        ).fetchone()[0]
        print(f"Records for {symbol}: {count}")
        
        # Sample data
        sample = db.execute(
            "SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp LIMIT 5",
            (symbol,)
        ).fetchall()
        print(f"Sample data: {sample[0] if sample else 'none'}")
    
    # Check CFGI
    cfgi_data = db.execute(
        "SELECT * FROM cfgi_daily WHERE symbol LIKE ? ORDER BY date LIMIT 5",
        (f'{base_coin}%',)
    ).fetchall()
    print(f"CFGI sample: {cfgi_data[0] if cfgi_data else 'none'}")
    
    db.close()
    
except Exception as e:
    print(f"Database error: {e}")

print("Done.")