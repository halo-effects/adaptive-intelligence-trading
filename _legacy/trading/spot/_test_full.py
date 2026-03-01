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

for sym in ['BTC/USDC','ETH/USDC','SOL/USDC']:
    df = db.get_candles(sym,'1h',start_ms,end_ms)
    print(f"\n{sym}: {len(df)} candles", flush=True)
    
    engine = SpotBacktestEngineV12(
        symbol=sym, capital=3333, profile='medium', timeframe='1h',
        exchange='binance', variant='regime_adaptive', fear_greed_history=fg,
        v12_exit_threshold=50.0, v12_mcap_ath_pct=0.25, v12_commitment_hours=48,
        v12_markup_deploy_pct=0.70, v12_markup_trail_pct=10.0, v12_short_enabled=True,
    )
    
    t0 = time.time()
    print(f"  prepare_step...", flush=True)
    engine.prepare_step(df)
    print(f"  done in {time.time()-t0:.1f}s", flush=True)

print("\nALL ENGINES PREPARED", flush=True)
