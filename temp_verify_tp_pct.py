import os, sys, json
sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")
from dotenv import load_dotenv
load_dotenv(r"C:\Users\Never\.openclaw\workspace\.env")
import ccxt

exchange = ccxt.aster({
    "apiKey": os.getenv("ASTER_API_KEY"),
    "secret": os.getenv("ASTER_API_SECRET"),
    "options": {"defaultType": "swap"},
})
exchange.load_markets()

orders = exchange.fetch_open_orders()
positions = exchange.fetch_positions()
pos_map = {}
for p in positions:
    if abs(float(p.get("contracts", 0))) > 0:
        pos_map[p["symbol"]] = float(p["entryPrice"])

print("Open trailing stops vs entry:")
for o in orders:
    sym = o["symbol"]
    otype = o.get("info", {}).get("type", "?")
    act = float(o.get("info", {}).get("activatePrice", 0))
    entry = pos_map.get(sym, 0)
    if entry > 0 and act > 0:
        pct = (act / entry - 1) * 100
        print(f"  {sym.replace(':USDT','')}: entry=${entry:.4f}, activation=${act}, gap={pct:.2f}%")
