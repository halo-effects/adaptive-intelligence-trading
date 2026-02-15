import pandas as pd
df = pd.read_csv(r'C:\Users\Never\.openclaw\workspace\trading\results\hype_optimization_v2.csv')

print('=== TOP 3 PER TIMEFRAME (by profit) ===')
for tf in ['5m', '15m', '1h', '4h']:
    sub = df[df['timeframe'] == tf].sort_values('total_profit_pct', ascending=False).head(3)
    if len(sub) > 0:
        print(f'\n{tf}:')
        for _, r in sub.iterrows():
            print(f'  TP={r["take_profit_pct"]}% SO={int(r["max_safety_orders"])} Dev={r["price_deviation_pct"]}% DevMult={r["deviation_multiplier"]} SOMult={r["safety_order_multiplier"]} -> {int(r["total_trades"])} trades, +{r["total_profit_pct"]:.1f}%, DD={r["max_drawdown_pct"]:.1f}%, RiskAdj={r["risk_adj_score"]:.1f}')

print('\n=== BEST RISK-ADJUSTED (profit / drawdown) ===')
best = df.sort_values('risk_adj_score', ascending=False).head(5)
for _, r in best.iterrows():
    print(f'  {r["timeframe"]} TP={r["take_profit_pct"]}% SO={int(r["max_safety_orders"])} Dev={r["price_deviation_pct"]}% -> {int(r["total_trades"])} trades, +{r["total_profit_pct"]:.1f}%, DD={r["max_drawdown_pct"]:.1f}%, RiskAdj={r["risk_adj_score"]:.1f}')

print('\n=== SWEET SPOT: Best profit with DD < 25% ===')
safe = df[df['max_drawdown_pct'] > -25].sort_values('total_profit_pct', ascending=False).head(5)
for _, r in safe.iterrows():
    print(f'  {r["timeframe"]} TP={r["take_profit_pct"]}% SO={int(r["max_safety_orders"])} Dev={r["price_deviation_pct"]}% DevMult={r["deviation_multiplier"]} SOMult={r["safety_order_multiplier"]} -> {int(r["total_trades"])} trades, +{r["total_profit_pct"]:.1f}%, DD={r["max_drawdown_pct"]:.1f}%')
