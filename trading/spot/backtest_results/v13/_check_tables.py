import sqlite3
c = sqlite3.connect(r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db')
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    print(t[0])
