from v13_signals import V13SignalPack
for coin in ['LINK/USDC', 'XRP/USDC']:
    try:
        pack = V13SignalPack(coin)
        sym = pack.daily.attrs.get('symbol', '?')
        print(f'{coin}: OK - {len(pack.daily)} rows, sym={sym}, {pack.daily.index[0]}..{pack.daily.index[-1]}')
    except Exception as e:
        print(f'{coin}: FAILED - {e}')
