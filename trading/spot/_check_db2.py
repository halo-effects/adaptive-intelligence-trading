import sqlite3
conn = sqlite3.connect("trading/spot/data/candles.db")

syms = conn.execute(
    "SELECT DISTINCT symbol FROM candles WHERE timeframe='1h' ORDER BY symbol"
).fetchall()
print(f"{len(syms)} symbols with 1h candles")
for s in syms[:15]:
    print(f"  {s[0]}")

# Check GRASS
for sym in ["GRASS/USDT", "GRASSUSDT", "GRASS"]:
    count = conn.execute(
        "SELECT COUNT(*) FROM candles WHERE symbol=? AND timeframe='1h'", (sym,)
    ).fetchone()[0]
    if count:
        print(f"  {sym}: {count} rows")

# Check what format the top PM coins use
for coin in ["GRASS", "TAO", "FET", "RENDER", "ZEC", "PENDLE", "TON", "ONDO"]:
    rows = conn.execute(
        "SELECT DISTINCT symbol FROM candles WHERE symbol LIKE ? AND timeframe='1h'",
        (f"%{coin}%",)
    ).fetchall()
    if rows:
        for r in rows:
            count = conn.execute(
                "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol=? AND timeframe='1h'",
                (r[0],)
            ).fetchone()
            print(f"  {r[0]}: {count[0]} rows, {count[1][:10] if count[1] else '?'} to {count[2][:10] if count[2] else '?'}")

conn.close()
