import sys, time; sys.path.insert(0, r'C:\Users\Never\.openclaw\workspace')
from trading.spot.candle_db import CandleDB
from trading.indicators import compute_all
from trading.regime_detector import classify_regime_v2
from datetime import datetime, timezone
db = CandleDB()
start_ms = int(datetime(2023,1,1,tzinfo=timezone.utc).timestamp()*1000)
end_ms = int(datetime(2026,2,15,tzinfo=timezone.utc).timestamp()*1000)
df = db.get_candles('BTC/USDC','1h',start_ms,end_ms)
print(f"Testing compute_all on {len(df)} candles...")
t0 = time.time()
df2 = compute_all(df)
print(f"compute_all done in {time.time()-t0:.2f}s")
t0 = time.time()
r = classify_regime_v2(df2, '1h')
print(f"classify_regime_v2 done in {time.time()-t0:.2f}s")
print("ALL DONE")
