"""Analyze the HYPE trailing stop trade."""
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

SYM = "HYPE/USDT:USDT"

# Get recent trades for HYPE
trades = exchange.fetch_my_trades(SYM, limit=10)
print("Recent HYPE trades:")
for t in trades:
    print(f"  {t['datetime']} | {t['side']} {t['amount']} @ ${t['price']} | cost=${t.get('cost',0):.2f} | fee=${t.get('fee',{}).get('cost', 0):.4f}")

# Get recent closed orders
orders = exchange.fetch_closed_orders(SYM, limit=10)
sells = [o for o in orders if o.get("side") == "sell"]
print("\nRecent HYPE sell orders:")
for o in sells[-5:]:
    otype = o.get("info", {}).get("type", "?")
    avg = o.get("average") or o.get("info", {}).get("avgPrice", "?")
    act = o.get("info", {}).get("activatePrice", "")
    cb = o.get("info", {}).get("priceRate", "")
    ts = o.get("datetime", "?")
    print(f"  {ts} | type={otype} | avg=${avg} | activate={act} | callback={cb}%")

# Calculate the trade
entry = 44.184
activation = entry * 1.015  # $44.8467
fill = 45.096
qty = 0.44  # from the Telegram message it says 0.75 but let me check

# With trailing stop: price ran past activation, trail followed
# Trail trigger = peak * (1 - 0.5%) 
# fill = $45.096 means peak was at least $45.096 / (1 - 0.005) = $45.322
peak_estimate = fill / (1 - 0.005)

print(f"\n=== TRADE ANALYSIS ===")
print(f"Entry: ${entry}")
print(f"Activation (TP level): ${activation:.4f}")
print(f"Fill price: ${fill}")
print(f"Estimated peak: ${peak_estimate:.3f}")
print(f"")
print(f"Without trailing stop (fixed TP): ${activation:.4f}")
print(f"With trailing stop (actual fill): ${fill}")
print(f"Extra captured: ${fill - activation:.4f} per coin")
print(f"")
print(f"Fixed TP profit: ${(activation - entry):.4f} per coin ({(activation/entry - 1)*100:.2f}%)")
print(f"Trail TP profit: ${(fill - entry):.4f} per coin ({(fill/entry - 1)*100:.2f}%)")
print(f"Improvement: {((fill - entry) / (activation - entry) - 1)*100:.1f}% more profit")
