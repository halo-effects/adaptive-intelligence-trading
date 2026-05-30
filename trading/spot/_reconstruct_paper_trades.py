"""
Reconstruct missing paper PM trades from bot.log.

The trades.csv was accidentally reverted to May 16 during git operations.
This script parses the bot log to recover trades from May 16-29.

Strategy:
- The paper bot logs "Router approved BUY for {SYM} L{N}: ${amt}" for entries
- The paper bot logs "Router approved SELL for {SYM}" or processes SELL actions
- L1 BUY = new deal. If we see another L1 BUY for same coin, previous deal closed.
- We need to find the actual trade execution pattern by reading the code first.
"""

import re
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

LOG_PATH = Path("trading/spot/paper/v14_portfolio/bot.log")
CSV_PATH = Path("trading/spot/paper/v14_portfolio/trades.csv")
BACKUP_PATH = Path("trading/spot/paper/v14_portfolio/trades_pre_reconstruct.csv")

# Date range to reconstruct
START_DATE = "2026-05-16"  # After last CSV entry
END_DATE = "2026-05-30"   # When crash-looping started being fixed

def parse_log():
    """Parse bot log for trade activity between May 16-29."""
    
    # Patterns
    buy_pattern = re.compile(
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ \[INFO\] v14_portfolio_paper: '
        r'Router approved BUY for (\S+) L(\d+): \$([0-9.]+)'
    )
    
    # Rejected BUY (partial capital) - these are NOT real trades
    reject_pattern = re.compile(
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ \[WARNING\] v14_portfolio_paper: '
        r'Router granted partial capital for (\S+).*Rejecting'
    )
    
    # Deal close with capital return (real closes return invested+pnl)
    deal_close_pattern = re.compile(
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ \[INFO\] V14CapitalManager: '
        r'Deal close for (\S+): Returned \$([0-9.]+) to Active Pool'
    )
    
    # Rejected BUY rollback
    rollback_pattern = re.compile(
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ \[INFO\] trading\.spot\.v14_lifecycle_engine: '
        r'(\S+): Rejected BUY, rolled back'
    )
    
    # Stale coin pruned (deal completed + pruned)
    prune_pattern = re.compile(
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ .* Stale coin pruned: (\S+) completed trade'
    )
    
    # Rotation
    rotation_pattern = re.compile(
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ .*Rotating slot: (\S+).*→\s*(\S+)'
    )
    
    # Rebalance date (to track regime)
    regime_pattern = re.compile(
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ .* regime=(\w+)'
    )

    events = []
    rejected_timestamps = set()  # Track rejected BUY timestamps to filter deal_close
    
    print(f"Reading {LOG_PATH}...")
    with open(LOG_PATH, 'r', encoding='utf-8', errors='replace') as f:
        for line_num, line in enumerate(f, 1):
            # Skip lines outside date range
            if line < f"2026-05-16" or line > f"2026-05-30":
                continue
                
            # Check for rejected BUYs first (to filter false deal closes)
            m = reject_pattern.search(line)
            if m:
                ts, sym = m.group(1), m.group(2)
                rejected_timestamps.add((ts[:16], sym))  # minute-level matching
                continue
            
            m = rollback_pattern.search(line)
            if m:
                ts, sym = m.group(1), m.group(2)
                rejected_timestamps.add((ts[:16], sym))
                continue
            
            m = buy_pattern.search(line)
            if m:
                ts, sym, layer, cost = m.group(1), m.group(2), int(m.group(3)), float(m.group(4))
                events.append({
                    'type': 'BUY',
                    'timestamp': ts,
                    'symbol': sym,
                    'layer': layer,
                    'cost': cost,
                    'line': line_num
                })
                continue
            
            m = deal_close_pattern.search(line)
            if m:
                ts, sym, amount = m.group(1), m.group(2), float(m.group(3))
                # Filter out rejected BUY rollbacks (same minute + symbol)
                key = (ts[:16], sym)
                if key in rejected_timestamps:
                    continue
                events.append({
                    'type': 'CLOSE',
                    'timestamp': ts,
                    'symbol': sym,
                    'returned': amount,
                    'line': line_num
                })
                continue
    
    print(f"Found {len(events)} events in date range")
    return events


def reconstruct_trades(events):
    """Match BUY entries with CLOSE events to reconstruct trade records."""
    
    # Track open deals per symbol
    open_deals = {}  # symbol -> {open_time, layers, invested, buys: [...]}
    completed_trades = []
    
    for event in events:
        sym = event['symbol']
        
        if event['type'] == 'BUY':
            layer = event['layer']
            
            if layer == 1:
                # L1 = new deal. If there's already an open deal, it means
                # the previous one closed (TP hit) but we missed the close event.
                # This shouldn't happen if we're parsing correctly.
                if sym in open_deals and open_deals[sym]['layers'] > 0:
                    # Previous deal must have closed - mark as incomplete
                    old = open_deals[sym]
                    print(f"  WARNING: {sym} L1 at {event['timestamp']} but deal was open "
                          f"(L{old['layers']}, invested=${old['invested']:.2f}). "
                          f"Previous deal likely TP'd without explicit close log.")
                    # Try to infer close: the deal closed sometime between last event and now
                    # We'll skip this case and let the close event handle it
                
                open_deals[sym] = {
                    'open_time': event['timestamp'],
                    'layers': 1,
                    'invested': event['cost'],
                    'buys': [event]
                }
            else:
                # L2+ = DCA layer on existing deal
                if sym in open_deals:
                    open_deals[sym]['layers'] = layer
                    open_deals[sym]['invested'] += event['cost']
                    open_deals[sym]['buys'].append(event)
                else:
                    # L2+ without L1 - deal was open before our window
                    open_deals[sym] = {
                        'open_time': event['timestamp'],  # approximate
                        'layers': layer,
                        'invested': event['cost'],
                        'buys': [event],
                        'pre_existing': True
                    }
        
        elif event['type'] == 'CLOSE':
            if sym in open_deals:
                deal = open_deals[sym]
                
                # Calculate trade record
                open_ts = deal['open_time']
                close_ts = event['timestamp']
                invested = deal['invested']
                returned = event['returned']
                pnl = returned - invested
                return_pct = (pnl / invested * 100) if invested > 0 else 0
                
                # Duration
                try:
                    open_dt = datetime.strptime(open_ts, "%Y-%m-%d %H:%M:%S")
                    close_dt = datetime.strptime(close_ts, "%Y-%m-%d %H:%M:%S")
                    duration_h = (close_dt - open_dt).total_seconds() / 3600
                except:
                    duration_h = 0
                
                # Determine regime from engine phase (default LONG_DCA)
                regime = "LONG_DCA"
                
                trade = {
                    'symbol': sym,
                    'open_time': open_ts.replace(' ', 'T') + '+00:00',
                    'close_time': close_ts.replace(' ', 'T') + '+00:00',
                    'regime': regime,
                    'layers': deal['layers'],
                    'invested': round(invested, 2),
                    'pnl': round(pnl, 4),
                    'return_pct': round(return_pct, 2),
                    'duration_h': round(duration_h, 1),
                    'recorded_at': close_ts.replace(' ', 'T') + '+00:00',
                    'pre_existing': deal.get('pre_existing', False)
                }
                
                completed_trades.append(trade)
                del open_deals[sym]
            # else: close without open - might be a pre-existing deal from before our window
    
    return completed_trades


def main():
    # Parse log
    events = parse_log()
    
    # Show event breakdown
    buys = [e for e in events if e['type'] == 'BUY']
    closes = [e for e in events if e['type'] == 'CLOSE']
    print(f"\nBUY events: {buys.__len__()}")
    print(f"CLOSE events: {closes.__len__()}")
    
    # Group by symbol
    buy_syms = defaultdict(list)
    for e in buys:
        buy_syms[e['symbol']].append(e)
    print("\nBUYs by symbol:")
    for sym, evts in sorted(buy_syms.items()):
        layers = [e['layer'] for e in evts]
        l1_count = layers.count(1)
        print(f"  {sym}: {len(evts)} buys ({l1_count} L1 entries)")
    
    close_syms = defaultdict(list)
    for e in closes:
        close_syms[e['symbol']].append(e)
    print("\nCLOSEs by symbol:")
    for sym, evts in sorted(close_syms.items()):
        print(f"  {sym}: {len(evts)} closes")
    
    # Reconstruct trades
    print("\n--- Reconstructing trades ---")
    trades = reconstruct_trades(events)
    
    # Filter out pre-existing deals (opened before our window)
    new_trades = [t for t in trades if not t.get('pre_existing')]
    pre_existing = [t for t in trades if t.get('pre_existing')]
    
    print(f"\nReconstructed {len(trades)} total trades")
    print(f"  New trades (L1 in our window): {len(new_trades)}")
    print(f"  Pre-existing (L2+ only in window): {len(pre_existing)}")
    
    # Show all reconstructed trades
    print("\n--- Reconstructed Trades ---")
    for t in sorted(trades, key=lambda x: x['close_time']):
        pre = " [PRE-EXISTING]" if t.get('pre_existing') else ""
        print(f"  {t['symbol']:15s} {t['open_time'][:19]} -> {t['close_time'][:19]} "
              f"L{t['layers']} ${t['invested']:>10.2f} PnL=${t['pnl']:>8.2f} "
              f"({t['return_pct']:>5.2f}%) {t['duration_h']:>5.1f}h{pre}")
    
    if not trades:
        print("No trades to reconstruct!")
        return
    
    # Read existing CSV to get last deal_id
    existing = []
    with open(CSV_PATH, 'r') as f:
        reader = csv.DictReader(f)
        existing = list(reader)
    last_deal_id = max(int(t['deal_id']) for t in existing) if existing else 0
    print(f"\nLast existing deal_id: {last_deal_id}")
    
    # Check for duplicates
    existing_keys = set()
    for t in existing:
        key = f"{t['symbol']}|{t['open_time']}|{t['close_time']}"
        existing_keys.add(key)
    
    new_records = []
    for t in sorted(trades, key=lambda x: x['close_time']):
        key = f"{t['symbol']}|{t['open_time']}|{t['close_time']}"
        if key in existing_keys:
            print(f"  SKIP duplicate: {key}")
            continue
        last_deal_id += 1
        record = {
            'deal_id': last_deal_id,
            'symbol': t['symbol'],
            'open_time': t['open_time'],
            'close_time': t['close_time'],
            'regime': t['regime'],
            'layers': t['layers'],
            'invested': t['invested'],
            'pnl': t['pnl'],
            'return_pct': t['return_pct'],
            'duration_h': t['duration_h'],
            'recorded_at': t['recorded_at'],
        }
        new_records.append(record)
    
    print(f"\n{len(new_records)} new records to append (after dedup)")
    
    if new_records:
        # Backup
        import shutil
        shutil.copy2(CSV_PATH, BACKUP_PATH)
        print(f"Backup saved to {BACKUP_PATH}")
        
        # Append
        with open(CSV_PATH, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "deal_id", "symbol", "open_time", "close_time", "regime",
                "layers", "invested", "pnl", "return_pct", "duration_h",
                "recorded_at"
            ])
            for r in new_records:
                writer.writerow(r)
        
        print(f"Appended {len(new_records)} trades to {CSV_PATH}")
        
        # Verify
        with open(CSV_PATH, 'r') as f:
            total = sum(1 for _ in f) - 1
        print(f"Total trades in CSV: {total}")


if __name__ == "__main__":
    main()
