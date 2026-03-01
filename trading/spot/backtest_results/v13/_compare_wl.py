"""Compare paper bot trades vs backtest trades side by side."""
import csv

# Load paper bot trades
paper = []
with open(r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v13\trades.csv') as f:
    for row in csv.DictReader(f):
        paper.append(row)

print("=" * 100)
print("PAPER BOT vs BACKTEST — TRADE-BY-TRADE COMPARISON")
print("=" * 100)

for coin_key in ['ETH', 'SOL', 'LINK', 'XRP']:
    symbol = f"{coin_key}/USDC"
    coin_trades = [t for t in paper if t['symbol'] == symbol]
    
    print(f"\n{'='*100}")
    print(f"  {coin_key}")
    print(f"{'='*100}")
    
    # Group by phase type
    for phase in ['DCA', 'MARKUP', 'MARKDOWN']:
        trades = [t for t in coin_trades if t['regime'] == phase]
        if not trades:
            continue
        
        wins = [t for t in trades if float(t['pnl']) > 0]
        losses = [t for t in trades if float(t['pnl']) <= 0]
        total_pnl = sum(float(t['pnl']) for t in trades)
        
        print(f"\n  {phase}: {len(wins)}W / {len(losses)}L  (${total_pnl:+,.1f})")
        print(f"  {'Open':<28} {'Close':<28} {'L':>2} {'Invested':>10} {'PnL':>10} {'Ret%':>8}")
        for t in trades:
            open_t = t['open_time'][:10]
            close_t = t['close_time'][:10]
            layers = t['layers']
            invested = float(t['invested'])
            pnl = float(t['pnl'])
            ret = float(t['return_pct'])
            tag = "W" if pnl > 0 else "L"
            print(f"  {open_t:<28} {close_t:<28} {layers:>2} ${invested:>9,.1f} ${pnl:>+9.1f} {ret:>+7.1f}% [{tag}]")

# Summary
print(f"\n{'='*100}")
print("PAPER BOT SUMMARY BY PHASE")
print(f"{'='*100}")

for phase in ['MARKUP', 'MARKDOWN', 'DCA']:
    trades = [t for t in paper if t['regime'] == phase]
    wins = [t for t in trades if float(t['pnl']) > 0]
    losses = [t for t in trades if float(t['pnl']) <= 0]
    total_pnl = sum(float(t['pnl']) for t in trades)
    print(f"  {phase:>10}: {len(wins):>2}W / {len(losses):>2}L  ${total_pnl:>+10,.1f}")

total_pnl = sum(float(t['pnl']) for t in paper)
total_wins = len([t for t in paper if float(t['pnl']) > 0])
total_losses = len([t for t in paper if float(t['pnl']) <= 0])
print(f"  {'TOTAL':>10}: {total_wins:>2}W / {total_losses:>2}L  ${total_pnl:>+10,.1f}")
