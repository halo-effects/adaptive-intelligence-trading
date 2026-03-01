"""Force close all futures positions and cancel all open orders on Aster."""
import ccxt
import os
import sys

# Load credentials from env or Windows registry
api_key = os.environ.get("ASTER_API_KEY", "")
api_secret = os.environ.get("ASTER_API_SECRET", "")
if not api_key:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Environment') as k:
            api_key = winreg.QueryValueEx(k, 'ASTER_API_KEY')[0]
            api_secret = winreg.QueryValueEx(k, 'ASTER_API_SECRET')[0]
    except Exception:
        pass
if not api_key:
    print("ERROR: ASTER_API_KEY not found")
    sys.exit(1)

print(f"API key: {api_key[:8]}...")

exchange = ccxt.aster({
    'apiKey': api_key,
    'secret': api_secret,
    'options': {'defaultType': 'future'},
})

# Cancel all open orders
print("\n=== Cancelling all open orders ===")
try:
    orders = exchange.fetch_open_orders('HYPEUSDT')
    print(f"Found {len(orders)} open orders")
    for o in orders:
        print(f"  Cancelling {o['id']}: {o['side']} {o['amount']} @ {o['price']}")
        exchange.cancel_order(o['id'], 'HYPEUSDT')
        print(f"  Cancelled.")
except Exception as e:
    print(f"Error: {e}")

# Check positions
print("\n=== Current positions ===")
try:
    resp = exchange.fapiPrivateGetPositionRisk({'symbol': 'HYPEUSDT'})
    for p in resp:
        amt = float(p.get('positionAmt', 0))
        entry = float(p.get('entryPrice', 0))
        pnl = float(p.get('unRealizedProfit', 0))
        if amt != 0:
            print(f"  {'LONG' if amt > 0 else 'SHORT'}: {abs(amt)} @ {entry}, uPnL: {pnl:.4f}")
except Exception as e:
    print(f"Error: {e}")

# Close net position with market order
print("\n=== Closing position ===")
try:
    resp = exchange.fapiPrivateGetPositionRisk({'symbol': 'HYPEUSDT'})
    for p in resp:
        amt = float(p.get('positionAmt', 0))
        if amt != 0:
            close_side = 'SELL' if amt > 0 else 'BUY'
            qty = abs(amt)
            print(f"  Market {close_side} {qty} HYPEUSDT")
            result = exchange.fapiPrivatePostOrder({
                'symbol': 'HYPEUSDT',
                'side': close_side,
                'type': 'MARKET',
                'quantity': qty,
            })
            print(f"  Order ID: {result.get('orderId')}, Status: {result.get('status')}")
            print(f"  Avg price: {result.get('avgPrice', 'pending')}")
except Exception as e:
    print(f"Error closing: {e}")

# Final balance
print("\n=== Final balance ===")
try:
    bal = exchange.fapiPrivateV2GetBalance()
    for b in bal:
        if b['asset'] == 'USDT':
            print(f"  USDT: total={b['balance']}, available={b['availableBalance']}")
except Exception as e:
    print(f"Error: {e}")

print("\nDone. Futures positions closed.")
