"""Cancel the 3 old trailing stop orders on Aster exchange via ccxt."""
import ccxt, os

api_key = os.environ.get("ASTER_API_KEY")
api_secret = os.environ.get("ASTER_API_SECRET")

if not api_key:
    # Try to find from the bot's config
    import json, sys
    sys.path.insert(0, r"C:\Users\Never\.openclaw\workspace")
    # Check .env files or config
    env_files = [
        r"C:\Users\Never\.openclaw\workspace\.env",
        r"C:\Users\Never\.openclaw\workspace\trading\.env",
        r"C:\Users\Never\.openclaw\workspace\trading\spot\.env",
    ]
    for ef in env_files:
        if os.path.exists(ef):
            with open(ef) as f:
                for line in f:
                    if "ASTER_API_KEY" in line:
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    elif "ASTER_API_SECRET" in line or "ASTER_SECRET" in line:
                        api_secret = line.split("=", 1)[1].strip().strip('"').strip("'")

    if not api_key:
        # Check env vars set at user level
        api_key = os.popen('powershell -c "[Environment]::GetEnvironmentVariable(\'ASTER_API_KEY\', \'User\')"').read().strip()
        api_secret = os.popen('powershell -c "[Environment]::GetEnvironmentVariable(\'ASTER_API_SECRET\', \'User\')"').read().strip()

if not api_key:
    print("ERROR: Cannot find ASTER_API_KEY")
    exit(1)

print(f"API key found: {api_key[:8]}...")

# Connect to Aster perps
ex = ccxt.aster({
    "apiKey": api_key,
    "secret": api_secret,
    "options": {"defaultType": "swap"},
})

print("Exchange connected")

orders_to_cancel = {
    "TAO/USDT:USDT": "214501653",
    "HYPE/USDT:USDT": "1881980937",
    "JTO/USDT:USDT": "10253071",
}

for sym, oid in orders_to_cancel.items():
    try:
        result = ex.cancel_order(oid, sym)
        print(f"Cancelled {sym} order {oid}: {result.get('status', 'OK')}")
    except Exception as e:
        print(f"{sym} order {oid}: {e}")

# Verify
print("\nRemaining open orders:")
for sym in orders_to_cancel:
    try:
        orders = ex.fetch_open_orders(sym)
        if orders:
            for o in orders:
                print(f"  {sym}: {o['id']} {o.get('type','?')} {o.get('side','?')}")
        else:
            print(f"  {sym}: Clean")
    except Exception as e:
        print(f"  {sym}: {e}")
