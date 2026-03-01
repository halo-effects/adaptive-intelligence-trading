"""Debug: Why isn't DCA buying?"""
import logging
logging.basicConfig(level=logging.DEBUG)

from trading.spot.v13_lifecycle_engine import V13LifecycleEngine, V13Config
from trading.spot.run_v13_paper import load_daily_candles, load_hourly_candles
from datetime import datetime, timezone

cfg = V13Config()
engine = V13LifecycleEngine("ETH/USDC", 2500.0, cfg)

# Feed daily
daily = load_daily_candles("ETH/USDT")
engine.feed_daily(daily[["open", "high", "low", "close", "volume"]])
print(f"Phase: {engine.phase}")
print(f"Signals date: {engine.signals.date}")
print(f"ADX: {engine.signals.adx:.1f}")

# Get first few 1h candles from Jan 2025
start_ts = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
hourly = load_hourly_candles("ETH/USDT", start_ts)
print(f"Hourly candles: {len(hourly)}")
print(f"First candle: {hourly.iloc[0]['close']}")

# Tick the first 5 candles
for i in range(min(5, len(hourly))):
    row = hourly.iloc[i]
    candle = {
        "timestamp": int(row["timestamp_ms"]),
        "open": float(row["open"]),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "close": float(row["close"]),
        "volume": float(row["volume"]),
    }
    actions = engine.tick(candle, 2500.0)
    print(f"Tick {i}: price={row['close']:.2f}, actions={len(actions)}, "
          f"phase={engine.phase}, layers={engine.dca_layers}, "
          f"days_in_phase={engine._days_in_phase(engine._parse_ts(candle['timestamp'])):.1f}")
    for a in actions:
        print(f"  -> {a}")
