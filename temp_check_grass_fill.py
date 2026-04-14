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

SYM = "GRASS/USDT:USDT"

# Check recent closed orders
orders = exchange.fetch_closed_orders(SYM, limit=10)
for o in orders:
    otype = o.get("info", {}).get("type", "?")
    avg = o.get("average") or o.get("info", {}).get("avgPrice", "?")
    ts = o.get("datetime", "?")
    print(f"  {ts} | id={o['id']} | type={otype} | side={o['side']} | qty={o.get('filled')} | avg={avg} | status={o['status']}")

# Check recent trades
print("\nRecent trades:")
trades = exchange.fetch_my_trades(SYM, limit=5)
for t in trades:
    print(f"  {t['datetime']} | {t['side']} {t['amount']} @ {t['price']} | cost={t.get('cost')} | fee={t.get('fee',{}).get('cost')}")
