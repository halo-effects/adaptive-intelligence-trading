import json, sys
sys.stdout.reconfigure(encoding='utf-8')

for coin in ['eth', 'sol', 'btc']:
    path = 'trading/spot/backtest_results/v12_lifecycle/%s_1h.json' % coin
    try:
        d = json.load(open(path))[0]
        pnl = d.get('pnl_pct', 0)
        dd = d.get('max_dd', 0)
        sharpe = d.get('sharpe', 0)
        short = d.get('short_pnl', 0)
        spring = d.get('spring_pnl', 0)
        markup = d.get('markup_pnl', 0)
        exits = d.get('exit_phases', 0)
        springs = d.get('spring_phases', 0)
        markups = d.get('markup_phases', 0)
        eq = d.get('final_equity', 0)
        deals = d.get('total_deals', 0)
        print("%s: PnL=%+.1f%% | DD=%.1f%% | Sharpe=%.2f | Eq=$%.0f" % (coin.upper(), pnl, dd, sharpe, eq))
        print("   Short=$%+.0f | Spring=$%+.0f | Markup=$%+.0f" % (short, spring, markup))
        print("   Exits=%d | Springs=%d | Markups=%d | Deals=%d" % (exits, springs, markups, deals))
        print()
    except Exception as e:
        print("%s: ERROR %s" % (coin.upper(), e))
