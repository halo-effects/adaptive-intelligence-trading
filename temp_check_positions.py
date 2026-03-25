import ccxt, os

client = ccxt.aster({
    'apiKey': os.environ.get('ASTER_API_KEY', ''),
    'secret': os.environ.get('ASTER_API_SECRET', ''),
    'options': {'defaultType': 'swap'},
    'timeout': 15000
})

positions = client.fetch_positions()
for p in positions:
    contracts = float(p.get('contracts', 0) or 0)
    if contracts > 0:
        sym = p['symbol']
        entry = float(p.get('entryPrice', 0))
        mark = float(p.get('markPrice', 0))
        upnl = float(p.get('unrealizedPnl', 0))
        side = p.get('side', '')
        cost = entry * contracts
        pnl_pct = ((mark - entry) / entry) * 100 if entry > 0 else 0
        print(f"{sym}")
        print(f"  Qty: {contracts} | Side: {side}")
        print(f"  Entry: ${entry:.4f} | Mark: ${mark:.4f}")
        print(f"  Cost: ${cost:.2f} | uPnL: ${upnl:.4f} ({pnl_pct:+.2f}%)")
        print()

bal = client.fetch_balance({'type': 'future'})
free = float(bal.get('USDT', {}).get('free', 0))
total = float(bal.get('USDT', {}).get('total', 0))
print(f"USDT: free=${free:.2f} | total=${total:.2f}")

# Open orders
for sym_check in ['GRASS/USDT:USDT', 'HYPE/USDT:USDT']:
    try:
        orders = client.fetch_open_orders(sym_check)
        coin = sym_check.split('/')[0]
        if orders:
            for o in orders:
                print(f"\n{coin} order: {o['side']} {o['amount']} @ ${o['price']} ({o['type']})")
        else:
            print(f"\n{coin}: no open orders")
    except Exception as e:
        print(f"\n{sym_check}: order check failed - {e}")
