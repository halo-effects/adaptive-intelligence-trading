"""Trade-by-trade diff: standalone backtest vs paper bot trades.csv.
Identifies EXACTLY where and why the two engines diverge."""
import sys, csv
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'
PAPER_TRADES = r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v13\trades.csv'

COINS = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
START = '2024-10-01'
END = '2026-02-27'

# Load paper bot trades
paper_trades = {}
with open(PAPER_TRADES) as f:
    reader = csv.DictReader(f)
    for row in reader:
        sym = row['symbol']
        if sym not in paper_trades:
            paper_trades[sym] = []
        paper_trades[sym].append(row)

for coin in COINS:
    short = coin.split('/')[0]
    print(f"\n{'='*100}")
    print(f"  {coin}")
    print(f"{'='*100}")
    
    # Run standalone backtest
    cfg = V13Config()
    cfg.CAPITAL = 2500
    cfg.START_DATE = START
    cfg.END_DATE = END
    cfg.TIER1_PCT = 0.60; cfg.TIER2_PCT = 0.20; cfg.TIER3_PCT = 0.10
    cfg.SHORT_TIER1_PCT = 0.60; cfg.SHORT_TIER2_PCT = 0.20; cfg.SHORT_TIER3_PCT = 0.10
    cfg.SHORTS_ENABLED = True
    
    pack = V13SignalPack(coin, db_path=DB)
    engine = V13BacktestV8(pack, cfg)
    result = engine.run()
    
    # Extract backtest phase transitions
    print(f"\n  BACKTEST PHASE LOG:")
    for p in engine.phase_log:
        fr = p.get('from')
        to = p.get('to')
        fr_s = fr.name if hasattr(fr, 'name') else str(fr) if fr else 'None'
        to_s = to.name if hasattr(to, 'name') else str(to) if to else '?'
        eq = p.get('equity', 0)
        dt = str(p['date'])[:10]
        reason = p.get('reason', '')
        print(f"    {dt}  {fr_s:>12} -> {to_s:<12} eq=${eq:>10,.0f}  {reason}")
    
    # Extract backtest deals (closed trades with PnL)
    bt_deals = []
    for t in engine.trades:
        action = t.get('action', '')
        if 'pnl_pct' in t:
            bt_deals.append({
                'date': str(t.get('date', ''))[:10],
                'action': action,
                'amount': t.get('amount', 0),
                'price': t.get('price', 0),
                'pnl_pct': t.get('pnl_pct', 0),
                'phase': t.get('phase', ''),
            })
    
    # Paper bot deals
    pb_deals = paper_trades.get(coin, [])
    
    print(f"\n  BACKTEST: {len(bt_deals)} trades with PnL, final equity ${result['final_equity']:,.0f}")
    print(f"  PAPER:   {len(pb_deals)} closed deals")
    
    # Compare deal-by-deal
    print(f"\n  DEAL COMPARISON:")
    print(f"  {'#':>3} {'BT Date':>12} {'BT Action':<40} {'BT$':>10} {'PB Date':>12} {'PB Regime':<12} {'PB$':>10} {'Match':>6}")
    print(f"  {'-'*3} {'-'*12} {'-'*40} {'-'*10} {'-'*12} {'-'*12} {'-'*10} {'-'*6}")
    
    max_deals = max(len(bt_deals), len(pb_deals))
    for i in range(max_deals):
        bt = bt_deals[i] if i < len(bt_deals) else None
        pb = pb_deals[i] if i < len(pb_deals) else None
        
        bt_date = bt['date'] if bt else ''
        bt_action = bt['action'][:40] if bt else ''
        bt_amt = bt['amount'] if bt else 0
        
        pb_date = pb['open_time'][:10] if pb else ''
        pb_regime = pb['regime'] if pb else ''
        pb_pnl = float(pb['pnl']) if pb else 0
        
        bt_pnl = bt['amount'] * bt['pnl_pct'] / (100 + bt['pnl_pct']) if bt and (100 + bt['pnl_pct']) != 0 else 0
        
        match = 'YES' if bt_date == pb_date else 'NO'
        
        print(f"  {i+1:>3} {bt_date:>12} {bt_action:<40} ${bt_pnl:>9.1f} {pb_date:>12} {pb_regime:<12} ${pb_pnl:>9.1f} {match:>6}")
    
    # Capital evolution comparison
    print(f"\n  CAPITAL EVOLUTION (backtest):")
    print(f"    Start: $2,500")
    running = 2500
    for t in engine.trades:
        action = t.get('action', '')
        if 'SELL_ALL' in action or 'SHORT_CLOSE' in action or 'DCA_TP' in action or 'DCA_CLOSE' in action:
            pnl_pct = t.get('pnl_pct', 0)
            amt = t.get('amount', 0)
            pnl = amt * pnl_pct / (100 + pnl_pct) if (100 + pnl_pct) != 0 else 0
            running += pnl  # rough tracking
            dt = str(t.get('date', ''))[:10]
            # Don't print DCA small trades, just big ones
            if abs(pnl) > 50 or 'SELL_ALL' in action or 'SHORT_CLOSE' in action:
                print(f"    {dt}  {action:<40} pnl=${pnl:>8.1f}  capital~${running:>9.1f}")
    
    print(f"    Final equity: ${result['final_equity']:,.1f}")
    
    # Compare with paper bot
    print(f"\n  PAPER BOT REALIZED PnL:")
    pb_total = 0
    for d in pb_deals:
        pnl = float(d['pnl'])
        pb_total += pnl
        if abs(pnl) > 50:
            print(f"    {d['open_time'][:10]}->{d['close_time'][:10]}  {d['regime']:<12} layers={d['layers']}  pnl=${pnl:>9.1f}  ({d['return_pct']}%)")
    print(f"    Total realized: ${pb_total:,.1f}")
    
print(f"\n{'='*100}")
print("SUMMARY")
print(f"{'='*100}")
print("\nKey: If dates match but PnL differs -> compounding/sizing difference")
print("     If dates DON'T match -> phase divergence (different trade path)")
