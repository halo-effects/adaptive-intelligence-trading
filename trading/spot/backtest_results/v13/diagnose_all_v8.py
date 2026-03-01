import sys, os, importlib.util
sys.path.insert(0, '.')
spec = importlib.util.spec_from_file_location('v8', 'trading/spot/backtest_results/v13/v13_phase_backtest_v8.py')
v8 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v8)

for coin in ['BTC', 'ETH', 'SOL', 'BNB', 'XRP']:
    cfg = v8.V13Config()
    pack = v8.V13SignalPack(coin)
    engine = v8.V13BacktestV8(pack, cfg)
    result = engine.run()
    if result:
        print(f"\n{'='*60}")
        roi = result['roi']
        closed = result['closed_roi']
        bh = result['buy_hold_return']
        dd = result['max_drawdown']
        changes = result['phase_changes']
        print(f"{coin}: ROI={roi:+.1f}%, Closed={closed:+.1f}%, B&H={bh:+.1f}%, Alpha={closed-bh:+.1f}%, DD={dd:.1f}%, Changes={changes}")
        for p in engine.phase_log:
            fr = str(p['from']) if p['from'] else 'START'
            to = str(p['to'])
            print(f"  {p['date'].strftime('%Y-%m-%d')}  {fr:>12} -> {to:<12} eq=${p['equity']:>10,.0f}  {p['reason']}")
        
        # Key issue: what happened in last markup?
        # Find the last markup entry and see unrealized loss
        if result['roi'] < result['closed_roi']:
            print(f"  >>> OPEN POSITION LOSS: {result['roi'] - result['closed_roi']:+.1f}% unrealized")
