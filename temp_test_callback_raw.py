"""Test Aster's callback rate limits using raw ccxt create_order with params."""
import ccxt, os, time

api_key = os.popen('powershell -c "[Environment]::GetEnvironmentVariable(\'ASTER_API_KEY\', \'User\')"').read().strip()
api_secret = os.popen('powershell -c "[Environment]::GetEnvironmentVariable(\'ASTER_API_SECRET\', \'User\')"').read().strip()

ex = ccxt.aster({
    "apiKey": api_key,
    "secret": api_secret,
    "options": {"defaultType": "swap"},
})
ex.load_markets()

# Check exchange info for JTO trailing stop constraints
sym = "JTO/USDT:USDT"
market = ex.market(sym)
print(f"Market: {sym}")
print(f"  Precision: {market.get('precision', {})}")
print(f"  Limits: {market.get('limits', {})}")

# Try placing via the private API directly
test_rates = [0.1, 0.2, 0.25, 0.3, 0.4, 0.5]

for rate in test_rates:
    try:
        params = {
            "type": "TRAILING_STOP_MARKET",
            "side": "SELL",
            "symbol": "JTOUSDT",
            "quantity": "10",
            "activationPrice": "0.35",
            "callbackRate": str(rate),
        }
        result = ex.fapiv4_private_post_order(params)
        oid = result.get("orderId")
        print(f"  {rate}% -> ACCEPTED (order {oid})")
        # Cancel
        ex.fapiv4_private_delete_order({"symbol": "JTOUSDT", "orderId": oid})
        print(f"         -> Cancelled")
        time.sleep(0.3)
    except Exception as e:
        err_str = str(e)
        if "-2007" in err_str:
            print(f"  {rate}% -> REJECTED (Invalid callBack rate)")
        elif "-4003" in err_str:
            print(f"  {rate}% -> REJECTED (below min)")
        else:
            print(f"  {rate}% -> ERROR: {err_str[:150]}")
        time.sleep(0.3)
