import sys, time; sys.path.insert(0, r'C:\Users\Never\.openclaw\workspace')
from trading.spot.candle_db import CandleDB
from trading.indicators import hurst_exponent
from datetime import datetime, timezone
db = CandleDB()
start_ms = int(datetime(2023,1,1,tzinfo=timezone.utc).timestamp()*1000)
end_ms = int(datetime(2026,2,15,tzinfo=timezone.utc).timestamp()*1000)
df = db.get_candles('BTC/USDC','1h',start_ms,end_ms)
print(f"Testing hurst on {len(df)} real BTC candles...")
t0 = time.time()
r = hurst_exponent(df["close"])
print(f"Done in {time.time()-t0:.2f}s, non-null: {r.notna().sum()}")
