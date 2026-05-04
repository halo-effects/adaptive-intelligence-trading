"""Test Aster's accepted callback rates for trailing stops."""
import ccxt, os, time

api_key = os.popen('powershell -c "[Environment]::GetEnvironmentVariable(\'ASTER_API_KEY\', \'User\')"').read().strip()
api_secret = os.popen('powershell -c "[Environment]::GetEnvironmentVariable(\'ASTER_API_SECRET\', \'User\')"').read().strip()

ex = ccxt.aster({
    "apiKey": api_key,
    "secret": api_secret,
    "options": {"defaultType": "swap"},
})

# Test with a tiny order on a cheap coin (JTO at $0.31)
# Try different callback rates
test_rates = [0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 1.0]

print("Testing callback rates on Aster TRAILING_STOP_MARKET...")
print("(Using JTO/USDT, qty=1, activation=$0.35 — will be way above market so won't fill)")

for rate in test_rates:
    try:
        result = ex.create_order(
            "JTO/USDT:USDT",
            "TRAILING_STOP_MARKET",
            "sell",
            1,  # tiny qty
            None,
            {
                "activationPrice": "0.35",
                "callbackRate": str(rate),
            }
        )
        oid = result.get("id")
        print(f"  {rate}% → ACCEPTED (order {oid})")
        # Cancel it immediately
        ex.cancel_order(oid, "JTO/USDT:USDT")
        print(f"         → Cancelled")
    except Exception as e:
        err = str(e)
        if "Invalid callBack" in err or "-2007" in err:
            print(f"  {rate}% → REJECTED (Invalid callBack rate)")
        else:
            print(f"  {rate}% → ERROR: {err[:100]}")
