"""
Regime Event Persistence — RH-1
Append-only event log for regime changes, phase transitions, and alerts.
Separate from candles.db (market-data-only).

Hard rule: persistence failure must NEVER block trading or alerting.
Every write is wrapped in try/except → log warning, continue.
"""

import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("regime_persistence")

# Default DB location: alongside candles.db in the data directory
_DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "regime_events.db"
DB_PATH = Path(os.environ.get("AIT_REGIME_DB", str(_DEFAULT_DB)))


def _get_conn() -> sqlite3.Connection:
    """Get or create the regime_events DB connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS regime_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_utc TEXT NOT NULL,
            event_type TEXT NOT NULL,
            symbol TEXT,
            from_state TEXT,
            to_state TEXT,
            machine TEXT,
            trigger TEXT,
            conviction_pct REAL,
            coins_flipped INTEGER,
            coins_total INTEGER,
            operator_action TEXT,
            source TEXT NOT NULL DEFAULT 'live'
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_regime_events_type_ts
        ON regime_events(event_type, ts_utc)
    """)
    conn.commit()
    return conn


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_coin_phase(
    symbol: str,
    from_phase: str,
    to_phase: str,
    trigger: str,
    machine: str = "engine_4_5",
    source: str = "live",
):
    """Log a per-coin phase transition (COIN_PHASE event).
    Called from engine phase transition logic.
    Fail-open: never raises."""
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO regime_events "
            "(ts_utc, event_type, symbol, from_state, to_state, machine, trigger, source) "
            "VALUES (?, 'COIN_PHASE', ?, ?, ?, ?, ?, ?)",
            (_now_iso(), symbol, from_phase, to_phase, machine, trigger, source),
        )
        conn.commit()
        conn.close()
        logger.debug(f"Regime event: COIN_PHASE {symbol} {from_phase}→{to_phase} ({trigger})")
    except Exception as e:
        logger.warning(f"Regime persistence failed (COIN_PHASE {symbol}): {e}")


def log_alert(
    threshold_pct: float,
    coins_flipped: int,
    coins_total: int,
    operator_action: Optional[str] = None,
    source: str = "live",
):
    """Log a regime monitor alert threshold crossing (ALERT event).
    Called when graduated alerts fire (15%→25%→50%).
    Fail-open: never raises."""
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO regime_events "
            "(ts_utc, event_type, from_state, to_state, conviction_pct, "
            "coins_flipped, coins_total, operator_action, source) "
            "VALUES (?, 'ALERT', NULL, NULL, ?, ?, ?, ?, ?)",
            (_now_iso(), threshold_pct, coins_flipped, coins_total, operator_action, source),
        )
        conn.commit()
        conn.close()
        logger.debug(f"Regime event: ALERT {threshold_pct:.0%} ({coins_flipped}/{coins_total})")
    except Exception as e:
        logger.warning(f"Regime persistence failed (ALERT {threshold_pct}): {e}")


def log_alert_response(
    threshold_pct: float,
    operator_action: str,
    source: str = "live",
):
    """Log operator response to a regime alert (separate append row).
    Fail-open: never raises."""
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO regime_events "
            "(ts_utc, event_type, conviction_pct, operator_action, source) "
            "VALUES (?, 'ALERT_RESPONSE', ?, ?, ?)",
            (_now_iso(), threshold_pct, operator_action, source),
        )
        conn.commit()
        conn.close()
        logger.debug(f"Regime event: ALERT_RESPONSE {operator_action} @ {threshold_pct:.0%}")
    except Exception as e:
        logger.warning(f"Regime persistence failed (ALERT_RESPONSE): {e}")


def log_global_flip(
    from_regime: str,
    to_regime: str,
    conviction_pct: Optional[float] = None,
    coins_flipped: Optional[int] = None,
    coins_total: Optional[int] = None,
    operator_action: str = "approve",
    source: str = "live",
):
    """Log a global regime change (GLOBAL_FLIP event).
    Called from APPROVE handler or manual regime set.
    Fail-open: never raises."""
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO regime_events "
            "(ts_utc, event_type, from_state, to_state, conviction_pct, "
            "coins_flipped, coins_total, operator_action, source) "
            "VALUES (?, 'GLOBAL_FLIP', ?, ?, ?, ?, ?, ?, ?)",
            (_now_iso(), from_regime, to_regime, conviction_pct,
             coins_flipped, coins_total, operator_action, source),
        )
        conn.commit()
        conn.close()
        logger.info(f"Regime event: GLOBAL_FLIP {from_regime}→{to_regime} ({operator_action})")
    except Exception as e:
        logger.warning(f"Regime persistence failed (GLOBAL_FLIP): {e}")


def seed_attested_history():
    """One-time seed of Brett's attested regime history.
    Idempotent — checks if attested rows already exist before inserting."""
    try:
        conn = _get_conn()

        # Check if already seeded
        row = conn.execute(
            "SELECT COUNT(*) FROM regime_events WHERE source = 'attested'"
        ).fetchone()
        if row[0] > 0:
            logger.info(f"Attested history already seeded ({row[0]} rows), skipping")
            conn.close()
            return

        attested = [
            # March 2024: Macro cycle top → SHORT began
            {
                "ts_utc": "2024-03-15T00:00:00Z",
                "event_type": "GLOBAL_FLIP",
                "from_state": "LONG_DCA",
                "to_state": "SHORT_DCA",
                "operator_action": "manual",
                "source": "attested",
            },
            # Nov/Dec 2025: Flipped back to LONG
            {
                "ts_utc": "2025-12-01T00:00:00Z",
                "event_type": "GLOBAL_FLIP",
                "from_state": "SHORT_DCA",
                "to_state": "LONG_DCA",
                "operator_action": "manual",
                "source": "attested",
            },
        ]

        for row in attested:
            conn.execute(
                "INSERT INTO regime_events "
                "(ts_utc, event_type, from_state, to_state, operator_action, source) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (row["ts_utc"], row["event_type"], row["from_state"],
                 row["to_state"], row["operator_action"], row["source"]),
            )

        conn.commit()
        conn.close()
        logger.info(f"Seeded {len(attested)} attested regime history rows")
    except Exception as e:
        logger.warning(f"Failed to seed attested history: {e}")


def seed_current_state(coins: dict, global_regime: str):
    """Backfill snapshot of current state at deploy time.
    Idempotent — checks if backfill rows already exist before inserting."""
    try:
        conn = _get_conn()

        row = conn.execute(
            "SELECT COUNT(*) FROM regime_events WHERE source = 'backfill'"
        ).fetchone()
        if row[0] > 0:
            logger.info(f"Current state backfill already exists ({row[0]} rows), skipping")
            conn.close()
            return

        ts = _now_iso()

        # Global regime snapshot
        conn.execute(
            "INSERT INTO regime_events "
            "(ts_utc, event_type, from_state, to_state, source) "
            "VALUES (?, 'GLOBAL_FLIP', NULL, ?, 'backfill')",
            (ts, global_regime),
        )

        # Per-coin phase snapshots
        for sym, cstate in coins.items():
            phase = None
            if isinstance(cstate, dict):
                es = cstate.get("engine_state", {})
                phase = es.get("phase") if es else cstate.get("lifecycle_phase")
            if phase:
                conn.execute(
                    "INSERT INTO regime_events "
                    "(ts_utc, event_type, symbol, from_state, to_state, "
                    "machine, source) "
                    "VALUES (?, 'COIN_PHASE', ?, NULL, ?, 'engine_4_5', 'backfill')",
                    (ts, sym, phase),
                )

        conn.commit()
        conn.close()
        logger.info(f"Backfilled current state: {global_regime}, {len(coins)} coins")
    except Exception as e:
        logger.warning(f"Failed to backfill current state: {e}")


def get_event_count() -> int:
    """Return total events in the log. For health checks."""
    try:
        conn = _get_conn()
        row = conn.execute("SELECT COUNT(*) FROM regime_events").fetchone()
        conn.close()
        return row[0]
    except Exception:
        return -1
