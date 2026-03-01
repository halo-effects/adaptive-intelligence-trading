"""Run V14 backtests for all 3 risk profiles × 4 coins for website update."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v14_dca_engine import V14DCAEngine, V14Config, V13SignalPack
import pandas as pd
import json

COINS = ['HBAR/USDT', 'ATOM/USDT', 'LINK/USDC', 'NEAR/USDT']
PROFILES = {
    'Low':    {'leverage': 1.0, 'deviation': 0.02, 'layers': 10},
    'Medium': {'leverage': 1.5, 'deviation': 0.02, 'layers': 10},
    'High':   {'leverage': 1.5, 'deviation': 0.015, 'layers': 12},
}
CAPITAL = 10000
PER_COIN_CAPITAL = CAPITAL / len(COINS)  # $2,500 each
START = '2024-10-01'

all_results = {}

for profile_name, params in PROFILES.items():
    print(f"\n{'='*80}")
    print(f"  PROFILE: {profile_name} | Leverage={params['leverage']}x, Dev={params['deviation']*100}%, Layers={params['layers']}")
    print(f"{'='*80}")
    
    profile_results = {}
    total_equity = 0
    total_long_trades = 0
    total_short_trades = 0
    total_long_wins = 0
    total_short_wins = 0
    max_dd_worst = 0
    
    for coin in COINS:
        print(f"\n  --- {coin} ---")
        try:
            pack = V13SignalPack(coin)
        except Exception as e:
            print(f"    ERROR: {e}")
            continue
        
        cfg = V14Config()
        cfg.CAPITAL = PER_COIN_CAPITAL
        cfg.START_DATE = START
        cfg.END_DATE = '2026-02-28'
        cfg.LEVERAGE = params['leverage']
        cfg.DCA_SO_DEVIATION = params['deviation']
        cfg.DCA_MAX_LAYERS = params['layers']
        
        eng = V14DCAEngine(pack, cfg)
        r = eng.run()
        
        if r:
            profile_results[coin] = r
            total_equity += r['final_equity']
            total_long_trades += r['total_long_trades']
            total_short_trades += r['total_short_trades']
            total_long_wins += r['long_wins']
            total_short_wins += r['short_wins']
            if r['max_drawdown'] < max_dd_worst:
                max_dd_worst = r['max_drawdown']
            
            total_trades = r['total_long_trades'] + r['total_short_trades']
            total_wins = r['long_wins'] + r['short_wins']
            win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
            
            # Calculate days
            eq_curve = r['equity_curve']
            num_days = (eq_curve['date'].iloc[-1] - eq_curve['date'].iloc[0]).days if len(eq_curve) > 1 else 1
            daily_roi = r['roi'] / num_days if num_days > 0 else 0
            
            print(f"    Equity: ${r['final_equity']:,.2f} (ROI: {r['roi']:+.1f}%)")
            print(f"    Max DD: {r['max_drawdown']:.1f}%")
            print(f"    Trades: {total_trades} (wins: {total_wins}, rate: {win_rate:.0f}%)")
            print(f"    Daily ROI: {daily_roi:.3f}%")
            print(f"    Fees: ${r['total_fees']:.2f}")
            if r['liquidation_events'] > 0:
                print(f"    ⚠️ LIQUIDATIONS: {r['liquidation_events']}")
    
    # Portfolio summary
    portfolio_roi = (total_equity - CAPITAL) / CAPITAL * 100
    all_trades = total_long_trades + total_short_trades
    all_wins = total_long_wins + total_short_wins
    portfolio_win_rate = (all_wins / all_trades * 100) if all_trades > 0 else 0
    
    # Get num days from any coin
    any_r = list(profile_results.values())[0] if profile_results else None
    num_days = 1
    if any_r:
        eq = any_r['equity_curve']
        num_days = (eq['date'].iloc[-1] - eq['date'].iloc[0]).days if len(eq) > 1 else 1
    portfolio_daily_roi = portfolio_roi / num_days if num_days > 0 else 0
    
    print(f"\n  PORTFOLIO SUMMARY ({profile_name}):")
    print(f"    Total Equity: ${total_equity:,.2f}")
    print(f"    Portfolio ROI: {portfolio_roi:+.1f}%")
    print(f"    Daily ROI: {portfolio_daily_roi:.4f}%")
    print(f"    Total Trades: {all_trades} (wins: {all_wins}, rate: {portfolio_win_rate:.0f}%)")
    print(f"    Worst Max DD: {max_dd_worst:.1f}%")
    print(f"    Days: {num_days}")
    
    all_results[profile_name] = {
        'coins': {coin: {
            'roi': r['roi'],
            'final_equity': r['final_equity'],
            'max_drawdown': r['max_drawdown'],
            'long_trades': r['total_long_trades'],
            'short_trades': r['total_short_trades'],
            'long_wins': r['long_wins'],
            'short_wins': r['short_wins'],
            'total_fees': r['total_fees'],
            'liquidations': r['liquidation_events'],
        } for coin, r in profile_results.items()},
        'portfolio_equity': total_equity,
        'portfolio_roi': portfolio_roi,
        'portfolio_daily_roi': portfolio_daily_roi,
        'portfolio_win_rate': portfolio_win_rate,
        'total_trades': all_trades,
        'total_wins': all_wins,
        'worst_max_dd': max_dd_worst,
        'num_days': num_days,
    }

# Save JSON
output_path = Path(__file__).resolve().parent / 'v14_website_results.json'
with open(output_path, 'w') as f:
    json.dump(all_results, f, indent=2, default=str)
print(f"\nResults saved to {output_path}")
