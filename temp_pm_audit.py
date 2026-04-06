"""V14PM Paper Bot trade audit - past 2 weeks"""
import csv
from collections import defaultdict

rows = []
with open(r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\trades.csv') as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

# Filter last 2 weeks
cutoff = '2026-03-23'
recent = [r for r in rows if r['close_time'] >= cutoff]

print(f"=== TRADES SINCE {cutoff} ===")
print(f"Total deals: {len(recent)}")
print()

# Summary by symbol
by_sym = defaultdict(lambda: {'count':0, 'pnl':0, 'invested':0, 'layers':[], 'durations':[], 'returns':[]})
total_pnl = 0
total_invested = 0

for r in recent:
    sym = r['symbol']
    pnl = float(r['pnl'])
    inv = float(r['invested'])
    layers = int(r['layers'])
    dur = float(r['duration_h'])
    ret = float(r['return_pct'])
    by_sym[sym]['count'] += 1
    by_sym[sym]['pnl'] += pnl
    by_sym[sym]['invested'] += inv
    by_sym[sym]['layers'].append(layers)
    by_sym[sym]['durations'].append(dur)
    by_sym[sym]['returns'].append(ret)
    total_pnl += pnl
    total_invested += inv

print(f"Total realized PnL: ${total_pnl:.2f}")
print(f"Total capital turned: ${total_invested:.2f}")
print()

# By symbol
hdr = f"{'Symbol':<15} {'Deals':>5} {'PnL':>10} {'Avg Inv':>10} {'Avg Layers':>10} {'Avg Dur(h)':>10} {'Avg Ret%':>8}"
print(hdr)
print('-' * len(hdr))
for sym in sorted(by_sym.keys(), key=lambda s: by_sym[s]['pnl'], reverse=True):
    d = by_sym[sym]
    avg_inv = d['invested'] / d['count']
    avg_layers = sum(d['layers']) / len(d['layers'])
    avg_dur = sum(d['durations']) / len(d['durations'])
    avg_ret = (d['pnl'] / d['invested']) * 100 if d['invested'] > 0 else 0
    print(f"{sym:<15} {d['count']:>5} {d['pnl']:>10.2f} {avg_inv:>10.2f} {avg_layers:>10.1f} {avg_dur:>10.1f} {avg_ret:>8.2f}%")

print()

# Check return percentages - should all be ~1.5% (DCA_TP_PCT)
returns = [float(r['return_pct']) for r in recent]
print(f"Return % range: {min(returns):.2f}% to {max(returns):.2f}%")
abnormal = [r for r in recent if abs(float(r['return_pct']) - 1.48) > 0.2]
if abnormal:
    print(f"  WARNING: {len(abnormal)} trades with return % outside 1.28-1.68% band")
    for r in abnormal[:15]:
        print(f"    deal={r['deal_id']} {r['symbol']} ret={r['return_pct']}% layers={r['layers']} inv={r['invested']} pnl={r['pnl']} dur={r['duration_h']}h")
else:
    print("  All returns within expected range (~1.48%)")

# Validate PnL = invested * return_pct / 100
print()
print("=== PNL INTEGRITY CHECK ===")
mismatches = []
for r in recent:
    pnl = float(r['pnl'])
    inv = float(r['invested'])
    ret = float(r['return_pct'])
    expected_pnl = inv * ret / 100
    diff = abs(pnl - expected_pnl)
    if diff > 0.50:  # more than $0.50 discrepancy
        mismatches.append((r, expected_pnl, diff))

if mismatches:
    print(f"WARNING: {len(mismatches)} trades where PnL doesn't match invested * return%")
    for r, exp, diff in mismatches[:10]:
        print(f"  deal={r['deal_id']} {r['symbol']} pnl={r['pnl']} expected={exp:.2f} diff={diff:.2f}")
else:
    print(f"All {len(recent)} trades: PnL matches invested * return% within $0.50 tolerance")

# Check invested vs capital allocation
# With 5 coin slots and $50K capital, each coin should get roughly $10K active
# At 90/10 split, active = $45K, so ~$9K per coin
print()
print("=== POSITION SIZE CHECK ===")
print("Expected: ~$9K per slot (5 slots, 90/10 split on $50K)")
large = [r for r in recent if float(r['invested']) > 20000]
if large:
    print(f"WARNING: {len(large)} trades with invested > $20K")
    for r in large[:10]:
        print(f"  deal={r['deal_id']} {r['symbol']} inv={r['invested']} layers={r['layers']} pnl={r['pnl']}")
else:
    print("No oversized positions found")

# Check for duplicate deal IDs
print()
print("=== DUPLICATE CHECK ===")
deal_ids = [r['deal_id'] for r in recent]
from collections import Counter
dupes = {k:v for k,v in Counter(deal_ids).items() if v > 1}
if dupes:
    print(f"WARNING: {len(dupes)} duplicate deal IDs")
    for did, cnt in list(dupes.items())[:10]:
        matches = [r for r in recent if r['deal_id'] == did]
        for m in matches:
            print(f"  deal={did} {m['symbol']} close={m['close_time']} pnl={m['pnl']} layers={m['layers']}")
else:
    print(f"No duplicate deal IDs among {len(recent)} trades")

# Check deal ID sequencing
print()
print("=== DEAL ID SEQUENCING ===")
all_ids = sorted(set(int(r['deal_id']) for r in recent))
gaps = []
for i in range(1, len(all_ids)):
    if all_ids[i] - all_ids[i-1] > 1:
        gaps.append((all_ids[i-1], all_ids[i]))
if gaps:
    print(f"Gaps in deal IDs: {len(gaps)}")
    for a, b in gaps[:10]:
        print(f"  Gap between {a} and {b} (missing {b-a-1} IDs)")
else:
    print("Deal IDs are sequential (no gaps)")
print(f"ID range: {all_ids[0]} to {all_ids[-1]}")

# Time-based analysis
print()
print("=== DAILY TRADE VOLUME ===")
from collections import OrderedDict
daily = defaultdict(lambda: {'count':0, 'pnl':0, 'invested':0})
for r in recent:
    day = r['close_time'][:10]
    daily[day]['count'] += 1
    daily[day]['pnl'] += float(r['pnl'])
    daily[day]['invested'] += float(r['invested'])

for day in sorted(daily.keys()):
    d = daily[day]
    print(f"  {day}: {d['count']:>3} deals, PnL ${d['pnl']:>8.2f}, turnover ${d['invested']:>10.2f}")

# Cumulative PnL check against status.json
print()
print("=== CUMULATIVE PNL CHECK ===")
all_pnl = sum(float(r['pnl']) for r in rows)
print(f"Sum of ALL trades.csv PnL: ${all_pnl:.2f}")

# Per-symbol lifetime PnL
sym_lifetime = defaultdict(float)
for r in rows:
    sym_lifetime[r['symbol']] += float(r['pnl'])

print(f"Per-symbol lifetime PnL from trades.csv:")
status_rpnl = {}
import json
with open(r'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json') as f:
    s = json.load(f)
for sym, c in s.get('coins', {}).items():
    status_rpnl[sym] = c.get('realized_pnl', 0)

for sym in sorted(set(list(sym_lifetime.keys()) + list(status_rpnl.keys()))):
    csv_pnl = sym_lifetime.get(sym, 0)
    st_pnl = status_rpnl.get(sym, 0)
    diff = abs(csv_pnl - st_pnl)
    flag = " *** MISMATCH" if diff > 1.0 else ""
    print(f"  {sym:<15} trades.csv=${csv_pnl:>10.2f}  status.json=${st_pnl:>10.2f}  diff=${diff:.2f}{flag}")

print(f"\nTotal trades.csv: ${all_pnl:.2f}")
print(f"Total status.json realized: ${sum(status_rpnl.values()):.2f}")
print(f"Difference: ${abs(all_pnl - sum(status_rpnl.values())):.2f}")

# Equity reconciliation
print()
print("=== EQUITY RECONCILIATION ===")
total_invested_open = sum(c.get('invested',0) for c in s.get('coins',{}).values())
total_unrealized = sum(c.get('unrealized_pnl',0) for c in s.get('coins',{}).values())
total_realized = sum(c.get('realized_pnl',0) for c in s.get('coins',{}).values())
reported_equity = s.get('equity', 0)
capital = s.get('capital', 50000)

# equity should = capital + realized_pnl + unrealized_pnl
expected_equity = capital + total_realized + total_unrealized
print(f"Capital: ${capital:.2f}")
print(f"Total realized PnL: ${total_realized:.2f}")
print(f"Total unrealized PnL: ${total_unrealized:.2f}")
print(f"Expected equity (cap + realized + unrealized): ${expected_equity:.2f}")
print(f"Reported equity: ${reported_equity:.2f}")
print(f"Difference: ${abs(expected_equity - reported_equity):.2f}")

# Leverage check
print()
print("=== LEVERAGE CHECK (should be 1x) ===")
print(f"Config leverage: {s.get('leverage')}")
# At 1x, total invested should never exceed equity
max_invested = max(float(r['invested']) for r in recent)
print(f"Max single-trade invested (recent): ${max_invested:.2f}")
print(f"Current open positions invested: ${total_invested_open:.2f}")
print(f"Equity: ${reported_equity:.2f}")
if total_invested_open > reported_equity * 1.1:
    print(f"WARNING: Open positions (${total_invested_open:.2f}) exceed equity (${reported_equity:.2f}) - possible leverage violation")
else:
    print("Open positions within equity bounds (1x leverage OK)")
