"""Check recent closed orders and trades on Aster to see if trailing stops triggered."""
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

# Get all recent closed orders across all symbols
symbols_to_check = [
    "GRASS/USDT:USDT", "TAO/USDT:USDT", "HYPE/USDT:USDT",
    "ZEC/USDT:USDT", "FET/USDT:USDT", "JTO/USDT:USDT"
]

print("=== Recent Closed SELL Orders (last 3 days) ===\n")
for sym in symbols_to_check:
    try:
        orders = exchange.fetch_closed_orders(sym, limit=10)
        sells = [o for o in orders if o.get("side") == "sell"]
        if sells:
            for o in sells[-5:]:  # last 5 sell orders per symbol
                otype = o.get("info", {}).get("type", "?")
                avg = o.get("average") or o.get("info", {}).get("avgPrice", "?")
                act_price = o.get("info", {}).get("activatePrice", "")
                callback = o.get("info", {}).get("priceRate", "")
                ts = o.get("datetime", "?")
                status = o.get("status", "?")
                qty = o.get("filled", o.get("amount", "?"))
                print(f"  {sym.split(':')[0]}")
                print(f"    Time: {ts}")
                print(f"    Type: {otype} | Status: {status}")
                print(f"    Qty: {qty} | Avg Price: {avg}")
                if act_price:
                    print(f"    Activation: {act_price} | Callback: {callback}%")
                print()
    except Exception as e:
        print(f"  {sym}: Error fetching orders: {e}\n")

# Also check recent trades
print("\n=== Recent Trades (all symbols) ===\n")
for sym in symbols_to_check:
    try:
        trades = exchange.fetch_my_trades(sym, limit=5)
        if trades:
            for t in trades[-3:]:
                print(f"  {sym.split(':')[0]} | {t['datetime']} | {t['side']} {t['amount']} @ {t['price']} | cost=${t.get('cost',0):.2f}")
    except:
        pass

# Check current open orders (trailing stops still waiting)
print("\n=== Current Open Orders ===\n")
for sym in symbols_to_check:
    try:
        orders = exchange.fetch_open_orders(sym)
        for o in orders:
            otype = o.get("info", {}).get("type", "?")
            act = o.get("info", {}).get("activatePrice", "")
            cb = o.get("info", {}).get("priceRate", "")
            print(f"  {sym.split(':')[0]}: id={o['id']} type={otype} side={o['side']} qty={o.get('amount')} activate={act} callback={cb}%")
    except:
        pass
