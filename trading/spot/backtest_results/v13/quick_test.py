"""Verify Run 4 results reproduce with START_DATE=2020-10-01"""
from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack
from run_new_coins_profiles import make_config

expected = {'ETH/USDC': 284, 'BTC/USDC': 167, 'SOL/USDC': 54}

for coin in ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']:
    pack = V13SignalPack(coin)
    cfg = make_config('high')
    bt = V13BacktestV8(pack, cfg)
    r = bt.run()
    ret = r.get('roi', 0)
    bh = r.get('buy_hold_return', 0)
    exp = expected[coin]
    delta = ret - exp
    flag = "OK" if abs(delta) < 5 else "CHANGED" if delta > 0 else "WORSE"
    print(f"{coin} High: {ret:.1f}% (was {exp}%) B&H: {bh:.0f}% {flag} ({delta:+.1f}%)")
