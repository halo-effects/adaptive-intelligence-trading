# V14PM Live Trading Bot - Code Audit & Data Flow Trace (2026-03-21)

> **Point-in-time code audit.** For current architecture, see V14PM_SYSTEM_ARCHITECTURE.md.
> Sections 4-7 of this document (External Dependencies, Gap Analysis, Data Source Map, Critical
> Findings) have been absorbed into the architecture doc (s8.6, s18, s6.8.7 respectively) and are
> replaced below with pointers. This file retains the detailed per-function traces (s2) and
> full data flow traces (s3) which are line-level implementation details.

**Generated:** 2026-03-21  
**Source file:** `trading/spot/run_v14_portfolio_live_aster.py`  
**Supporting files:** `v14_lifecycle_engine.py`, `v14_capital_manager.py`, `exchange_client.py` (SpotExchangeClient - not used by this bot), plus the inline `AsterPerpClient`  
**Scope:** Real-money live trading (~$340 USDT on Aster DEX Perpetuals)


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
| `SpotExchangeClient` | Universal exchange client â€" **IMPORTED BUT NOT USED BY THIS BOT** |

### 1.2 Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `DB_PATH` | `$AIT_CANDLES_DB` or `trading/spot/data/candles.db` | Candle database (SQLite) â€" read by engine's V13SignalPack |
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

- **`send_telegram(msg, buttons=None)`** â€" HTTP POST to Telegram Bot API (`sendMessage`). Reads `AIT_TG_TOKEN` and `AIT_TG_CHAT_ID` from env. Silent on failure.
- **`get_telegram_updates(offset=0)`** â€" HTTP GET `getUpdates` with 0 long-poll timeout. Returns list of update dicts.

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
| `_open_deals` | `Dict[str, dict]` | `{}` â€" key format: `"{symbol}:long"` |
| `_existing_keys` | `set` | `set()` â€" dedup guard using `"{symbol}|{open_time}|{close_time}"` |

**Methods:**
| Method | Signature | Purpose |
|--------|-----------|---------|
| `load_existing` | `() -> None` | Load trades.csv on startup; populates `_existing_keys`, `_deal_counter`, `trades` |
| `on_buy` | `(symbol, qty, price, ts) -> None` | Opens or extends a deal in `_open_deals`; increments `layers`, accumulates `invested` |
| `on_sell` | `(symbol, qty, actual_price, actual_proceeds, fee, ts) -> dict` | Closes deal; computes PnL, return_pct, duration; appends to `trades`; returns record dict |
| `save_csv` | `() -> None` | Atomic write (tmp â†' rename) of trades.csv |
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
| `_leverage_set` | `set` | `set()` â€" tracks symbols with leverage already set |

**Methods:**
| Method | Signature | Purpose |
|--------|-----------|---------|
| `ensure_leverage` | `(db_symbol, leverage=1.0) -> None` | Set leverage once per symbol; skips if already set |
| `_aster_symbol` | `(db_symbol) -> str` | Converts `PEPE/USDT` â†' `1000PEPE/USDT:USDT` (handles 1000-prefix coins) |
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
| `engine` | `Optional[V14LifecycleEngine]` | `None` â†' set after init |
| `tp_order_id` | `Optional[str]` | `None` â†' set after TP placed |
| `tp_limit_price` | `Optional[float]` | `None` â†' set after TP placed (separate from `eng.long_tp`) |
| `last_candle_ts` | `int` | `0` â†' set to processed candle ms timestamp |
| `cumulative_funding` | `float` | `0.0` |
| `last_funding_check_ms` | `int` | `0` |
| `_last_buy_time` | `float` | `0.0` â†' dedup guard |
| `layer_count` | `int` | `0` â†' incremented on BUY, zeroed on SELL/TP |

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
| `_wind_down_direction` | `Optional[str]` | `None` | Target direction after wind-down (not used â€" direction flip not implemented) |
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
| `_do_rebalance` | `(current_dt) -> None` | Daily rebalance: scanner â†' allocations â†' new engines |
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
| `active_pool_total` | `float` | `total_equity * 0.90` (constructor); `total_equity * 0.75` (after first rebalance â€" **see Gap #2**) |
| `reserve_pool_total` | `float` | `total_equity * 0.10` (constructor); `total_equity * 0.25` (after first rebalance â€" **see Gap #2**) |
| `active_pool_cash` | `float` | `active_pool_total` |
| `reserve_pool_cash` | `float` | `reserve_pool_total` |
| `active_allocations` | `Dict[str, float]` | `{}` â€" running tally of capital out per coin |
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
- `_engine` â†' `V14DCAEngine` instance (inner DCA state machine)
- `_live_mode`, `_warmed_up`, `_last_daily_date`, `_last_candle_ts`
- `current_price`, `_candles_1h`

**Key Methods:**
- `tick(candle_1h, cash_available)` â†' `List[dict]` â€" Main entry; emits BUY/SELL action dicts
- `snapshot_state() -> dict` â€" Serialize all state for persistence
- `restore_state(state)` â€" Restore from saved dict
- `reject_action(action_dict)` â€" Roll back engine state for rejected BUY
- `get_status() -> dict` â€" Returns status dict (NOTE: hardcodes `'exchange': 'hyperliquid'`)
- `backfill_direct(start_date, end_date)` â€" Run V14 engine's full history

---

## 3. Data Flow Traces

### 3.1 Startup Flow

```
main()
  â""â"€ parse_args() â†' args.capital, args.confirm, args.skip_backfill, args.fresh
  â""â"€ logging.basicConfig() [force=True, second config overrides module-level]
  â""â"€ OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
  â""â"€ V14PortfolioLiveAster(capital, confirm, skip_backfill, fresh)
       â""â"€ __init__():
            Validates: confirm=True required
            Reads: ASTER_API_KEY, ASTER_API_SECRET from env
            Creates: CapitalRouter(capital=340)  â†' active_pool=306, reserve=34
            Creates: TradeTracker(OUTPUT_DIR)
            Calls: tracker.load_existing()
              â†' reads OUTPUT_DIR/trades.csv (if exists)
              â†' populates: _deal_counter, _existing_keys, trades[]
            Creates: AsterPerpClient(api_key, api_secret)
              â†' ccxt.aster({...options...})
              â†' client._exchange.load_markets()  [EXCHANGE API CALL #1]
            Initializes all state fields to defaults
  â""â"€ bot.run():
       1. Acquires file lock: OUTPUT_DIR/bot.lock (msvcrt.locking â€" Windows-only!)
       2. Writes PID: OUTPUT_DIR/bot.pid
       3. State load (unless --fresh):
          _load_state()
            â†' reads OUTPUT_DIR/state.json
            â†' restores: bot_state, coins (each CoinState + engine), router pools,
                        regime state, tg_update_offset, open_deals
            â†' for each coin engine: V14LifecycleEngine(sym, capital, profile, leverage)
              â†' V14DCAEngine init, V13SignalPack(coin) [reads candles.db]
              â†' restore_state(engine_state)
              â†' sets _live_mode=True, _warmed_up=True
              â†' if no open position: resets engine capital to allocated amount
       4. Initial rebalance (only if fresh OR no coins loaded):
          _do_rebalance(now)
            â†' router.load_scanner_json(SCANNER_PATH)  [FILE READ: cycle_scanner.json]
            â†' _compute_equity()  [EXCHANGE API CALL: fetch_full_balance, fetch_ticker_price per coin]
            â†' router.rebalance_daily(scanner_data, current_equity)
              â†' changes pool split to 75/25 (see Gap #2)
              â†' filters: DCA Score >= 5.0 Ã- trend_multiplier
              â†' sorts by adjusted_score desc, takes top N (tier cap)
              â†' returns {symbol: allocated_dollars}
            â†' for each new symbol: CoinState + V14LifecycleEngine (warmed_up=True)
            â†' ensures leverage on exchange for each coin
       5. Set leverage on exchange for all coins:
          client.ensure_leverage(sym, 1.0)  [EXCHANGE API CALL per coin]
       6. Initial exchange sync:
          _sync_positions_from_exchange()
            â†' client.fetch_full_balance()  [EXCHANGE API CALL]
            â†' client.fetch_open_positions()  [EXCHANGE API CALL]
            â†' overwrites engine.long_coins, long_cost, long_avg_entry, long_tp
            â†' caches: _exchange_usdt_free, _exchange_usdt_total, _last_exchange_positions
       7. TP recovery:
          _recover_tp_orders()
            â†' Phase 1: for each cs with tp_order_id:
                client.check_order_status(sym, order_id)  [EXCHANGE API CALL per coin]
                â†' if filled: _handle_tp_fill()
                â†' if cancelled: clear tp_order_id
            â†' Phase 2: for each coin:
                client.fetch_open_orders(sym)  [EXCHANGE API CALL per coin]
                â†' if orphan sell + position: adopt as TP
                â†' if stale sell + no position: cancel
                â†' if position + no TP order: _place_tp_order()
       8. send_telegram("ðŸš€ Live Bot Started...")  [HTTP: Telegram API]
       9. Enter main loop
```

**Data available at each step:**
- After `__init__`: Capital, exchange client, empty coins dict, clean router
- After `_load_state`: All coin engines with restored DCA state, router pools, regime state
- After initial rebalance: Coin engines initialized for scanner top picks
- After exchange sync: Engine position fields overwritten from exchange (ground truth)
- After TP recovery: All TP orders reconciled with exchange state
- **Missing at startup:** `_last_rebalance_date`, `_regime_last_eval_date` are NOT restored â†' rebalance and regime eval will run immediately on first cycle regardless of whether they ran today (see Gap #3)

---

### 3.2 Main Loop â€" Single Cycle

**Loop condition:** `while not self._shutdown` (65-second target period)

```
cycle_start = time.time()
current_dt = datetime.now(UTC)

STEP 1: Telegram commands (every 15s)
  _process_telegram_commands()
    â†' get_telegram_updates(offset=_tg_update_offset)  [HTTP: Telegram API]
    â†' filter by AIT_TG_CHAT_ID
    â†' parse text as UPPER
    â†' _handle_command(text)
  Data read: _tg_update_offset, AIT_TG_CHAT_ID env
  Data write: _tg_update_offset, bot_state (on PAUSE/RESUME/APPROVE)

STEP 2: Daily rebalance (once per calendar day, at any hour)
  _do_rebalance(current_dt)
    â†' guard: _last_rebalance_date == today â†' skip
    â†' guard: < 60s since last rebalance â†' skip
    â†' reads: SCANNER_PATH  [FILE READ: cycle_scanner.json]
    â†' _compute_equity()
      â†' client.fetch_full_balance()  [EXCHANGE API CALL]
      â†' for each coin with position: client.fetch_ticker_price(sym)  [EXCHANGE API CALL per coin]
    â†' router.rebalance_daily(scanner_data, equity)
    â†' creates new CoinState + V14LifecycleEngine for new symbols
    â†' updates allocated_capital for existing coins
    â†' resets engine capital if no position open
  Data read: SCANNER_PATH, exchange balance, ticker prices
  Data write: self.coins, cs.allocated_capital, engine.capital, _last_rebalance_date

STEP 3: Regime evaluation (once per day at midnight UTC)
  _evaluate_regime(current_dt)
    â†' guard: _regime_last_eval_date == today â†' skip
    â†' guard: current_dt.hour != 0 â†' skip
    â†' reads: SCANNER_PATH  [FILE READ: cycle_scanner.json]
    â†' counts coins with TOP/BOTTOM signals from cycle_scanner.json fields
    â†' tiers: EARLY (â‰¥5), STRONG (â‰¥12), MAJORITY (â‰¥25)
    â†' if threshold crossed: send_telegram(alert + APPROVE/DENY buttons)
    â†' sets _regime_alert_state = "AWAITING_APPROVAL"
  Data read: SCANNER_PATH, _regime_signal_count, _regime_last_eval_date
  Data write: _regime_signal_count, _regime_signal_type, _regime_alert_state, _regime_last_eval_date

STEP 4: TP fill check (every 65s)
  if time.time() - last_tp_check >= 65:
    _check_tp_fills()
      â†' for each coin with tp_order_id:
          client.check_order_status(sym, tp_order_id)  [EXCHANGE API CALL per coin]
          â†' if filled: _handle_tp_fill(sym, cs, result)
    _update_funding()
      â†' for each coin with open position:
          if 8h since last check: client.fetch_funding_history(sym)  [EXCHANGE API CALL]
    last_tp_check = time.time()

STEP 5: Exchange position sync
  _sync_positions_from_exchange()
    â†' client.fetch_full_balance()  [EXCHANGE API CALL]
    â†' client.fetch_open_positions()  [EXCHANGE API CALL]
    â†' for each coin: overwrite engine.long_coins, long_cost, long_avg_entry, long_tp
    â†' cache: _exchange_usdt_free, _exchange_usdt_total, _last_exchange_positions

STEP 6: Candle processing (for each active coin)
  for sym, cs in coins.items():
    candles = _fetch_candles(sym)
      â†' client._exchange.fetch_ohlcv(aster_sym, "1h", limit=50)  [EXCHANGE API CALL]
      â†' filters out incomplete (current) candle
      â†' applies 1000-prefix price scaling
    for candle in candles:
      if candle.timestamp <= cs.last_candle_ts: skip
      actions = cs.engine.tick(candle, cash_available=cs.allocated_capital)
        â†' V14LifecycleEngine.tick()
          â†' on daily boundary: refresh signal pack, run full daily tick
          â†' between daily: run DCA grid tick hourly
          â†' returns List[action_dicts] with BUY/SELL/PHASE_CHANGE actions
      for action in actions:
        _execute_action(sym, cs, action)  [see Â§3.4 / Â§3.5]
      cs.last_candle_ts = ts_ms
      cs.engine._last_candle_ts = ts_ms
    phase change detection: if phase changed â†' cancel stale TP

STEP 7: CFGI poll (once per hour)
  _poll_cfgi()
    â†' if < 3600s since last poll: skip
    â†' CFGIClient.get_current(["MARKET"], period=4)  [HTTP: CFGI API]
    â†' CFGIClient.get_current(supported_coins, period=4)  [HTTP: CFGI API]
    â†' updates _cfgi_market, _cfgi_coins
  Data read: CFGI_API_KEY env, active coin bases
  Data write: _cfgi_market, _cfgi_coins, _cfgi_last_poll

STEP 8: Status write (every 60s)
  _write_status()
    â†' uses cached _last_exchange_positions, _exchange_usdt_free, _exchange_usdt_total
    â†' for each coin: cs.engine.get_status(), ticker fetch for current_price
    â†' reads trades.csv for per-coin PnL and aggregates  [FILE READ: trades.csv]
    â†' writes OUTPUT_DIR/status.json (atomic: .tmp â†' rename)
  Data read: cached exchange data, engine status, trades.csv
  Data write: OUTPUT_DIR/status.json

STEP 9: State save
  _save_state()
    â†' coin engines: cs.engine.snapshot_state()
    â†' writes OUTPUT_DIR/state.json (atomic: .tmp â†' rename)
  tracker.save_csv()
    â†' writes OUTPUT_DIR/trades.csv (atomic: .tmp â†' rename)
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
    â†' ccxt.aster.fetch_balance({"type": "future"})
    â†' returns {usdt_free: float, usdt_total: float}
  self._exchange_usdt_free = balance["usdt_free"]
  self._exchange_usdt_total = balance["usdt_total"]
except:
  logger.warning("..."); return  [EARLY RETURN â€" keeps previous cached values]

try:
  positions = client.fetch_open_positions()
    â†' ccxt.aster.fetch_positions()
    â†' filters: contracts > 0
    â†' reverses 1000-prefix scaling on qty and entry_price
    â†' returns {base_symbol: {qty, entry_price, side, unrealized_pnl}}
except:
  logger.warning("..."); return  [EARLY RETURN â€" does NOT overwrite engine with empty]

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
- Balance failure â†' `return` (keeps previous `_exchange_usdt_free/total`)
- Position fetch failure â†' `return` (does NOT zero engine state â€" correct safety behavior)

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
  price = action["price"]    [from engine â€" engine's estimated entry price]
  qty = action["qty"]        [from engine â€" calculated from capital/price]
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
      â†' deducts from pool cash
      â†' adds to pool allocations[sym]
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
      send_telegram("âš ï¸ BUY skipped â€" insufficient USDT")
      return

  ORDER PLACEMENT:
    result = client.create_market_buy(sym, qty)
      â†' ccxt.aster.create_market_buy_order(aster_sym, exchange_qty, {positionSide:"BOTH"})
      â†' fill price from order.average, else trades fetch, else ticker
      â†' returns {status:"filled", price:actual, qty:filled, cost:actual, fee, order_id}

    if result and result["status"] in ("filled", "dry_run"):
      actual_price = result["price"]    [EXCHANGE FILL â€" not engine price]
      actual_qty = result["qty"]
      actual_cost = result["cost"]
      fee = result["fee"]
      spread_bps = abs(actual_price - price) / price * 10000
      if spread_bps > 50: send_telegram("âš ï¸ High spread")

      TRACKER UPDATE:
        tracker.on_buy(sym, actual_qty, actual_price, now_utc)
          â†' creates/updates _open_deals["{sym}:long"]
          â†' layers += 1
          â†' invested += actual_qty * actual_price

      cs._last_buy_time = time.time()  [dedup guard reset]
      cs.layer_count += 1              [local count]

      TP PLACEMENT:
        _place_tp_order(sym, cs)
          â†' tp_price = eng.long_tp      [from engine, freshly set after buy]
          â†' fetch exchange position qty for accuracy  [EXCHANGE API CALL]
          â†' if cs.tp_order_id: cancel old TP  [EXCHANGE API CALL]
          â†' place_limit_sell(sym, qty, tp_price)  [EXCHANGE API CALL: GTC limit sell]
          â†' cs.tp_order_id = oid
          â†' cs.tp_limit_price = tp_price  [stored separately from eng.long_tp]

      NOTIFICATION:
        send_telegram("ðŸ"µ DCA Layer N | Fill: ... | TP: ... | Reason: ...")

    else:  [buy failed]
      router.return_capital(sym, granted)
      cs.engine.reject_action(action)
```

**NOTE:** After a successful buy, the engine state is NOT immediately corrected â€" it already recorded the buy internally (via `_long_dca_tick`). The engine's `long_coins`, `long_cost`, `long_avg_entry`, `long_tp` reflect the buy. The next `_sync_positions_from_exchange()` call will overwrite these with actual exchange values.

**What if router denies capital?**
â†' `reject_action()` rolls back the engine's internal trade record. The engine's `long_coins`, `long_cost`, `long_layers` are decremented. `long_trades` is decremented. No exchange call is made.

**What if exchange balance insufficient?**
â†' Router capital is returned (refunded to pool), engine rolled back. Telegram alert sent.

---

### 3.5 SELL Execution Path

**Trigger:** Engine emits `{action: "SELL", qty: X, price: Y, reason: "LONG_DCA_TP" or "LONG_DCA_CLOSE"}`

```
_execute_action(sym, cs, action):
  act_type = "SELL"

  GUARD: TP order active on exchange?
    if cs.tp_order_id and "TP" in reason:
      logger.info("Skipping engine TP â€" exchange TP order active")
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
      â†' ccxt.aster.create_market_sell_order(sym, qty, {positionSide:"BOTH", reduceOnly:True})
      â†' fill = order.average or ticker price
      â†' returns {status:"filled", price, qty, proceeds, fee}

    if result["status"] in ("filled", "dry_run"):
      actual_price = result["price"]
      actual_qty = result["qty"]
      actual_proceeds = result["proceeds"]
      fee = result["fee"]

      TRACKER UPDATE:
        record = tracker.on_sell(sym, actual_qty, actual_price, actual_proceeds, fee, now)
          â†' pops _open_deals["{sym}:long"]
          â†' computes pnl = actual_proceeds - invested - fee
          â†' appends to trades[]

      ROUTER UPDATE:
        router.return_capital(sym, actual_proceeds)
          â†' active_pool_cash += actual_proceeds
          â†' active_allocations[sym] = 0
          â†' reserve_allocations[sym] = 0
        NOTE: returns PROCEEDS (not original cost) â€" correct for PnL accounting

      cs.layer_count = 0

      if record: send_telegram("ðŸŸ¢/ðŸ"´ Deal Closed")
      cs.tp_order_id = None
      cs.tp_limit_price = None
      tracker.save_csv()

      if bot_state == WIND_DOWN: _check_wind_down_complete()

    else:  [sell failed]
      logger.error("SELL FAILED â€" will retry on next candle")
      send_telegram("âš ï¸ SELL FAILED")
      NOTE: NO rollback attempted. Engine state left inconsistent.
            Next _sync_positions_from_exchange() will show position still open.
            Engine will re-emit SELL on next candle tick (correct behavior).
```

**What if exchange TP is active?**
â†' Engine TP sell is silently skipped. Exchange limit order stays. `_check_tp_fills()` detects when it fills.

**What if sell fails?**
â†' No rollback. Engine state is preserved (showing position open). Next exchange sync will show position still open. Next candle will re-trigger the sell signal. This is the correct recovery behavior.

---

### 3.6 TP Fill Detection

**Method:** `_check_tp_fills()` (runs every `TP_CHECK_INTERVAL` = 65 seconds)

```
_check_tp_fills():
  for sym, cs in coins.items():
    if not cs.tp_order_id: continue
    try:
      result = client.check_order_status(sym, cs.tp_order_id)
        â†' ccxt.aster.fetch_order(order_id, sym)
        â†' if status in ("closed", "filled"):
            returns {filled:True, price:fill, qty:filled_qty, proceeds:cost, fee}
        â†' else: {filled:False, status}
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
      â†' pops _open_deals["{sym}:long"]
      â†' pnl = actual_proceeds - invested - fee
      â†' return_pct = pnl / invested * 100
      â†' appends to trades[]

  TELEGRAM:
    if record: send_telegram("ðŸŸ¢/ðŸ"´ Deal Closed (TP Hit) | Fill | PnL | Funding | Layers")

  ROUTER:
    router.return_capital(sym, actual_proceeds)
      â†' active_pool_cash += actual_proceeds
      â†' active_allocations[sym] = 0; reserve_allocations[sym] = 0
    NOTE: returns PROCEEDS (market value). If TP hit â†' proceeds > cost â†' pool grows. Correct.

  ENGINE CLEANUP:
    eng.capital += actual_proceeds
    [correction logged if stored_tp * qty â‰  actual_proceeds]
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

  ORPHANED ORDER CLEANUP (BUGGY â€" see Gap #1):
    try:
      open_orders = self.client.client.fetch_open_orders(  â† BUG: "client.client" doesn't exist
          self.client._to_ccxt_symbol(sym))               â† BUG: "_to_ccxt_symbol" doesn't exist
    â†' This always throws AttributeError, silently caught.
    â†' Orphaned sell orders are NOT cleaned up after TP fill.

  if bot_state == WIND_DOWN: _check_wind_down_complete()
```

**Capital accounting correctness:**
- Proceeds returned to router â†' pool grows by proceeds (includes profit)
- This is correct: profit is realized and returned to active pool
- Tracker records actual_proceeds, fee, pnl separately â€" correct for reporting

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
| `invested` | Sum of `entry_price Ã- qty` from `_last_exchange_positions` | Exchange data |
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
- `client.fetch_ticker_price(sym)` â€" one call per active coin

**File reads during status write:**
- `OUTPUT_DIR/trades.csv` â€" read once per coin (per-coin PnL) + once for aggregates = N+1 reads total

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
| `_last_rebalance_date` | Rebalance runs immediately on first cycle (minor â€" correct behavior) |
| `_regime_last_eval_date` | Regime eval runs immediately if it's midnight UTC |
| `_start_time` | Uptime resets to 0 on restart |
| `_cfgi_market`, `_cfgi_coins`, `_cfgi_last_poll` | CFGI refreshed on first cycle |
| `router.total_equity`, `router.active_pool_total`, `router.reserve_pool_total` | Recalculated from cash + allocations on next rebalance |
| `cs._last_buy_time` | Dedup guard resets â€" first buy after restart not deduped |
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
    â†' reads cycle_scanner.json  [FILE READ]
    â†' navigates: windows.30d.rankings (primary path)
    â†' enriches with trend_scores (trend_multiplier, trend_direction)
    â†' returns List[{symbol, dca_score, trend_multiplier, trend_direction}]

STEP 2: Compute equity
  _compute_equity()
    â†' client.fetch_full_balance()  [EXCHANGE API CALL]
    â†' for each coin with open position: client.fetch_ticker_price()  [EXCHANGE API CALL per coin]
    â†' equity = usdt_total + Î£(current_price Ã- eng.long_coins - eng.long_cost)
    NOTE: eng.long_coins/long_cost were overwritten by last _sync_positions_from_exchange()

STEP 3: Router rebalance
  router.rebalance_daily(scanner_data, current_equity=equity)
    â†' Updates: total_equity = equity
    â†' Updates: active_pool_total = equity Ã- 0.75  [âš ï¸ Changes from 0.90!]
    â†' Updates: reserve_pool_total = equity Ã- 0.25  [âš ï¸ Changes from 0.10!]
    â†' Updates: tier_coin_cap from EQUITY_TIER_CAPS
      $340 equity â†' 1 coin cap (falls in $100-$10K bracket)
    â†' Filter: dca_score >= 5.0 (hurdle rate)
    â†' Adjust: adjusted_score = dca_score Ã- trend_multiplier
    â†' Sort: by adjusted_score descending
    â†' Take: top N = min(qualifying, tier_coin_cap)
    â†' Cap per coin: min(100%, 20% + 80%/max(len,1)) Ã- active_pool_total
      For 1 coin: cap_pct = 1.0 â†' max 100% of active_pool_total
    â†' Weight: proportional by adjusted_score â†' allocations
    â†' Returns: {symbol: allocation_amount}

STEP 4: Apply allocations
  For new symbols not in self.coins:
    if bot_state != RUNNING: skip
    CoinState(sym, alloc)
    V14LifecycleEngine(sym, alloc, profile="high", leverage=1.0)
      â†' creates V14DCAEngine, V13SignalPack (reads candles.db)
      â†' _live_mode = True, _warmed_up = True
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
- Active pool (post-rebalance): $340 Ã- 0.75 = **$255**
- Reserve pool (post-rebalance): $340 Ã- 0.25 = **$85**
- If 1 qualifying coin: allocated = min($255, 100% cap) = **$255**

---

### 3.10 Capital Router Interaction

**Every call to the router:**

| Call Site | Method | Amount | Notes |
|-----------|--------|--------|-------|
| `__init__` | `CapitalRouter(capital=340)` | Init | active=306, reserve=34 (90/10) |
| `_do_rebalance` â†' `router.rebalance_daily()` | Internal update | N/A | Changes pools to 75/25! |
| `_execute_action` BUY | `request_capital(sym, cost, pool)` | `price Ã- qty` from engine | Layer â‰¥6 â†' reserve pool |
| `_execute_action` BUY partial/fail | `return_capital(sym, granted)` | `granted` amount | Refund on failure |
| `_execute_action` BUY balance fail | `return_capital(sym, granted)` | `granted` amount | Refund on exchange balance check fail |
| `_execute_action` BUY exchange fail | `return_capital(sym, granted)` | `granted` amount | Refund on order failure |
| `_execute_action` SELL | `return_capital(sym, actual_proceeds)` | Actual sell proceeds | Includes profit |
| `_handle_tp_fill` | `return_capital(sym, actual_proceeds)` | Actual TP fill proceeds | Includes profit |
| `_force_close_coin` | `return_capital(sym, actual_proceeds)` | Actual proceeds | |

**Accounting consistency analysis:**

1. **Initial state:** `active_pool_cash = 306` (90% of 340)
2. **After first rebalance:** `active_pool_total` recalculated as `equity Ã- 0.75`. If equity=$340 â†' `active_pool_total = 255`. BUT `active_pool_cash` is NOT adjusted here â€" only `active_pool_total` changes. The cash available may now differ from the new total. This creates an accounting inconsistency.
3. **Buy:** `active_pool_cash -= cost`; `active_allocations[sym] += cost`
4. **Sell/TP:** `active_pool_cash += proceeds`; `active_allocations[sym] = 0`; `reserve_allocations[sym] = 0`

**Potential over-return:** If a TP fill returns more than was originally requested (due to profit), `active_pool_cash` can exceed `active_pool_total`. This is logically correct (profits increase pool) but `active_pool_total` is never updated to reflect this.

**Layer pool routing:**
- Layers 1-5 â†' `active` pool
- Layer 6+ â†' `reserve` pool
- Layer count comes from `tracker._open_deals.get(key, {}).get("layers", 0) + 1` at time of request

---

### 3.11 Telegram Command Processing

**Polling:** Every 15 seconds (via `_last_tg_check` throttle).
**API:** `get_telegram_updates(offset)` â†' HTTP GET `getUpdates`
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
- `CLOSE ALL` uses engine's `long_coins` to find open positions â€" if engine state is stale before sync, may miss positions
- `_force_close_coin` uses `eng.long_coins` for sell qty (not exchange position), which is acceptable since exchange sync runs at top of each cycle
- No `STATUS` command to request manual status
- No `HELP` command listing available commands
- No command acknowledgment for unknown commands

---

## 4. Sections Absorbed Into Architecture Doc

The following sections have been absorbed into `V14PM_SYSTEM_ARCHITECTURE.md` v1.6 (2026-03-21)
as the authoritative, maintained reference. This file retains Â§1â€"Â§3 (module overview, class
inventory, and data flow traces) as a point-in-time implementation snapshot.

| Section | Content | Now In Architecture Doc |
|---------|---------|------------------------|
| Â§4 External Dependencies | All exchange API calls, file I/O, DB queries, HTTP calls | **Â§8.6 External API Dependencies** |
| Â§5 Gap Analysis | 13 gaps with descriptions and suggested fixes | **Â§18 Code Audit & Gap Analysis (2026-03-21)** |
| Â§6 Data Source Map | Variable-to-source mapping for all runtime state | **Â§6.8.7 Data Source Map** |
| Â§7 Summary of Critical Findings | P1/P2/P3 gap status table | **Â§18.1 Gap Summary Table** |

> See `V14PM_SYSTEM_ARCHITECTURE.md` Â§8.6, Â§6.8.7, and Â§18 for the current, maintained versions
> of these sections. Gap statuses reflect fixes applied during the 2026-03-21 exchange-as-truth
> refactor session.

---

*Point-in-time code audit. All line numbers and behavioral descriptions are based on direct
code analysis of the files listed above, as of 2026-03-21.*
*Gap fixes applied 2026-03-21 by exchange-as-truth refactor session.*
*For current architecture and design decisions, see [`V14PM_SYSTEM_ARCHITECTURE.md`](V14PM_SYSTEM_ARCHITECTURE.md).*

<!-- REMOVED SECTIONS (now in architecture doc):
  s4 External Dependencies -> V14PM_SYSTEM_ARCHITECTURE.md s8.6
  s5 Gap Analysis -> V14PM_SYSTEM_ARCHITECTURE.md s18
  s6 Data Source Map -> V14PM_SYSTEM_ARCHITECTURE.md s6.8.7
  s7 Summary -> V14PM_SYSTEM_ARCHITECTURE.md s18.1
-->
