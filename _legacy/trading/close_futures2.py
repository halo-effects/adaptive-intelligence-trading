"""Close remaining futures positions on Aster."""
import ccxt, os, sys, json

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

exchange = ccxt.aster({
    'apiKey': api_key,
    'secret': api_secret,
    'options': {'defaultType': 'future'},
})
exchange.load_markets()

# Check position via signed GET
print("=== Checking positions ===")
try:
    positions = exchange.fetch_positions(['HYPE/USDT:USDT'])
    for p in positions:
        print(f"  Symbol: {p['symbol']}, Side: {p['side']}, Contracts: {p['contracts']}, Entry: {p['entryPrice']}, uPnL: {p['unrealizedPnl']}")
except Exception as e:
    print(f"fetch_positions error: {e}")
    # Try raw API
    try:
        resp = exchange.fetch('/fapi/v2/positionRisk', 'private', 'GET', {'symbol': 'HYPEUSDT'})
        print(f"  Raw: {json.dumps(resp, indent=1)}")
    except Exception as e2:
        print(f"  Raw also failed: {e2}")

# Try to close via CCXT
print("\n=== Closing position ===")
try:
    positions = exchange.fetch_positions(['HYPE/USDT:USDT'])
    for p in positions:
        contracts = float(p['contracts'] or 0)
        if contracts > 0:
            side = p['side']
            close_side = 'sell' if side == 'long' else 'buy'
            print(f"  Closing {side} {contracts} with market {close_side}")
            order = exchange.create_market_order('HYPE/USDT:USDT', close_side, contracts)
            print(f"  Order: {order['id']}, status={order['status']}, avg={order.get('average')}")
except Exception as e:
    print(f"Close error: {e}")

# Balance
print("\n=== Balance ===")
try:
    bal = exchange.fetch_balance()
    usdt = bal.get('USDT', {})
    print(f"  USDT total: {usdt.get('total', '?')}, free: {usdt.get('free', '?')}")
except Exception as e:
    print(f"Balance error: {e}")
