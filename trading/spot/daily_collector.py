"""
V13 Daily Data Collector — Fetches candles, CFGI, signals, and correlations.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
import sqlite3
import time
import traceback
from datetime import datetime, timedelta, timezone
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd


from trading.spot.engine.build_daily_candles import aggregate_daily, compute_indicators
from trading.spot.engine.v13_signals import V13SignalPack

DB_PATH = Path(__file__).resolve().parent / 'data' / 'candles.db'

# Symbols that Binance doesn't list
SKIP_BINANCE = {'HYPE/USDC', 'FTM/USDT', 'MATIC/USDT'}


def _binance_symbol(symbol):
    """Convert 'BTC/USDT' to 'BTCUSDT' for ccxt."""
    return symbol.replace('/', '')


def collect_candles(conn, tokens, min_days=290):
    """Step 1: Fetch latest 1h candles for all coins."""
    import ccxt
    exchange = ccxt.binance({'enableRateLimit': True})

    updated = []
    for coin, symbol in tokens.items():
        if symbol in SKIP_BINANCE:
            print(f"  {symbol}: skipped (not on Binance)")
            continue

        try:
            row = conn.execute(
                "SELECT MAX(timestamp) FROM candles WHERE symbol=? AND timeframe='1h'",
                (symbol,)
            ).fetchone()
            max_ts = row[0] if row and row[0] else None

            if max_ts:
                since = max_ts + 1
            else:
                since = int((datetime.now(timezone.utc) - timedelta(days=min_days + 10)).timestamp() * 1000)

            all_candles = []
            fetch_since = since
            while True:
                candles = exchange.fetch_ohlcv(symbol, '1h', since=fetch_since, limit=1000)
                if not candles:
                    break
                all_candles.extend(candles)
                fetch_since = candles[-1][0] + 1
                if len(candles) < 1000:
                    break
                time.sleep(0.1)

            if all_candles:
                conn.executemany(
                    "INSERT INTO candles (symbol, timestamp, open, high, low, close, volume, timeframe) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    [(symbol, c[0], c[1], c[2], c[3], c[4], c[5], '1h') for c in all_candles]
                )
                conn.commit()
                updated.append(symbol)
                print(f"  {symbol}: +{len(all_candles)} new 1h candles")
            else:
                print(f"  {symbol}: up to date")

            time.sleep(0.1)
        except Exception as e:
            print(f"  {symbol}: fetch error - {e}")

    return updated


def rebuild_daily(conn, updated_symbols, all_tokens):
    """Step 2: Rebuild daily candles for updated symbols."""
    for symbol in updated_symbols:
        try:
            df_1h = pd.read_sql_query(
                "SELECT timestamp, open, high, low, close, volume FROM candles "
                "WHERE symbol=? AND timeframe='1h' ORDER BY timestamp",
                conn, params=(symbol,)
            )
            if len(df_1h) == 0:
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
            print(f"  {symbol}: {len(daily)} daily candles rebuilt")
        except Exception as e:
            print(f"  {symbol}: daily rebuild error - {e}")


def collect_cfgi(conn, cfgi_tokens):
    """Step 3: Fetch CFGI for all coins."""
    api_key = os.environ.get('CFGI_API_KEY', '')
    if not api_key:
        print("  No CFGI_API_KEY set, skipping")
        return

    try:
        cfgi_path = str(Path(__file__).resolve().parent)
        if cfgi_path not in sys.path:
            sys.path.insert(0, cfgi_path)
        from cfgi_client import CFGIClient

        client = CFGIClient(api_key)
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        result = client.get_current(cfgi_tokens)
        inserted = 0
        for token, data in result.items():
            # data is dict like {'cfgi': value} or just a number
            if isinstance(data, dict):
                val = data.get('cfgi', data.get('value'))
            else:
                val = data
            if val is None:
                continue

            # Find symbol for this token
            from trading.spot.coin_scanner import ALL_TOKENS
            symbol = ALL_TOKENS.get(token, f"{token}/USDT")

            # Check if already exists
            existing = conn.execute(
                "SELECT 1 FROM cfgi_daily WHERE symbol=? AND date=?",
                (symbol, today)
            ).fetchone()
            if existing:
                continue

            conn.execute(
                "INSERT INTO cfgi_daily (symbol, date, cfgi) VALUES (?, ?, ?)",
                (symbol, today, val)
            )
            inserted += 1

        conn.commit()
        print(f"  CFGI: inserted {inserted} rows for {today}")
    except Exception as e:
        print(f"  CFGI error: {e}")
        traceback.print_exc()


def compute_signal_snapshots(conn, tokens):
    """Step 4: Compute signal snapshots for today."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    # Delete existing for today
    conn.execute("DELETE FROM signal_snapshots WHERE date=?", (today,))

    inserted = 0
    for coin, symbol in tokens.items():
        try:
            pack = V13SignalPack(coin, db_path=str(DB_PATH))
            daily = pack.daily
            if daily is None or len(daily) == 0:
                continue

            last_date = daily.index[-1]
            last_row = daily.iloc[-1]

            # StochRSI K values
            s1w_k = pack.stoch_1w.get_k_at(last_date)
            s2w_k = pack.stoch_2w.get_k_at(last_date)
            s3w_k = pack.stoch_3w.get_k_at(last_date)

            # CFGI
            cfgi_val = pack.cfgi.value_at(last_date)

            # HVF score
            hvf = None
            try:
                from test_hvf_daily import composite_hvf_score
                comp, _, _, _ = composite_hvf_score(daily, lookback=44)
                if len(comp) > 0:
                    hvf = float(comp.iloc[-1])
            except Exception:
                pass

            conn.execute(
                "INSERT INTO signal_snapshots "
                "(symbol, date, adx, plus_di, minus_di, stoch_1w_k, stoch_2w_k, stoch_3w_k, "
                "sma50_slope, sma200_slope, consec_hh_hl, consec_lh_ll, hvf_score, cfgi_value, "
                "price, price_vs_sma50, price_vs_sma200, rsi14, atr_pct, bb_pct) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (symbol, today,
                 _safe_float(last_row, 'adx'),
                 _safe_float(last_row, 'plus_di'),
                 _safe_float(last_row, 'minus_di'),
                 _nan_to_none(s1w_k),
                 _nan_to_none(s2w_k),
                 _nan_to_none(s3w_k),
                 _safe_float(last_row, 'sma50_slope'),
                 _safe_float(last_row, 'sma200_slope'),
                 _safe_int(last_row, 'consec_hh_hl'),
                 _safe_int(last_row, 'consec_lh_ll'),
                 hvf,
                 _nan_to_none(cfgi_val),
                 _safe_float(last_row, 'close'),
                 _safe_float(last_row, 'price_vs_sma50'),
                 _safe_float(last_row, 'price_vs_sma200'),
                 _safe_float(last_row, 'rsi14'),
                 _safe_float(last_row, 'atr_pct'),
                 _safe_float(last_row, 'bb_pct'))
            )
            inserted += 1
        except Exception as e:
            print(f"  {symbol}: signal snapshot error - {e}")

    conn.commit()
    print(f"  Signal snapshots: {inserted} coins for {today}")


def compute_correlations(conn, tokens):
    """Step 5: Compute weekly correlations (only on Sundays or if empty)."""
    today = datetime.now(timezone.utc)
    today_str = today.strftime('%Y-%m-%d')

    # Check if we should run
    is_sunday = today.weekday() == 6
    row = conn.execute("SELECT COUNT(*) FROM coin_correlations").fetchone()
    is_empty = (row[0] == 0)

    if not is_sunday and not is_empty:
        print("  Correlations: skipped (not Sunday and table not empty)")
        return

    # Load daily closes for all coins
    closes = {}
    for coin, symbol in tokens.items():
        df = pd.read_sql_query(
            "SELECT date, close FROM candles_daily WHERE symbol=? ORDER BY date",
            conn, params=(symbol,)
        )
        if len(df) > 30:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')['close'].astype(float)
            closes[symbol] = df

    if len(closes) < 2:
        print("  Correlations: not enough coins with data")
        return

    # Build returns dataframe
    all_returns = pd.DataFrame({s: c.pct_change() for s, c in closes.items()})

    # Delete existing for today
    conn.execute("DELETE FROM coin_correlations WHERE date=?", (today_str,))

    inserted = 0
    symbols = list(closes.keys())
    for i, j in combinations(range(len(symbols)), 2):
        sa, sb = symbols[i], symbols[j]
        ra = all_returns[sa].dropna()
        rb = all_returns[sb].dropna()
        common = ra.index.intersection(rb.index)

        corr_30 = None
        corr_90 = None

        common_30 = common[-30:] if len(common) >= 30 else common
        if len(common_30) >= 10:
            corr_30 = float(ra[common_30].corr(rb[common_30]))

        common_90 = common[-90:] if len(common) >= 90 else common
        if len(common_90) >= 20:
            corr_90 = float(ra[common_90].corr(rb[common_90]))

        if corr_30 is not None or corr_90 is not None:
            conn.execute(
                "INSERT INTO coin_correlations (date, coin_a, coin_b, correlation_30d, correlation_90d) "
                "VALUES (?,?,?,?,?)",
                (today_str, sa, sb, corr_30, corr_90)
            )
            inserted += 1

    conn.commit()
    print(f"  Correlations: {inserted} pairs for {today_str}")


def _safe_float(row, col):
    try:
        v = row[col]
        if pd.isna(v):
            return None
        return float(v)
    except (KeyError, TypeError):
        return None


def _safe_int(row, col):
    try:
        v = row[col]
        if pd.isna(v):
            return None
        return int(v)
    except (KeyError, TypeError):
        return None


def _nan_to_none(v):
    if v is None:
        return None
    try:
        if np.isnan(v):
            return None
    except (TypeError, ValueError):
        pass
    return float(v)


def run_collector(tokens=None):
    """Run the full daily collection pipeline."""
    if tokens is None:
        from trading.spot.coin_scanner import ALL_TOKENS, CFGI_TOKENS
        tokens = ALL_TOKENS
        cfgi_tokens = CFGI_TOKENS
    else:
        from trading.spot.coin_scanner import CFGI_TOKENS
        cfgi_tokens = [c for c in tokens.keys() if c in CFGI_TOKENS]

    conn = sqlite3.connect(str(DB_PATH))

    print("\n=== Step 1: Fetch 1h Candles ===")
    updated = collect_candles(conn, tokens)

    print("\n=== Step 2: Rebuild Daily Candles ===")
    rebuild_daily(conn, updated, tokens)

    print("\n=== Step 3: Fetch CFGI ===")
    collect_cfgi(conn, cfgi_tokens)

    print("\n=== Step 4: Signal Snapshots ===")
    compute_signal_snapshots(conn, tokens)

    print("\n=== Step 5: Correlations ===")
    compute_correlations(conn, tokens)

    conn.close()
    print("\n=== Daily collection complete ===")


if __name__ == '__main__':
    run_collector()
