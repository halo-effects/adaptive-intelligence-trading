import sys, time; sys.path.insert(0, r'C:\Users\Never\.openclaw\workspace')
from trading.spot.candle_db import CandleDB
from trading.indicators import hurst_exponent, compute_all
from trading.regime_detector import classify_regime_v2
from datetime import datetime, timezone

db = CandleDB()
start_ms = int(datetime(2022,6,1,tzinfo=timezone.utc).timestamp()*1000)
end_ms = int(datetime(2026,2,15,tzinfo=timezone.utc).timestamp()*1000)
df = db.get_candles('ETH/USDC','1h',start_ms,end_ms)
print(f"ETH: {len(df)} candles, min={df['close'].min()}", flush=True)

t0 = time.time()
print("hurst...", flush=True)
h = hurst_exponent(df["close"])
print(f"  done in {time.time()-t0:.1f}s", flush=True)

t0 = time.time()
print("compute_all...", flush=True)
df2 = compute_all(df)
print(f"  done in {time.time()-t0:.1f}s", flush=True)

t0 = time.time()
print("classify_regime_v2...", flush=True)
r = classify_regime_v2(df2, '1h')
print(f"  done in {time.time()-t0:.1f}s", flush=True)
print("DONE", flush=True)
