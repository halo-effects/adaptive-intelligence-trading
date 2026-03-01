import sqlite3, pandas as pd
db = sqlite3.connect(r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db')

# What symbols exist for BTC in cfgi_daily?
syms = db.execute("SELECT DISTINCT symbol FROM cfgi_daily WHERE symbol LIKE 'BTC%'").fetchall()
print(f"BTC CFGI symbols: {syms}")

# Get all BTC CFGI
df = pd.read_sql("SELECT date, symbol, cfgi FROM cfgi_daily WHERE symbol LIKE 'BTC%' ORDER BY date", db)
print(f"\nTotal rows: {len(df)}")
print(f"Date range: {df['date'].iloc[0]} to {df['date'].iloc[-1]}")

# Around trigger dates (Oct-Dec 2022)
print("\nBTC CFGI Oct-Dec 2022:")
mask = (df['date'] >= '2022-10-01') & (df['date'] <= '2022-12-31')
print(df[mask][['date','cfgi']].to_string())

# Around Jul 2022 (ETH trigger)
print("\nBTC CFGI Jun-Aug 2022:")
mask = (df['date'] >= '2022-06-01') & (df['date'] <= '2022-08-31')
print(df[mask][['date','cfgi']].to_string())

# Current period
print("\nBTC CFGI Jan-Feb 2026:")
mask = df['date'] >= '2026-01-01'
print(df[mask][['date','cfgi']].to_string())

db.close()
