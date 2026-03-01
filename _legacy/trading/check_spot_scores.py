import json

sr = json.load(open(r'C:\Users\Never\.openclaw\workspace\trading\live\scanner_t1.json'))
aster_spot = {'ETH/USDT','BTC/USDT','BNB/USDT','ASTER/USDT','DEXE/USDT','BIO/USDT','VELO/USDT','FORM/USDT'}

print('=== Scanner scores for Aster spot coins ===')
for coin in sr:
    sym = coin['symbol']
    if sym in aster_spot:
        print(f"  {sym}: score={coin['score']:.1f}, daily_roi={coin.get('daily_roi',0):.4f}, deals/day={coin.get('deals_per_day',0):.2f}")

print()
print('=== Full top 10 for reference ===')
for coin in sr[:10]:
    avail = ' ** ASTER-SPOT' if coin['symbol'] in aster_spot else ''
    print(f"  {coin['symbol']}: {coin['score']:.1f}{avail}")
