"""BTC DCA window breakdown — where does it lose money?"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dca_long_sweep import SweepParams, LongDCAEngine, load_candles, add_regime, get_dca_windows
from datetime import datetime

windows = get_dca_windows('BTC/USDC', 'high')
windows = [w for w in windows if w['end'] >= '2023-03-12']

# Best params from sweep
p = SweepParams(tp_pct=0.008, dev_pct=0.012, so_mult=2.5, max_layers=5, base_pct=0.05, adaptive=False)

print(f"BTC DCA Windows — TP=0.8%, DEV=1.2%, SO=2.5x, L=5, Fixed")
print(f"{'Start':>12} {'End':>12} {'Exit':>10} {'Days':>5} {'ROI':>8} {'PnL':>9} {'Lots':>5} {'WR%':>6} {'DD%':>6}  Price range")
print(f"{'-'*12} {'-'*12} {'-'*10} {'-'*5} {'-'*8} {'-'*9} {'-'*5} {'-'*6} {'-'*6}  {'-'*20}")

for w in windows:
    engine = LongDCAEngine(p, 2500)
    df = load_candles('BTC/USDC', '15m', w['start'], w['end'])
    if df.empty:
        print(f"  {w['start']:>12} {w['end']:>12} {w['exit_to']:>10}  NO DATA")
        continue
    df = add_regime(df)
    for _, row in df.iterrows():
        if not __import__('pandas').isna(row.get('atr_pct')):
            engine.update_regime(row['regime'], row['atr_pct'])
        engine.tick(row['close'], row['high'], row['low'], str(row['date']))
    
    start_price = df.iloc[0]['close']
    end_price = df.iloc[-1]['close']
    price_chg = (end_price - start_price) / start_price * 100
    hi = df['high'].max()
    lo = df['low'].min()
    
    # Force close
    engine.force_close(end_price, str(df.iloc[-1]['date']))
    
    days = (datetime.strptime(w['end'], '%Y-%m-%d') - datetime.strptime(w['start'], '%Y-%m-%d')).days
    print(f"  {w['start']:>12} {w['end']:>12} {w['exit_to']:>10} {days:>5} {engine.roi:>+7.1f}% ${engine.total_pnl:>+8.1f} {engine.total_lots_closed:>5} {engine.win_rate:>5.1f}% {engine._max_dd*100:>5.1f}%  ${start_price:.0f}-${end_price:.0f} ({price_chg:+.1f}%)")
