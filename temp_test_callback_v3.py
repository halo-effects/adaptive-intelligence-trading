"""Test Aster callback rates — use the same approach as the live bot."""
import ccxt, os, time

api_key = os.popen('powershell -c "[Environment]::GetEnvironmentVariable(\'ASTER_API_KEY\', \'User\')"').read().strip()
api_secret = os.popen('powershell -c "[Environment]::GetEnvironmentVariable(\'ASTER_API_SECRET\', \'User\')"').read().strip()

ex = ccxt.aster({
    "apiKey": api_key,
    "secret": api_secret,
    "options": {"defaultType": "swap"},
})
ex.load_markets()

# Check what methods are available
methods = [m for m in dir(ex) if 'order' in m.lower() and not m.startswith('_')]
print("Order methods:", [m for m in methods if 'create' in m.lower() or 'post' in m.lower()])

# Try using create_order with proper params like the live bot does
test_rates = [0.1, 0.2, 0.25, 0.3, 0.4, 0.5]

for rate in test_rates:
    try:
        result = ex.create_order(
            symbol="JTO/USDT:USDT",
            type="TRAILING_STOP_MARKET",
            side="sell",
            amount=10,
            price=None,
            params={
                "activationPrice": "0.35",
                "callbackRate": str(rate),
            }
        )
        oid = result.get("id")
        print(f"  {rate}% -> ACCEPTED (order {oid})")
        ex.cancel_order(oid, "JTO/USDT:USDT")
        print(f"         -> Cancelled")
        time.sleep(0.5)
    except Exception as e:
        err_str = str(e)
        if "-2007" in err_str or "Invalid callBack" in err_str:
            print(f"  {rate}% -> REJECTED (Invalid callBack rate)")
        else:
            print(f"  {rate}% -> ERROR: {err_str[:200]}")
        time.sleep(0.5)
