import sys, time; sys.path.insert(0, r'C:\Users\Never\.openclaw\workspace')
from trading.spot.candle_db import CandleDB
from trading.regime_detector import classify_regime_v2
from datetime import datetime, timezone

db = CandleDB()
start_ms = int(datetime(2023,1,1,tzinfo=timezone.utc).timestamp()*1000)
end_ms = int(datetime(2026,2,15,tzinfo=timezone.utc).timestamp()*1000)
df = db.get_candles('BTC/USDC','1h',start_ms,end_ms).head(10000).copy().reset_index(drop=True)
print(f"Testing classify_regime_v2 on {len(df)} candles...")
t0 = time.time()
r = classify_regime_v2(df, '1h')
print(f"Done in {time.time()-t0:.1f}s")
