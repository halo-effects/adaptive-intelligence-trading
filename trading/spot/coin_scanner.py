"""
V13 Coin Scanner ΓÇö Backtest all CFGI-compatible tokens through V13 phase engine.
Outputs ranked results for the dashboard.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
import json
import sqlite3
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Add v13 modules to path

from trading.spot.engine.build_daily_candles import aggregate_daily, compute_indicators
from trading.spot.engine.v13_signals import V13SignalPack
from trading.spot.engine.v13_phase_backtest_v8 import V13BacktestV8, V13Config

DB_PATH = Path(__file__).resolve().parent / 'data' / 'candles.db'

# 50-coin Aster Perps universe (updated 2026-03-19)
# All coins trade as COIN/USDT perpetual on Aster DEX
# Note: PEPE, BONK, FLOKI use 1000-prefix on Aster (1000PEPEUSDT etc.)
ALL_TOKENS = {
    # Established (pre-2024)
    "AAVE": "AAVE/USDT", "ADA": "ADA/USDT",   "ARB": "ARB/USDT",
    "ATOM": "ATOM/USDT", "AVAX": "AVAX/USDT", "BTC": "BTC/USDT",
    "CRV":  "CRV/USDT",  "DOGE": "DOGE/USDT", "DOT": "DOT/USDT",
    "ETH":  "ETH/USDT",  "FIL":  "FIL/USDT",  "HBAR": "HBAR/USDT",
    "INJ":  "INJ/USDT",  "LINK": "LINK/USDT", "LTC": "LTC/USDT",
    "NEAR": "NEAR/USDT", "SNX":  "SNX/USDT",  "SOL": "SOL/USDT",
    "UNI":  "UNI/USDT",  "XRP":  "XRP/USDT",  "ZEC": "ZEC/USDT",
    # DeFi / Mid-cap
    "JUP":    "JUP/USDT",    "PENDLE": "PENDLE/USDT",
    "STX":    "STX/USDT",    "ZRO":    "ZRO/USDT",
    # High-beta / Speculative
    "APT":   "APT/USDT",  "BONK":  "BONK/USDT",  "FLOKI": "FLOKI/USDT",
    "JTO":   "JTO/USDT",  "PEPE":  "PEPE/USDT",  "PYTH":  "PYTH/USDT",
    "SEI":   "SEI/USDT",  "SUI":   "SUI/USDT",   "TIA":   "TIA/USDT",
    # AI / Infrastructure
    "FET":     "FET/USDT",   "HYPE":    "HYPE/USDT",
    "RENDER":  "RENDER/USDT","TAO":     "TAO/USDT",
    "VIRTUAL": "VIRTUAL/USDT",
    # New L1/L2
    "BERA": "BERA/USDT", "INIT": "INIT/USDT", "IP":   "IP/USDT",
    "MOVE": "MOVE/USDT", "S":    "S/USDT",
    # Yield / RWA
    "EIGEN": "EIGEN/USDT", "ENA": "ENA/USDT", "ONDO": "ONDO/USDT",
    # DePIN / Other
    "GRASS": "GRASS/USDT", "ORCA": "ORCA/USDT", "TRUMP": "TRUMP/USDT",
}

# All 50 coins are on Aster Perps
EXCHANGE_AVAILABILITY = {coin: ["aster_perp"] for coin in ALL_TOKENS}

# CFGI tokens that have a coin-specific Fear & Greed index
# (subset of ALL_TOKENS — not all coins have CFGI data)
CFGI_TOKENS = [
    "BTC", "ETH", "SOL", "DOGE", "PEPE", "AVAX", "ADA", "XRP",
    "DOT", "LINK", "UNI", "AAVE", "SUI", "ARB", "INJ", "TRUMP",
    "HYPE", "NEAR", "ATOM", "FIL", "ONDO", "ENA",
]

BACKTEST_DAYS = 90
CAPITAL_PER_COIN = 2500


def ensure_1h_candles(coin, symbol, conn, min_days=290):
    """Check if coin has enough 1h candles; fetch from Binance if not."""
    row = conn.execute(
        "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol=? AND timeframe='1h'",
        (symbol,)
    ).fetchone()
    count = row[0] or 0
    
    if count > 0:
        min_ts, max_ts = row[1], row[2]
        days_span = (max_ts - min_ts) / (1000 * 86400)
        if days_span >= min_days:
            print(f"  {symbol}: {count} candles ({days_span:.0f} days) -- OK")
            return True
    
    # Need to fetch
    print(f"  {symbol}: {count} candles -- fetching from Binance...")
    try:
        import ccxt
        exchange = ccxt.binance({'enableRateLimit': True})
        
        since = int((datetime.now(timezone.utc) - timedelta(days=min_days + 10)).timestamp() * 1000)
        all_candles = []
        
        # ccxt uses symbol format like 'ETH/USDT'
        while True:
            candles = exchange.fetch_ohlcv(symbol, '1h', since=since, limit=1000)
            if not candles:
                break
            all_candles.extend(candles)
            since = candles[-1][0] + 1
            if len(candles) < 1000:
                break
            time.sleep(0.1)
        
        if not all_candles:
            print(f"  {symbol}: No data from Binance")
            return False
        
        # Delete existing and insert
        conn.execute("DELETE FROM candles WHERE symbol=? AND timeframe='1h'", (symbol,))
        conn.executemany(
            "INSERT INTO candles (symbol, timestamp, open, high, low, close, volume, timeframe) VALUES (?,?,?,?,?,?,?,?)",
            [(symbol, c[0], c[1], c[2], c[3], c[4], c[5], '1h') for c in all_candles]
        )
        conn.commit()
        print(f"  {symbol}: Fetched {len(all_candles)} candles from Binance")
        return True
    except Exception as e:
        print(f"  {symbol}: Fetch failed: {e}")
        return False


def build_daily_candles(symbol, conn):
    """Build daily candles with indicators for a symbol."""
    df_1h = pd.read_sql_query(
        "SELECT timestamp, open, high, low, close, volume FROM candles "
        "WHERE symbol=? AND timeframe='1h' ORDER BY timestamp",
        conn, params=(symbol,)
    )
    if len(df_1h) == 0:
        return False
    
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
    
    # Delete existing and insert
    conn.execute("DELETE FROM candles_daily WHERE symbol=?", (symbol,))
    daily[cols].to_sql('candles_daily', conn, if_exists='append', index=False)
    conn.commit()
    
    print(f"  {symbol}: {len(daily)} daily candles built")
    return True


def compute_composite_score(r):
    """Compute composite score 0-100 from backtest results."""
    closed_roi = r.get('closed_roi', 0)
    win_rate = r.get('win_rate', 0)
    outperformance = r.get('outperformance', 0)
    max_dd = abs(r.get('max_drawdown', -1))
    
    # 35% closed_roi (50% = perfect)
    roi_score = min(closed_roi / 50.0, 1.0) * 100 if closed_roi > 0 else max(0, 50 + closed_roi)
    
    # 25% win_rate (100% = perfect)
    wr_score = win_rate
    
    # 20% outperformance (50% = perfect)
    out_score = min(outperformance / 50.0, 1.0) * 100 if outperformance > 0 else max(0, 50 + outperformance)
    
    # 20% risk-adjusted (closed_roi / max_dd, 3.0 = perfect)
    if max_dd > 0:
        risk_adj = closed_roi / max_dd
        ra_score = min(risk_adj / 3.0, 1.0) * 100
    else:
        ra_score = 100 if closed_roi >= 0 else 0
    
    composite = 0.35 * roi_score + 0.25 * wr_score + 0.20 * out_score + 0.20 * ra_score
    return round(max(0, min(100, composite)), 1)


def _store_analytics(conn, scan_date, rankings, raw_results):
    """Store scanner results, phase transitions, and trades in analytics tables."""
    try:
        # Ensure tables exist
        from trading.spot.db_migrate_v13_analytics import run_migration
        run_migration(conn.execute("PRAGMA database_list").fetchone()[2] if False else None)
    except Exception:
        pass  # Tables may already exist

    cur = conn.cursor()

    # 1. Store scanner_results
    cur.execute("DELETE FROM scanner_results WHERE scan_date=?", (scan_date,))
    for r in rankings:
        cur.execute(
            "INSERT INTO scanner_results "
            "(symbol, scan_date, composite_score, closed_roi, win_rate, max_drawdown, "
            "total_deals, current_phase, markup_cycles, shorts_enabled, outperformance, "
            "buy_hold_return, time_markup_pct, time_dca_pct, time_flat_pct, time_markdown_pct, "
            "has_coin_cfgi, daily_roi_pct) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r['symbol'], scan_date, r['composite_score'], r['closed_roi'],
             r['win_rate'], r['max_drawdown_pct'], r['total_deals'],
             str(r['current_phase']), r['markup_cycles'],
             1 if r['shorts_enabled'] else 0, r['outperformance'],
             r['buy_hold_return'], r['time_markup_pct'], r['time_dca_pct'],
             r['time_flat_pct'], r['time_markdown_pct'],
             1 if r['has_coin_cfgi'] else 0, r['daily_roi_pct'])
        )

    # 2. Store phase_transitions and trade_context
    cur.execute("DELETE FROM phase_transitions WHERE scan_date=?", (scan_date,))
    cur.execute("DELETE FROM trade_context WHERE scan_date=?", (scan_date,))

    for symbol, r in raw_results.items():
        # Phase transitions
        phases = r.get('phases', [])
        for p in phases:
            p_date = str(p.get('date', ''))[:10]
            from_phase = str(p.get('from', '')) if p.get('from') else None
            to_phase = str(p.get('to', ''))
            reason = p.get('reason', '')

            # Best effort lookups for adx, stochrsi_2w_k, cfgi
            adx_val = None
            stoch_2w_k = None
            cfgi_val = None
            try:
                row = cur.execute(
                    "SELECT adx FROM candles_daily WHERE symbol=? AND date=?",
                    (symbol, p_date)
                ).fetchone()
                if row:
                    adx_val = row[0]
            except Exception:
                pass
            try:
                row = cur.execute(
                    "SELECT cfgi FROM cfgi_daily WHERE symbol=? AND date=?",
                    (symbol, p_date)
                ).fetchone()
                if row:
                    cfgi_val = row[0]
            except Exception:
                pass

            cur.execute(
                "INSERT INTO phase_transitions "
                "(symbol, date, from_phase, to_phase, trigger_signal, price, equity, "
                "adx_value, stochrsi_2w_k, cfgi_value, scan_date) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (symbol, p_date, from_phase, to_phase, reason,
                 p.get('price'), p.get('equity'),
                 adx_val, stoch_2w_k, cfgi_val, scan_date)
            )

        # Trades
        # Build phase lookup from phase_log
        phase_at = {}
        for pi, p in enumerate(phases):
            phase_at[str(p.get('date', ''))[:10]] = str(p.get('to', ''))

        trades = r.get('trades', [])
        for t in trades:
            t_date = str(t.get('date', ''))[:10]
            action = t.get('action', '')
            price = t.get('price')
            amount = t.get('amount')
            pnl_pct = t.get('pnl_pct')
            phase = str(t.get('phase', ''))

            pnl_usd = None
            was_winner = None
            if pnl_pct is not None:
                was_winner = 1 if pnl_pct > 0 else 0
                if amount and (100 + pnl_pct) != 0:
                    pnl_usd = amount * pnl_pct / (100 + pnl_pct)

            cur.execute(
                "INSERT INTO trade_context "
                "(symbol, date, action, phase, price, amount, pnl_pct, pnl_usd, "
                "entry_price, hold_duration_days, adx_at_entry, cfgi_at_entry, "
                "adx_at_exit, cfgi_at_exit, trigger_signal, was_winner, scan_date) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (symbol, t_date, action, phase, price, amount,
                 pnl_pct, pnl_usd, None, None, None, None, None, None,
                 None, was_winner, scan_date)
            )

    conn.commit()
    stored_sr = cur.execute("SELECT COUNT(*) FROM scanner_results WHERE scan_date=?", (scan_date,)).fetchone()[0]
    stored_pt = cur.execute("SELECT COUNT(*) FROM phase_transitions WHERE scan_date=?", (scan_date,)).fetchone()[0]
    stored_tc = cur.execute("SELECT COUNT(*) FROM trade_context WHERE scan_date=?", (scan_date,)).fetchone()[0]
    print(f"\n  Analytics stored: {stored_sr} scanner_results, {stored_pt} phase_transitions, {stored_tc} trade_context")


def run_scanner(tokens=None, output_paths=None):
    """Run the V13 scanner on specified tokens (or all).
    
    Args:
        tokens: dict of {coin: symbol} to scan, or None for all
        output_paths: list of paths to write JSON results to
    
    Returns:
        dict with scanner results
    """
    if tokens is None:
        tokens = ALL_TOKENS
    if output_paths is None:
        output_paths = [
            str(Path(__file__).resolve().parent / 'data' / 'scanner_v13.json'),
            str(Path(__file__).resolve().parent.parent / 'docs' / 'data' / 'scanner_t2.json'),
        ]
    
    conn = sqlite3.connect(str(DB_PATH))
    
    # Ensure candles_daily table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candles_daily (
            symbol TEXT, date TEXT, timestamp INTEGER,
            open REAL, high REAL, low REAL, close REAL, volume REAL,
            candle_count INTEGER,
            sma20 REAL, sma50 REAL, sma200 REAL,
            bb_width REAL, bb_pct REAL, atr14 REAL, atr_pct REAL,
            adx REAL, plus_di REAL, minus_di REAL, rsi14 REAL,
            consec_hh_hl INTEGER, consec_lh_ll INTEGER,
            sma50_slope REAL, sma200_slope REAL,
            price_vs_sma50 REAL, price_vs_sma200 REAL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_symbol_date ON candles_daily(symbol, date)")
    
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    start_date = (datetime.now(timezone.utc) - timedelta(days=BACKTEST_DAYS)).strftime('%Y-%m-%d')
    
    # --- Step 1: Data pipeline ---
    print("\n=== STEP 1: Data Pipeline ===")
    data_ready = {}
    for coin, symbol in tokens.items():
        print(f"\n[{coin}]")
        has_data = ensure_1h_candles(coin, symbol, conn)
        if has_data:
            built = build_daily_candles(symbol, conn)
            data_ready[coin] = built
        else:
            data_ready[coin] = False
    
    # --- Step 2: CFGI check ---
    print("\n=== STEP 2: CFGI Check ===")
    cfgi_map = {}
    try:
        api_key = os.environ.get('CFGI_API_KEY', '')
        if api_key:
            # Import from trading.spot package
            cfgi_path = str(Path(__file__).resolve().parent)
            if cfgi_path not in sys.path:
                sys.path.insert(0, cfgi_path)
            from cfgi_client import CFGIClient
            client = CFGIClient(api_key)
            # Only check tokens that are in the CFGI valid list
            check_tokens = [c for c in tokens.keys() if c in CFGI_TOKENS]
            if check_tokens:
                cfgi_map = client.get_current(check_tokens)
                print(f"  Got CFGI for {len(cfgi_map)} tokens: {list(cfgi_map.keys())}")
        else:
            print("  No CFGI_API_KEY set, skipping CFGI check")
    except Exception as e:
        print(f"  CFGI check failed: {e}")
    
    # --- Step 3: V13 Backtest per coin ---
    print("\n=== STEP 3: V13 Backtests ===")
    rankings = []
    raw_results = {}  # coin -> raw backtest result (phases, trades)
    
    for coin, symbol in tokens.items():
        if not data_ready.get(coin):
            print(f"  {coin}: SKIP (no data)")
            continue
        
        print(f"\n  [{coin}] Running V13 backtest...")
        try:
            pack = V13SignalPack(coin, db_path=str(DB_PATH))
            
            config = V13Config()
            config.START_DATE = start_date
            config.END_DATE = today
            config.CAPITAL = CAPITAL_PER_COIN
            
            bt = V13BacktestV8(pack, config)
            r = bt.run()
            
            if r is None:
                print(f"  {coin}: No results (insufficient data)")
                continue
            
            closed_roi = r.get('closed_roi', 0)
            outperformance = closed_roi - r.get('buy_hold_return', 0)
            composite = compute_composite_score({
                'closed_roi': closed_roi,
                'win_rate': r.get('win_rate', 0),
                'outperformance': outperformance,
                'max_drawdown': r.get('max_drawdown', 0),
            })
            
            # Determine current phase
            current_phase = 'UNKNOWN'
            if r.get('phases'):
                current_phase = r['phases'][-1].get('to', 'UNKNOWN')
            
            entry = {
                'symbol': symbol,
                'total_deals': r.get('closed_trades', 0),
                'win_rate': round(r.get('win_rate', 0), 1),
                'total_profit_pct': round(closed_roi, 2),
                'max_drawdown_pct': round(abs(r.get('max_drawdown', 0)), 2),
                'daily_roi_pct': round(closed_roi / BACKTEST_DAYS, 3) if BACKTEST_DAYS > 0 else 0,
                'composite_score': composite,
                'has_coin_cfgi': coin in cfgi_map,
                'available_on': EXCHANGE_AVAILABILITY.get(coin, []),
                'engine': 'v13_phase_backtest_v8',
                'current_phase': current_phase,
                'markup_cycles': r.get('markup_cycles', 0),
                'shorts_enabled': r.get('shorts_enabled', False),
                'time_markup_pct': round(r.get('time_markup_pct', 0), 0),
                'time_dca_pct': round(r.get('time_dca_pct', 0), 0),
                'time_flat_pct': round(r.get('time_flat_pct', 0), 0),
                'time_markdown_pct': round(r.get('time_markdown_pct', 0), 0),
                'closed_roi': round(closed_roi, 2),
                'buy_hold_return': round(r.get('buy_hold_return', 0), 2),
                'outperformance': round(outperformance, 2),
            }
            rankings.append(entry)
            raw_results[symbol] = r
            
            print(f"  {coin}: ROI={closed_roi:+.1f}% WR={r.get('win_rate',0):.0f}% "
                  f"DD={r.get('max_drawdown',0):.1f}% Score={composite}")
            
        except Exception as e:
            print(f"  {coin}: ERROR - {e}")
            traceback.print_exc()
    
    # Sort by composite score descending
    rankings.sort(key=lambda x: x['composite_score'], reverse=True)
    
    coin_cfgi_count = sum(1 for r in rankings if r['has_coin_cfgi'])
    
    result = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'engine': 'v13_phase_backtest_v8',
        'profile': 'high',
        'timeframe': 'daily_signals_1h_dca',
        'backtest_days': BACKTEST_DAYS,
        'candidates_tested': len(tokens),
        'passed': len(rankings),
        'cfgi_summary': {
            'coin_cfgi': coin_cfgi_count,
            'market_fallback': len(rankings) - coin_cfgi_count,
        },
        'rankings': rankings,
    }
    
    # --- Step 4: Store results in analytics tables ---
    _store_analytics(conn, today, rankings, raw_results)
    
    # Write output
    for path in output_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nWrote: {path}")
    
    conn.close()
    return result


def print_summary(result):
    """Print a summary table of scanner results."""
    rankings = result.get('rankings', [])
    print(f"\n{'='*80}")
    print(f"  V13 SCANNER RESULTS")
    print(f"  Engine: {result['engine']} | Profile: {result['profile']}")
    print(f"  Backtest: {result['backtest_days']} days | Tested: {result['candidates_tested']} | Passed: {result['passed']}")
    print(f"  CFGI: {result['cfgi_summary']['coin_cfgi']} coin-specific, {result['cfgi_summary']['market_fallback']} market fallback")
    print(f"{'='*80}")
    
    if not rankings:
        print("  No results.")
        return
    
    print(f"\n  {'#':<4} {'Symbol':<12} {'Score':>6} {'ROI':>8} {'WR':>5} {'DD':>7} {'Deals':>6} {'Phase':<10} {'Exchanges'}")
    print(f"  {'-'*75}")
    
    for i, r in enumerate(rankings, 1):
        exchanges = ','.join(r.get('available_on', [])) or '-'
        print(f"  {i:<4} {r['symbol']:<12} {r['composite_score']:>5.1f} "
              f"{r['closed_roi']:>+7.1f}% {r['win_rate']:>4.0f}% "
              f"{r['max_drawdown_pct']:>6.1f}% {r['total_deals']:>5} "
              f"{r['current_phase']:<10} {exchanges}")
