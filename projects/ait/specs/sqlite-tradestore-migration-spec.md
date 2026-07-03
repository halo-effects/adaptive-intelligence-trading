# SQLite TradeStore Migration Spec
_Version: 1.0 | Date: 2026-07-03 | Status: SPEC — pending implementation_
_References: V14PM_SYSTEM_ARCHITECTURE.md §16, audit findings M3 (CSV identity issues), P8_

---

## 1. Problem Statement

The current `trades.csv` per-bot design has reached its limits (audit M3):
- 6 duplicate deal_ids found (fixed via reconcile --fix-ids)
- No concurrent write safety
- No querying capability (slicing by account, time, coin requires full file read)
- No atomicity (crash mid-write can corrupt)
- No schema enforcement (malformed rows silently corrupt)
- `_deal_counter` collision bugs (fixed twice: load_existing + startup reconciliation)

## 2. Target Architecture

```
trades.csv (per-bot)  →  trades table (shared SQLite database)
```

**Database**: Add `trades` table to existing `candles.db` (already 225MB SQLite, proven).

### 2.1 Schema

```sql
CREATE TABLE trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      TEXT NOT NULL,       -- e.g. 'live-aster-pm', 'paper-v14pm'
    deal_id         INTEGER NOT NULL,    -- monotonic per account
    symbol          TEXT NOT NULL,
    side            TEXT NOT NULL DEFAULT 'long',  -- 'long' or 'short' (F3 ready)
    open_time       TEXT NOT NULL,
    close_time      TEXT NOT NULL,
    regime          TEXT,                -- LONG_DCA, SHORT_DCA
    layers          INTEGER,
    invested        REAL,
    proceeds        REAL,
    fee             REAL DEFAULT 0,
    pnl             REAL,
    return_pct      REAL,
    duration_h      REAL,
    fill_price      REAL,               -- exchange fill price (exchange-truth)
    recorded_at     TEXT NOT NULL,       -- wall-clock forensic timestamp (Rule #1)
    UNIQUE(account_id, symbol, open_time, close_time)
);

CREATE INDEX idx_trades_account ON trades(account_id);
CREATE INDEX idx_trades_symbol ON trades(account_id, symbol);
CREATE INDEX idx_trades_close ON trades(account_id, close_time);
```

### 2.2 TradeStore Class

```python
class TradeStore:
    """SQLite-backed trade ledger replacing CSV file I/O."""
    
    def __init__(self, db_path: Path, account_id: str):
        self.db_path = db_path
        self.account_id = account_id
    
    def record_trade(self, trade: dict) -> int:
        """Insert a closed trade. Returns auto-generated id."""
    
    def get_trades(self, symbol=None, since=None, limit=None) -> List[dict]:
        """Query trades with optional filters."""
    
    def get_stats(self) -> dict:
        """Aggregate stats: total PnL, win rate, deal count, etc."""
    
    def get_realized_pnl(self) -> float:
        """Sum of all PnL for this account (replaces CSV sum)."""
    
    def export_csv(self, path: Path):
        """Read-only CSV export for dashboard/debugging."""
    
    def import_csv(self, csv_path: Path):
        """One-time migration: import existing trades.csv into the table."""
```

## 3. Migration Path

1. Add `trades` table to `candles.db` schema
2. Create `TradeStore` class (zero dependencies on engine/runner)
3. Import existing CSV data (one-time migration script per bot)
4. Update `_write_status()` to query `TradeStore` instead of CSV
5. Update `TradeTracker.on_sell` to write to DB instead of CSV
6. Keep CSV export as read-only convenience (dashboard sync still reads CSV)
7. Add `account_id` to all records for multi-account isolation

## 4. What This Enables

- **Multi-account dashboard**: Single query across all accounts
- **Cross-account analytics**: Which strategy/coin performs best
- **Audit trail**: Immutable records with `recorded_at` (Rule #1)
- **Reconciliation queries**: Compare DB vs exchange order history
- **No more deal_id collisions**: AUTOINCREMENT handles this
- **F2 ready**: Realized-velocity feedback queries (Task 4.4) become trivial

## 5. Sequencing

- Implement after Hyperliquid migration (multi-account is the trigger)
- Paper bot first, then live
- CSV export maintained throughout for backward compatibility
- `account_id` convention: `live-{exchange}-{strategy}`, `paper-{strategy}`
