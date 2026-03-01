"""Check which coins from the qualified universe are currently in SHORT vs LONG phase."""
import sys, os
import pathlib

sys.path.insert(0, os.path.dirname(__file__))
from v14_dca_engine import V14DCAEngine, V14Config
from v13_signals import V13SignalPack

db_path = str(pathlib.Path(__file__).resolve().parents[3] / 'spot' / 'data' / 'candles.db')
print(f"DB: {db_path}")

coins_usdc = ['ETH/USDC','SOL/USDC','LINK/USDC','XRP/USDC','BTC/USDC','ADA/USDC','LTC/USDC','DOT/USDC','UNI/USDC','AVAX/USDC','AAVE/USDC','BNB/USDC']
coins_usdt = ['HBAR/USDT','ATOM/USDT','NEAR/USDT']

shorts = []
longs = []
router = []

for coin in coins_usdc + coins_usdt:
    try:
        pack = V13SignalPack(coin, db_path)
        if pack.daily is None or len(pack.daily) < 100:
            print(f"  {coin}: SKIP (insufficient data)")
            continue
        engine = V14DCAEngine(pack, V14Config())
        results = engine.run()
        phase = engine.phase
        conv = engine.conviction_fired
        top = engine.top_detected
        roi = results['roi']
        print(f"  {coin}: {phase} | top={top} conv={conv} | ROI={roi:+.1f}%")
        if 'SHORT' in str(phase):
            shorts.append(coin)
        elif 'ROUTER' in str(phase):
            router.append(coin)
        else:
            longs.append(coin)
    except Exception as e:
        print(f"  {coin}: ERROR - {str(e)[:80]}")

print(f"\n=== SUMMARY ===")
print(f"LONG_DCA  ({len(longs)}): {', '.join(longs)}")
print(f"SHORT_DCA ({len(shorts)}): {', '.join(shorts)}")
print(f"ROUTER    ({len(router)}): {', '.join(router)}")
