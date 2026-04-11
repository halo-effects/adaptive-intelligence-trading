"""Scan ALL paper bot deals for false TPs: deals where the daily candle high
couldn't have legitimately reached TP given the position's avg entry."""
import csv, sqlite3, datetime, json
from pathlib import Path
from collections import defaultdict

BASE = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio")
db = sqlite3.connect(r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db")

# Load all daily candles into a dict: (symbol, date) -> (high, low, close)
daily_candles = {}
for row in db.execute("SELECT symbol, timestamp, high, low, close FROM candles_daily").fetchall():
    sym, ts, h, l, c = row
    dt = datetime.datetime.fromtimestamp(ts/1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
    daily_candles[(sym, dt)] = (h, l, c)

# Load all 1h candles for TP reconstruction
hourly_candles = {}
for row in db.execute("SELECT symbol, timestamp, high, close FROM candles WHERE timeframe='1h'").fetchall():
    sym, ts, h, c = row
    hourly_candles[(sym, ts)] = (h, c)

# Load trades
with open(BASE / "trades.csv") as f:
    trades = list(csv.DictReader(f))

print(f"Total deals: {len(trades)}")
print(f"Deals with exactly 1.48% return: {sum(1 for t in trades if float(t['return_pct']) == 1.48)}")

# For each multi-layer deal with 1.48% return, check if the daily high 
# on the close date could have reached the TP
suspicious = []
confirmed_ok = []

for t in trades:
    ret = float(t["return_pct"])
    layers = int(t["layers"])
    invested = float(t["invested"])
    pnl = float(t["pnl"])
    sym = t["symbol"]
    close_date = t["close_time"][:10]
    open_date = t["open_time"][:10]
    
    # Only check multi-layer deals with exact TP return
    if ret != 1.48 or layers < 2:
        continue
    
    # Get the daily candle for close_date and the day before
    # The daily tick at midnight processes the PREVIOUS day
    close_dt = datetime.datetime.strptime(close_date, "%Y-%m-%d")
    prev_date = (close_dt - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Get daily high for the previous day (what the daily tick uses)
    daily_key = (sym, prev_date)
    if daily_key not in daily_candles:
        continue
    
    prev_high, prev_low, prev_close = daily_candles[daily_key]
    
    # Estimate TP from invested and return
    # TP = avg_entry * 1.015
    # pnl = invested * 0.0148 (approximately, after fees)
    # avg_entry = invested / total_coins
    # We can estimate: if invested=$16939 and return=1.48%, proceeds = $17190
    # This means fill_price = TP = avg * 1.015
    # And avg = invested / coins
    # But we don't have coins... we can estimate from the close price context
    
    # Better approach: if the DAILY HIGH for the close-day's previous candle 
    # is significantly ABOVE the close-day price range, it's suspicious
    close_key = (sym, close_date)
    if close_key in daily_candles:
        close_high, close_low, close_close = daily_candles[close_key]
    else:
        continue
    
    # The deal's avg entry can be estimated:
    # For a TP at 1.48% return, the fill was at avg * 1.015
    # The price at close time was close_close
    # If close_close is significantly below avg * 1.015, it's suspicious
    
    # A deal closing at TP means price hit avg * 1.015 at some point
    # If the max price on close_date never reached avg * 1.015, it's false
    
    # We know: pnl = coins * (tp - avg) - fees ≈ invested * 0.0148
    # And tp = avg * 1.015
    # So approximately: invested * 0.015 - fees ≈ invested * 0.0148
    # This checks out (0.02% fee drag)
    
    # The maximum possible TP price = prev_high (from daily tick) or close_high (from hourly ticks)
    max_possible_price = max(prev_high, close_high)
    
    # If all hourly candle highs on close_date are below some threshold, it's suspicious
    # But the daily tick uses prev_high, and hourly ticks use hourly highs
    
    # For the TAO case: prev_high=$341, close_high=$307
    # The deal had avg ~$320, TP ~$325
    # prev_high $341 >= TP $325 → daily tick would trigger TP
    # But avg of $320 was achieved with layers added AFTER the prev_high day
    
    # Key metric: if close_date's close price is more than 5% below invested/layers average
    # it strongly suggests the position was deep underwater when "TP hit"
    
    # Rough avg_entry estimate: for the close to be at TP, price ~ avg * 1.015
    # If current price is way below that, the "TP" was from a stale daily high
    
    if close_close < prev_close * 0.9:  # Close date price dropped >10% from prev day
        suspicious.append({
            "symbol": sym,
            "open": open_date,
            "close": close_date,
            "layers": layers,
            "invested": invested,
            "pnl": pnl,
            "prev_high": prev_high,
            "prev_close": prev_close,
            "close_close": close_close,
            "close_high": close_high,
            "price_drop_pct": round((prev_close - close_close) / prev_close * 100, 1),
        })
    else:
        confirmed_ok.append(sym)

print(f"\n=== SUSPICIOUS DEALS (close price >10% below prev day) ===")
print(f"Count: {len(suspicious)}")
for s in suspicious:
    print(f"  {s['symbol']:12s} {s['open']}->{s['close']} L{s['layers']} inv=${s['invested']:.0f} pnl=${s['pnl']:.0f}")
    print(f"    Prev day: high=${s['prev_high']:.2f} close=${s['prev_close']:.2f}")
    print(f"    Close day: high=${s['close_high']:.2f} close=${s['close_close']:.2f} (dropped {s['price_drop_pct']}%)")

# Also count how many multi-layer 1.48% deals had the position open across multiple days
print(f"\n=== MULTI-DAY MULTI-LAYER DEALS (1.48% return) ===")
multi_day = [t for t in trades if float(t["return_pct"]) == 1.48 and int(t["layers"]) >= 2 
             and t["open_time"][:10] != t["close_time"][:10]]
print(f"Count: {len(multi_day)}")
for t in multi_day:
    print(f"  {t['symbol']:12s} {t['open_time'][:10]}->{t['close_time'][:10]} L{t['layers']} inv=${float(t['invested']):.0f} dur={t['duration_h']}h")

db.close()
