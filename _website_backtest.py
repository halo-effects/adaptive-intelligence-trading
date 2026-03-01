"""Run V14 backtests for all 3 profiles for website numbers."""
import sys
sys.path.insert(0, 'trading/spot/backtest_results/v13')
from v14_dca_engine import V14DCAEngine, V14Config
from v13_signals import V13SignalPack

coins = ['HBAR/USDT', 'ATOM/USDT', 'LINK/USDC', 'NEAR/USDT']

profiles = {
    'Low': {'LEVERAGE': 1.0, 'DCA_SO_DEVIATION': 0.02, 'DCA_MAX_LAYERS': 10},
    'Medium': {'LEVERAGE': 1.5, 'DCA_SO_DEVIATION': 0.02, 'DCA_MAX_LAYERS': 10},
    'High': {'LEVERAGE': 1.5, 'DCA_SO_DEVIATION': 0.015, 'DCA_MAX_LAYERS': 12},
}

for pname, overrides in profiles.items():
    total_equity = 0; total_trades = 0; total_wins = 0; total_fees = 0
    print(f'\n=== {pname} Profile ===')
    for coin in coins:
        cfg = V14Config()
        cfg.CAPITAL = 2500
        cfg.START_DATE = '2024-10-01'
        cfg.DCA_BO_PCT = 0.40
        cfg.DCA_SO_MULTIPLIER = 1.5
        cfg.DCA_TP_PCT = 0.015
        cfg.DCA_ACCUMULATE = False  # cycling mode
        cfg.CONVICTION_MIN_SCORE = 3
        cfg.MAKER_FEE = 0.0002
        cfg.TAKER_FEE = 0.0005
        for k, v in overrides.items():
            setattr(cfg, k, v)

        pack = V13SignalPack(coin)
        engine = V14DCAEngine(pack, cfg)
        result = engine.run()

        eq = result['final_equity']
        lt = result.get('total_long_trades', 0)
        st = result.get('total_short_trades', 0)
        lw = result.get('long_wins', 0)
        sw = result.get('short_wins', 0)
        trades = lt + st
        wins = lw + sw
        fees = result.get('total_fees', 0)
        dd = result.get('max_drawdown', 0)
        roi = ((eq - 2500) / 2500) * 100
        total_equity += eq
        total_trades += trades
        total_wins += wins
        total_fees += fees
        wr = (wins/trades*100) if trades > 0 else 0
        print(f'  {coin}: eq=${eq:,.0f} ROI=+{roi:.0f}% trades={trades} wr={wr:.0f}% fees=${fees:.0f} dd={dd:.1f}%')
    
    port_roi = ((total_equity - 10000) / 10000) * 100
    wr = (total_wins / total_trades * 100) if total_trades > 0 else 0
    print(f'  PORTFOLIO: ${total_equity:,.0f} ROI=+{port_roi:.0f}% trades={total_trades} wr={wr:.0f}% fees=${total_fees:.0f}')
