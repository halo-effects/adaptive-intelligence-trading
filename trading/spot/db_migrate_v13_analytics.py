"""
V13 Analytics DB Migration — Create tables for scanner results, phase transitions,
signal snapshots, correlations, and trade context.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'data' / 'candles.db'


def run_migration(db_path=None):
    db_path = db_path or DB_PATH
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # 1. scanner_results
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scanner_results (
            symbol TEXT,
            scan_date TEXT,
            composite_score REAL,
            closed_roi REAL,
            win_rate REAL,
            max_drawdown REAL,
            total_deals INTEGER,
            current_phase TEXT,
            markup_cycles INTEGER,
            shorts_enabled INTEGER,
            outperformance REAL,
            buy_hold_return REAL,
            time_markup_pct REAL,
            time_dca_pct REAL,
            time_flat_pct REAL,
            time_markdown_pct REAL,
            has_coin_cfgi INTEGER,
            daily_roi_pct REAL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_scanner_results_symbol_date ON scanner_results(symbol, scan_date)")
    print("  Created: scanner_results")

    # 2. phase_transitions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS phase_transitions (
            symbol TEXT,
            date TEXT,
            from_phase TEXT,
            to_phase TEXT,
            trigger_signal TEXT,
            price REAL,
            equity REAL,
            adx_value REAL,
            stochrsi_2w_k REAL,
            cfgi_value REAL,
            scan_date TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_phase_trans_symbol ON phase_transitions(symbol, date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_phase_trans_scan ON phase_transitions(scan_date)")
    print("  Created: phase_transitions")

    # 3. signal_snapshots
    cur.execute("""
        CREATE TABLE IF NOT EXISTS signal_snapshots (
            symbol TEXT,
            date TEXT,
            adx REAL,
            plus_di REAL,
            minus_di REAL,
            stoch_1w_k REAL,
            stoch_2w_k REAL,
            stoch_3w_k REAL,
            sma50_slope REAL,
            sma200_slope REAL,
            consec_hh_hl INTEGER,
            consec_lh_ll INTEGER,
            hvf_score REAL,
            cfgi_value REAL,
            price REAL,
            price_vs_sma50 REAL,
            price_vs_sma200 REAL,
            rsi14 REAL,
            atr_pct REAL,
            bb_pct REAL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_signal_snap_symbol_date ON signal_snapshots(symbol, date)")
    print("  Created: signal_snapshots")

    # 4. coin_correlations
    cur.execute("""
        CREATE TABLE IF NOT EXISTS coin_correlations (
            date TEXT,
            coin_a TEXT,
            coin_b TEXT,
            correlation_30d REAL,
            correlation_90d REAL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_corr_date ON coin_correlations(date)")
    print("  Created: coin_correlations")

    # 5. trade_context
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trade_context (
            symbol TEXT,
            date TEXT,
            action TEXT,
            phase TEXT,
            price REAL,
            amount REAL,
            pnl_pct REAL,
            pnl_usd REAL,
            entry_price REAL,
            hold_duration_days REAL,
            adx_at_entry REAL,
            cfgi_at_entry REAL,
            adx_at_exit REAL,
            cfgi_at_exit REAL,
            trigger_signal TEXT,
            was_winner INTEGER,
            scan_date TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_trade_ctx_symbol ON trade_context(symbol, date)")
    print("  Created: trade_context")

    conn.commit()
    conn.close()
    print("\n  Migration complete -- all 5 tables ready.")


if __name__ == '__main__':
    print("=== V13 Analytics DB Migration ===")
    run_migration()
