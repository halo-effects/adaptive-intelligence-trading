"""Analyze conviction trigger outcomes in V14 DCA engine."""
import sys
import pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
from v14_dca_engine import V14DCAEngine, V14Config

coins = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']

print("CONVICTION TRIGGER ANALYSIS - V14 DCA ENGINE")
print("=" * 70)

for coin in coins:
    pack = V13SignalPack(coin)
    cfg = V14Config()
    cfg.CAPITAL = 2500
    eng = V14DCAEngine(pack, cfg)
    r = eng.run()

    # Get equity curve - figure out its format
    ec = r['equity_curve']
    if isinstance(ec, pd.DataFrame):
        ec_dates = ec.index if isinstance(ec.index, pd.DatetimeIndex) else pd.to_datetime(ec.iloc[:, 0])
        ec_vals = ec.iloc[:, 0] if isinstance(ec.index, pd.DatetimeIndex) else ec.iloc[:, 1]
    else:
        ec = None

    for ct in r['conviction_triggers']:
        date = ct['date']
        price = float(ct['details']['price'])
        score = ct['score']
        short_pnl = float(ct.get('short_pnl_pct', 0))

        # Post-conviction trades
        post_trades = [t for t in r['trades'] if t['date'] >= date]
        long_buys = [t for t in post_trades if 'LONG' in t['action'] and 'BUY' in t['action']]

        # Find price trajectory after conviction from daily data
        daily = pack.daily
        post_daily = daily[daily.index >= date]
        if len(post_daily) > 0:
            price_at_conv = post_daily.iloc[0]['close']
            min_price_after = post_daily['close'].min()
            price_drop = (min_price_after - price_at_conv) / price_at_conv * 100
            min_date = post_daily['close'].idxmin()
            final_price = post_daily.iloc[-1]['close']
            price_recovery = (final_price - price_at_conv) / price_at_conv * 100
        else:
            price_at_conv = price_drop = min_date = final_price = price_recovery = 0

        # Next phase change
        next_phases = [p for p in r['phases'] if p['date'] > date]

        print(f"\n{coin}: CONVICTION fired {date.date()} @ ${price:.2f}")
        print(f"  Score: {score}/4  |  Short PnL at flip: {short_pnl:+.1f}%")
        d = ct['details']
        print(f"  Details: SMA200={'Y' if d['below_sma200'] else 'N'}"
              f"  RSI={float(d['rsi14']):.1f}({'Y' if d['rsi_ok'] else 'N'})"
              f"  StochK={float(d['stochrsi_k']):.1f}({'Y' if d['stoch_ok'] else 'N'})"
              f"  CFGI={float(d['cfgi']):.0f}({'Y' if d['cfgi_ok'] else 'N'})")
        print(f"  Price after conviction:")
        print(f"    At trigger: ${price_at_conv:.2f}")
        print(f"    Min after:  ${min_price_after:.2f} ({price_drop:+.1f}%) on {min_date.date()}")
        print(f"    Final:      ${final_price:.2f} ({price_recovery:+.1f}%)")
        print(f"  Long buys deployed: {len(long_buys)}")
        for lb in long_buys[:6]:
            print(f"    {lb['date'].date()} {lb['action']} @ ${lb['price']:.2f} amt=${lb['amount']:.0f}")
        if next_phases:
            np_ = next_phases[0]
            print(f"  Next phase: {np_['date'].date()} -> {np_['to']} ({np_['reason']})")
        else:
            print(f"  Stays LONG_DCA to end of backtest")

    # All phase transitions
    print(f"\n  ALL PHASES for {coin}:")
    for p in r['phases']:
        print(f"    {p['date'].date()}: {p['from']} -> {p['to']} ({p['reason']})")

    # Top triggers
    for tt in r.get('top_triggers', []):
        print(f"  TOP: {tt['date'].date()} {tt['reason']} @ ${tt['price']:.2f} (armed {tt.get('days_armed', '?')}d)")

    print(f"\n  RESULT: ${r['final_equity']:.2f} ({r['roi']:+.1f}%)")
    print(f"  Long PnL: ${r['long_pnl']:.2f}  Short PnL: ${r['short_pnl']:.2f}")
    print("-" * 70)

# Summary
print("\nPORTFOLIO SUMMARY")
total = 0
for coin in coins:
    pack = V13SignalPack(coin)
    cfg = V14Config()
    cfg.CAPITAL = 2500
    eng = V14DCAEngine(pack, cfg)
    r = eng.run()
    total += r['final_equity']
    print(f"  {coin:<12} ${r['final_equity']:>8,.2f} ({r['roi']:>+7.1f}%)")
print(f"  {'TOTAL':<12} ${total:>8,.2f} ({(total-10000)/10000*100:>+7.1f}%)")
