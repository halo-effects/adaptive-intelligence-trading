"""
One-time script: Close ASTER spot position and transfer USDT to Perps account.
"""
import io, sys, os, json, time
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import ccxt

DRY_RUN = "--dry-run" in sys.argv

def main():
    api_key = os.environ.get("ASTER_API_KEY", "")
    api_secret = os.environ.get("ASTER_API_SECRET", "")
    if not api_key:
        # Try Windows registry
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\AIT")
            api_key = winreg.QueryValueEx(key, "ASTER_API_KEY")[0]
            api_secret = winreg.QueryValueEx(key, "ASTER_API_SECRET")[0]
        except Exception:
            pass
    if not api_key:
        print("ERROR: No ASTER_API_KEY found")
        sys.exit(1)

    # Connect to Aster Spot
    spot = ccxt.aster({
        "apiKey": api_key,
        "secret": api_secret,
        "enableRateLimit": True,
        "options": {"defaultType": "spot"},
    })
    spot.load_markets()

    # Step 1: Cancel any open orders for ASTER/USDT
    print("Step 1: Cancel open orders...")
    try:
        orders = spot.fetch_open_orders("ASTER/USDT")
        for o in orders:
            print(f"  Cancelling order {o['id']} ({o['type']} {o['side']} {o['amount']} @ {o['price']})")
            if not DRY_RUN:
                spot.cancel_order(o["id"], "ASTER/USDT")
        if not orders:
            print("  No open orders")
    except Exception as e:
        print(f"  Warning: {e}")

    # Step 2: Check ASTER balance (re-fetch after cancel to see freed coins)
    print("\nStep 2: Check balances...")
    time.sleep(2)  # Give exchange time to process cancellations
    bal = spot.fetch_balance()
    aster_free = float(bal.get("ASTER", {}).get("free", 0))
    usdt_free = float(bal.get("USDT", {}).get("free", 0))
    print(f"  ASTER free: {aster_free}")
    print(f"  USDT free: ${usdt_free:.2f}")

    # Step 3: Market sell all ASTER
    if aster_free > 0.01:
        # Get current price
        ticker = spot.fetch_ticker("ASTER/USDT")
        price = ticker.get("last", 0)
        value = aster_free * price
        print(f"\nStep 3: Market sell {aster_free:.4f} ASTER @ ~${price:.6f} (~${value:.2f})")
        
        if DRY_RUN:
            print("  [DRY RUN] Would sell")
        else:
            # Round to exchange precision
            amount = float(spot.amount_to_precision("ASTER/USDT", aster_free))
            order = spot.create_market_sell_order("ASTER/USDT", amount)
            fill = order.get("average") or order.get("price") or price
            cost = order.get("cost") or float(fill) * amount
            fee = (order.get("fee") or {}).get("cost", 0)
            print(f"  SOLD: {amount} ASTER @ ${fill} = ${cost:.2f} (fee: ${fee:.4f})")
            print(f"  Order ID: {order.get('id')}")
            time.sleep(2)
    else:
        print("\nStep 3: No ASTER to sell")

    # Refresh balance
    bal = spot.fetch_balance()
    usdt_total = float(bal.get("USDT", {}).get("free", 0))
    print(f"\nTotal USDT after sell: ${usdt_total:.2f}")

    # Step 4: Transfer USDT from Spot to Futures
    print(f"\nStep 4: Transfer ${usdt_total:.2f} USDT → Futures account...")
    if DRY_RUN:
        print("  [DRY RUN] Would transfer")
    else:
        try:
            # Aster uses Binance-compatible transfer endpoint
            result = spot.transfer("USDT", usdt_total, "spot", "future")
            print(f"  Transfer result: {json.dumps(result, default=str)}")
        except Exception as e:
            print(f"  Transfer via ccxt failed: {e}")
            print("  Trying direct API call...")
            try:
                # Direct fapi endpoint
                result = spot.sapi_private_post_v1_asset_wallet_transfer({
                    "asset": "USDT",
                    "amount": str(usdt_total),
                    "type": "1",  # 1 = spot to futures
                })
                print(f"  Direct transfer result: {json.dumps(result, default=str)}")
            except Exception as e2:
                print(f"  Direct API also failed: {e2}")
                print(f"\n  ⚠️ You'll need to transfer ${usdt_total:.2f} USDT from Spot → Futures manually in the Aster UI.")

    # Step 5: Verify futures balance
    print("\nStep 5: Verify futures balance...")
    try:
        perp = ccxt.aster({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "future"},
        })
        perp.load_markets()
        fbal = perp.fetch_balance()
        fusdt = float(fbal.get("USDT", {}).get("free", 0))
        print(f"  Futures USDT balance: ${fusdt:.2f}")
        if fusdt > 0:
            print(f"\n✅ Ready to launch V14PM Live with ${fusdt:.2f}")
        else:
            print(f"\n⚠️ Futures balance is $0. Manual transfer needed.")
    except Exception as e:
        print(f"  Failed to check futures balance: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
