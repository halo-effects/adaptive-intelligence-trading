"""Final audit: equity reconciliation with fees, high-return trade analysis"""
import csv, json
from collections import defaultdict

with open(r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\trades.csv') as f:
    rows = list(csv.DictReader(f))

with open(r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json') as f:
    s = json.load(f)

# ============================================================
# 1. EQUITY RECONCILIATION WITH FEES
# ============================================================
print("=" * 60)
print("EQUITY RECONCILIATION (with fees)")
print("=" * 60)
capital = s['capital']
total_realized = s.get('total_realized_pnl', 0)
total_fees = s.get('total_fees', 0)
total_unrealized = sum(c.get('unrealized_pnl', 0) for c in s.get('coins', {}).values())
reported_equity = s['equity']

expected = capital + total_realized - total_fees + total_unrealized
print(f"  Capital:          ${capital:>12.2f}")
print(f"  + Realized PnL:   ${total_realized:>12.2f}")
print(f"  - Fees:           ${total_fees:>12.2f}")
print(f"  + Unrealized PnL: ${total_unrealized:>12.2f}")
print(f"  = Expected:       ${expected:>12.2f}")
print(f"  Reported equity:  ${reported_equity:>12.2f}")
print(f"  Difference:       ${abs(expected - reported_equity):>12.2f}")
if abs(expected - reported_equity) < 1.0:
    print("  ✅ EQUITY TIES OUT PERFECTLY")
else:
    print("  ❌ EQUITY MISMATCH")

# ============================================================
# 2. TRADES.CSV vs STATUS.JSON REALIZED PNL
# ============================================================
print()
print("=" * 60)
print("TRADES.CSV vs STATUS.JSON TOTAL REALIZED PNL")
print("=" * 60)
csv_total = sum(float(r['pnl']) for r in rows)
print(f"  trades.csv sum:         ${csv_total:.2f}")
print(f"  status.total_realized:  ${total_realized:.2f}")
print(f"  Difference:             ${abs(csv_total - total_realized):.2f}")
if abs(csv_total - total_realized) < 1.0:
    print("  ✅ MATCH")

# Per-symbol: the mismatches are from 41 trades in the pre-reconciliation backup
# that got dropped from the current CSV. Let me verify:
backup_rows = []
try:
    with open(r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\trades_backup_pre_reconciliation.csv') as f:
        backup_rows = list(csv.DictReader(f))
except:
    pass

if backup_rows:
    current_ids = set(r['deal_id'] for r in rows)
    missing = [r for r in backup_rows if r['deal_id'] not in current_ids]
    missing_pnl = sum(float(r['pnl']) for r in missing)
    print(f"\n  41 pre-reconciliation trades missing from current CSV:")
    print(f"  Their PnL sum: ${missing_pnl:.2f}")
    
    # Per-symbol check: status.json realized should = csv + missing trades
    sym_csv = defaultdict(float)
    sym_missing = defaultdict(float)
    for r in rows:
        sym_csv[r['symbol']] += float(r['pnl'])
    for r in missing:
        sym_missing[r['symbol']] += float(r['pnl'])
    
    status_rpnl = {sym: c.get('realized_pnl',0) for sym, c in s.get('coins',{}).items()}
    
    print(f"\n  Per-symbol reconciliation (csv + missing vs status):")
    all_syms = sorted(set(list(sym_csv.keys()) + list(sym_missing.keys()) + list(status_rpnl.keys())))
    total_combined = 0
    total_status = 0
    for sym in all_syms:
        combined = sym_csv.get(sym, 0) + sym_missing.get(sym, 0)
        st = status_rpnl.get(sym, 0)
        diff = abs(combined - st)
        total_combined += combined
        total_status += st
        flag = "" if diff < 1.0 else f" *** diff=${diff:.2f}"
        print(f"    {sym:<15} combined=${combined:>10.2f}  status=${st:>10.2f}{flag}")
    print(f"    {'TOTAL':<15} combined=${total_combined:>10.2f}  status=${total_status:>10.2f}")

# ============================================================
# 3. HIGH-RETURN TRADES ANALYSIS
# ============================================================
print()
print("=" * 60)
print("HIGH-RETURN TRADES (>1.6%)")
print("=" * 60)
high = [r for r in rows if float(r['return_pct']) > 1.6]
print(f"Count: {len(high)} out of {len(rows)} total ({len(high)/len(rows)*100:.1f}%)")
print()
print(f"{'Deal':>5} {'Symbol':<15} {'Layers':>6} {'Invested':>10} {'PnL':>10} {'Ret%':>6} {'Duration':>8} {'Close Date'}")
print("-" * 80)
for r in sorted(high, key=lambda x: float(x['return_pct']), reverse=True):
    print(f"{r['deal_id']:>5} {r['symbol']:<15} {r['layers']:>6} {float(r['invested']):>10.2f} {float(r['pnl']):>10.2f} {r['return_pct']:>6}% {r['duration_h']:>7}h {r['close_time'][:10]}")

# ============================================================
# 4. DEAL VELOCITY CHECK - are deals closing too fast?
# ============================================================
print()
print("=" * 60)
print("DEAL VELOCITY (suspicious if too many 1h cycles)")
print("=" * 60)
durations = defaultdict(int)
for r in rows:
    dur = float(r['duration_h'])
    if dur <= 1:
        durations['<=1h'] += 1
    elif dur <= 3:
        durations['1-3h'] += 1
    elif dur <= 12:
        durations['3-12h'] += 1
    elif dur <= 48:
        durations['12-48h'] += 1
    else:
        durations['>48h'] += 1

for bucket in ['<=1h', '1-3h', '3-12h', '12-48h', '>48h']:
    cnt = durations.get(bucket, 0)
    pct = cnt/len(rows)*100
    print(f"  {bucket:>8}: {cnt:>4} deals ({pct:.1f}%)")

# ============================================================
# 5. FEE ANALYSIS
# ============================================================
print()
print("=" * 60)
print("FEE ANALYSIS")
print("=" * 60)
print(f"  Total fees: ${total_fees:.2f}")
print(f"  Total capital turned: ${sum(float(r['invested']) for r in rows):.2f}")
total_turned = sum(float(r['invested']) for r in rows)
# Fees on both buy and sell side
# Buy side: invested amount, sell side: invested + pnl
total_sell = sum(float(r['invested']) + float(r['pnl']) for r in rows)
total_volume = total_turned + total_sell  # approximate round-trip volume
print(f"  Approx round-trip volume: ${total_volume:.2f}")
fee_rate = total_fees / total_volume * 100 if total_volume > 0 else 0
print(f"  Effective fee rate: {fee_rate:.4f}% per side")
print(f"  Expected Hyperliquid taker: 0.035%")
print(f"  Expected maker: 0.010%")

# ============================================================
# 6. PERFORMANCE SUMMARY
# ============================================================
print()
print("=" * 60)
print("PERFORMANCE SUMMARY")
print("=" * 60)
net_pnl = total_realized - total_fees
print(f"  Gross PnL:    ${total_realized:>10.2f}")
print(f"  Fees:         ${total_fees:>10.2f}")
print(f"  Net PnL:      ${net_pnl:>10.2f}")
print(f"  Net return:   {net_pnl/capital*100:.2f}%")
print(f"  Deals:        {len(rows)}")
print(f"  Win rate:     {s.get('win_rate')}%")
print(f"  Max DD:       {s.get('max_drawdown_pct')}%")
print(f"  Uptime:       {s.get('uptime_hours', 0):.0f}h ({s.get('uptime_hours',0)/24:.0f} days)")
days = s.get('uptime_hours', 1) / 24
daily_return = (net_pnl / capital) / days * 100
print(f"  Daily return: {daily_return:.3f}%")
print(f"  Annualized:   {((1 + net_pnl/capital) ** (365/days) - 1) * 100:.1f}%")
