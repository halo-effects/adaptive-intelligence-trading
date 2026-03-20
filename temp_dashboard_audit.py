import json

with open(r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\status.json") as f:
    S = json.load(f)

print("=" * 60)
print("DASHBOARD FIELD AUDIT - Live PM Status")
print("=" * 60)

# Header fields
print("\n--- HEADER ---")
print(f"  running: {S.get('running')}")
print(f"  halted: {S.get('halted')}")
print(f"  leverage: {S.get('leverage')}")
print(f"  regime: {S.get('regime')}")
print(f"  trend_direction: {S.get('trend_direction')}")
print(f"  symbols: {S.get('symbols')}")
print(f"  timeframe: {S.get('timeframe')}")
print(f"  last_update: {S.get('last_update')}")

# Summary cards
print("\n--- SUMMARY CARDS ---")
print(f"  capital: {S.get('capital')}")
print(f"  equity: {S.get('equity')}")
pnl_pct = S.get('pnl_pct')
cap = S.get('capital', 0)
eq = S.get('equity', 0)
calc_growth = ((eq - cap) / cap * 100) if cap > 0 else 0
print(f"  pnl_pct (stored): {pnl_pct}")
print(f"  growth (calc'd by dashboard): {calc_growth:.2f}%")
print(f"  total_realized_pnl: {S.get('total_realized_pnl')}")
print(f"  deals_completed: {S.get('deals_completed')}")
print(f"  total_fees: {S.get('total_fees')}")
print(f"  win_rate: {S.get('win_rate')}")
print(f"  cash: {S.get('cash')}")
print(f"  max_drawdown_pct: {S.get('max_drawdown_pct')}")
print(f"  uptime_hours: {S.get('uptime_hours')}")
print(f"  profile: {S.get('profile')}")

# Per-coin data
coins = S.get('coins', {})
print(f"\n--- COINS ({len(coins)}) ---")
for sym, c in coins.items():
    print(f"\n  {sym}:")
    for field in ['state', 'lifecycle_phase', 'side', 'layers', 'avg_entry', 
                  'current_price', 'invested', 'unrealized_pnl', 'realized_pnl',
                  'next_tp_price', 'tp_order_id', 'liquidation_price', 
                  'distance_to_liq_pct', 'cfgi', 'cumulative_funding', 'total_fees']:
        print(f"    {field}: {c.get(field)}")

# Exchange balance
print(f"\n--- EXCHANGE ---")
eb = S.get('exchange_balance', {})
print(f"  usdt_free: {eb.get('usdt_free') if eb else None}")
print(f"  usdt_total: {eb.get('usdt_total') if eb else None}")

# Router
print(f"\n--- ROUTER ---")
router = S.get('router', {})
print(f"  active_cash: {router.get('active_cash')}")
print(f"  reserve_cash: {router.get('reserve_cash')}")

# Bot state
print(f"\n--- STATE ---")
print(f"  bot_state: {S.get('bot_state')}")
print(f"  mode: {S.get('mode')}")
print(f"  engine: {S.get('engine')}")

# Missing fields the dashboard expects
print("\n--- MISSING/NULL FIELDS DASHBOARD NEEDS ---")
expected = ['fear_greed_index', 'trend_direction', 'regime']
for f in expected:
    v = S.get(f)
    if v is None or v == '':
        print(f"  ⚠️  {f}: {v}")

# Check trades.csv
import csv
trades_path = r"C:\Users\Never\.openclaw\workspace\trading\spot\live\v14pm\trades.csv"
try:
    with open(trades_path) as f:
        reader = csv.DictReader(f)
        trades = list(reader)
    print(f"\n--- TRADES CSV ({len(trades)} trades) ---")
    if trades:
        print(f"  Columns: {list(trades[0].keys())}")
        wins = sum(1 for t in trades if float(t.get('pnl', 0)) > 0)
        losses = sum(1 for t in trades if float(t.get('pnl', 0)) < 0)
        total_pnl = sum(float(t.get('pnl', 0)) for t in trades)
        print(f"  Wins: {wins}, Losses: {losses}")
        print(f"  Total PnL: ${total_pnl:.4f}")
        for t in trades[-3:]:
            print(f"  Recent: {t.get('symbol')} | pnl={t.get('pnl')} | layers={t.get('layers')} | close={t.get('close_time')}")
except Exception as e:
    print(f"\n--- TRADES CSV: {e} ---")
