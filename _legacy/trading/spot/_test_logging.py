"""Test if logging level affects hurst/regime computation."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# SAME logging setup as the real script
import logging
for mod in ["trading.spot.backtest_engine_v3", "trading.spot.backtest_engine_v4",
            "trading.spot.backtest_engine_v5", "trading.spot.backtest_engine_v6",
            "trading.spot.backtest_engine_v8", "trading.spot.backtest_engine_v9",
            "trading.spot.backtest_engine_v12", "trading.spot.distribution_scorer",
            "trading.spot.ta_top_scorer", "trading.spot.reversal_detector",
            "trading.regime_detector", "trading.indicators",
            "trading.spot.conviction_scorer", "trading.spot.backtest_exit_scorer"]:
    logging.getLogger(mod).setLevel(logging.ERROR)
logging.basicConfig(level=logging.WARNING)

from datetime import datetime, timezone
from trading.spot.candle_db import CandleDB
from trading.indicators import hurst_exponent, compute_all
from trading.regime_detector import classify_regime_v2

db = CandleDB()
start_ms = int(datetime(2022,6,1,tzinfo=timezone.utc).timestamp()*1000)
end_ms = int(datetime(2026,2,15,tzinfo=timezone.utc).timestamp()*1000)
df = db.get_candles('BTC/USDC','1h',start_ms,end_ms)
print(f"BTC: {len(df)} candles", flush=True)

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
