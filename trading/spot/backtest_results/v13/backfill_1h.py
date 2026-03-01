"""
Backfill 1h candles from Binance for ETH/USDC and SOL/USDC.
BTC/USDC already has data from Oct 2020.
After backfill, rebuild daily candles with indicators.
"""
import sys
import time
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, '.')
from build_daily_candles import aggregate_daily, compute_indicators

DB_PATH = Path(__file__).resolve().parents[2] / 'data' / 'candles.db'

# Binance uses different symbols for spot USDC pairs
# ETH/USDC on Binance = ETHUSDC, SOL/USDC = SOLUSDC
BACKFILLS = [
    {
        'db_symbol': 'ETH/USDC',
        'binance_symbol': 'ETHUSDC',
        'start': '2020-10-01',  # Target start
    },
    {
        'db_symbol': 'SOL/USDC',
        'binance_symbol': 'SOLUSDC',
        'start': '2020-08-01',  # SOL listed Aug 2020
    },
]


def fetch_binance_1h(binance_symbol, start_ms, end_ms):
    """Fetch 1h candles from Binance REST API."""
    import urllib.request
    import json

    all_candles = []
    since = start_ms

    while since < end_ms:
        url = (f"https://api.binance.com/api/v3/klines?"
               f"symbol={binance_symbol}&interval=1h&startTime={since}&limit=1000")
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
        except Exception as e:
            print(f"    Error fetching {binance_symbol} at {since}: {e}")
            break

        if not data:
            break

        for c in data:
            all_candles.append({
                'timestamp': int(c[0]),
                'open': float(c[1]),
                'high': float(c[2]),
                'low': float(c[3]),
                'close': float(c[4]),
                'volume': float(c[5]),
            })

        since = data[-1][0] + 1
        if len(data) < 1000:
            break
        time.sleep(0.2)  # Rate limit

    return all_candles


def main():
    conn = sqlite3.connect(str(DB_PATH))

    for bf in BACKFILLS:
        symbol = bf['db_symbol']
        binance_sym = bf['binance_symbol']
        target_start = bf['start']

        # Check existing data
        row = conn.execute(
            "SELECT MIN(timestamp) FROM candles WHERE symbol=? AND timeframe='1h'",
            (symbol,)
        ).fetchone()
        existing_min_ts = row[0] if row and row[0] else None

        if existing_min_ts:
            existing_start = pd.Timestamp(existing_min_ts, unit='ms')
            print(f"{symbol}: existing 1h data starts {existing_start.date()}")
        else:
            print(f"{symbol}: no existing 1h data")
            existing_start = pd.Timestamp(datetime.now(timezone.utc))

        target_ts = pd.Timestamp(target_start)
        if existing_start <= target_ts:
            print(f"  Already have data from {existing_start.date()}, target {target_start} - SKIP")
            continue

        # Fetch from target to existing start
        start_ms = int(target_ts.timestamp() * 1000)
        end_ms = int(existing_start.timestamp() * 1000)
        print(f"  Fetching {target_start} to {existing_start.date()} ...")

        candles = fetch_binance_1h(binance_sym, start_ms, end_ms)
        if not candles:
            print(f"  No candles returned! Binance may not have {binance_sym} USDC pair that far back.")
            # Try USDT pair instead
            usdt_sym = binance_sym.replace('USDC', 'USDT')
            print(f"  Trying {usdt_sym} instead...")
            candles = fetch_binance_1h(usdt_sym, start_ms, end_ms)
            if candles:
                print(f"  Got {len(candles)} candles from {usdt_sym} - will store as {symbol}")

        if not candles:
            print(f"  FAILED - no data available")
            continue

        # Filter out any that overlap with existing
        if existing_min_ts:
            candles = [c for c in candles if c['timestamp'] < existing_min_ts]

        if not candles:
            print(f"  No new candles after filtering overlaps - SKIP")
            continue

        print(f"  Inserting {len(candles)} new 1h candles...")
        conn.executemany(
            "INSERT INTO candles (symbol, timestamp, open, high, low, close, volume, timeframe) "
            "VALUES (?,?,?,?,?,?,?,?)",
            [(symbol, c['timestamp'], c['open'], c['high'], c['low'], c['close'], c['volume'], '1h')
             for c in candles]
        )
        conn.commit()

        first_date = pd.Timestamp(candles[0]['timestamp'], unit='ms').date()
        last_date = pd.Timestamp(candles[-1]['timestamp'], unit='ms').date()
        print(f"  Inserted: {first_date} to {last_date}")

    # Now rebuild daily candles for all three coins
    print("\n=== Rebuilding daily candles from 1h data ===")
    for symbol in ['ETH/USDC', 'SOL/USDC', 'BTC/USDC']:
        df_1h = pd.read_sql_query(
            "SELECT timestamp, open, high, low, close, volume FROM candles "
            "WHERE symbol=? AND timeframe='1h' ORDER BY timestamp",
            conn, params=(symbol,)
        )
        if len(df_1h) == 0:
            print(f"  {symbol}: no 1h data")
            continue

        for col in ['open', 'high', 'low', 'close', 'volume']:
            df_1h[col] = pd.to_numeric(df_1h[col], errors='coerce')
        df_1h['timestamp'] = df_1h['timestamp'].astype(int)

        daily = aggregate_daily(df_1h)
        daily = compute_indicators(daily)
        daily['date'] = daily['date'].dt.strftime('%Y-%m-%d')
        daily['symbol'] = symbol

        cols = ['symbol', 'date', 'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'candle_count', 'sma20', 'sma50', 'sma200', 'bb_width', 'bb_pct',
                'atr14', 'atr_pct', 'adx', 'plus_di', 'minus_di', 'rsi14',
                'consec_hh_hl', 'consec_lh_ll', 'sma50_slope', 'sma200_slope',
                'price_vs_sma50', 'price_vs_sma200']

        conn.execute("DELETE FROM candles_daily WHERE symbol=?", (symbol,))
        daily[cols].to_sql('candles_daily', conn, if_exists='append', index=False)
        conn.commit()

        adx_valid = daily['adx'].notna().sum()
        print(f"  {symbol}: {len(daily)} daily candles, ADX valid={adx_valid}, "
              f"{daily['date'].iloc[0]} to {daily['date'].iloc[-1]}")

    conn.close()
    print("\nDone!")


if __name__ == '__main__':
    main()
