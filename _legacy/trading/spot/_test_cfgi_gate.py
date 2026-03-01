"""Quick test: BTC Medium with CFGI hard gate"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from trading.spot.backtest_engine_v12 import SpotBacktestEngineV12 as V12BacktestEngine
import pandas as pd

base = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(base, 'data', 'rotation_test', 'ETH_USDT_1h.csv'))
print(f'Loaded {len(df)} candles')

engine = V12BacktestEngine(
    symbol='ETH/USDT',
    capital=10000,
    profile='medium',
    exchange='aster',
    compounding=True,
    v12_slippage_pct=0.0005,
)
result = engine.run(df)
print(f"\nETH Medium Results (with CFGI >=75 hard gate):")
r = result if isinstance(result, dict) else result._asdict() if hasattr(result, '_asdict') else vars(result)
roi = r.get('roi_pct', r.get('total_return_pct', '?'))
dd = r.get('max_drawdown_pct', '?')
sharpe = r.get('sharpe_ratio', '?')
exits = r.get('v12_exit_phases', r.get('exit_phases', '?'))
trades = r.get('total_trades', r.get('num_trades', '?'))
print(f"  ROI: {roi}")
print(f"  Max DD: {dd}")
print(f"  Sharpe: {sharpe}")
print(f"  Exit phases: {exits}")
print(f"  Trades: {trades}")
print(f"  Total return: {r.get('total_return_pct', '?')}")
print(f"  Final equity: {r.get('final_equity', '?')}")
print(f"  Deals completed: {r.get('total_deals_completed', '?')}")
print(f"  Win rate: {r.get('win_rate', '?')}")
print(f"  Extra: {r.get('extra', {})}")
print(f"  Runner stats: {r.get('runner_stats', {})}")
