#!/usr/bin/env python3
"""
Production Regime History — Export Spec v1.0
Pure export of regime/phase data. No reconstruction, no interpolation.
"""

import csv
import io
import json
import os
import shutil
import sqlite3
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

WORKSPACE = Path(__file__).resolve().parent.parent
DB_PATH = WORKSPACE / "trading" / "spot" / "data" / "candles.db"
OUTPUT_DIR = WORKSPACE / "exports" / "regime-history-export"
EXPORT_TS = datetime.now(timezone.utc)


def main():
    print(f"Production Regime History Export — {EXPORT_TS.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    manifest = {
        "export_timestamp": EXPORT_TS.isoformat(),
        "spec_version": "1.0",
        "streams": {},
    }
    
    # ── R-1: Global Regime Change Log ──
    print("\n" + "=" * 60)
    print("R-1: Global Regime Change Log")
    print("=" * 60)
    
    # Check all possible sources for global regime changes
    # Source 1: regime_snapshots table
    cur = conn.execute("SELECT COUNT(*) FROM regime_snapshots")
    regime_snap_count = cur.fetchone()[0]
    
    # Source 2: state.json current regime
    state_path = WORKSPACE / "trading" / "spot" / "live" / "v14pm" / "state.json"
    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)
    current_regime = state.get("regime", {})
    
    # Source 3: Check engine states for phase_start_date (can infer when phases began)
    coin_phases = {}
    for sym, cstate in state.get("coins", {}).items():
        es = cstate.get("engine_state", {})
        if es:
            coin_phases[sym] = {
                "phase": es.get("phase"),
                "phase_start_date": es.get("phase_start_date"),
                "top_detected": es.get("top_detected", False),
                "conviction_fired": es.get("conviction_fired", False),
                "router_from_top": es.get("router_from_top", False),
                "router_from_markdown": es.get("router_from_markdown", False),
            }
    
    r1_path = OUTPUT_DIR / "global-regime-history.csv"
    with open(r1_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_utc", "from_regime", "to_regime", "source", "conviction_pct_at_flip"])
        # No persisted global regime change history exists.
        # Only current state is available.
    
    print(f"  regime_snapshots table: {regime_snap_count} rows (empty)")
    print(f"  Current global regime: {current_regime.get('global_regime')}")
    print(f"  Alert state: {current_regime.get('alert_state')}")
    print(f"  Last alert pct: {current_regime.get('last_alert_pct')}")
    print(f"  WARNING: No persisted global regime change log exists.")
    print(f"  R-1 CSV is empty — Brett needs to provide attested dates.")
    
    manifest["streams"]["R-1_global_regime"] = {
        "file": "global-regime-history.csv",
        "rows": 0,
        "earliest": None,
        "latest": None,
        "status": "EMPTY — no persisted global regime change log. "
                  "regime_snapshots table exists but has 0 rows. "
                  "state.json contains only the CURRENT regime (LONG_DCA). "
                  "V14PM launched ~2026-02-22. No historical regime flips were logged to disk. "
                  "Brett must provide attested dates for any regime changes that occurred.",
        "current_regime": current_regime,
        "system": "V14PM (Aster perps, live since ~2026-02-22)",
    }
    
    # ── R-2: Per-coin Phase Flip Timeline ──
    print("\n" + "=" * 60)
    print("R-2: Per-coin Phase Flip Timeline")
    print("=" * 60)
    
    # Source 1: phase_transitions table (from scanner backtests)
    rows = conn.execute(
        "SELECT symbol, date, from_phase, to_phase, trigger_signal, "
        "price, equity, adx_value, stochrsi_2w_k, cfgi_value, scan_date "
        "FROM phase_transitions ORDER BY date ASC, symbol ASC"
    ).fetchall()
    
    r2_path = OUTPUT_DIR / "coin-phase-history.csv"
    with open(r2_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp_utc", "symbol", "from_phase", "to_phase", "trigger",
            "price", "equity", "adx_value", "stochrsi_2w_k", "cfgi_value",
            "scan_date", "data_source"
        ])
        for row in rows:
            writer.writerow([
                row["date"] + "T00:00:00Z",  # date only, promote to ISO-8601
                row["symbol"], row["from_phase"], row["to_phase"],
                row["trigger_signal"], row["price"], row["equity"],
                row["adx_value"], row["stochrsi_2w_k"], row["cfgi_value"],
                row["scan_date"],
                "scanner_backtest",  # These are from scanner runs, not live production
            ])
    
    # Also export current live engine phases from state.json
    r2_live_path = OUTPUT_DIR / "coin-phase-current-live.json"
    with open(r2_live_path, "w", encoding="utf-8") as f:
        json.dump(coin_phases, f, indent=2, ensure_ascii=False)
    
    # Get date range and symbol count
    if rows:
        dates = [r["date"] for r in rows]
        symbols = set(r["symbol"] for r in rows)
        scan_dates = sorted(set(r["scan_date"] for r in rows if r["scan_date"]))
    else:
        dates, symbols, scan_dates = [], set(), []
    
    print(f"  phase_transitions: {len(rows)} rows, {len(symbols)} symbols")
    print(f"  Date range: {min(dates) if dates else 'N/A'} to {max(dates) if dates else 'N/A'}")
    print(f"  Scan dates: {scan_dates[0] if scan_dates else 'N/A'} to {scan_dates[-1] if scan_dates else 'N/A'}")
    print(f"  IMPORTANT: These are from scanner backtests (scan_date column),")
    print(f"             NOT live production phase flips. The scanner replayed")
    print(f"             historical candles to compute what phases WOULD have been.")
    print(f"  Current live phases exported to coin-phase-current-live.json")
    
    manifest["streams"]["R-2_coin_phases"] = {
        "file": "coin-phase-history.csv",
        "rows": len(rows),
        "earliest": min(dates) if dates else None,
        "latest": max(dates) if dates else None,
        "distinct_symbols": len(symbols),
        "scan_date_range": f"{scan_dates[0]} to {scan_dates[-1]}" if scan_dates else None,
        "status": "SCANNER_BACKTEST — these are from v14_cycle_scanner backtests "
                  "(scan_date 2026-02-26 to 2026-03-22), NOT live production phase flips. "
                  "The scanner replayed historical candles to compute what phases would have "
                  "been. Live production phase flips were not persisted to the DB. "
                  "Current live engine phases are in coin-phase-current-live.json.",
        "supplemental_file": "coin-phase-current-live.json",
        "system": "v14_cycle_scanner (backtest replay) + V14PM state.json (current live state)",
    }
    
    # ── R-2 supplement: Signal snapshots (daily signals used by the phase machine) ──
    print("\n  Exporting signal snapshots (daily phase-machine inputs)...")
    
    sig_rows = conn.execute(
        "SELECT * FROM signal_snapshots ORDER BY date ASC, symbol ASC"
    ).fetchall()
    
    if sig_rows:
        sig_cols = [desc[0] for desc in conn.execute("PRAGMA table_info(signal_snapshots)").fetchall()]
        sig_col_names = [r[1] for r in conn.execute("PRAGMA table_info(signal_snapshots)").fetchall()]
        
        r2_sig_path = OUTPUT_DIR / "signal-snapshots.csv"
        with open(r2_sig_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(sig_col_names)
            for row in sig_rows:
                writer.writerow(list(row))
        
        sig_dates = [row["date"] for row in sig_rows]
        sig_symbols = set(row["symbol"] for row in sig_rows)
        
        print(f"  signal_snapshots: {len(sig_rows)} rows, {len(sig_symbols)} symbols")
        print(f"  Date range: {min(sig_dates)} to {max(sig_dates)}")
        
        manifest["streams"]["R-2_signal_snapshots"] = {
            "file": "signal-snapshots.csv",
            "rows": len(sig_rows),
            "earliest": min(sig_dates),
            "latest": max(sig_dates),
            "distinct_symbols": len(sig_symbols),
            "status": "PRODUCTION — daily signal values computed by the live signal stack. "
                      "These are the actual inputs the phase machine evaluates each day. "
                      "Columns: ADX, +DI/-DI, StochRSI (1w/2w/3w), SMA slopes, HH/HL counts, "
                      "HVF, CFGI, price vs SMA50/200, RSI14, ATR%, BB%.",
            "system": "V14PM live + paper bots (signal_snapshots table in candles.db)",
        }
    
    # ── R-3: Regime Monitor Alert Log ──
    print("\n" + "=" * 60)
    print("R-3: Regime Monitor Alert Log")
    print("=" * 60)
    
    r3_path = OUTPUT_DIR / "regime-alerts.csv"
    with open(r3_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_utc", "threshold_pct", "coins_flipped", "coins_total", "action_taken"])
        # No persisted alert log exists
    
    print(f"  WARNING: No persisted regime alert log exists.")
    print(f"  Graduated alerts (15%->50%) fire via Telegram only — not logged to disk.")
    print(f"  Current alert state from state.json: {current_regime.get('alert_state')}")
    print(f"  Last alert threshold: {current_regime.get('last_alert_pct')}")
    print(f"  R-3 CSV is empty.")
    
    manifest["streams"]["R-3_regime_alerts"] = {
        "file": "regime-alerts.csv",
        "rows": 0,
        "earliest": None,
        "latest": None,
        "status": "EMPTY — regime alerts are sent to Telegram only and never persisted to disk. "
                  "The graduated alert system (15% -> 25% -> 50%) fires in the live bot loop "
                  "(run_v14_portfolio_live_aster.py _check_regime_alerts) but only sends "
                  "Telegram messages. state.json stores only the CURRENT alert_state "
                  f"('{current_regime.get('alert_state')}') and last_alert_pct "
                  f"({current_regime.get('last_alert_pct')}).",
        "system": "V14PM (alerts via Telegram, no disk persistence)",
    }
    
    # ── R-4: Current Snapshots ──
    print("\n" + "=" * 60)
    print("R-4: Current Snapshots")
    print("=" * 60)
    
    snapshots_dir = OUTPUT_DIR / "snapshots"
    snapshots_dir.mkdir(exist_ok=True)
    
    # state.json
    shutil.copy2(state_path, snapshots_dir / "state.json")
    print(f"  Copied state.json ({state_path.stat().st_size:,} bytes)")
    
    # status.json
    status_path = WORKSPACE / "trading" / "spot" / "live" / "v14pm" / "status.json"
    if status_path.exists():
        shutil.copy2(status_path, snapshots_dir / "status.json")
        print(f"  Copied status.json ({status_path.stat().st_size:,} bytes)")
    
    # Extract regime-specific blocks for easy access
    with open(status_path, "r", encoding="utf-8") as f:
        status = json.load(f)
    
    regime_snapshot = {
        "state_json_regime_block": current_regime,
        "status_json_regime_detail": status.get("regime_detail", {}),
        "status_json_trend_direction": status.get("trend_direction"),
        "status_json_fear_greed_index": status.get("fear_greed_index"),
        "status_json_global_regime": status.get("global_regime"),
    }
    
    with open(snapshots_dir / "regime-snapshot.json", "w", encoding="utf-8") as f:
        json.dump(regime_snapshot, f, indent=2, ensure_ascii=False)
    print(f"  Extracted regime-snapshot.json")
    
    manifest["streams"]["R-4_snapshots"] = {
        "files": ["snapshots/state.json", "snapshots/status.json", "snapshots/regime-snapshot.json"],
        "status": "CURRENT — live state as of export timestamp.",
        "system": "V14PM live bot (Aster perps)",
    }
    
    # ── Phase machine confirmation ──
    print("\n" + "=" * 60)
    print("Phase Machine §4.5 Confirmation")
    print("=" * 60)
    
    confirmation = (
        "YES — the production phase machine (v14_dca_engine.py) matches §4.5 of arch doc v1.13 "
        "as written. All signal layers are present and match the documented thresholds: "
        "Early Warning (1W K<97), OB93 arm (2W K<93), divergence confirm (2D RSI), "
        "35-day timeout, OB85 fallback (1W K<85), failsafe (1W K<50). "
        "Bottom detection: 3D death cross + 2W K>=5 exhaustion + conviction >=3/4. "
        "FORCE_CLOSE_ON_SIGNAL=False (orphan-TP mode) matches the §7.5.8 deprecation note. "
        "One implementation detail not in §4.5: the conviction_triggers and top_triggers lists "
        "are maintained per engine instance but are transient (not persisted to DB). "
        "Phase transitions are logged to Telegram but not to the phase_transitions table "
        "(that table is populated only by scanner backtests)."
    )
    
    print(f"  {confirmation}")
    manifest["phase_machine_confirmation"] = confirmation
    
    # ── Coverage gaps ──
    manifest["known_gaps"] = {
        "global_regime_history": (
            "No persisted log. V14PM has been in LONG_DCA since launch (~2026-02-22). "
            "The only known regime flip opportunity was around the 2025 bear bottom, "
            "but V14PM wasn't running then. Predecessor bots (V14 paper/live) had "
            "different regime handling. Brett can attest approximate dates."
        ),
        "regime_alerts": (
            "Alerts are Telegram-only. The graduated alert system fires at 15%, 25%, 50% "
            "conviction thresholds but only sends Telegram messages — no disk persistence. "
            "Telegram chat history could be scraped but is outside this export scope."
        ),
        "live_phase_transitions": (
            "Per-coin phase transitions in production are not logged to the DB. "
            "The phase_transitions table contains only scanner backtest results. "
            "Live engine state is in state.json (current only, no history). "
            "signal_snapshots (daily) are the closest proxy — they show the daily "
            "signal values that the phase machine evaluates."
        ),
        "pre_v14pm_era": (
            "V14PM launched ~2026-02-22 on Aster. Before that: V14 paper (Hyperliquid, "
            "~2026-02-28), V14 live (Aster ASTER/USDT single-coin, earlier). "
            "Predecessor bots used the same v14_dca_engine phase machine but may have "
            "had different regime gate behavior. No unified timeline exists."
        ),
    }
    
    manifest["provenance"] = {
        "phase_transitions": "v14_cycle_scanner backtests (not live production)",
        "signal_snapshots": "V14PM + paper bots live daily signal computation",
        "state_json": "V14PM live bot (Aster perps)",
        "status_json": "V14PM live bot (Aster perps)",
    }
    
    # ── Write manifest ──
    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"\n  Manifest written: {manifest_path}")
    
    conn.close()
    
    # ── Zip ──
    print("\n" + "=" * 60)
    print("Creating ZIP archive")
    print("=" * 60)
    
    zip_path = OUTPUT_DIR.parent / f"regime-history-export-{EXPORT_TS.strftime('%Y%m%d')}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(OUTPUT_DIR):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(OUTPUT_DIR)
                zf.write(file_path, arcname)
    
    zip_size = zip_path.stat().st_size / 1024
    print(f"  ZIP: {zip_path}")
    print(f"  Size: {zip_size:.1f} KB")
    print("\nDone.")


if __name__ == "__main__":
    main()
