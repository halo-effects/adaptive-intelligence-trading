import sys, time; sys.path.insert(0, r'C:\Users\Never\.openclaw\workspace')
from trading.spot.candle_db import CandleDB
from datetime import datetime, timezone
import trading.indicators as indicators

db = CandleDB()
start_ms = int(datetime(2023,1,1,tzinfo=timezone.utc).timestamp()*1000)
end_ms = int(datetime(2026,2,15,tzinfo=timezone.utc).timestamp()*1000)
df = db.get_candles('BTC/USDC','1h',start_ms,end_ms).head(10000).copy().reset_index(drop=True)
print(f"Testing on {len(df)} candles")

t0 = time.time()
df2 = indicators.compute_all(df)
print(f"compute_all: {time.time()-t0:.1f}s")

t0 = time.time()
vc = indicators.volume_climax(df2)
print(f"volume_climax: {time.time()-t0:.1f}s")

t0 = time.time()
spring = indicators.spring_detection(df2)
print(f"spring_detection: {time.time()-t0:.1f}s")

t0 = time.time()
vt = indicators.volume_trend(df2)
print(f"volume_trend: {time.time()-t0:.1f}s")

t0 = time.time()
rt = indicators.range_tightening(df2)
print(f"range_tightening: {time.time()-t0:.1f}s")

t0 = time.time()
vuvu = indicators.hvf_vuvuzela(df2)
print(f"hvf_vuvuzela: {time.time()-t0:.1f}s")

t0 = time.time()
cb = indicators.channel_breakout(df2)
print(f"channel_breakout: {time.time()-t0:.1f}s")

t0 = time.time()
cwp = indicators.channel_width_pct(df2)
print(f"channel_width_pct: {time.time()-t0:.1f}s")

print("ALL indicator calls done")
