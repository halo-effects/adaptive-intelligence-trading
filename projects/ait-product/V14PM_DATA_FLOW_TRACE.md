# V14PM Live Trading Bot — Complete Data Flow Trace
**Generated:** 2026-03-21  
**Source file:** `trading/spot/run_v14_portfolio_live_aster.py`  
**Supporting files:** `v14_lifecycle_engine.py`, `v14_capital_manager.py`, `exchange_client.py` (SpotExchangeClient — not used by this bot), plus the inline `AsterPerpClient`  
**Scope:** Real-money live trading (~$340 USDT on Aster DEX Perpetuals)

---

## 1. Module Overview

### 1.1 Imports

| Import | Purpose |
|--------|---------|
| `argparse` | CLI argument parsing (`--capital`, `--confirm`, `--fresh`, `--skip-backfill`) |
| `csv` | Trade history read/write (trades.csv) |
| `json` | State persistence (state.json, status.json), scanner JSON parsing |
| `logging` | Console + file logging |
| `os` | Env var reads (API keys, DB path, scanner path) |
| `signal` | SIGINT/SIGTERM shutdown handling |
| `sqlite3` | Candles DB access (via engine's V13SignalPack, not directly in main file) |
| `sys` | sys.exit, sys.path, stdout/stderr encoding |
| `io` | UTF-8 stdout wrapper (Windows) |
| `time` | Polling intervals, dedup timestamps |
| `traceback` | Main loop exception formatting |
| `datetime`, `timezone`, `timedelta` | Timestamps, UTC conversion |
| `pathlib.Path` | File paths |
| `typing` (Dict, List, Optional) | Type hints |
| `ccxt` | Aster DEX exchange API (native ccxt.aster) |
| `V14LifecycleEngine` | Per-coin engine wrapper (signal generation + DCA state machine) |
| `CapitalRouter` | Capital allocation across coins (90/10 pool) |
| `SpotExchangeClient` | Universal exchange client — **IMPORTED BUT NOT USED BY THIS BOT** |

### 1.2 Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `DB_PATH` | `$AIT_CANDLES_DB` or `trading/spot/data/candles.db` | Candle database (SQLite) — read by engine's V13SignalPack |
| `OUTPUT_DIR` | `trading/spot/live/v14pm/` | All output files (state.json, status.json, trades.csv, bot.log) |
| `SCANNER_PATH` | `$AIT_SCANNER_JSON` or `docs/data/v14/cycle_scanner.json` | Coin scanner rankings JSON |
| `LIVE_POLL_INTERVAL` | `65` seconds | Main loop sleep target |
| `TP_CHECK_INTERVAL` | `65` seconds | TP order fill check interval |
| `STATUS_WRITE_INTERVAL` | `60` seconds | Status JSON write interval |
| `REGIME_EVAL_HOUR` | `0` (midnight UTC) | Hour for daily regime evaluation |
| `TG_PREFIX` | `"[V14-PM]"` | Telegram message prefix |
| `PRODUCTION_PROFILE` | `"high"` | Risk profile (BO=40%, Dev=1.5%, Mult=1.5x, 12 layers, TP=1.5%) |
| `PRODUCTION_LEVERAGE` | `1.0` | Leverage (1x = no liquidation risk) |
| `_WORKSPACE` | `Path(__file__).resolve().parent.parent.parent` | Root workspace path |

### 1.3 Global-Scope Code

- **Logging setup (lines ~60-70):** `logging.basicConfig()` creating StreamHandler + FileHandler to `OUTPUT_DIR/bot.log`. Runs at module import time.
- **Windows stdout fix (lines ~55-57):** Wraps `sys.stdout` and `sys.stderr` with UTF-8 encoding.
- **`sys.path.insert(0, str(_WORKSPACE))`:** Adds workspace root to Python path.
- **`BotState` class (lines ~111-114):** Named constants for state machine: `RUNNING`, `PAUSED`, `WIND_DOWN`.

### 1.4 Module-Level Functions

- **`send_telegram(msg, buttons=None)`** — HTTP POST to Telegram Bot API (`sendMessage`). Reads `AIT_TG_TOKEN` and `AIT_TG_CHAT_ID` from env. Silent on failure.
- **`get_telegram_updates(offset=0)`** — HTTP GET `getUpdates` with 0 long-poll timeout. Returns list of update dicts.

---

## 2. Class Inventory

### 2.1 `BotState` (lines ~111-114)
**Purpose:** Named constants for bot operational state.  
**Attributes:** `RUNNING="RUNNING"`, `PAUSED="PAUSED"`, `WIND_DOWN="WIND_DOWN"`  
**Methods:** None (pure constants class)

---

### 2.2 `TradeTracker` (lines ~163-258)
**Purpose:** Records closed trade history to trades.csv. Exchange fills are truth.

**Attributes:**
| Attribute | Type | Initial Value |
|-----------|------|---------------|
| `output_dir` | `Path` | Injected |
| `trades` | `List[dict]` | `[]` |
| `_deal_counter` | `int` | `0` |
| `_open_deals` | `Dict[str, dict]` | `{}` — key format: `"{symbol}:long"` |
| `_existing_keys` | `set` | `set()` — dedup guard using `"{symbol}|{open_time}|{close_time}"` |

**Methods:**
| Method | Signature | Purpose |
|--------|-----------|---------|
| `load_existing` | `() -> None` | Load trades.csv on startup; populates `_existing_keys`, `_deal_counter`, `trades` |
| `on_buy` | `(symbol, qty, price, ts) -> None` | Opens or extends a deal in `_open_deals`; increments `layers`, accumulates `invested` |
| `on_sell` | `(symbol, qty, actual_price, actual_proceeds, fee, ts) -> dict` | Closes deal; computes PnL, return_pct, duration; appends to `trades`; returns record dict |
| `save_csv` | `() -> None` | Atomic write (tmp → rename) of trades.csv |
| `deal_count` | `(property)` | `len(self.trades)` |
| `win_count` | `(property)` | Count of trades with PnL > 0 |
| `total_pnl` | `(property)` | Sum of all trade PnLs |

---

### 2.3 `AsterPerpClient` (lines ~260-570)
**Purpose:** Aster DEX Perpetuals client. Wraps `ccxt.aster` with `defaultType=future`. Handles buy/sell/TP orders, balance, positions.

**Attributes:**
| Attribute | Type | Initial Value |
|-----------|------|---------------|
| `dry_run` | `bool` | Injected |
| `_exchange` | `ccxt.aster` | Initialized in `__init__` with `enableRateLimit=True, timeout=15000` |
| `_leverage_set` | `set` | `set()` — tracks symbols with leverage already set |

**Methods:**
| Method | Signature | Purpose |
|--------|-----------|---------|
| `ensure_leverage` | `(db_symbol, leverage=1.0) -> None` | Set leverage once per symbol; skips if already set |
| `_aster_symbol` | `(db_symbol) -> str` | Converts `PEPE/USDT` → `1000PEPE/USDT:USDT` (handles 1000-prefix coins) |
| `fetch_balance` | `() -> float` | Returns USDT `free` balance from perp account |
| `fetch_full_balance` | `() -> dict` | Returns `{usdt_free, usdt_total}` from perp account |
| `fetch_ticker_price` | `(db_symbol) -> float` | Fetches current price; reverses 1000-prefix scaling |
| `create_market_buy` | `(db_symbol, qty) -> dict` | Market buy; returns `{status, price, qty, cost, fee, order_id}`; falls back to trades then ticker for fill price |
| `create_market_sell` | `(db_symbol, qty) -> dict` | Market sell with `reduceOnly=True`; returns `{status, price, qty, proceeds, fee, order_id}` |
| `place_limit_sell` | `(db_symbol, qty, price) -> Optional[str]` | Places GTC limit sell (TP); returns order_id |
| `cancel_tp_order` | `(db_symbol, order_id) -> bool` | Cancels a limit order |
| `check_order_status` | `(db_symbol, order_id) -> dict` | Polls order; returns `{filled:True, price, qty, proceeds, fee}` if filled, else `{filled:False, status}` |
| `fetch_open_orders` | `(db_symbol=None) -> list` | Returns all open orders filtered by symbol |
| `fetch_open_positions` | `() -> dict` | Returns open positions keyed by base symbol; handles 1000-prefix qty/price scaling |
| `fetch_funding_history` | `(db_symbol, since_ms=None) -> list` | Fetches funding payment history |

---

### 2.4 `CoinState` (lines ~572-605)
**Purpose:** Tracks live state for a single coin position.

**Attributes:**
| Attribute | Type | Initial Value |
|-----------|------|---------------|
| `symbol` | `str` | Injected |
| `allocated_capital` | `float` | Injected (from router rebalance) |
| `engine` | `Optional[V14LifecycleEngine]` | `None` → set after init |
| `tp_order_id` | `Optional[str]` | `None` → set after TP placed |
| `tp_limit_price` | `Optional[float]` | `None` → set after TP placed (separate from `eng.long_tp`) |
| `last_candle_ts` | `int` | `0` → set to processed candle ms timestamp |
| `cumulative_funding` | `float` | `0.0` |
| `last_funding_check_ms` | `int` | `0` |
| `_last_buy_time` | `float` | `0.0` → dedup guard |
| `layer_count` | `int` | `0` → incremented on BUY, zeroed on SELL/TP |

**Methods:**
| Method | Signature | Purpose |
|--------|-----------|---------|
| `to_dict` | `() -> dict` | Serializes all fields for state.json |

---

### 2.5 `V14PortfolioLiveAster` (lines ~607-end)
**Purpose:** Main bot class. Orchestrates all trading logic.

**Attributes:**
| Attribute | Type | Initial Value | Notes |
|-----------|------|---------------|-------|
| `capital` | `float` | CLI arg | Starting/reference capital |
| `skip_backfill` | `bool` | CLI arg | Unused in current code (no backfill path) |
| `fresh` | `bool` | CLI arg | Forces clean state on startup |
| `profile` | `str` | `"high"` | Risk profile (LOCKED) |
| `leverage` | `float` | `1.0` | Exchange leverage (LOCKED) |
| `bot_state` | `str` | `BotState.RUNNING` | State machine: RUNNING/PAUSED/WIND_DOWN |
| `_wind_down_direction` | `Optional[str]` | `None` | Target direction after wind-down (not used — direction flip not implemented) |
| `coins` | `Dict[str, CoinState]` | `{}` | Per-coin state, keyed by `"{BASE}/USDT"` |
| `router` | `CapitalRouter` | `CapitalRouter(capital)` | Capital allocation manager |
| `tracker` | `TradeTracker` | `TradeTracker(OUTPUT_DIR)` | Trade history |
| `client` | `AsterPerpClient` | Reads `ASTER_API_KEY`/`ASTER_API_SECRET` | Exchange client |
| `_cfgi_market` | `Optional[float]` | `None` | Market CFGI value |
| `_cfgi_coins` | `Dict[str, float]` | `{}` | Per-coin CFGI values |
| `_cfgi_last_poll` | `float` | `0.0` | Timestamp of last CFGI poll |
| `_regime_signal_count` | `int` | `0` | Count of coins signaling TOP/BOTTOM |
| `_regime_signal_type` | `Optional[str]` | `None` | "TOP" or "BOTTOM" |
| `_regime_alert_state` | `str` | `"NONE"` | "NONE" or "AWAITING_APPROVAL" |
| `_regime_last_eval_date` | `Optional[date]` | `None` | Date of last regime eval |
| `_tg_update_offset` | `int` | `0` | Telegram update ID watermark |
| `_last_tg_check` | `float` | `0.0` | Throttle Telegram polls |
| `_start_time` | `datetime` | `datetime.now(UTC)` | For uptime calc |
| `_shutdown` | `bool` | `False` | SIGINT/SIGTERM flag |
| `_last_rebalance_date` | `Optional[date]` | `None` | Prevents duplicate rebalances |
| `_last_status_write` | `float` | `0.0` | Throttle status writes |
| `_reentry_cooldown_until` | `float` | `0.0` | Declared but **never updated or checked** |
| `_exchange_usdt_free` | `float` | `0.0` | Cached from last exchange sync |
| `_exchange_usdt_total` | `float` | `0.0` | Cached from last exchange sync |
| `_last_exchange_positions` | `dict` | `{}` | Cached positions from last exchange sync |

**Methods:**
| Method | Signature | Purpose |
|--------|-----------|---------|
| `__init__` | `(capital, confirm, skip_backfill, fresh)` | Initialize all state |
| `_save_state` | `() -> None` | Atomic write of state.json |
| `_load_state` | `() -> bool` | Restore state from state.json |
| `_sync_positions_from_exchange` | `() -> None` | Overwrite engine state from exchange API; update cached values |
| `_update_funding` | `() -> None` | Fetch funding payments every 8h per coin |
| `_place_tp_order` | `(sym, cs) -> None` | Place (or replace) TP limit sell on exchange |
| `_check_tp_fills` | `() -> None` | Poll exchange for TP order fills |
| `_recover_tp_orders` | `() -> None` | Startup reconciliation of TP orders |
| `_handle_tp_fill` | `(sym, cs, fill_result) -> None` | Process a filled TP order (record trade, return capital, clean engine) |
| `_fetch_candles` | `(sym) -> List[dict]` | Fetch last 50 closed 1h candles from Aster |
| `_execute_action` | `(sym, cs, action) -> None` | Execute BUY or SELL against exchange |
| `_do_rebalance` | `(current_dt) -> None` | Daily rebalance: scanner → allocations → new engines |
| `_evaluate_regime` | `(current_dt) -> None` | Daily regime signal evaluation across scanner coins |
| `_check_wind_down_complete` | `() -> None` | Check if all positions closed during wind-down |
| `_process_telegram_commands` | `() -> None` | Poll Telegram for commands (every 15s) |
| `_handle_command` | `(text) -> None` | Handle parsed command: PAUSE/RESUME/CLOSE/APPROVE/DENY |
| `_force_close_coin` | `(sym) -> None` | Force market-sell a single position |
| `_force_close_all` | `() -> None` | Force market-sell all open positions |
| `_compute_equity` | `() -> float` | Compute total equity (exchange balance + unrealized PnL) |
| `_write_status` | `() -> None` | Write status.json for dashboard |
| `_poll_cfgi` | `() -> None` | Hourly CFGI fetch for market + per-coin |
| `run` | `() -> None` | Main loop |

---

### 2.6 `CapitalRouter` (v14_capital_manager.py)
**Purpose:** Manages capital distribution across active coins.

**Attributes:**
| Attribute | Type | Initial Value |
|-----------|------|---------------|
| `total_equity` | `float` | Injected (`initial_capital`) |
| `active_pool_total` | `float` | `total_equity * 0.90` (constructor); `total_equity * 0.75` (after first rebalance — **see Gap #2**) |
| `reserve_pool_total` | `float` | `total_equity * 0.10` (constructor); `total_equity * 0.25` (after first rebalance — **see Gap #2**) |
| `active_pool_cash` | `float` | `active_pool_total` |
| `reserve_pool_cash` | `float` | `reserve_pool_total` |
| `active_allocations` | `Dict[str, float]` | `{}` — running tally of capital out per coin |
| `reserve_allocations` | `Dict[str, float]` | `{}` |
| `tier_coin_cap` | `int` | From `EQUITY_TIER_CAPS` lookup |

**Methods:**
| Method | Signature | Purpose |
|--------|-----------|---------|
| `get_tier_coin_cap` | `(equity) -> int` | Returns max coins for equity level |
| `load_scanner_json` | `(filepath) -> List[dict]` | Parse cycle_scanner.json; enrich with trend_multiplier |
| `rebalance_daily` | `(scanner_rankings, current_equity=None) -> Dict[str, float]` | Compute target allocations; **changes pool split to 75/25** |
| `request_capital` | `(coin, amount, pool="active") -> float` | Deduct from pool; return granted amount |
| `return_capital` | `(coin, amount) -> None` | Return to active pool; zero allocations for coin |

---

### 2.7 `V14LifecycleEngine` (v14_lifecycle_engine.py)
**Purpose:** Per-coin live wrapper around V14DCAEngine. Manages signal pack, daily ticks, state persistence.

**Key Attributes:**
- `symbol`, `initial_capital`, `profile`, `leverage`
- `_engine` → `V14DCAEngine` instance (inner DCA state machine)
- `_live_mode`, `_warmed_up`, `_last_daily_date`, `_last_candle_ts`
- `current_price`, `_candles_1h`

**Key Methods:**
- `tick(candle_1h, cash_available)` → `List[dict]` — Main entry; emits BUY/SELL action dicts
- `snapshot_state() -> dict` — Serialize all state for persistence
- `restore_state(state)` — Restore from saved dict
- `reject_action(action_dict)` — Roll back engine state for rejected BUY
- `get_status() -> dict` — Returns status dict (NOTE: hardcodes `'exchange': 'hyperliquid'`)
- `backfill_direct(start_date, end_date)` — Run V14 engine's full history

---

## 3. Data Flow Traces

### 3.1 Startup Flow

```
main()
  └─ parse_args() → args.capital, args.confirm, args.skip_backfill, args.fresh
  └─ logging.basicConfig() [force=True, second config overrides module-level]
  └─ OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
  └─ V14PortfolioLiveAster(capital, confirm, skip_backfill, fresh)
       └─ __init__():
            Validates: confirm=True required
            Reads: ASTER_API_KEY, ASTER_API_SECRET from env
            Creates: CapitalRouter(capital=340)  → active_pool=306, reserve=34
            Creates: TradeTracker(OUTPUT_DIR)
            Calls: tracker.load_existing()
              → reads OUTPUT_DIR/trades.csv (if exists)
              → populates: _deal_counter, _existing_keys, trades[]
            Creates: AsterPerpClient(api_key, api_secret)
              → ccxt.aster({...options...})
              → client._exchange.load_markets()  [EXCHANGE API CALL #1]
            Initializes all state fields to defaults
  └─ bot.run():
       1. Acquires file lock: OUTPUT_DIR/bot.lock (msvcrt.locking — Windows-only!)
       2. Writes PID: OUTPUT_DIR/bot.pid
       3. State load (unless --fresh):
          _load_state()
            → reads OUTPUT_DIR/state.json
            → restores: bot_state, coins (each CoinState + engine), router pools,
                        regime state, tg_update_offset, open_deals
            → for each coin engine: V14LifecycleEngine(sym, capital, profile, leverage)
              → V14DCAEngine init, V13SignalPack(coin) [reads candles.db]
              → restore_state(engine_state)
              → sets _live_mode=True, _warmed_up=True
              → if no open position: resets engine capital to allocated amount
       4. Initial rebalance (only if fresh OR no coins loaded):
          _do_rebalance(now)
            → router.load_scanner_json(SCANNER_PATH)  [FILE READ: cycle_scanner.json]
            → _compute_equity()  [EXCHANGE API CALL: fetch_full_balance, fetch_ticker_price per coin]
            → router.rebalance_daily(scanner_data, current_equity)
              → changes pool split to 75/25 (see Gap #2)
              → filters: DCA Score >= 5.0 × trend_multiplier
              → sorts by adjusted_score desc, takes top N (tier cap)
              → returns {symbol: allocated_dollars}
            → for each new symbol: CoinState + V14LifecycleEngine (warmed_up=True)
            → ensures leverage on exchange for each coin
       5. Set leverage on exchange for all coins:
          client.ensure_leverage(sym, 1.0)  [EXCHANGE API CALL per coin]
       6. Initial exchange sync:
          _sync_positions_from_exchange()
            → client.fetch_full_balance()  [EXCHANGE API CALL]
            → client.fetch_open_positions()  [EXCHANGE API CALL]
            → overwrites engine.long_coins, long_cost, long_avg_entry, long_tp
            → caches: _exchange_usdt_free, _exchange_usdt_total, _last_exchange_positions
       7. TP recovery:
          _recover_tp_orders()
            → Phase 1: for each cs with tp_order_id:
                client.check_order_status(sym, order_id)  [EXCHANGE API CALL per coin]
                → if filled: _handle_tp_fill()
                → if cancelled: clear tp_order_id
            → Phase 2: for each coin:
                client.fetch_open_orders(sym)  [EXCHANGE API CALL per coin]
                → if orphan sell + position: adopt as TP
                → if stale sell + no position: cancel
                → if position + no TP order: _place_tp_order()
       8. send_telegram("🚀 Live Bot Started...")  [HTTP: Telegram API]
       9. Enter main loop
```

**Data available at each step:**
- After `__init__`: Capital, exchange client, empty coins dict, clean router
- After `_load_state`: All coin engines with restored DCA state, router pools, regime state
- After initial rebalance: Coin engines initialized for scanner top picks
- After exchange sync: Engine position fields overwritten from exchange (ground truth)
- After TP recovery: All TP orders reconciled with exchange state
- **Missing at startup:** `_last_rebalance_date`, `_regime_last_eval_date` are NOT restored → rebalance and regime eval will run immediately on first cycle regardless of whether they ran today (see Gap #3)

---

### 3.2 Main Loop — Single Cycle

**Loop condition:** `while not self._shutdown` (65-second target period)

```
cycle_start = time.time()
current_dt = datetime.now(UTC)

STEP 1: Telegram commands (every 15s)
  _process_telegram_commands()
    → get_telegram_updates(offset=_tg_update_offset)  [HTTP: Telegram API]
    → filter by AIT_TG_CHAT_ID
    → parse text as UPPER
    → _handle_command(text)
  Data read: _tg_update_offset, AIT_TG_CHAT_ID env
  Data write: _tg_update_offset, bot_state (on PAUSE/RESUME/APPROVE)

STEP 2: Daily rebalance (once per calendar day, at any hour)
  _do_rebalance(current_dt)
    → guard: _last_rebalance_date == today → skip
    → guard: < 60s since last rebalance → skip
    → reads: SCANNER_PATH  [FILE READ: cycle_scanner.json]
    → _compute_equity()
      → client.fetch_full_balance()  [EXCHANGE API CALL]
      → for each coin with position: client.fetch_ticker_price(sym)  [EXCHANGE API CALL per coin]
    → router.rebalance_daily(scanner_data, equity)
    → creates new CoinState + V14LifecycleEngine for new symbols
    → updates allocated_capital for existing coins
    → resets engine capital if no position open
  Data read: SCANNER_PATH, exchange balance, ticker prices
  Data write: self.coins, cs.allocated_capital, engine.capital, _last_rebalance_date

STEP 3: Regime evaluation (once per day at midnight UTC)
  _evaluate_regime(current_dt)
    → guard: _regime_last_eval_date == today → skip
    → guard: current_dt.hour != 0 → skip
    → reads: SCANNER_PATH  [FILE READ: cycle_scanner.json]
    → counts coins with TOP/BOTTOM signals from cycle_scanner.json fields
    → tiers: EARLY (≥5), STRONG (≥12), MAJORITY (≥25)
    → if threshold crossed: send_telegram(alert + APPROVE/DENY buttons)
    → sets _regime_alert_state = "AWAITING_APPROVAL"
  Data read: SCANNER_PATH, _regime_signal_count, _regime_last_eval_date
  Data write: _regime_signal_count, _regime_signal_type, _regime_alert_state, _regime_last_eval_date

STEP 4: TP fill check (every 65s)
  if time.time() - last_tp_check >= 65:
    _check_tp_fills()
      → for each coin with tp_order_id:
          client.check_order_status(sym, tp_order_id)  [EXCHANGE API CALL per coin]
          → if filled: _handle_tp_fill(sym, cs, result)
    _update_funding()
      → for each coin with open position:
          if 8h since last check: client.fetch_funding_history(sym)  [EXCHANGE API CALL]
    last_tp_check = time.time()

STEP 5: Exchange position sync
  _sync_positions_from_exchange()
    → client.fetch_full_balance()  [EXCHANGE API CALL]
    → client.fetch_open_positions()  [EXCHANGE API CALL]
    → for each coin: overwrite engine.long_coins, long_cost, long_avg_entry, long_tp
    → cache: _exchange_usdt_free, _exchange_usdt_total, _last_exchange_positions

STEP 6: Candle processing (for each active coin)
  for sym, cs in coins.items():
    candles = _fetch_candles(sym)
      → client._exchange.fetch_ohlcv(aster_sym, "1h", limit=50)  [EXCHANGE API CALL]
      → filters out incomplete (current) candle
      → applies 1000-prefix price scaling
    for candle in candles:
      if candle.timestamp <= cs.last_candle_ts: skip
      actions = cs.engine.tick(candle, cash_available=cs.allocated_capital)
        → V14LifecycleEngine.tick()
          → on daily boundary: refresh signal pack, run full daily tick
          → between daily: run DCA grid tick hourly
          → returns List[action_dicts] with BUY/SELL/PHASE_CHANGE actions
      for action in actions:
        _execute_action(sym, cs, action)  [see §3.4 / §3.5]
      cs.last_candle_ts = ts_ms
      cs.engine._last_candle_ts = ts_ms
    phase change detection: if phase changed → cancel stale TP

STEP 7: CFGI poll (once per hour)
  _poll_cfgi()
    → if < 3600s since last poll: skip
    → CFGIClient.get_current(["MARKET"], period=4)  [HTTP: CFGI API]
    → CFGIClient.get_current(supported_coins, period=4)  [HTTP: CFGI API]
    → updates _cfgi_market, _cfgi_coins
  Data read: CFGI_API_KEY env, active coin bases
  Data write: _cfgi_market, _cfgi_coins, _cfgi_last_poll

STEP 8: Status write (every 60s)
  _write_status()
    → uses cached _last_exchange_positions, _exchange_usdt_free, _exchange_usdt_total
    → for each coin: cs.engine.get_status(), ticker fetch for current_price
    → reads trades.csv for per-coin PnL and aggregates  [FILE READ: trades.csv]
    → writes OUTPUT_DIR/status.json (atomic: .tmp → rename)
  Data read: cached exchange data, engine status, trades.csv
  Data write: OUTPUT_DIR/status.json

STEP 9: State save
  _save_state()
    → coin engines: cs.engine.snapshot_state()
    → writes OUTPUT_DIR/state.json (atomic: .tmp → rename)
  tracker.save_csv()
    → writes OUTPUT_DIR/trades.csv (atomic: .tmp → rename)
  Data write: state.json, trades.csv

STEP 10: Sleep
  sleep until cycle_start + 65s (in 1-second ticks, checking _shutdown flag)
```

---

### 3.3 Exchange Sync Flow

**Method:** `_sync_positions_from_exchange()`

```
try:
  balance = client.fetch_full_balance()
    → ccxt.aster.fetch_balance({"type": "future"})
    → returns {usdt_free: float, usdt_total: float}
  self._exchange_usdt_free = balance["usdt_free"]
  self._exchange_usdt_total = balance["usdt_total"]
except:
  logger.warning("..."); return  [EARLY RETURN — keeps previous cached values]

try:
  positions = client.fetch_open_positions()
    → ccxt.aster.fetch_positions()
    → filters: contracts > 0
    → reverses 1000-prefix scaling on qty and entry_price
    → returns {base_symbol: {qty, entry_price, side, unrealized_pnl}}
except:
  logger.warning("..."); return  [EARLY RETURN — does NOT overwrite engine with empty]

for sym, cs in coins.items():
  if not cs.engine or not cs.engine._engine: continue
  eng = cs.engine._engine
  base = sym.split("/")[0]
  pos = positions.get(base, {})
  ex_qty = pos.get("qty", 0) or 0
  ex_entry = pos.get("entry_price", 0) or 0

  if ex_qty > 0:
    eng.long_coins = ex_qty           [OVERWRITE]
    eng.long_cost = ex_entry * ex_qty  [OVERWRITE]
    eng.long_avg_entry = ex_entry      [OVERWRITE]
    eng.long_tp = ex_entry * (1 + cfg.DCA_TP_PCT)  [RECALCULATED from entry]
    # Layer count sync:
    if cs.layer_count == 0 and ex_qty > 0:
      cs.layer_count = max(1, eng.long_layers)
    eng.long_layers = cs.layer_count   [OVERWRITE]
  else:
    eng.long_coins = 0.0
    eng.long_cost = 0.0
    eng.long_avg_entry = 0.0
    eng.long_layers = 0
    eng.long_tp = 0.0
    cs.layer_count = 0

self._last_exchange_positions = positions  [CACHE for status write]
```

**API failure behavior:**
- Balance failure → `return` (keeps previous `_exchange_usdt_free/total`)
- Position fetch failure → `return` (does NOT zero engine state — correct safety behavior)

**Fields overwritten on engine per cycle:**
- `long_coins`, `long_cost`, `long_avg_entry`, `long_tp`, `long_layers`

**Fields NOT synced from exchange:**
- `eng.capital` (only reset on TP fill or rebalance when no position)
- `eng.long_pnl`, `eng.long_trades`, `eng.long_wins` (only updated on sells)
- `eng.phase`, `eng.phase_log` (engine-only signal state)
- Short position fields (short side not currently trading)

**Cached for status write:**
- `_exchange_usdt_free`, `_exchange_usdt_total`, `_last_exchange_positions`

---

### 3.4 BUY Execution Path

**Trigger:** `cs.engine.tick(candle)` returns `[{action: "BUY", qty: X, price: Y, reason: "LONG_DCA_BUY", cost: Z}]`

```
_execute_action(sym, cs, action):

  act_type = "BUY"
  price = action["price"]    [from engine — engine's estimated entry price]
  qty = action["qty"]        [from engine — calculated from capital/price]
  reason = action["reason"]  [e.g. "LONG_DCA_BUY_L1"]

  GUARD 1: Bot state check
    if bot_state in (PAUSED, WIND_DOWN):
      cs.engine.reject_action(action)  [rolls back engine: long_coins, long_cost, long_layers--]
      return

  GUARD 2: Order dedup (30-second window)
    if time.time() - cs._last_buy_time < 30:
      cs.engine.reject_action(action)
      return

  GUARD 3: Cost check
    cost = price * qty
    if cost < 5.0:
      cs.engine.reject_action(action)
      return

  CAPITAL REQUEST:
    key = f"{sym}:long"
    layer = tracker._open_deals.get(key, {}).get("layers", 0) + 1
    pool = "reserve" if layer >= 6 else "active"
    granted = router.request_capital(sym, cost, pool=pool)
      → deducts from pool cash
      → adds to pool allocations[sym]
    if granted <= 0:
      cs.engine.reject_action(action); return
    if granted < cost:  [partial grant]
      cs.engine.reject_action(action)
      router.return_capital(sym, granted)  [refund partial]
      return

  GUARD 4: Exchange balance pre-check
    exchange_balance = client.fetch_balance()  [EXCHANGE API CALL: fetch USDT free]
    if exchange_balance < cost * 1.01:  [need 1% buffer]
      router.return_capital(sym, granted)  [refund]
      cs.engine.reject_action(action)
      send_telegram("⚠️ BUY skipped — insufficient USDT")
      return

  ORDER PLACEMENT:
    result = client.create_market_buy(sym, qty)
      → ccxt.aster.create_market_buy_order(aster_sym, exchange_qty, {positionSide:"BOTH"})
      → fill price from order.average, else trades fetch, else ticker
      → returns {status:"filled", price:actual, qty:filled, cost:actual, fee, order_id}
    
    if result and result["status"] in ("filled", "dry_run"):
      actual_price = result["price"]    [EXCHANGE FILL — not engine price]
      actual_qty = result["qty"]
      actual_cost = result["cost"]
      fee = result["fee"]
      spread_bps = abs(actual_price - price) / price * 10000
      if spread_bps > 50: send_telegram("⚠️ High spread")

      TRACKER UPDATE:
        tracker.on_buy(sym, actual_qty, actual_price, now_utc)
          → creates/updates _open_deals["{sym}:long"]
          → layers += 1
          → invested += actual_qty * actual_price

      cs._last_buy_time = time.time()  [dedup guard reset]
      cs.layer_count += 1              [local count]

      TP PLACEMENT:
        _place_tp_order(sym, cs)
          → tp_price = eng.long_tp      [from engine, freshly set after buy]
          → fetch exchange position qty for accuracy  [EXCHANGE API CALL]
          → if cs.tp_order_id: cancel old TP  [EXCHANGE API CALL]
          → place_limit_sell(sym, qty, tp_price)  [EXCHANGE API CALL: GTC limit sell]
          → cs.tp_order_id = oid
          → cs.tp_limit_price = tp_price  [stored separately from eng.long_tp]

      NOTIFICATION:
        send_telegram("🔵 DCA Layer N | Fill: ... | TP: ... | Reason: ...")

    else:  [buy failed]
      router.return_capital(sym, granted)
      cs.engine.reject_action(action)
```

**NOTE:** After a successful buy, the engine state is NOT immediately corrected — it already recorded the buy internally (via `_long_dca_tick`). The engine's `long_coins`, `long_cost`, `long_avg_entry`, `long_tp` reflect the buy. The next `_sync_positions_from_exchange()` call will overwrite these with actual exchange values.

**What if router denies capital?**  
→ `reject_action()` rolls back the engine's internal trade record. The engine's `long_coins`, `long_cost`, `long_layers` are decremented. `long_trades` is decremented. No exchange call is made.

**What if exchange balance insufficient?**  
→ Router capital is returned (refunded to pool), engine rolled back. Telegram alert sent.

---

### 3.5 SELL Execution Path

**Trigger:** Engine emits `{action: "SELL", qty: X, price: Y, reason: "LONG_DCA_TP" or "LONG_DCA_CLOSE"}`

```
_execute_action(sym, cs, action):
  act_type = "SELL"

  GUARD: TP order active on exchange?
    if cs.tp_order_id and "TP" in reason:
      logger.info("Skipping engine TP — exchange TP order active")
      return  [exchange will handle it; _check_tp_fills() detects fill]

  Non-TP sell or forced sell (CLOSE):
    if cs.tp_order_id:
      client.cancel_tp_order(sym, cs.tp_order_id)  [EXCHANGE API CALL]
      cs.tp_order_id = None
      cs.tp_limit_price = None

  QTY RESOLUTION:
    sell_qty = qty  [engine qty as default]
    positions = client.fetch_open_positions()  [EXCHANGE API CALL]
    if exchange has position and qty differs by > 0.01:
      sell_qty = exchange_qty  [use exchange position as truth]

  ORDER:
    result = client.create_market_sell(sym, sell_qty)
      → ccxt.aster.create_market_sell_order(sym, qty, {positionSide:"BOTH", reduceOnly:True})
      → fill = order.average or ticker price
      → returns {status:"filled", price, qty, proceeds, fee}

    if result["status"] in ("filled", "dry_run"):
      actual_price = result["price"]
      actual_qty = result["qty"]
      actual_proceeds = result["proceeds"]
      fee = result["fee"]

      TRACKER UPDATE:
        record = tracker.on_sell(sym, actual_qty, actual_price, actual_proceeds, fee, now)
          → pops _open_deals["{sym}:long"]
          → computes pnl = actual_proceeds - invested - fee
          → appends to trades[]

      ROUTER UPDATE:
        router.return_capital(sym, actual_proceeds)
          → active_pool_cash += actual_proceeds
          → active_allocations[sym] = 0
          → reserve_allocations[sym] = 0
        NOTE: returns PROCEEDS (not original cost) — correct for PnL accounting

      cs.layer_count = 0

      if record: send_telegram("🟢/🔴 Deal Closed")
      cs.tp_order_id = None
      cs.tp_limit_price = None
      tracker.save_csv()

      if bot_state == WIND_DOWN: _check_wind_down_complete()

    else:  [sell failed]
      logger.error("SELL FAILED — will retry on next candle")
      send_telegram("⚠️ SELL FAILED")
      NOTE: NO rollback attempted. Engine state left inconsistent.
            Next _sync_positions_from_exchange() will show position still open.
            Engine will re-emit SELL on next candle tick (correct behavior).
```

**What if exchange TP is active?**  
→ Engine TP sell is silently skipped. Exchange limit order stays. `_check_tp_fills()` detects when it fills.

**What if sell fails?**  
→ No rollback. Engine state is preserved (showing position open). Next exchange sync will show position still open. Next candle will re-trigger the sell signal. This is the correct recovery behavior.

---

### 3.6 TP Fill Detection

**Method:** `_check_tp_fills()` (runs every `TP_CHECK_INTERVAL` = 65 seconds)

```
_check_tp_fills():
  for sym, cs in coins.items():
    if not cs.tp_order_id: continue
    try:
      result = client.check_order_status(sym, cs.tp_order_id)
        → ccxt.aster.fetch_order(order_id, sym)
        → if status in ("closed", "filled"):
            returns {filled:True, price:fill, qty:filled_qty, proceeds:cost, fee}
        → else: {filled:False, status}
      if result.get("filled"):
        _handle_tp_fill(sym, cs, result)
    except: logger.error()

_handle_tp_fill(sym, cs, fill_result):
  actual_price = fill_result["price"]    [from exchange order fill]
  actual_qty = fill_result["qty"]
  actual_proceeds = fill_result["proceeds"]
  fee = fill_result.get("fee", 0)

  TRACKER:
    ts = datetime.now(UTC)
    record = tracker.on_sell(sym, actual_qty, actual_price, actual_proceeds, fee, ts)
      → pops _open_deals["{sym}:long"]
      → pnl = actual_proceeds - invested - fee
      → return_pct = pnl / invested * 100
      → appends to trades[]

  TELEGRAM:
    if record: send_telegram("🟢/🔴 Deal Closed (TP Hit) | Fill | PnL | Funding | Layers")

  ROUTER:
    router.return_capital(sym, actual_proceeds)
      → active_pool_cash += actual_proceeds
      → active_allocations[sym] = 0; reserve_allocations[sym] = 0
    NOTE: returns PROCEEDS (market value). If TP hit → proceeds > cost → pool grows. Correct.

  ENGINE CLEANUP:
    eng.capital += actual_proceeds
    [correction logged if stored_tp * qty ≠ actual_proceeds]
    eng.long_trades += 1
    if pnl >= 0: eng.long_wins += 1
    eng.long_pnl += pnl
    # Zero ALL position fields:
    eng.long_coins = 0.0
    eng.long_avg_entry = 0.0
    eng.long_layers = 0
    eng.long_last_buy = None
    eng.long_tp = 0.0
    eng.long_cost = 0.0
    eng.capital = cs.allocated_capital  [reset to allocated amount]

  CLEANUP:
    cs.tp_order_id = None
    cs.tp_limit_price = None
    cs.cumulative_funding = 0.0
    tracker.save_csv()

  ORPHANED ORDER CLEANUP (BUGGY — see Gap #1):
    try:
      open_orders = self.client.client.fetch_open_orders(  ← BUG: "client.client" doesn't exist
          self.client._to_ccxt_symbol(sym))               ← BUG: "_to_ccxt_symbol" doesn't exist
    → This always throws AttributeError, silently caught.
    → Orphaned sell orders are NOT cleaned up after TP fill.

  if bot_state == WIND_DOWN: _check_wind_down_complete()
```

**Capital accounting correctness:**
- Proceeds returned to router → pool grows by proceeds (includes profit)
- This is correct: profit is realized and returned to active pool
- Tracker records actual_proceeds, fee, pnl separately — correct for reporting

---

### 3.7 Status Write Flow

**Method:** `_write_status()` (throttled to once per 60 seconds)

Every field in `status.json` mapped to its source:

| JSON Field | Source | Notes |
|------------|--------|-------|
| `running` | Hardcoded `True` | |
| `mode` | Hardcoded `"live"` | |
| `engine` | Hardcoded `"v14-pm"` | |
| `exchange` | Hardcoded `"aster_perp"` | |
| `profile` | `self.profile` = `"high"` | |
| `leverage` | `self.leverage` = `1.0` | |
| `bot_state` | `self.bot_state` | RUNNING/PAUSED/WIND_DOWN |
| `capital` | `self.capital` (CLI arg) | Starting capital reference |
| `equity` | `usdt_total + unrealized_pnl` (from cached exchange data) | Computed from `_last_exchange_positions` |
| `cash` | `_exchange_usdt_free` | Cached from last sync |
| `invested` | Sum of `entry_price × qty` from `_last_exchange_positions` | Exchange data |
| `exchange_balance.usdt_free` | `_exchange_usdt_free` | Cached |
| `exchange_balance.usdt_total` | `_exchange_usdt_total` | Cached |
| `pnl_pct` | `(equity - capital) / capital * 100` | |
| `total_pnl` | `tracker.total_pnl` (sum of trades.pnl) | Overridden by CSV aggregate below |
| `total_realized_pnl` | CSV aggregate (re-read trades.csv) | |
| `total_fees` | CSV aggregate (re-read trades.csv) | |
| `deals_completed` | CSV aggregate count | |
| `win_rate` | CSV aggregate `wins/deals * 100` | |
| **Per-coin fields:** | | |
| `coins[sym].avg_entry` | `_last_exchange_positions[base]["entry_price"]` | Exchange truth |
| `coins[sym].unrealized_pnl` | `_last_exchange_positions[base]["unrealized_pnl"]` | Exchange truth |
| `coins[sym].position_size` | `_last_exchange_positions[base]["qty"]` | Exchange truth |
| `coins[sym].current_price` | `client.fetch_ticker_price(sym)` | LIVE API CALL per coin |
| `coins[sym].realized_pnl` | CSV filtered by symbol (re-read per coin) | |
| `coins[sym].cumulative_funding` | `cs.cumulative_funding` | |
| `coins[sym].tp_order_id` | `cs.tp_order_id` | |
| `coins[sym].layer_count` | `cs.layer_count` | |
| `coins[sym].next_tp_price` | `cs.tp_limit_price` | Stored separately from eng.long_tp |
| `coins[sym].cfgi` | `_cfgi_coins.get(sym)` | Hourly-polled |
| `coins[sym].state` | `cs.engine.get_status()["coins"][sym]` | Engine phase/signal state |
| `regime` | `_regime_alert_state` | |
| `regime_detail.*` | `_regime_alert_state, _regime_signal_type, _regime_signal_count` | |
| `trend_direction` | `"bearish" if _regime_signal_type == "TOP" else "bullish"` | |
| `fear_greed_index` / `cfgi` | `_cfgi_market` | Hourly-polled |
| `router.active_cash` | `router.active_pool_cash` | |
| `router.reserve_cash` | `router.reserve_pool_cash` | |
| `tier_coin_cap` | `router.tier_coin_cap` | |
| `approved_symbols` | `sorted(router.active_allocations.keys())` | |
| `uptime_hours` | `(now - _start_time).total_seconds() / 3600` | |

**API calls during status write:**
- `client.fetch_ticker_price(sym)` — one call per active coin

**File reads during status write:**
- `OUTPUT_DIR/trades.csv` — read once per coin (per-coin PnL) + once for aggregates = N+1 reads total

---

### 3.8 State Save/Load Round-Trip

**What `_save_state()` persists:**
```json
{
  "saved_at": "...",
  "bot_state": "RUNNING|PAUSED|WIND_DOWN",
  "capital": 340.0,
  "coins": {
    "SYM/USDT": {
      "symbol", "allocated_capital", "tp_order_id", "tp_limit_price",
      "last_candle_ts", "cumulative_funding", "last_funding_check_ms",
      "layer_count",
      "engine_state": { ...V14LifecycleEngine.snapshot_state() }
    }
  },
  "router": {
    "active_pool_cash", "reserve_pool_cash",
    "active_allocations", "reserve_allocations"
  },
  "regime": { "signal_count", "signal_type", "alert_state" },
  "tg_update_offset": 0,
  "open_deals": { "{sym}:long": {deal_id, symbol, open_time, layers, invested} }
}
```

**Engine snapshot includes (from `snapshot_state()`):**
- All phase state: `phase`, `capital`, `phase_start_date`
- Long DCA: `long_coins`, `long_avg_entry`, `long_layers`, `long_last_buy`, `long_tp`, `long_cost`, `long_trades`, `long_wins`, `long_pnl`
- Short DCA: same fields for short side
- Top detection: `early_warning_date`, `failsafe_armed`, `peak_2w_k`, `ob93_armed`, `unwinding`
- Bottom detection: `top_detected`, `conviction_fired`
- Wrapper: `_last_daily_date`, `_live_mode`, `_last_candle_ts`, `current_price`

**What is NOT persisted (lost on restart):**
| Lost Field | Impact |
|------------|--------|
| `_last_rebalance_date` | Rebalance runs immediately on first cycle (minor — correct behavior) |
| `_regime_last_eval_date` | Regime eval runs immediately if it's midnight UTC |
| `_start_time` | Uptime resets to 0 on restart |
| `_cfgi_market`, `_cfgi_coins`, `_cfgi_last_poll` | CFGI refreshed on first cycle |
| `router.total_equity`, `router.active_pool_total`, `router.reserve_pool_total` | Recalculated from cash + allocations on next rebalance |
| `cs._last_buy_time` | Dedup guard resets — first buy after restart not deduped |
| `cs.engine._warmed_up` | Set to True in `_load_state` for restored engines |

**`_load_state()` restoration logic:**
1. Reads state.json
2. Restores `bot_state`, `capital`
3. For each coin:
   - Creates `CoinState` with restored fields
   - Creates `V14LifecycleEngine`, calls `restore_state(engine_state)`
   - Sets `_live_mode=True`, `_warmed_up=True`
   - If no open position: resets `eng.capital` to `allocated_capital` (prevents sizing drift)
4. Restores router pools (cash + allocations)
5. Restores regime state
6. Restores `tg_update_offset`
7. Restores `open_deals` into `tracker._open_deals`

**Data loss risk:**  
The only critical data is in `open_deals` (tracks active trades for PnL). This is saved and restored correctly. The `trades.csv` is the permanent closed-trade history and is always loaded on startup via `tracker.load_existing()`.

---

### 3.9 Daily Rebalance

**Method:** `_do_rebalance(current_dt)`

```
Guards:
  if _last_rebalance_date == today: return
  if time since _last_rebalance_ts < 60s: return  [rapid-fire guard]

STEP 1: Load scanner rankings
  router.load_scanner_json(SCANNER_PATH)
    → reads cycle_scanner.json  [FILE READ]
    → navigates: windows.30d.rankings (primary path)
    → enriches with trend_scores (trend_multiplier, trend_direction)
    → returns List[{symbol, dca_score, trend_multiplier, trend_direction}]

STEP 2: Compute equity
  _compute_equity()
    → client.fetch_full_balance()  [EXCHANGE API CALL]
    → for each coin with open position: client.fetch_ticker_price()  [EXCHANGE API CALL per coin]
    → equity = usdt_total + Σ(current_price × eng.long_coins - eng.long_cost)
    NOTE: eng.long_coins/long_cost were overwritten by last _sync_positions_from_exchange()

STEP 3: Router rebalance
  router.rebalance_daily(scanner_data, current_equity=equity)
    → Updates: total_equity = equity
    → Updates: active_pool_total = equity × 0.75  [⚠️ Changes from 0.90!]
    → Updates: reserve_pool_total = equity × 0.25  [⚠️ Changes from 0.10!]
    → Updates: tier_coin_cap from EQUITY_TIER_CAPS
      $340 equity → 1 coin cap (falls in $100-$10K bracket)
    → Filter: dca_score >= 5.0 (hurdle rate)
    → Adjust: adjusted_score = dca_score × trend_multiplier
    → Sort: by adjusted_score descending
    → Take: top N = min(qualifying, tier_coin_cap)
    → Cap per coin: min(100%, 20% + 80%/max(len,1)) × active_pool_total
      For 1 coin: cap_pct = 1.0 → max 100% of active_pool_total
    → Weight: proportional by adjusted_score → allocations
    → Returns: {symbol: allocation_amount}

STEP 4: Apply allocations
  For new symbols not in self.coins:
    if bot_state != RUNNING: skip
    CoinState(sym, alloc)
    V14LifecycleEngine(sym, alloc, profile="high", leverage=1.0)
      → creates V14DCAEngine, V13SignalPack (reads candles.db)
      → _live_mode = True, _warmed_up = True
    self.coins[sym] = cs
    client.ensure_leverage(sym, 1.0)  [EXCHANGE API CALL]

  For existing symbols:
    cs.allocated_capital = alloc
    if eng.long_coins == 0 and eng.short_coins == 0:
      eng.capital = alloc  [sync engine capital to new allocation]

  Updates: _last_rebalance_date = today, _last_rebalance_ts = now
```

**How capital is allocated at $340 equity:**
- Tier cap: 1 coin
- Active pool (post-rebalance): $340 × 0.75 = **$255**
- Reserve pool (post-rebalance): $340 × 0.25 = **$85**
- If 1 qualifying coin: allocated = min($255, 100% cap) = **$255**

---

### 3.10 Capital Router Interaction

**Every call to the router:**

| Call Site | Method | Amount | Notes |
|-----------|--------|--------|-------|
| `__init__` | `CapitalRouter(capital=340)` | Init | active=306, reserve=34 (90/10) |
| `_do_rebalance` → `router.rebalance_daily()` | Internal update | N/A | Changes pools to 75/25! |
| `_execute_action` BUY | `request_capital(sym, cost, pool)` | `price × qty` from engine | Layer ≥6 → reserve pool |
| `_execute_action` BUY partial/fail | `return_capital(sym, granted)` | `granted` amount | Refund on failure |
| `_execute_action` BUY balance fail | `return_capital(sym, granted)` | `granted` amount | Refund on exchange balance check fail |
| `_execute_action` BUY exchange fail | `return_capital(sym, granted)` | `granted` amount | Refund on order failure |
| `_execute_action` SELL | `return_capital(sym, actual_proceeds)` | Actual sell proceeds | Includes profit |
| `_handle_tp_fill` | `return_capital(sym, actual_proceeds)` | Actual TP fill proceeds | Includes profit |
| `_force_close_coin` | `return_capital(sym, actual_proceeds)` | Actual proceeds | |

**Accounting consistency analysis:**

1. **Initial state:** `active_pool_cash = 306` (90% of 340)
2. **After first rebalance:** `active_pool_total` recalculated as `equity × 0.75`. If equity=$340 → `active_pool_total = 255`. BUT `active_pool_cash` is NOT adjusted here — only `active_pool_total` changes. The cash available may now differ from the new total. This creates an accounting inconsistency.
3. **Buy:** `active_pool_cash -= cost`; `active_allocations[sym] += cost`
4. **Sell/TP:** `active_pool_cash += proceeds`; `active_allocations[sym] = 0`; `reserve_allocations[sym] = 0`

**Potential over-return:** If a TP fill returns more than was originally requested (due to profit), `active_pool_cash` can exceed `active_pool_total`. This is logically correct (profits increase pool) but `active_pool_total` is never updated to reflect this.

**Layer pool routing:**
- Layers 1-5 → `active` pool
- Layer 6+ → `reserve` pool
- Layer count comes from `tracker._open_deals.get(key, {}).get("layers", 0) + 1` at time of request

---

### 3.11 Telegram Command Processing

**Polling:** Every 15 seconds (via `_last_tg_check` throttle).  
**API:** `get_telegram_updates(offset)` → HTTP GET `getUpdates`  
**Auth:** Filters by `AIT_TG_CHAT_ID` env var.

| Command | Action | Side Effects |
|---------|--------|--------------|
| `PAUSE` | Sets `bot_state = PAUSED` | Blocks new BUY/SELL; existing exchange TP orders remain; `_save_state()` called |
| `RESUME` | Sets `bot_state = RUNNING` | Re-enables BUY execution; `_save_state()` called |
| `APPROVE` | Sets `bot_state = WIND_DOWN`, clears `_regime_alert_state` | Blocks new entries; TPs active; `_save_state()` called |
| `DENY` | Clears `_regime_alert_state`, resets `_regime_signal_count = 0` | Continues current strategy; `_save_state()` called |
| `CLOSE <SYMBOL>` | `_force_close_coin(target)` | Cancels TP, market sell, returns capital, saves CSV |
| `CLOSE ALL` | `_force_close_all()` | Calls `_force_close_coin` for each open position |
| Unknown | Silently ignored | No telegram reply sent |

**Gaps in command handling:**
- `CLOSE ALL` uses engine's `long_coins` to find open positions — if engine state is stale before sync, may miss positions
- `_force_close_coin` uses `eng.long_coins` for sell qty (not exchange position), which is acceptable since exchange sync runs at top of each cycle
- No `STATUS` command to request manual status
- No `HELP` command listing available commands
- No command acknowledgment for unknown commands

---

## 4. External Dependencies

### 4.1 Exchange API Calls (Aster DEX Perpetuals via ccxt.aster)

| Call | Method in AsterPerpClient | Parameters | When Called |
|------|--------------------------|------------|-------------|
| Load markets | `load_markets()` | — | Startup (once) |
| Set leverage | `set_leverage(int, sym)` | leverage=1, symbol | Per new coin (once each) |
| Fetch balance (free) | `fetch_balance({"type":"future"})` | — | BUY pre-flight check |
| Fetch balance (full) | `fetch_balance({"type":"future"})` | — | Exchange sync, compute_equity, status write |
| Fetch positions | `fetch_positions()` | — | Exchange sync (every cycle), TP placement |
| Fetch ticker | `fetch_ticker(sym)` | symbol | Status write (per coin), fill price fallback |
| Fetch OHLCV | `fetch_ohlcv(sym, "1h", limit=50)` | symbol | Candle fetch (every cycle per coin) |
| Market buy | `create_market_buy_order(sym, qty, {positionSide:"BOTH"})` | symbol, qty | BUY execution |
| Market sell | `create_market_sell_order(sym, qty, {positionSide:"BOTH", reduceOnly:True})` | symbol, qty | SELL execution, force-close |
| Fetch my trades | `fetch_my_trades(sym, limit=5)` | symbol | Fill price fallback if order.average missing |
| Limit sell (TP) | `create_limit_sell_order(sym, qty, price, {GTC, positionSide, reduceOnly})` | symbol, qty, price | TP placement after BUY |
| Cancel order | `cancel_order(order_id, sym)` | order_id, symbol | TP cancellation before SELL or on phase change |
| Fetch order status | `fetch_order(order_id, sym)` | order_id, symbol | TP fill check (every 65s per coin) |
| Fetch open orders | `fetch_open_orders(sym)` | symbol | TP recovery (startup), orphan cleanup (post-TP) |
| Fetch funding history | `fetch_funding_history(sym, params)` | symbol, startTime | Every 8h per open position |

### 4.2 File I/O

| File | Path | Operations | When |
|------|------|------------|------|
| State | `OUTPUT_DIR/state.json` | Read on startup; atomic write (via .tmp) every cycle | Every 65s |
| Status | `OUTPUT_DIR/status.json` | Atomic write (via .tmp) | Every 60s |
| Trades | `OUTPUT_DIR/trades.csv` | Read on startup; atomic write (via .tmp) on every trade and every cycle | On trade + every cycle |
| Bot log | `OUTPUT_DIR/bot.log` | Append (all logging output) | Continuous |
| Bot lock | `OUTPUT_DIR/bot.lock` | Create + msvcrt.locking on startup; unlock on shutdown | Startup/shutdown |
| Bot PID | `OUTPUT_DIR/bot.pid` | Write PID on startup; delete on clean shutdown | Startup/shutdown |
| Scanner | `SCANNER_PATH` (`docs/data/v14/cycle_scanner.json`) | Read on rebalance + regime eval | Daily |
| Candles DB | `DB_PATH` (`trading/spot/data/candles.db`) | Read by V13SignalPack (via SQLite3) | On engine init + daily signal refresh |

### 4.3 Database Queries (candles.db)

Not made directly from this file. Made by `V13SignalPack(coin)` inside `V14LifecycleEngine.__init__()` and during daily signal refresh on the daily boundary tick. Queries are per-coin historical OHLCV + signal data.

### 4.4 External HTTP Calls

| Service | URL | When | Auth |
|---------|-----|------|------|
| Telegram sendMessage | `https://api.telegram.org/bot{token}/sendMessage` | On events (BUY, SELL, TP, alerts, status) | `AIT_TG_TOKEN` |
| Telegram getUpdates | `https://api.telegram.org/bot{token}/getUpdates` | Every 15 seconds | `AIT_TG_TOKEN` |
| CFGI API | `CFGIClient.get_current(...)` | Hourly | `CFGI_API_KEY` |

---

## 5. Gap Analysis

### GAP-01 — `_handle_tp_fill`: Broken orphaned order cleanup
**Severity:** P1 (data-incorrect / silent failure)  
**Flow:** 3.6 TP Fill Detection  
**Description:**  
After a TP fill, the code attempts to cancel any remaining stale sell orders:
```python
open_orders = self.client.client.fetch_open_orders(
    self.client._to_ccxt_symbol(sym)
)
```
`self.client` is an `AsterPerpClient` instance. `AsterPerpClient` has no `.client` attribute (it has `._exchange`). It also has no `._to_ccxt_symbol()` method (the correct method is `._aster_symbol()`). This raises `AttributeError` which is silently caught by the surrounding `try/except`. **Orphaned sell orders are never cleaned up after TP fills.**

**Impact:** If any stale sell order exists post-TP (e.g., from a crash mid-operation), it will remain on the exchange indefinitely, potentially filling unexpectedly and causing a short position or unexpected capital changes.

**Suggested fix:**
```python
# Replace:
open_orders = self.client.client.fetch_open_orders(self.client._to_ccxt_symbol(sym))
# With:
open_orders = self.client.fetch_open_orders(sym)
```

---

### GAP-02 — `CapitalRouter.rebalance_daily`: Pool split changes from 90/10 to 75/25
**Severity:** P1 (data-incorrect — capital allocation drift)  
**Flow:** 3.9 Daily Rebalance, 3.10 Capital Router Interaction  
**Description:**  
The `CapitalRouter` constructor initializes with a **90/10** pool split:
```python
self.active_pool_total = self.total_equity * 0.90   # $306
self.reserve_pool_total = self.total_equity * 0.10  # $34
```
But `rebalance_daily()` changes the split to **75/25**:
```python
self.active_pool_total = self.total_equity * 0.75   # $255
self.reserve_pool_total = self.total_equity * 0.25  # $85
```
The docstring says "90/10 Pool Split" but the live behavior after first rebalance uses 75/25. The cash amounts (`active_pool_cash`, `reserve_pool_cash`) are NOT adjusted when this happens — only the `total` reference values change.

At $340 equity:
- Before rebalance: active_pool_total=$306, reserve=$34
- After rebalance: active_pool_total=$255, reserve=$85

This means target allocation from `rebalance_daily` is based on **$255 active pool**, but the actual capital distributed could have been based on $306. The allocation math uses `active_pool_total` for calculations, so this affects max allocation per coin.

**Suggested fix:** Decide on one split (90/10 or 75/25) and make it consistent in both constructor and rebalance. Update docstring.

---

### GAP-03 — `_last_rebalance_date` and `_regime_last_eval_date` not persisted
**Severity:** P2 (cosmetic / minor operational)  
**Flow:** 3.8 State Save/Load, 3.2 Main Loop  
**Description:**  
After restart, `_last_rebalance_date = None` and `_regime_last_eval_date = None`. This means:
- Rebalance runs immediately on first cycle after restart (any time of day)
- Regime eval runs if `current_dt.hour == 0` (midnight check), which is probably fine

For rebalance, running on every restart means the scanner is re-read and allocations recalculated, which is usually desired behavior on restart.

**Suggested fix (optional):** Add `_last_rebalance_date` to state.json if preventing startup rebalances is desired.

---

### GAP-04 — `_reentry_cooldown_until` declared but never used
**Severity:** P2 (dead code / maintenance)  
**Flow:** 3.4 BUY Execution  
**Description:**  
`self._reentry_cooldown_until = 0.0` is set in `__init__` but is never read or updated anywhere in the codebase. The comment says "prevents rapid-fire after TP fills". This was presumably replaced by the 30-second `ORDER_DEDUP_WINDOW` in `_execute_action`, but the old variable was left.

**Suggested fix:** Remove the dead attribute.

---

### GAP-05 — `_force_close_coin` uses engine qty, not exchange position
**Severity:** P1 (potential incorrect sell qty in edge case)  
**Flow:** 3.11 Telegram Command Processing  
**Description:**  
```python
qty = eng.long_coins
if not qty:
    send_telegram("No open position"); return
result = self.client.create_market_sell(sym, qty)
```
This uses `eng.long_coins` which was last set by `_sync_positions_from_exchange()`. If the engine state is stale (e.g., force-close called very soon after a buy, before the next exchange sync), `eng.long_coins` may differ from the actual exchange position. The `_execute_action` SELL path correctly fetches exchange position for qty, but `_force_close_coin` does not.

**Suggested fix:** Fetch exchange position in `_force_close_coin` and use exchange qty as source of truth:
```python
positions = self.client.fetch_open_positions()
base = sym.split("/")[0]
qty = positions.get(base, {}).get("qty", 0) or eng.long_coins
```

---

### GAP-06 — `_write_status` reads trades.csv N+1 times per write
**Severity:** P3 (performance)  
**Flow:** 3.7 Status Write  
**Description:**  
For N active coins, `_write_status` reads trades.csv once per coin (per-coin realized PnL) and then once more for aggregate stats. This is N+1 CSV reads per 60-second status update. At low N (1-3 coins) this is negligible, but it's inefficient.

**Suggested fix:** Read once, compute all per-coin and aggregate stats in one pass.

---

### GAP-07 — `V14LifecycleEngine.get_status()` hardcodes wrong exchange name
**Severity:** P2 (cosmetic — incorrect metadata in status output)  
**Flow:** 3.7 Status Write  
**Description:**  
`V14LifecycleEngine.get_status()` returns `'exchange': 'hyperliquid'` (hardcoded from the paper bot template). The main runner's `_write_status()` overrides this at the top level with `"exchange": "aster_perp"`, but any consumer of the per-engine `get_status()` directly would see the wrong exchange.

**Suggested fix:** Pass exchange name into `V14LifecycleEngine` or parameterize `get_status()`.

---

### GAP-08 — `msvcrt` file lock is Windows-only
**Severity:** P1 (will crash on Linux/cloud deployment)  
**Flow:** 3.1 Startup  
**Description:**  
```python
import msvcrt
msvcrt.locking(self._lock_fh.fileno(), msvcrt.LK_NBLCK, 1)
```
`msvcrt` is Windows-only. If this bot is ever deployed to a Linux server or cloud VM, this will raise `ModuleNotFoundError` on startup.

**Suggested fix:** Wrap in platform check:
```python
if sys.platform == "win32":
    import msvcrt; msvcrt.locking(...)
else:
    import fcntl; fcntl.flock(...)
```

---

### GAP-09 — `_compute_equity` double-counts unrealized PnL
**Severity:** P1 (data-incorrect — equity calculation may be inflated)  
**Flow:** 3.9 Daily Rebalance  
**Description:**  
`_compute_equity()` computes:
```python
equity = usdt_total + unrealized
```
Where `usdt_total` = `fetch_full_balance()["usdt_total"]`.  

On Aster DEX Perpetuals (perp futures), `usdt_total` from the exchange balance **may already include unrealized PnL** as margin balance. Adding unrealized PnL from engine position data (based on engine's `long_coins` and `long_cost` vs current ticker price) on top could double-count.

This depends on how Aster's API reports `total` — if total = free + margin (not including unrealized), then adding unrealized is correct. If total already includes unrealized, this inflates equity.

**Status:** NEEDS VERIFICATION against actual Aster API response format.

---

### GAP-10 — No handling for SHORT_OPEN/SHORT_CLOSE actions in `_execute_action`
**Severity:** P2 (incomplete feature — short side silently dropped)  
**Flow:** 3.4 / 3.5  
**Description:**  
`_execute_action` only handles `act_type == "BUY"` and `act_type == "SELL"`. The engine can emit `SHORT_OPEN` and `SHORT_CLOSE` actions (for coins in SHORT_DCA phase). These actions are silently ignored — no exchange order is placed, no error is logged.

Since the bot is currently long-only (LONG_DCA phase) this is not an active issue, but if a coin transitions to SHORT_DCA, the engine would generate short actions that are never executed while the engine state drifts to reflect shorts.

**Suggested fix:** Add explicit handling (or explicit rejection with `reject_action`) for `SHORT_OPEN` and `SHORT_CLOSE`.

---

### GAP-11 — `_place_tp_order` fetches positions again (extra API call)
**Severity:** P3 (performance — redundant API call)  
**Flow:** 3.4 BUY Execution  
**Description:**  
`_place_tp_order` calls `client.fetch_open_positions()` to get the exchange position qty for the TP order. This happens immediately after the BUY which also triggered an exchange balance check. The positions were also just synced at the top of the cycle. Three position fetches in close succession per buy.

**Suggested fix:** Use the qty returned from the BUY result (`actual_qty`) directly for the TP order.

---

### GAP-12 — `_recover_tp_orders` Phase 2 runs even if Phase 1 just handled the TP
**Severity:** P2 (redundant work, minor)  
**Flow:** 3.1 Startup  
**Description:**  
Phase 1 of `_recover_tp_orders` may call `_handle_tp_fill()` which sets `cs.tp_order_id = None`. Then Phase 2 runs immediately and scans for open orders on the exchange for the same symbol — but since the position was just closed (TP filled), the exchange may show no open orders, which is correct. However, Phase 2 checking Phase 1's already-handled coins is redundant.

**Suggested fix:** Track which symbols were already handled in Phase 1 and skip them in Phase 2.

---

### GAP-13 — Engine capital accounting diverges from router in multi-layer DCA
**Severity:** P1 (data-incorrect — engine sizing may produce wrong order amounts)  
**Flow:** 3.4 BUY Execution, 3.10 Capital Router  
**Description:**  
The engine uses its internal `capital` to size orders: DCA buy amount = `capital × DCA_BO_PCT` (40% of engine capital). The engine capital (`eng.capital`) is reset to `cs.allocated_capital` on:
1. State load (if no position)
2. TP fill cleanup

But between layers, `eng.capital` decreases as the engine records buys internally. However, the router is the real capital source. After Layer 1, the engine thinks it has less capital, so Layer 2 is smaller in percentage terms. This matches V14's DCA design (diminishing layers). 

However, if the engine capital was reset between layers (e.g., on restart with no open position when there IS one on exchange), the engine would size Layer 2 the same as Layer 1, potentially over-requesting capital.

The exchange sync (`_sync_positions_from_exchange`) updates `long_coins`, `long_cost`, etc. but does NOT reset `eng.capital`. So `eng.capital` after Layer 1 = `allocated_capital - layer1_cost`, which is the correct base for Layer 2 sizing.

**Status:** Logic appears correct for the normal flow. NEEDS VERIFICATION on the edge case of mid-DCA restart.

---

## 6. Data Source Map

| Variable | Authoritative Source | Updated When | Used By |
|----------|---------------------|--------------|---------|
| `eng.long_coins` | Exchange (`fetch_open_positions`) | Every cycle (exchange sync) | BUY sizing, TP qty, status |
| `eng.long_avg_entry` | Exchange (`fetch_open_positions.entry_price`) | Every cycle (exchange sync) | Status display |
| `eng.long_cost` | Exchange (`entry_price × qty`) | Every cycle (exchange sync) | PnL calc, equity |
| `eng.long_tp` | Engine (calculated: `entry × 1.015`) | Exchange sync overwrites; engine recalculates on buy | TP placement |
| `eng.long_layers` | `cs.layer_count` (CoinState) | BUY (+1), SELL/TP (0), exchange sync (copies layer_count) | Status, DCA logic |
| `eng.capital` | Initialized to `allocated_capital`; decremented by engine on buys; reset on TP fill and rebalance | On buy (decremented), TP fill (reset), rebalance (reset if no position) | Buy sizing |
| `cs.allocated_capital` | `router.rebalance_daily()` | Daily rebalance | Engine capital reset, status |
| `cs.tp_order_id` | `_place_tp_order()` (exchange order_id) | On BUY (set), on SELL/TP fill (cleared) | TP fill detection, TP cancel |
| `cs.tp_limit_price` | `_place_tp_order()` (stored separately) | On BUY (set), on SELL/TP fill (cleared) | Status display, fill correction logging |
| `cs.layer_count` | `_execute_action` BUY (+1); SELL/TP fill (0) | On every buy/sell | TP qty, status |
| `cs.last_candle_ts` | Main loop after each processed candle | Per candle | Dedup — prevent reprocessing |
| `cs.cumulative_funding` | `_update_funding()` | Every 8h | Status, TP fill message |
| `_exchange_usdt_free` | `client.fetch_full_balance()` | Every cycle (exchange sync) | Status (cash field) |
| `_exchange_usdt_total` | `client.fetch_full_balance()` | Every cycle (exchange sync) | Status (equity calc) |
| `_last_exchange_positions` | `client.fetch_open_positions()` | Every cycle (exchange sync) | Status (positions data) |
| `router.active_pool_cash` | CapitalRouter: +/- on request/return | On every BUY (−) and SELL/TP (+ proceeds) | Capital availability |
| `router.active_allocations` | CapitalRouter: +amount on request; 0 on return | On every BUY and SELL/TP | Accounting |
| `router.tier_coin_cap` | `EQUITY_TIER_CAPS` lookup on equity | On rebalance | Max simultaneous coins |
| `tracker._open_deals` | `on_buy()` (create/extend); `on_sell()` (pop) | On every BUY and SELL | PnL calculation, layer count for pool routing |
| `tracker.trades` | `on_sell()` (append) | On every SELL/TP fill | CSV, win_rate, total_pnl |
| `_cfgi_market` | CFGI API | Hourly | Status, regime eval message |
| `_cfgi_coins` | CFGI API | Hourly | Per-coin status |
| `_regime_signal_count` | `_evaluate_regime()` | Daily at midnight UTC | Telegram alerts |
| `_regime_alert_state` | `_evaluate_regime()`, `_handle_command()` | On regime signal / APPROVE / DENY | BUY blocking (WIND_DOWN), status |
| `bot_state` | `_handle_command()`, `_check_wind_down_complete()` | On PAUSE/RESUME/APPROVE/wind-down complete | BUY guard, status |
| `_tg_update_offset` | `_process_telegram_commands()` | On each update processed | Telegram dedup |
| `_last_rebalance_date` | `_do_rebalance()` | On successful rebalance | Prevents duplicate rebalances |
| `_last_status_write` | `_write_status()` | On each status write | Throttle |

---

## 7. Summary of Critical Findings

### P1 Bugs (Data-Incorrect or Potential Trade Impact)

| # | Bug | Impact |
|---|-----|--------|
| GAP-01 | `self.client.client` / `._to_ccxt_symbol()` AttributeError — orphaned TP order cleanup never runs | Stale sell orders can accumulate on exchange |
| GAP-02 | Pool split changes from 90/10 to 75/25 on first rebalance — undocumented and inconsistent with constructor | $51 less active capital than expected |
| GAP-05 | `_force_close_coin` uses engine qty, not exchange position | Could leave residual position open on force-close |
| GAP-09 | Possible double-counting of unrealized PnL in `_compute_equity` | Inflated equity → inflated rebalance allocations |
| GAP-10 | `SHORT_OPEN`/`SHORT_CLOSE` actions silently ignored | Engine state diverges from exchange if coin enters short phase |
| GAP-13 | Engine capital accounting mid-DCA restart edge case | NEEDS VERIFICATION |

### P2 Bugs (Cosmetic or Minor)

| # | Bug | Impact |
|---|-----|--------|
| GAP-03 | `_last_rebalance_date` not persisted | Rebalance runs on every restart |
| GAP-04 | `_reentry_cooldown_until` dead attribute | Dead code |
| GAP-07 | Engine `get_status()` returns `exchange: hyperliquid` | Wrong metadata in per-engine status |
| GAP-08 | `msvcrt` lock is Windows-only | Would crash on Linux deployment |
| GAP-12 | TP recovery Phase 2 runs on already-handled symbols | Redundant API calls at startup |

### P3 (Enhancement)

| # | Issue |
|---|-------|
| GAP-06 | `_write_status` reads CSV N+1 times |
| GAP-11 | `_place_tp_order` makes redundant `fetch_open_positions` call |

---

*Document ends. All line numbers and behavioral descriptions are based on direct code analysis of the files listed above. Any field marked NEEDS VERIFICATION requires runtime testing or exchange API documentation to confirm.*
