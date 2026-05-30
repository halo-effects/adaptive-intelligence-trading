"""
Parse trades from bot.log and compare with existing trades.csv
This script:
1. Parses the log for BUY/SELL patterns
2. Identifies real trade closes (not rollbacks)
3. Compares with existing CSV
4. Reports missing trades
"""

import re
from datetime import datetime, timezone
from collections import defaultdict

LOG_PATH = r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\bot.log"
CSV_PATH = r"C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\trades.csv"

# Pattern: 2026-05-16 00:00:32,745 [INFO] v14_portfolio_paper: Router approved BUY for INJ/USDT L2: $3662.57
BUY_PATTERN = re.compile(
    r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ \[INFO\] (?:v14_portfolio_paper|V14PortfolioPaper): Router approved BUY for (\S+) L(\d+): \$([0-9.]+)'
)

# Pattern for Deal close: 2026-05-16 00:00:30,163 [INFO] V14CapitalManager: Deal close for NEAR/USDT: Returned $2253.04 to Active Pool.
DEAL_CLOSE_PATTERN = re.compile(
    r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ \[INFO\] V14CapitalManager: Deal close for (\S+): Returned \$([0-9.]+) to Active Pool'
)

# Also look for trade recording patterns (in paper bot, log may show trade recorded)
TRADE_RECORD_PATTERN = re.compile(
    r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+.*(?:Trade recorded|trade recorded|Recorded trade).*?(\w+/\w+)'
)

print("Loading log file...")
with open(LOG_PATH, 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()
print(f"Loaded {len(lines)} lines")

# Parse all BUY events
buy_events = []
deal_close_events = []

for line in lines:
    m = BUY_PATTERN.search(line)
    if m:
        ts_str, symbol, layer, amount = m.groups()
        ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        buy_events.append({
            'timestamp': ts,
            'symbol': symbol,
            'layer': int(layer),
            'amount': float(amount),
            'raw': line.strip()
        })
    
    m = DEAL_CLOSE_PATTERN.search(line)
    if m:
        ts_str, symbol, amount = m.groups()
        ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        deal_close_events.append({
            'timestamp': ts,
            'symbol': symbol,
            'amount': float(amount),
            'raw': line.strip()
        })

print(f"\nTotal BUY events: {len(buy_events)}")
print(f"Total Deal close events: {len(deal_close_events)}")

# Show BUY events by symbol
by_symbol_buys = defaultdict(list)
for b in buy_events:
    by_symbol_buys[b['symbol']].append(b)

print("\n=== BUY events by symbol (all time) ===")
for sym in sorted(by_symbol_buys.keys()):
    events = by_symbol_buys[sym]
    min_ts = min(e['timestamp'] for e in events)
    max_ts = max(e['timestamp'] for e in events)
    print(f"  {sym}: {len(events)} buys, {min_ts.strftime('%m-%d')} to {max_ts.strftime('%m-%d')}")

# Show Deal close events by symbol
by_symbol_closes = defaultdict(list)
for c in deal_close_events:
    by_symbol_closes[c['symbol']].append(c)

print("\n=== Deal close events by symbol (all time) ===")
for sym in sorted(by_symbol_closes.keys()):
    events = by_symbol_closes[sym]
    # Count unique amounts per symbol (to identify rollbacks vs real closes)
    amounts = [e['amount'] for e in events]
    unique_amounts = set(amounts)
    print(f"  {sym}: {len(events)} closes, amounts: {sorted(unique_amounts)[:5]}{'...' if len(unique_amounts) > 5 else ''}")

# Now try to reconstruct trades
# The TradeTracker logic:
# - L1 BUY opens a new deal (or if one is already open, the old one must have TP'd)
# - L2+ BUY adds layers to existing deal
# - SELL closes the deal

# But we don't see SELL entries in the log! The paper bot likely logs trade closes
# differently. Let me look for what comes right before/after a deal close.

print("\n\n=== Checking log around a real Deal close for INJ/USDT ===")
# Find the May 18 16:00 close (returned $9308.63 - real close)
for i, line in enumerate(lines):
    if '2026-05-18 16:00:12' in line and 'INJ/USDT' in line:
        start = max(0, i-5)
        end = min(len(lines), i+10)
        print(f"\nContext around line {i}:")
        for j in range(start, end):
            print(f"  {j}: {lines[j].rstrip()}")
        break

print("\n=== Checking log around a known TP for NEAR/USDT (deal 834 close) ===")
for i, line in enumerate(lines):
    if '2026-05-16 00:00:30' in line and 'NEAR/USDT' in line:
        start = max(0, i-5)
        end = min(len(lines), i+15)
        print(f"\nContext around line {i}:")
        for j in range(start, end):
            print(f"  {j}: {lines[j].rstrip()}")
        break
