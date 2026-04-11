"""Trace exactly what happened with the TAO 5-layer deal on Apr 10-11"""
import sqlite3, datetime
db = sqlite3.connect(r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db")

# The deal: open Apr 10 01:00 UTC, close Apr 11 00:00 UTC, 5 layers
# But log shows buys starting Apr 9 19:00
# The CSV open_time is from the FIRST layer's candle timestamp

# Key question: what daily candle was used by the daily tick that closed this deal?

# Daily boundary processing:
# At midnight Apr 11 (00:00 UTC), the engine processes Apr 10's daily candle
# Apr 10 daily: O=305.20 H=307.40 L=248.90 C=262.70

# At 18:00 Apr 10 (which is when the PM paper bot runs its daily tick):
# It processes the "previous day" = Apr 9's daily candle
# Apr 9 daily: O=325.10 H=341.20 L=300.10 C=305.10

# Position at 18:00 Apr 10: 5 layers
# L1: $6,109 @ ~$338 (Apr 9 19:00 close)
# L2: $4,276 @ ~$335 (Apr 9 21:00 close)
# L3: $2,993 @ ~$332 (Apr 9 22:00 close)
# L4: $2,095 @ ~$285 (Apr 10 00:00 close)
# L5: $1,466 @ ~$258 (Apr 10 16:00 close)
# Approx avg entry: ~$320, TP: ~$325

# But wait - does the PM paper bot use 18:00 UTC or midnight?
# Let me check the actual daily boundary detection

# The lifecycle engine checks: current_date != last_daily_date
# So when processing a candle at 00:00 UTC, the date changes

# But the deals close at various times. Let me check the log pattern
print("=== TAO deal timeline reconstruction ===")
print()

# Check Apr 9 daily candle
print("Apr 9 daily candle:")
print("  O=325.10 H=341.20 L=300.10 C=305.10")
print()

# Check Apr 10 daily candle  
print("Apr 10 daily candle:")
print("  O=305.20 H=307.40 L=248.90 C=262.70")
print()

# The 5-layer deal from CSV: open=Apr 10 01:00, close=Apr 11 00:00
# But there's also a 2-layer deal: TAO Apr 9->Apr 10, $10,142, 9h
# That 2L deal: open Apr 9, close Apr 10, 9 hours
# If it opened Apr 9 ~15:00 and closed Apr 10 ~00:00, that's 9h

# So the sequence might be:
# Deal A: 2L, opens ~Apr 9 15:00, closes Apr 10 00:00 (midnight daily tick)
# Deal B: 5L, opens Apr 10 01:00, closes Apr 11 00:00

# For Deal A (2L): avg entry probably around $335-340
# Apr 8 daily high = $351.10
# At midnight Apr 10, daily tick uses Apr 9 daily: H=$341.20
# If 2L avg ~$337, TP ~$342 -- $341.20 < $342, NO TP
# But Apr 8 daily high was $351.10...

# Actually the daily tick at midnight Apr 10 processes Apr 9's candle
# prev_date = Apr 9
# daily_high = Apr 9 high = $341.20
# If 2L deal had layers on Apr 9, avg ~$337, TP ~$342
# $341.20 < $342 -- no TP from daily tick
# But the hourly catch-up runs too: with current candle (midnight Apr 10)
# Apr 10 00:00 candle: H=307.40 -- way below TP
# So how did Deal A close?

# Wait, maybe the deal times are the candle timestamps, not wall clock
# open_time=Apr 9 means the candle at that timestamp
# The PM paper bot uses 18:00 UTC as daily evaluation? Let me check:

# Actually, looking at the log: "Signal pack refreshed" happens at 18:00 UTC
# That means the bot considers 18:00 UTC as the daily boundary for signal refresh
# But the lifecycle engine code uses midnight UTC for the daily tick

# Let me check: what time does the paper bot process daily candles?
# The paper bot fetches 1h candles and feeds them to the engine
# When the engine sees a candle at midnight UTC (00:00), it triggers the daily tick
# But the signal pack refresh happens when the bot runs its daily scan

# For the PM paper bot, the daily scan/rebalance runs at 18:00 UTC
# This might process a different set of candles

print("TAO 1h candles around Apr 9 18:00 (daily boundary):")
for ts_ms in range(1775656800000, 1775671200000, 3600000):  # Apr 9 10:00 to 14:00 UTC
    row = db.execute("SELECT high, close FROM candles WHERE symbol='TAO/USDT' AND timeframe='1h' AND timestamp=?", (ts_ms,)).fetchone()
    if row:
        dt = datetime.datetime.fromtimestamp(ts_ms/1000, tz=datetime.timezone.utc)
        print(f"  {dt.strftime('%Y-%m-%d %H:%M')}: H={row[0]:.2f} C={row[1]:.2f}")

# The key insight: the daily tick uses prev_date's candle from the SIGNAL PACK
# The signal pack has daily OHLC resampled from DB
# If the DB daily candle for Apr 9 has H=$341.20, that's the value used

# Now for Deal B (5L, close Apr 11 00:00):
# Daily tick at boundary processes Apr 10's candle
# Apr 10 daily: H=$307.40
# 5L avg ~$320, TP ~$325
# $307.40 < $325 -- NO TP from daily tick
# 
# But the hourly ticks check too! Each hour, _long_dca_tick runs
# The highest 1h candle on Apr 10 was H=$307.40 at 00:00
# That's still below $325
#
# So HOW did this deal close?? 

# Unless... the daily tick at the boundary that closes the deal is NOT Apr 10
# but the NEXT daily tick that uses Apr 9's daily data (if there's a lag)

# Or maybe the deal didn't close via TP at all - maybe it was a signal-based close

print()
print("=== Checking if deal closed via TP or signal ===")
# The return is exactly 1.48% = TP return. Signal closes have variable returns.
# So it appears to be a TP close.

# But the price never reached $325 on Apr 10 or Apr 11 early morning...
# Unless the DAILY tick uses Apr 9's high ($341) when processing at some point

# Actually, here's another possibility:
# The "close_time" in CSV is 2026-04-11T00:00:00 -- that's the CANDLE timestamp
# The daily tick at this boundary processes Apr 10's data
# But what if the signal pack ALSO includes some different daily aggregation?

# Let me check the hourly candle highs for the entire deal period
print()
print("MAX hourly high per day for TAO during the deal:")
for date_str in ["2026-04-09", "2026-04-10"]:
    rows = db.execute("""
        SELECT MAX(high), MIN(low) FROM candles 
        WHERE symbol='TAO/USDT' AND timeframe='1h'
        AND timestamp >= ? AND timestamp < ?
    """, (
        int(datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc).timestamp() * 1000),
        int((datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc) + datetime.timedelta(days=1)).timestamp() * 1000)
    )).fetchone()
    if rows and rows[0]:
        print(f"  {date_str}: max_high=${rows[0]:.2f}, min_low=${rows[1]:.2f}")

db.close()
