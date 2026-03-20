import ccxt, os

client = ccxt.aster({
    'apiKey': os.environ.get('ASTER_API_KEY', ''),
    'secret': os.environ.get('ASTER_API_SECRET', ''),
    'options': {'defaultType': 'swap'},
    'timeout': 15000
})

# Test fetch_balance
try:
    bal = client.fetch_balance({"type": "future"})
    usdt = bal.get("USDT", {})
    print(f"USDT free: {usdt.get('free')}")
    print(f"USDT total: {usdt.get('total')}")
except Exception as e:
    print(f"fetch_balance FAILED: {e}")

# Test fetch_positions  
try:
    positions = client.fetch_positions()
    for p in positions:
        c = float(p.get('contracts', 0) or 0)
        if c > 0:
            print(f"Position: {p['symbol']} qty={c} entry={p.get('entryPrice')} upnl={p.get('unrealizedPnl')}")
except Exception as e:
    print(f"fetch_positions FAILED: {e}")
