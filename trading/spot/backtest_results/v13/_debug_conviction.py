"""Debug script to test conviction weighted system components."""

import sys, os
import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path

# Add path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing basic imports...")

try:
    from v13_signals import V13SignalPack, load_daily, load_cfgi
    print("SUCCESS: V13SignalPack imported successfully")
except Exception as e:
    print(f"ERROR: Error importing V13SignalPack: {e}")
    
try:
    from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
    print("SUCCESS: V13BacktestV8 imported successfully")
except Exception as e:
    print(f"ERROR: Error importing V13BacktestV8: {e}")

# Test database path
DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'
print(f"Database path: {DB_PATH}")
print(f"Database exists: {DB_PATH.exists()}")

if DB_PATH.exists():
    print(f"Database size: {DB_PATH.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Test basic database connection
    try:
        db = sqlite3.connect(str(DB_PATH))
        tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print(f"Tables in database: {[t[0] for t in tables]}")
        
        # Check candles table
        candles_count = db.execute("SELECT COUNT(*) FROM candles").fetchone()[0]
        print(f"Total candle records: {candles_count}")
        
        # Check for daily candles
        daily_count = db.execute("SELECT COUNT(*) FROM candles WHERE timeframe='1d'").fetchone()[0]
        print(f"Daily candle records: {daily_count}")
        
        # Check CFGI table
        cfgi_count = db.execute("SELECT COUNT(*) FROM cfgi_daily").fetchone()[0]
        print(f"CFGI records: {cfgi_count}")
        
        # Check available coins
        coins = db.execute("SELECT DISTINCT symbol FROM candles WHERE timeframe='1d' LIMIT 10").fetchall()
        print(f"Sample daily symbols: {[c[0] for c in coins[:5]]}")
        
        db.close()
        
    except Exception as e:
        print(f"Database connection error: {e}")

# Test loading a single coin
test_coin = 'BTC'
print(f"\nTesting data loading for {test_coin}...")

try:
    print("Loading V13SignalPack...")
    pack = V13SignalPack(test_coin)
    if pack.daily is not None:
        print(f"SUCCESS: Daily data loaded: {len(pack.daily)} rows")
        print(f"  Date range: {pack.daily.index.min()} to {pack.daily.index.max()}")
    else:
        print("ERROR: No daily data loaded")
        
except Exception as e:
    print(f"ERROR: Error loading V13SignalPack: {e}")

print("\nDone.")