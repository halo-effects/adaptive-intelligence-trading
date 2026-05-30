"""
Reconstruct live PM trades from Aster exchange trade history.

Fetches all fills from Aster via fetch_my_trades() for each coin
that the live PM bot traded, then groups fills into deals and
appends missing deals to trades.csv.
"""

import os
import sys
import csv
import time
import ccxt
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

CSV_PATH = Path("trading/spot/live/v14pm/trades.csv")
BACKUP_PATH = Path("trading/spot/live/v14pm/trades_pre_reconstruct.csv")

# All coins the live PM bot has traded (from status.json history)
SYMBOLS = [
    "TAO/USDT", "HYPE/USDT", "JTO/USDT", "PEPE/USDT", "DYDX/USDT",
    "ENA/USDT", "TON/USDT", "JUP/USDT", "PENDLE/USDT", "ONDO/USDT",
    "INJ/USDT", "HYPE/USDC", "NEAR/USDT", "EIGEN/USDT",
]

# Map to Aster perp symbols
def aster_symbol(sym):
    """Convert generic symbol to Aster perpetual format."""
    base = sym.split("/")[0]
    # Aster uses USDT for all perps
    if base == "PEPE":
        return "1000PEPE/USDT:USDT"
    return f"{base}/USDT:USDT"


def fetch_all_trades(exchange, sym, since_ms):
    """Fetch all trades for a symbol since a given timestamp."""
    aster_sym = aster_symbol(sym)
    all_trades = []
    cursor = since_ms
    
    while True:
        try:
            trades = exchange.fetch_my_trades(aster_sym, since=cursor, limit=500)
        except Exception as e:
            print(f"  Error fetching {aster_sym}: {e}")
            break
        
        if not trades:
            break
            
        all_trades.extend(trades)
        print(f"  {aster_sym}: fetched {len(trades)} trades (total: {len(all_trades)})")
        
        # Advance cursor past last trade
        cursor = trades[-1]['timestamp'] + 1
        
        if len(trades) < 500:
            break
        
        time.sleep(0.5)  # Rate limit
    
    return all_trades


def group_fills_into_deals(fills, sym):
    """
    Group exchange fills into DCA deals.
    
    A deal = consecutive BUY fills followed by a SELL fill.
    The SELL closes the deal.
    """
    deals = []
    current_deal = None
    
    for fill in sorted(fills, key=lambda f: f['timestamp']):
        side = fill.get('side', '').lower()
        
        if side == 'buy':
            if current_deal is None:
                current_deal = {
                    'symbol': sym,
                    'open_time': fill['datetime'],
                    'buys': [],
                    'sells': [],
                    'total_invested': 0,
                    'total_qty': 0,
                    'layers': 0,
                    'fees': 0,
                }
            current_deal['buys'].append(fill)
            current_deal['total_invested'] += fill['cost']
            current_deal['total_qty'] += fill['amount']
            current_deal['layers'] += 1
            current_deal['fees'] += fill.get('fee', {}).get('cost', 0) or 0
            
        elif side == 'sell':
            if current_deal is not None:
                current_deal['sells'].append(fill)
                current_deal['close_time'] = fill['datetime']
                current_deal['proceeds'] = fill['cost']
                current_deal['fill_price'] = fill['price']
                current_deal['fees'] += fill.get('fee', {}).get('cost', 0) or 0
                
                # Calculate PnL
                invested = current_deal['total_invested']
                proceeds = current_deal['proceeds']
                fees = current_deal['fees']
                pnl = proceeds - invested - fees
                
                # Duration
                try:
                    open_dt = datetime.fromisoformat(current_deal['open_time'].replace('Z', '+00:00'))
                    close_dt = datetime.fromisoformat(current_deal['close_time'].replace('Z', '+00:00'))
                    duration_h = round((close_dt - open_dt).total_seconds() / 3600, 1)
                except:
                    duration_h = 0
                
                current_deal['pnl'] = round(pnl, 4)
                current_deal['return_pct'] = round((pnl / invested * 100) if invested > 0 else 0, 2)
                current_deal['duration_h'] = duration_h
                current_deal['invested'] = round(invested, 4)
                
                deals.append(current_deal)
                current_deal = None
            else:
                # Sell without open deal — might be a TP from before our window
                print(f"  WARN: Sell for {sym} at {fill['datetime']} without open deal")
    
    if current_deal is not None:
        print(f"  NOTE: {sym} has an open deal (L{current_deal['layers']}, ${current_deal['total_invested']:.2f} invested)")
    
    return deals


def main():
    api_key = os.environ.get("ASTER_API_KEY", "")
    api_secret = os.environ.get("ASTER_API_SECRET", "")
    
    if not (api_key and api_secret):
        print("ERROR: ASTER_API_KEY and ASTER_API_SECRET must be set")
        sys.exit(1)
    
    # Init exchange
    exchange = ccxt.aster({
        "apiKey": api_key,
        "secret": api_secret,
        "enableRateLimit": True,
        "options": {"defaultType": "future"},
        "timeout": 15000,
    })
    
    # Load existing trades to find last close time and deduplicate
    existing = []
    existing_keys = set()
    last_deal_id = 0
    
    with open(CSV_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing.append(row)
            key = f"{row['symbol']}|{row['close_time'][:19]}"
            existing_keys.add(key)
            did = int(row.get('deal_id', 0))
            if did > last_deal_id:
                last_deal_id = did
    
    print(f"Existing trades: {len(existing)}, last deal_id: {last_deal_id}")
    
    # Find the last close time to know where to start fetching
    last_close = max(row['close_time'] for row in existing)
    print(f"Last existing close: {last_close}")
    
    # Start fetching from the last close time
    # Parse the ISO timestamp
    last_close_dt = datetime.fromisoformat(last_close.replace('Z', '+00:00'))
    since_ms = int(last_close_dt.timestamp() * 1000)
    
    print(f"\nFetching trades from Aster since {last_close_dt.isoformat()}...")
    
    all_deals = []
    seen_symbols = set()
    
    for sym in SYMBOLS:
        print(f"\n--- {sym} ---")
        fills = fetch_all_trades(exchange, sym, since_ms)
        
        if fills:
            seen_symbols.add(sym)
            deals = group_fills_into_deals(fills, sym)
            print(f"  Grouped into {len(deals)} completed deals")
            all_deals.extend(deals)
        else:
            print(f"  No fills found")
        
        time.sleep(0.3)
    
    print(f"\n=== RESULTS ===")
    print(f"Total new deals found: {len(all_deals)}")
    
    # Deduplicate against existing
    new_records = []
    for deal in sorted(all_deals, key=lambda d: d['close_time']):
        close_key = f"{deal['symbol']}|{deal['close_time'][:19]}"
        if close_key in existing_keys:
            print(f"  SKIP duplicate: {close_key}")
            continue
        
        last_deal_id += 1
        record = {
            'deal_id': last_deal_id,
            'symbol': deal['symbol'],
            'open_time': deal['open_time'],
            'close_time': deal['close_time'],
            'layers': deal['layers'],
            'invested': deal['invested'],
            'proceeds': round(deal['proceeds'], 4),
            'fee': round(deal['fees'], 4),
            'pnl': deal['pnl'],
            'return_pct': deal['return_pct'],
            'duration_h': deal['duration_h'],
            'fill_price': deal.get('fill_price', 0),
            'recorded_at': deal['close_time'],
        }
        new_records.append(record)
        print(f"  NEW: {deal['symbol']:15s} {deal['close_time'][:19]} L{deal['layers']} "
              f"${deal['invested']:>8.2f} PnL=${deal['pnl']:>7.2f} ({deal['return_pct']:>5.2f}%)")
    
    if not new_records:
        print("\nNo new trades to append.")
        return
    
    print(f"\n{len(new_records)} new records to append")
    
    # Backup
    import shutil
    shutil.copy2(CSV_PATH, BACKUP_PATH)
    print(f"Backup: {BACKUP_PATH}")
    
    # Append
    fieldnames = [
        "deal_id", "symbol", "open_time", "close_time",
        "layers", "invested", "proceeds", "fee", "pnl", "return_pct",
        "duration_h", "fill_price", "recorded_at"
    ]
    
    with open(CSV_PATH, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        for r in new_records:
            writer.writerow(r)
    
    total = sum(1 for _ in open(CSV_PATH)) - 1
    print(f"\nAppended {len(new_records)} trades. Total in CSV: {total}")


if __name__ == "__main__":
    main()
