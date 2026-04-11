"""Full tick-by-tick reconstruction of PM Paper bot deals.
Replays hourly candles through DCA logic WITHOUT the daily tick TP check,
then compares against actual recorded deals to find false TPs."""

import sqlite3, csv, json, datetime
from pathlib import Path
from collections import defaultdict

BASE = Path(r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio")
db = sqlite3.connect(r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db")

# DCA parameters (High profile)
DCA_BO_PCT = 0.30
DCA_SO_DEV = 0.02  # 2% deviation per layer
DCA_SO_MULT = 1.5
DCA_MAX_LAYERS = 12  # High profile override
DCA_TP_PCT = 0.015
TAKER_FEE = 0.00035  # 0.035%
MAKER_FEE = 0.0001   # 0.01%

# Load all recorded deals from CSV
with open(BASE / "trades.csv") as f:
    recorded_deals = list(csv.DictReader(f))

# Load all buy entries from the bot log
buy_log = []
with open(BASE / "bot.log", encoding="utf-8") as f:
    for line in f:
        if "Router approved BUY" in line:
            # Parse: 2026-04-09 19:00:59,114 [INFO] v14_portfolio_paper: Router approved BUY for TAO/USDT L1: $6109.19
            try:
                ts_str = line[:19]
                parts = line.split("Router approved BUY for ")
                if len(parts) < 2:
                    continue
                rest = parts[1].strip()
                sym = rest.split()[0].rstrip(":")
                layer_str = rest.split()[1].rstrip(":")
                layer_num = int(layer_str[1:])
                amount = float(rest.split("$")[1])
                ts = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                buy_log.append({
                    "timestamp": ts,
                    "symbol": sym,
                    "layer": layer_num,
                    "amount": amount,
                })
            except Exception:
                continue

print(f"Loaded {len(recorded_deals)} deals, {len(buy_log)} buy log entries")

# Group buy entries by symbol
buys_by_sym = defaultdict(list)
for b in buy_log:
    buys_by_sym[b["symbol"]].append(b)

# Get all symbols with deals
symbols = sorted(set(t["symbol"] for t in recorded_deals))
print(f"Symbols: {symbols}")

# For each symbol, replay hourly candles and check if TPs were legitimately reachable
false_tp_deals = []
legitimate_deals = []
uncertain_deals = []

for sym in symbols:
    # Get all hourly candles for this symbol
    candles = db.execute("""
        SELECT timestamp, open, high, low, close 
        FROM candles 
        WHERE symbol = ? AND timeframe = '1h'
        ORDER BY timestamp
    """, (sym,)).fetchall()
    
    if not candles:
        continue
    
    # Build candle lookup: ts_ms -> (open, high, low, close)
    candle_map = {}
    for ts_ms, o, h, l, c in candles:
        candle_map[ts_ms] = (o, h, l, c)
    
    # Get buy entries for this symbol
    sym_buys = sorted(buys_by_sym.get(sym, []), key=lambda x: x["timestamp"])
    
    # Get recorded deals for this symbol
    sym_deals = [d for d in recorded_deals if d["symbol"] == sym]
    
    # Simulate: track position state
    # For each deal, check if any hourly candle high DURING THE DEAL
    # exceeded the TP that existed at that specific hour
    
    # Match buys to deals by time window
    for deal in sym_deals:
        ret = float(deal["return_pct"])
        if ret != 1.48:  # Only check TP deals
            continue
        
        layers = int(deal["layers"])
        if layers < 2:  # Single layer deals are less likely to have the bug
            # But still check them
            pass
        
        invested = float(deal["invested"])
        pnl = float(deal["pnl"])
        open_time = deal["open_time"][:19].replace("T", " ")
        close_time = deal["close_time"][:19].replace("T", " ")
        
        try:
            open_dt = datetime.datetime.strptime(open_time, "%Y-%m-%d %H:%M:%S")
            close_dt = datetime.datetime.strptime(close_time, "%Y-%m-%d %H:%M:%S")
        except:
            continue
        
        open_ms = int(open_dt.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
        close_ms = int(close_dt.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
        
        # Find buy entries within this deal's time window
        deal_buys = [b for b in sym_buys 
                     if open_dt - datetime.timedelta(hours=2) <= b["timestamp"] <= close_dt + datetime.timedelta(hours=1)]
        
        # Take the first N buys matching the layer count
        deal_buys = deal_buys[:layers]
        
        if len(deal_buys) < layers:
            uncertain_deals.append({
                "symbol": sym, "open": open_time, "close": close_time,
                "layers": layers, "invested": invested, "reason": "missing buy log entries"
            })
            continue
        
        # Replay: simulate DCA grid with hourly candles
        position_coins = 0.0
        position_cost = 0.0
        position_avg = 0.0
        position_tp = 0.0
        buy_idx = 0
        tp_hit_hourly = False
        tp_hit_candle = None
        
        # Process every hourly candle from first buy to deal close
        first_buy_ms = int(deal_buys[0]["timestamp"].replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
        # Round to hour
        first_buy_ms = (first_buy_ms // 3600000) * 3600000
        
        current_ms = first_buy_ms
        while current_ms <= close_ms:
            if current_ms not in candle_map:
                current_ms += 3600000
                continue
            
            o, h, l, c = candle_map[current_ms]
            candle_dt = datetime.datetime.fromtimestamp(current_ms / 1000, tz=datetime.timezone.utc)
            
            # Check if a buy happens at this candle
            while buy_idx < len(deal_buys):
                buy = deal_buys[buy_idx]
                buy_ms = int(buy["timestamp"].replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
                buy_ms_rounded = (buy_ms // 3600000) * 3600000
                
                if buy_ms_rounded == current_ms:
                    # Add layer at candle close price
                    coins = buy["amount"] / c
                    position_coins += coins
                    position_cost += buy["amount"]
                    position_avg = position_cost / position_coins
                    position_tp = position_avg * (1 + DCA_TP_PCT)
                    buy_idx += 1
                else:
                    break
            
            # Check TP with this candle's high (only if we have a position)
            if position_coins > 0 and position_tp > 0:
                if h >= position_tp:
                    tp_hit_hourly = True
                    tp_hit_candle = candle_dt.strftime("%Y-%m-%d %H:%M")
                    break
            
            current_ms += 3600000
        
        if tp_hit_hourly:
            legitimate_deals.append({
                "symbol": sym, "open": open_time[:10], "close": close_time[:10],
                "layers": layers, "invested": invested, "pnl": pnl,
                "tp_candle": tp_hit_candle, "avg": round(position_avg, 4),
                "tp": round(position_tp, 4)
            })
        else:
            false_tp_deals.append({
                "symbol": sym, "open": open_time[:10], "close": close_time[:10],
                "layers": layers, "invested": invested, "pnl": pnl,
                "avg": round(position_avg, 4), "tp": round(position_tp, 4),
                "max_high_after_all_layers": 0  # We'll fill this
            })

# For false TPs, find the max hourly high after all layers were placed
for d in false_tp_deals:
    close_dt = datetime.datetime.strptime(d["close"] + " 00:00:00", "%Y-%m-%d %H:%M:%S")
    close_ms = int(close_dt.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
    open_dt = datetime.datetime.strptime(d["open"] + " 00:00:00", "%Y-%m-%d %H:%M:%S")
    open_ms = int(open_dt.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
    
    max_h = 0
    for ts_ms in range(open_ms, close_ms + 86400000, 3600000):
        if ts_ms in candle_map:
            _, h, _, _ = candle_map[ts_ms]
            if (d["symbol"], ts_ms) in candle_map or True:
                row = db.execute("SELECT high FROM candles WHERE symbol=? AND timeframe='1h' AND timestamp=?",
                                (d["symbol"], ts_ms)).fetchone()
                if row and row[0] > max_h:
                    max_h = row[0]
    d["max_high_during_deal"] = round(max_h, 4)

print(f"\n{'='*70}")
print(f"RESULTS")
print(f"{'='*70}")
print(f"\nTotal TP deals analyzed: {len(legitimate_deals) + len(false_tp_deals) + len(uncertain_deals)}")
print(f"  Legitimate (hourly high hit TP): {len(legitimate_deals)}")
print(f"  FALSE TP (daily tick artifact):  {len(false_tp_deals)}")
print(f"  Uncertain (missing data):        {len(uncertain_deals)}")

if false_tp_deals:
    total_false_pnl = sum(d["pnl"] for d in false_tp_deals)
    total_false_inv = sum(d["invested"] for d in false_tp_deals)
    print(f"\n  False TP total PnL: ${total_false_pnl:.2f}")
    print(f"  False TP total invested: ${total_false_inv:.2f}")
    
    print(f"\n{'='*70}")
    print(f"FALSE TP DEALS (position was underwater, daily tick closed it)")
    print(f"{'='*70}")
    for d in false_tp_deals:
        print(f"  {d['symbol']:12s} {d['open']}->{d['close']} L{d['layers']} "
              f"inv=${d['invested']:.0f} pnl=${d['pnl']:.0f} "
              f"avg=${d['avg']:.2f} TP=${d['tp']:.2f} maxH=${d.get('max_high_during_deal',0):.2f}")

if uncertain_deals:
    print(f"\n  Uncertain deals:")
    for d in uncertain_deals[:10]:
        print(f"    {d['symbol']:12s} {d['open']}->{d['close']} L{d['layers']} - {d['reason']}")

db.close()
