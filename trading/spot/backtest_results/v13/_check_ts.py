import sqlite3, pandas as pd
conn = sqlite3.connect('trading/spot/data/candles.db')
df = pd.read_sql_query("SELECT timestamp, open, close FROM candles_daily WHERE symbol LIKE 'ETH%' ORDER BY timestamp LIMIT 3", conn)
print(df)
print(df.dtypes)
print('Sample ts:', df['timestamp'].iloc[0], type(df['timestamp'].iloc[0]))
