"""Deep dive on discrepancies"""
import csv, json
from collections import defaultdict

# Load trades
rows = []
with open(r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\trades.csv') as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

# Load status
with open(r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json') as f:
    s = json.load(f)

# Load engine state for deeper inspection
with open(r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\engine_state.json') as f:
    estate = json.load(f)

print("=== ENGINE STATE INSPECTION ===")
for sym, eng in estate.items():
    if isinstance(eng, dict):
        lt = eng.get('long_trades', 0)
        lw = eng.get('long_wins', 0)
        lpnl = eng.get('long_pnl', 0)
        cap = eng.get('capital', 0)
        coins = eng.get('long_coins', 0)
        entry = eng.get('long_avg_entry', 0)
        tp = eng.get('long_tp', 0)
        layers = eng.get('long_layers', 0)
        print(f"  {sym}: trades={lt} wins={lw} pnl=${lpnl:.2f} cap=${cap:.2f} coins={coins:.4f} entry=${entry:.4f} layers={layers}")

# Check for backup trades file
print()
print("=== BACKUP TRADES CHECK ===")
backup_rows = []
try:
    with open(r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\trades_backup_pre_reconciliation.csv') as f:
        reader = csv.DictReader(f)
        for r in reader:
            backup_rows.append(r)
    print(f"Backup has {len(backup_rows)} trades vs current {len(rows)} trades")
    
    # Check if backup has trades not in current
    current_ids = set(r['deal_id'] for r in rows)
    backup_ids = set(r['deal_id'] for r in backup_rows)
    missing_from_current = backup_ids - current_ids
    if missing_from_current:
        print(f"Trades in backup but NOT in current: {len(missing_from_current)}")
        for did in sorted(missing_from_current, key=int)[:20]:
            r = next(x for x in backup_rows if x['deal_id'] == did)
            print(f"  deal={did} {r['symbol']} pnl={r['pnl']} close={r['close_time']}")
except FileNotFoundError:
    print("No backup file found")

# Check equity calculation path
print()
print("=== EQUITY CALCULATION DEEP DIVE ===")
# Engine-level capital + PnL
total_engine_cap = 0
total_engine_pnl = 0
for sym, eng in estate.items():
    if isinstance(eng, dict):
        total_engine_cap += eng.get('capital', 0)
        total_engine_pnl += eng.get('long_pnl', 0)

print(f"Sum of engine capitals: ${total_engine_cap:.2f}")
print(f"Sum of engine realized PnL: ${total_engine_pnl:.2f}")

# Check if the capital router has its own accounting
coins_data = s.get('coins', {})
total_allocated = sum(c.get('allocated_capital', c.get('invested', 0)) for c in coins_data.values() if c.get('invested', 0) == 0)
print(f"Status coins with 0 invested (flat): {sum(1 for c in coins_data.values() if c.get('invested',0) == 0)}")
print(f"Status coins with positions: {sum(1 for c in coins_data.values() if c.get('invested',0) > 0)}")

# Cash tracking
print(f"Free cash (status): ${s.get('cash', 'N/A')}")
print(f"Exchange balance (status): ${s.get('exchange_balance', 'N/A')}")

# Check: does status have fields we're missing?
for k in sorted(s.keys()):
    v = s[k]
    if isinstance(v, (int, float, str, bool, type(None))):
        print(f"  status.{k} = {v}")

# Verify every return % is exactly 1.48
print()
print("=== RETURN % DISTRIBUTION ===")
ret_counts = defaultdict(int)
for r in rows:
    ret = r['return_pct']
    ret_counts[ret] += 1
for ret in sorted(ret_counts.keys()):
    print(f"  {ret}%: {ret_counts[ret]} trades")

# Check if multi-layer trades have correct TP math
# For DCA: TP = avg_entry * (1 + 0.015) = avg_entry * 1.015
# So return should always be ~1.48% on invested (slightly less than 1.5% due to rounding)
# 1.48% = 1.5% / 1.015 (the TP is 1.5% above entry, but return on invested is entry/invested * 1.5%)
# Actually: PnL = qty * (tp_price - avg_entry) = qty * avg_entry * 0.015
# invested = qty * avg_entry
# So return % = PnL / invested = 0.015 = 1.5%
# But we see 1.48% consistently... let's check
print()
print("=== TP MATH VERIFICATION ===")
print("Expected: return should be ~1.5% (DCA_TP_PCT)")
print("Observed: 1.48% consistently")
print("Possible explanation: fees or slight price slippage in paper simulation")
print()

# Check: is 1.48 = 1.5 * (1 - fee)?
# If fee = 0.1% per side (0.2% round trip), return = 1.5% - 0.2% = 1.3% (no)
# If fee deducted differently... 1.48/1.50 = 0.9867 => fee ~1.33%? No.
# 1.48% means the TP is computed slightly differently. Let's check:
# In the engine: TP = avg * (1 + TP_PCT). Paper sell at TP.
# PnL = (TP - avg) * qty = avg * TP_PCT * qty
# invested = avg * qty (approximately, ignoring layer cost accumulation)
# return = TP_PCT = 0.015 = 1.5%
# But if return = 1.48%, then effective TP_PCT = 0.0148
# Or: if invested includes fees (invested = cost + fee), return is slightly less
# Hyperliquid taker fee = 0.035%, maker = 0.01%
# On buy: invested = cost * (1 + 0.00035) 
# On sell: proceeds = price * qty * (1 - 0.00035)
# Return = (proceeds - invested) / invested
# = (avg*1.015*qty*(1-0.00035) - avg*qty*(1+0.00035)) / (avg*qty*(1+0.00035))
# = (1.015*0.99965 - 1.00035) / 1.00035
# = (1.01464 - 1.00035) / 1.00035
# = 0.01429 / 1.00035
# = 1.429% ... not 1.48%

# Let's just check: is paper bot even simulating fees?
print("Fee check: Paper bots on Hyperliquid typically simulate 0.035% taker fees")
print("With round-trip fees of 0.07%, 1.5% TP -> ~1.43% net return")
print("But we see 1.48% consistently, suggesting either:")
print("  1. Fees are lower than expected (maker fills?)")
print("  2. The engine uses a slightly different calculation")
print("  3. No fees in paper mode")
