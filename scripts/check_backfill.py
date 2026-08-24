import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect('trading/spot/data/candles.db')
cur = conn.cursor()

print("=== Post-collector DB check ===")
for sym in ['GRAM/USDT', 'GRAM/USDC', 'TON/USDT', 
            'APT/USDT', 'JTO/USDT', 'BERA/USDT', 'S/USDT', 
            'MOVE/USDT', 'GRASS/USDT', 'VIRTUAL/USDT', 
            'INIT/USDT', 'TRUMP/USDT', 'HYPE/USDT']:
    cur.execute(
        "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) "
        "FROM candles WHERE symbol = ? AND timeframe = '1h'", (sym,)
    )
    count, mn, mx = cur.fetchone()
    if count > 0 and mn:
        e = datetime.fromtimestamp(mn/1000, tz=timezone.utc)
        l = datetime.fromtimestamp(mx/1000, tz=timezone.utc)
        days = (l - e).days
        print("  %-18s %6d candles  %s to %s  (%d days)" % (
            sym, count, e.strftime('%Y-%m-%d'), l.strftime('%Y-%m-%d'), days))
    else:
        print("  %-18s %6d candles" % (sym, count))

conn.close()
