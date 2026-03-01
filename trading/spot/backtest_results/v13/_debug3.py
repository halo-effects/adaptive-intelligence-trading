import sqlite3
from pathlib import Path
DB = Path(r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db')
db = sqlite3.connect(DB)
syms = [r[0] for r in db.execute(
    "SELECT DISTINCT symbol FROM candles_daily WHERE symbol LIKE ?",
    ('LINK/USDC%',)).fetchall()]
print('Symbols matching LINK/USDC%:', syms)

syms2 = [r[0] for r in db.execute(
    "SELECT DISTINCT symbol FROM candles_daily WHERE symbol LIKE ?",
    ('LINK/%',)).fetchall()]
print('Symbols matching LINK/%:', syms2)
db.close()
