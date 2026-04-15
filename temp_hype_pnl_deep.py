"""Deep dive on the HYPE $0.11 trade."""
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

# All recent trades
trades = exchange.fetch_my_trades(SYM, limit=20)
print("All recent HYPE trades:")
for t in trades:
    fee = t.get("fee", {})
    print(f"  {t['datetime']} | {t['side']:4s} {t['amount']:6.2f} @ ${t['price']:8.3f} | "
          f"cost=${t.get('cost',0):7.2f} | fee=${fee.get('cost',0):.4f} {fee.get('currency','')}")

# Now trace the specific trade that shows $33.71 invested, $0.11 PnL
# The Telegram said: 0.75 qty, fill $45.096
# But the trade log shows buy 0.75 @ $44.453 ($33.34) then sell 0.75 @ $45.096 ($33.82)

print("\n=== Tracing the $33.71 / $0.11 trade ===")
# Find the buy and sell
buys = [t for t in trades if t["side"] == "buy" and t["amount"] == 0.75]
sells = [t for t in trades if t["side"] == "sell" and t["amount"] == 0.75]

if buys:
    b = buys[-1]
    buy_cost = float(b["cost"])
    buy_fee = float(b.get("fee", {}).get("cost", 0))
    buy_price = float(b["price"])
    print(f"Buy:  {b['amount']} @ ${buy_price} = ${buy_cost:.2f} + fee ${buy_fee:.4f}")
    print(f"Total cost (invested): ${buy_cost + buy_fee:.2f}")

if sells:
    s = sells[-1]
    sell_proceeds = float(s["cost"])
    sell_fee = float(s.get("fee", {}).get("cost", 0))
    sell_price = float(s["price"])
    print(f"Sell: {s['amount']} @ ${sell_price} = ${sell_proceeds:.2f} - fee ${sell_fee:.4f}")
    print(f"Net proceeds: ${sell_proceeds - sell_fee:.2f}")

if buys and sells:
    total_in = buy_cost + buy_fee
    total_out = sell_proceeds - sell_fee
    pnl = total_out - total_in
    pct = (pnl / total_in) * 100
    print(f"\nPnL: ${pnl:.2f} ({pct:.2f}%)")
    print(f"Price move: ${sell_price} / ${buy_price} - 1 = {(sell_price/buy_price - 1)*100:.2f}%")
    
    # What SHOULD have happened with 1.5% trailing activation
    activation = buy_price * 1.015
    min_exit = activation * (1 - 0.005)
    print(f"\nExpected:")
    print(f"  Activation: ${activation:.3f}")
    print(f"  Min exit (activation - 0.5%): ${min_exit:.3f}")
    print(f"  Actual exit: ${sell_price:.3f}")
    print(f"  Actual vs min exit: {'BELOW' if sell_price < min_exit else 'ABOVE'} by ${abs(sell_price - min_exit):.3f}")

# Also check the trades.csv for how the bot recorded it
csv_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\trades.csv"
try:
    with open(csv_path) as f:
        lines = f.readlines()
    hype_lines = [l for l in lines if "HYPE" in l]
    print(f"\nCSV (last 5 HYPE entries):")
    for l in hype_lines[-5:]:
        print(f"  {l.strip()}")
except:
    print("\nCouldn't read trades.csv")
