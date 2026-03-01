import sys, time; sys.path.insert(0, r'C:\Users\Never\.openclaw\workspace')
from trading.spot.candle_db import CandleDB
from trading.indicators import hurst_exponent
from datetime import datetime, timezone

db = CandleDB()
start_ms = int(datetime(2023,1,1,tzinfo=timezone.utc).timestamp()*1000)
end_ms = int(datetime(2026,2,15,tzinfo=timezone.utc).timestamp()*1000)
df = db.get_candles('BTC/USDC','1h',start_ms,end_ms)

for n in [5000, 10000, 15000, 20000, 27384]:
    sub = df.head(n)
    t0 = time.time()
    r = hurst_exponent(sub["close"])
    elapsed = time.time()-t0
    print(f"hurst {n}: {elapsed:.2f}s")
    if elapsed > 30:
        print("Too slow")
        break
print("DONE")
