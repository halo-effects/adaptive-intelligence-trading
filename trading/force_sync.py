"""
Force-sync: close orphaned excess position on exchange.

Compares exchange net position vs bot's tracked deals,
then market-sells the excess to bring them in line.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading.aster_trader import AsterAPI
import json
import time

SYMBOL = "HYPEUSDT"

def main():
    api = AsterAPI()
    
    # 1. Get exchange position
    positions = api.position_risk(SYMBOL)
    exchange_net = 0
    entry_price = 0
    for p in positions:
        if p["symbol"] == SYMBOL and p.get("positionSide", "BOTH") == "BOTH":
            exchange_net = float(p.get("positionAmt", 0))
            entry_price = float(p.get("entryPrice", 0))
            unrealized = float(p.get("unRealizedProfit", 0))
    
    print(f"Exchange net position: {exchange_net:+.4f} HYPE")
    print(f"Exchange entry price: ${entry_price:.5f}")
    print(f"Exchange unrealized PnL: ${unrealized:.4f}")
    print()
    
    # 2. Get bot's tracked deals from status.json
    status_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live", "status.json")
    with open(status_path) as f:
        status = json.load(f)
    
    long_qty = 0
    short_qty = 0
    if status.get("long_deal"):
        long_qty = float(status["long_deal"].get("total_qty", 0))
    if status.get("short_deal"):
        short_qty = float(status["short_deal"].get("total_qty", 0))
    
    tracked_net = round(long_qty - short_qty, 4)
    
    print(f"Bot tracked long qty: {long_qty:.4f}")
    print(f"Bot tracked short qty: {short_qty:.4f}")
    print(f"Bot tracked net: {tracked_net:+.4f}")
    print()
    
    # 3. Calculate drift
    drift = round(exchange_net - tracked_net, 4)
    
    # Get current price
    ticker = api._get("/fapi/v1/ticker/price", {"symbol": SYMBOL})
    current_price = float(ticker["price"])
    drift_value = abs(drift) * current_price
    
    print(f"DRIFT: {drift:+.4f} HYPE (~${drift_value:.2f} at ${current_price:.3f})")
    print()
    
    if abs(drift) < 0.01:
        print("No significant drift. Nothing to do.")
        return
    
    # 4. Determine action
    if drift > 0:
        # Exchange has more long than tracked — need to SELL the excess
        action = "SELL"
        qty = abs(drift)
        print(f"ACTION: SELL {qty:.2f} HYPE to close orphaned long excess")
    else:
        # Exchange has more short than tracked — need to BUY the excess
        action = "BUY"
        qty = abs(drift)
        print(f"ACTION: BUY {qty:.2f} HYPE to close orphaned short excess")
    
    # 5. Confirm
    estimated_loss = unrealized * (abs(drift) / abs(exchange_net)) if exchange_net != 0 else 0
    print(f"Estimated realized loss from closing excess: ~${estimated_loss:.2f}")
    print()
    
    confirm = input("Type YES to execute: ").strip()
    if confirm != "YES":
        print("Aborted.")
        return
    
    # 6. Execute
    print(f"\nExecuting {action} {qty:.2f} {SYMBOL} MARKET...")
    try:
        result = api.place_order(SYMBOL, action, "MARKET", qty)
        print(f"Order result: {result}")
        
        # Wait and check new position
        time.sleep(3)
        positions = api.position_risk(SYMBOL)
        for p in positions:
            if p["symbol"] == SYMBOL and p.get("positionSide", "BOTH") == "BOTH":
                new_net = float(p.get("positionAmt", 0))
                new_unrealized = float(p.get("unRealizedProfit", 0))
                print(f"\nNew exchange position: {new_net:+.4f} HYPE")
                print(f"New unrealized PnL: ${new_unrealized:.4f}")
                print(f"Expected: {tracked_net:+.4f}")
                new_drift = abs(new_net - tracked_net)
                if new_drift < 0.05:
                    print("✅ Position synced successfully!")
                else:
                    print(f"⚠️  Still drifted by {new_drift:.4f} — may need another pass")
    except Exception as e:
        print(f"❌ Order failed: {e}")

if __name__ == "__main__":
    main()
