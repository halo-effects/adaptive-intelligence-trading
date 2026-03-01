"""
Deep backfill: Get 1h candles back to Jan 2019 for BTC/USDC and ETH/USDC.
This gives ~21 months warmup before Oct 2020 backtest start.
Then rebuild daily candles + indicators for all coins.
"""
import sys, os, time, sqlite3, requests
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "candles.db"


def fetch_1h_binance(symbol_binance, start_date, end_date):
    """Fetch 1h candles from Binance. Returns list of kline arrays."""
    start_ms = int(datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp() * 1000)
    
    all_candles = []
    current = start_ms
    
    while current < end_ms:
        r = requests.get('https://api.binance.com/api/v3/klines', params={
            'symbol': symbol_binance, 'interval': '1h',
            'startTime': current, 'endTime': end_ms, 'limit': 1000
        })
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        all_candles.extend(batch)
        current = batch[-1][0] + 1
        latest = datetime.fromtimestamp(batch[-1][0]/1000).strftime('%Y-%m-%d')
        print(f"  {symbol_binance}: {len(all_candles)} candles, latest {latest}")
        time.sleep(0.15)
    
    return all_candles


def insert_1h(conn, db_symbol, candles):
    """Insert 1h candles, skip duplicates."""
    inserted = skipped = 0
    for c in candles:
        try:
            conn.execute(
                'INSERT INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (db_symbol, '1h', c[0], float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5]))
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1
    conn.commit()
    print(f"  {db_symbol}: inserted {inserted}, skipped {skipped}")
    return inserted


def main():
    conn = sqlite3.connect(str(DB_PATH))
    
    # Step 1: Backfill 1h candles to Jan 2019
    backfills = [
        ('BTC/USDC', 'BTCUSDC', '2019-01-01', '2020-01-01'),
        ('ETH/USDC', 'ETHUSDC', '2019-01-01', '2020-01-01'),
    ]
    
    print("=== Step 1: Backfill 1h candles to Jan 2019 ===")
    for db_sym, binance_sym, start, end in backfills:
        # Check what we already have
        row = conn.execute(
            'SELECT MIN(timestamp), COUNT(*) FROM candles WHERE symbol=? AND timeframe=?',
            (db_sym, '1h')
        ).fetchone()
        if row[0]:
            earliest = datetime.fromtimestamp(row[0]/1000).strftime('%Y-%m-%d')
            print(f"\n{db_sym}: currently starts {earliest} ({row[1]} rows)")
        else:
            print(f"\n{db_sym}: no data")
        
        print(f"Fetching {start} -> {end}...")
        candles = fetch_1h_binance(binance_sym, start, end)
        if candles:
            insert_1h(conn, db_sym, candles)
    
    # Step 2: Rebuild daily candles using build_daily_candles.py
    print("\n=== Step 2: Rebuild daily candles ===")
    from build_daily_candles import main as build_main
    build_main()
    
    # Step 3: Merge SOL/USDT early data into SOL/USDC
    print("\n=== Step 3: Merge SOL/USDT -> SOL/USDC for early data ===")
    earliest_usdc = conn.execute('SELECT MIN(date) FROM candles_daily WHERE symbol=?', ('SOL/USDC',)).fetchone()[0]
    print(f"SOL/USDC starts: {earliest_usdc}")
    
    cols = [c[1] for c in conn.execute('PRAGMA table_info(candles_daily)').fetchall()]
    col_str = ', '.join(cols)
    placeholders = ', '.join(['?'] * len(cols))
    
    rows = conn.execute(f'SELECT {col_str} FROM candles_daily WHERE symbol=? AND date < ? ORDER BY date',
                        ('SOL/USDT', earliest_usdc)).fetchall()
    merged = 0
    for r in rows:
        r = list(r)
        r[0] = 'SOL/USDC'
        try:
            conn.execute(f'INSERT INTO candles_daily ({col_str}) VALUES ({placeholders})', r)
            merged += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    print(f"Merged {merged} SOL/USDT rows as SOL/USDC")
    
    # Step 4: Recompute indicators on merged SOL/USDC
    print("\n=== Step 4: Recompute indicators on SOL/USDC ===")
    import pandas as pd
    import numpy as np
    from build_daily_candles import compute_indicators
    
    sol_rows = conn.execute(
        'SELECT date, timestamp, open, high, low, close, volume FROM candles_daily WHERE symbol=? ORDER BY date',
        ('SOL/USDC',)
    ).fetchall()
    df = pd.DataFrame(sol_rows, columns=['date', 'timestamp', 'open', 'high', 'low', 'close', 'volume'])
    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = df[c].astype(float)
    df = compute_indicators(df)
    
    update_cols = [c for c in ['sma20','sma50','sma200','bb_width','bb_pct','atr14','atr_pct',
                                'adx','plus_di','minus_di','rsi14','consec_hh_hl','consec_lh_ll',
                                'sma50_slope','sma200_slope','price_vs_sma50','price_vs_sma200'] if c in df.columns]
    for _, row in df.iterrows():
        sets = ', '.join([f'{c}=?' for c in update_cols])
        vals = [None if pd.isna(row.get(c)) else float(row[c]) for c in update_cols]
        vals.extend(['SOL/USDC', row['date']])
        conn.execute(f'UPDATE candles_daily SET {sets} WHERE symbol=? AND date=?', vals)
    conn.commit()
    print(f"Recomputed indicators for {len(df)} SOL/USDC rows")
    
    # Step 5: Verify
    print("\n=== Final verification ===")
    for sym in ['BTC/USDC', 'ETH/USDC', 'SOL/USDC']:
        h_row = conn.execute('SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM candles WHERE symbol=? AND timeframe=?',
                              (sym, '1h')).fetchone()
        d_row = conn.execute('SELECT MIN(date), MAX(date), COUNT(*) FROM candles_daily WHERE symbol=?', (sym,)).fetchone()
        adx_count = conn.execute('SELECT COUNT(*) FROM candles_daily WHERE symbol=? AND adx IS NOT NULL', (sym,)).fetchone()[0]
        
        h_start = datetime.fromtimestamp(h_row[0]/1000).strftime('%Y-%m-%d') if h_row[0] else 'N/A'
        print(f"\n{sym}:")
        print(f"  1h candles: {h_start} to ..., {h_row[2]} rows")
        print(f"  Daily: {d_row[0]} to {d_row[1]}, {d_row[2]} rows ({adx_count} with ADX)")
    
    # Step 6: Verify 2W StochRSI at key dates
    print("\n=== 2W StochRSI verification ===")
    from v13_signals import V13SignalPack
    
    for coin in ['BTC', 'ETH']:
        pack = V13SignalPack(coin, str(DB_PATH))
        print(f"\n{coin}:")
        test_dates = ['2020-10-01', '2021-01-01', '2021-04-01', '2021-04-15',
                      '2021-10-01', '2021-11-01', '2021-11-10', '2021-11-15']
        for d in test_dates:
            k = pack.stoch_2w.get_k_at(d)
            s = f'{k:.1f}' if k == k else 'NaN'
            print(f"  {d}: 2W K = {s}")
    
    conn.close()
    print("\nDone!")


if __name__ == '__main__':
    main()
