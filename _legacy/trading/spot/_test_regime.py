import sys, time; sys.path.insert(0, r'C:\Users\Never\.openclaw\workspace')
from trading.spot.candle_db import CandleDB
from trading.regime_detector import classify_regime_v2
from datetime import datetime, timezone
db = CandleDB()
start_ms = int(datetime(2023,1,1,tzinfo=timezone.utc).timestamp()*1000)
end_ms = int(datetime(2026,2,15,tzinfo=timezone.utc).timestamp()*1000)
df = db.get_candles('BTC/USDC','1h',start_ms,end_ms)

# Test with subsets
for n in [1000, 5000, 10000, 27384]:
    sub = df.head(n).copy().reset_index(drop=True)
    t0 = time.time()
    r = classify_regime_v2(sub, '1h')
    elapsed = time.time()-t0
    print(f"{n} candles: {elapsed:.1f}s")
    if elapsed > 120:
        print("Too slow, stopping")
        break
print("DONE")
