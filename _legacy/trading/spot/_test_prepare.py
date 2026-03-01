import sys, time; sys.path.insert(0, r'C:\Users\Never\.openclaw\workspace')
import logging; logging.basicConfig(level=logging.INFO)
from trading.spot.candle_db import CandleDB
from trading.spot.backtest_engine_v12 import SpotBacktestEngineV12
from trading.spot.macro_indicators import load_historical_fear_greed
from datetime import datetime, timezone

db = CandleDB()
fg = load_historical_fear_greed()
start_ms = int(datetime(2022,6,1,tzinfo=timezone.utc).timestamp()*1000)
end_ms = int(datetime(2026,2,15,tzinfo=timezone.utc).timestamp()*1000)
df = db.get_candles('BTC/USDC','1h',start_ms,end_ms)
print(f"Got {len(df)} candles", flush=True)

engine = SpotBacktestEngineV12(
    symbol='BTC/USDC', capital=10000, profile='medium', timeframe='1h',
    exchange='binance', variant='regime_adaptive', fear_greed_history=fg,
    v12_exit_threshold=50.0, v12_mcap_ath_pct=0.25, v12_commitment_hours=48,
    v12_markup_deploy_pct=0.70, v12_markup_trail_pct=10.0, v12_short_enabled=True,
)

# Manually run prepare_step with timing
from trading.spot.backtest_engine_v5 import _stochastic
from trading.spot.backtest_engine_v4 import HARD_SNAPBACK_REGIMES, SOFT_SNAPBACK_REGIMES
from trading.spot.backtest_engine_v6 import DONCHIAN_LOOKBACK, DONCHIAN_RANGE_MAX_PCT
from trading.spot.backtest_engine_v3 import BLOCKED_REGIMES
from trading.indicators import (
    atr_pct as compute_atr_pct, atr as compute_atr,
    compute_all as compute_all_indicators,
    bollinger_band_width, volume_sma,
)
from trading.regime_detector import classify_regime_v2
import numpy as np, pandas as pd

t0 = time.time()
print("1. conductor.prepare...", flush=True)
engine._accumulated_1h = df.copy()
engine._conductor.prepare(engine._accumulated_1h)
print(f"   done {time.time()-t0:.1f}s", flush=True)

t0 = time.time()
print("2. compute_all...", flush=True)
df2 = compute_all_indicators(df)
print(f"   done {time.time()-t0:.1f}s", flush=True)

t0 = time.time()
print("3. classify_regime_v2...", flush=True)
regimes = classify_regime_v2(df2, '1h')
print(f"   done {time.time()-t0:.1f}s", flush=True)

t0 = time.time()
print("4. other indicators...", flush=True)
atr_pct_s = compute_atr_pct(df2, 14)
atr_abs_s = compute_atr(df2, 14)
sma50 = df2["close"].rolling(50).mean()
bbw = df2["bbw"]
bbw_med = bbw.rolling(100, min_periods=20).median()
vol = df2["volume"]
vol_avg = volume_sma(df2, 20)
stoch = _stochastic(df2, 14, 3, 3)
print(f"   done {time.time()-t0:.1f}s", flush=True)

print("ALL DONE", flush=True)
