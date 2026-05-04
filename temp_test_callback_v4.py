"""Test Aster callback rates via raw API."""
import ccxt, os, time

api_key = os.popen('powershell -c "[Environment]::GetEnvironmentVariable(\'ASTER_API_KEY\', \'User\')"').read().strip()
api_secret = os.popen('powershell -c "[Environment]::GetEnvironmentVariable(\'ASTER_API_SECRET\', \'User\')"').read().strip()

ex = ccxt.aster({
    "apiKey": api_key,
    "secret": api_secret,
    "options": {"defaultType": "swap"},
})
ex.load_markets()

# Use fapiprivate_post_v1_order directly
test_rates = [0.1, 0.2, 0.25, 0.3, 0.4, 0.5]

for rate in test_rates:
    try:
        result = ex.fapiprivate_post_v1_order({
            "symbol": "JTOUSDT",
            "type": "TRAILING_STOP_MARKET",
            "side": "SELL",
            "quantity": "10",
            "activationPrice": "0.35",
            "callbackRate": str(rate),
        })
        oid = result.get("orderId")
        print(f"  {rate}% -> ACCEPTED (order {oid})")
        # Cancel
        try:
            ex.cancel_order(str(oid), "JTO/USDT:USDT")
            print(f"         -> Cancelled")
        except:
            print(f"         -> Cancel failed, may need manual cleanup")
        time.sleep(0.5)
    except Exception as e:
        err_str = str(e)
        if "-2007" in err_str or "Invalid callBack" in err_str:
            print(f"  {rate}% -> REJECTED (Invalid callBack rate)")
        else:
            print(f"  {rate}% -> ERROR: {err_str[:200]}")
        time.sleep(0.5)
