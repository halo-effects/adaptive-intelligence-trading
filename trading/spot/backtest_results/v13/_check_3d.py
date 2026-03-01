import sqlite3, pandas as pd
conn = sqlite3.connect('trading/spot/data/candles.db')
tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)
print('Tables:', tables['name'].tolist())
tf = pd.read_sql_query("SELECT DISTINCT timeframe FROM candles LIMIT 10", conn)
print('Timeframes:', tf['timeframe'].tolist())
# Check 3d signals table
try:
    df = pd.read_sql_query("SELECT * FROM signals_3d LIMIT 2", conn)
    print('signals_3d columns:', df.columns.tolist())
except:
    print('No signals_3d table')
conn.close()
