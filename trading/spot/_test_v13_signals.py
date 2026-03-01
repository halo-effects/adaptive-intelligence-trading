"""Debug: Why no DCA→MARKUP transition?"""
import logging
logging.basicConfig(level=logging.WARNING)

from trading.spot.v13_lifecycle_engine import V13LifecycleEngine, V13Config
from trading.spot.run_v13_paper import load_daily_candles, load_hourly_candles
from datetime import datetime, timezone

cfg = V13Config()
engine = V13LifecycleEngine("ETH/USDC", 2500.0, cfg)

# Feed daily
daily = load_daily_candles("ETH/USDT")
engine.feed_daily(daily[["open", "high", "low", "close", "volume"]])

# Check signals
sig = engine.signals
print(f"Signals date: {sig.date}")
print(f"ADX: {sig.adx:.1f}")
print(f"HH_HL streak: {sig.hh_hl_streak}")
print(f"Fib support: {sig.fib_support}")
print(f"SMA200 distance: {sig.sma200_distance_pct:.1f}%")
print(f"Trend: {sig.trend}")
print(f"1W K: {sig.stoch_1w_k:.1f}")
print(f"2W K: {sig.stoch_2w_k:.1f}")

# Check markup entry conditions
hh_hl = sig.hh_hl_streak >= 1
fib_sup = sig.fib_support
sma_ok = sig.sma200_distance_pct <= 20
print(f"\nMARKUP entry conditions:")
print(f"  HH_HL >= 1: {hh_hl} (streak={sig.hh_hl_streak})")
print(f"  Fib support: {fib_sup}")
print(f"  SMA200 <= 20%: {sma_ok} ({sig.sma200_distance_pct:.1f}%)")
print(f"  ALL met: {hh_hl and fib_sup and sma_ok}")

# Check what _phase_dca checks
print(f"\nEngine phase: {engine.phase}")
print(f"Has daily signals: {engine.signals is not None}")

# Let's also check intermediate daily signals through the backfill period
start_ts = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
hourly = load_hourly_candles("ETH/USDT", start_ts)

# Process candles and track signal changes
last_markup_check = None
for i in range(len(hourly)):
    row = hourly.iloc[i]
    candle = {
        "timestamp": int(row["timestamp_ms"]),
        "open": float(row["open"]),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "close": float(row["close"]),
        "volume": float(row["volume"]),
    }
    engine.tick(candle, 2500.0)

    # Check on daily boundaries
    ts = datetime.fromtimestamp(candle["timestamp"] / 1000, tz=timezone.utc)
    if ts.hour == 0 and engine.signals:
        sig = engine.signals
        entry = (sig.hh_hl_streak >= 1 and sig.fib_support and sig.sma200_distance_pct <= 20)
        if entry and last_markup_check != ts.date():
            print(f"  {ts.date()}: MARKUP entry signal! HH_HL={sig.hh_hl_streak}, "
                  f"Fib_sup={sig.fib_support}, SMA200={sig.sma200_distance_pct:.1f}%, "
                  f"Phase={engine.phase}")
            last_markup_check = ts.date()

print(f"\nFinal phase: {engine.phase}, deals={engine.deals_completed}")
