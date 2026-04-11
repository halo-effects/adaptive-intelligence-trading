import sqlite3
from datetime import datetime, timezone

db = sqlite3.connect(r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db")
syms = ["TAO/USDT", "FET/USDT", "JTO/USDT", "GRASS/USDT", "ZEC/USDT",
        "NEAR/USDT", "DOT/USDT", "HYPE/USDT", "RENDER/USDT", "SOL/USDC"]

for s in syms:
    r = db.execute("SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM candles WHERE symbol=? AND timeframe='1h'", (s,)).fetchone()
    if r and r[0]:
        mn = datetime.fromtimestamp(r[0]/1000, tz=timezone.utc).strftime("%Y-%m-%d")
        mx = datetime.fromtimestamp(r[1]/1000, tz=timezone.utc).strftime("%Y-%m-%d")
        days = (r[1] - r[0]) / 86400000
        print(f"{s:15s} {mn} to {mx} ({days:.0f} days, {r[2]} candles)")
    else:
        print(f"{s:15s} NO DATA")
db.close()
