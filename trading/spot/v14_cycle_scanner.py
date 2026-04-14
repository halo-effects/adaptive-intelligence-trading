"""
V14 DCA Cycle Scanner — Bear Market Capital Velocity Optimizer

Scores coins by DCA cycle efficiency: how fast they complete profitable cycles,
how much capital gets trapped, and how deep the drawdowns go.

Scoring: DCA Score = Realized_PnL × (1 - MaxDD%) × Capital_Freedom / 100
"""

import sys
import os
import io
import json
import sqlite3
import logging
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# Force UTF-8 stdout on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logger = logging.getLogger("v14_cycle_scanner")

# ─── DCA Parameters (V14 High Profile) ─────────────────────────────────────

BO_PCT = 0.40          # 40% base order of DCA allocation
SO_DEV = 0.015         # 1.5% safety order price deviation
SO_STEP_MULT = 1.5     # Price step multiplier (each SO further apart)
SO_VOL_MULT = 1.5      # Volume multiplier (each SO bigger)
MAX_LAYERS = 12
TP_PCT = 0.015         # 1.5% take profit from avg entry
TAKER_FEE = 0.00025    # Hyperliquid taker fee
CAPITAL = 10_000.0     # Capital per coin
DCA_ALLOC = 0.90       # 90% allocated to DCA

# Minimum months of 1h candle history to appear on the published rankings.
# Coins below this threshold are still scanned (for internal tracking) but
# flagged as immature and excluded from the dashboard feed.
MIN_HISTORY_MONTHS = 6

# Full Hyperliquid quality perp universe + ASTER (Aster exchange live bot).
# Format: preferred symbol as found in candles.db.  The scanner will also
# try the other quote (USDT↔USDC) if the primary isn't found.
COINS = [
    # --- Established (pre-2024) ---
    'BTC/USDC',   'ETH/USDC',   'SOL/USDC',   'XRP/USDT',   'LINK/USDT',
    'DOGE/USDT',  'ADA/USDT',   'LTC/USDT',   'AVAX/USDT',  'DOT/USDT',
    'UNI/USDT',   'ATOM/USDT',  'NEAR/USDT',  'HBAR/USDT',  'INJ/USDT',
    'FIL/USDT',   'RUNE/USDT',  'CRV/USDT',   'SNX/USDT',   'COMP/USDT',
    'MKR/USDT',   'ENS/USDT',   'DYDX/USDT',  'LDO/USDT',   'ARB/USDT',
    'OP/USDT',    'STX/USDT',   'SEI/USDT',    'RENDER/USDT',
    # --- 2024 launches ---
    'SUI/USDT',   'FET/USDT',   'TAO/USDT',   'TON/USDT',   'JUP/USDT',
    'KAS/USDT',   'PENDLE/USDT','PYTH/USDT',  'TIA/USDT',   'ONDO/USDT',
    'ENA/USDT',   'EIGEN/USDT', 'W/USDT',     'ZRO/USDT',
    # --- Mid-cycle 2025 (OK per Brett — launched before bear) ---
    'HYPE/USDC',  'ASTER/USDT',
    # --- AAVE (established but listed separately for clarity) ---
    'AAVE/USDT',
]

# ─── Data Paths ─────────────────────────────────────────────────────────────

WORKSPACE = Path(__file__).resolve().parent.parent.parent
DB_PATH = Path(os.environ.get("AIT_CANDLES_DB", str(WORKSPACE / "trading" / "spot" / "data" / "candles.db")))
OUTPUT_PATH = WORKSPACE / "docs" / "data" / "v14" / "cycle_scanner.json"
SCORE_HISTORY_PATH = WORKSPACE / "trading" / "spot" / "data" / "score_history.json"


def load_candles(conn: sqlite3.Connection, symbol: str, start_ms: int, end_ms: int) -> list[tuple]:
    """Load 1h candles for a symbol within a time range, sorted by timestamp."""
    cursor = conn.execute(
        "SELECT timestamp, open, high, low, close, volume FROM candles "
        "WHERE symbol = ? AND timeframe = '1h' AND timestamp >= ? AND timestamp <= ? "
        "ORDER BY timestamp",
        (symbol, start_ms, end_ms)
    )
    return cursor.fetchall()


def run_dca_sim(candles: list[tuple], symbol: str, window: str) -> dict:
    """
    Run DCA simulation on a series of 1h candles.

    Each deal:
    1. Open base order at candle open price
    2. Safety orders placed at geometric deviation from entry
    3. TP = avg_entry * (1 + TP_PCT) after fees
    4. On TP hit: close, bank PnL, start new deal next candle
    5. On SO hit: add layer, recalculate weighted avg entry
    """
    result = {
        "symbol": symbol,
        "coin": symbol.split("/")[0],
        "window": window,
        "candles_used": len(candles),
        "deals_completed": 0,
        "deals_per_week": 0.0,
        "avg_cycle_hours": 0.0,
        "realized_pnl": 0.0,
        "avg_pnl_per_deal": 0.0,
        "max_drawdown_pct": 0.0,
        "open_layers": 0,
        "unrealized_pnl": 0.0,
        "net_return_pct": 0.0,
        "capital_freedom": 1.0,
        "dca_score": 0.0,
        "win_rate": 0.0,
    }

    if len(candles) < 2:
        return result

    alloc = CAPITAL * DCA_ALLOC  # $9,000

    # Pre-compute SO grid: for layer i (0-indexed), what's the volume?
    # Layer 0 = base order, layer 1+ = safety orders
    # BO volume = alloc * BO_PCT
    bo_size = alloc * BO_PCT  # $3,600

    # SO sizes: SO_1 = bo_size * 1.0, SO_2 = SO_1 * SO_VOL_MULT, etc.
    # Actually in standard 3commas-style: SO base = BO * some ratio
    # But the spec says BO_PCT=0.40, so BO=$3600 of $9000
    # Remaining $5400 for SOs. Let's compute SO sizes with geometric scaling.
    # SO_i = base_so * SO_VOL_MULT^(i-1)
    # Total SOs = base_so * (SO_VOL_MULT^n - 1) / (SO_VOL_MULT - 1) for n SOs
    # We'll just cap at available cash

    # Track deals
    deals_pnl = []
    deals_hours = []

    # State
    in_position = False
    layers = 0
    entries = []  # list of (price, qty, cost) for weighted avg
    total_qty = 0.0
    total_cost = 0.0
    avg_entry = 0.0
    tp_price = 0.0
    so_prices = []  # pre-computed SO trigger prices
    deal_start_ms = 0
    cash = alloc
    cumulative_pnl = 0.0

    # Drawdown tracking
    peak_equity = alloc
    max_dd = 0.0

    def compute_so_grid(entry_price: float) -> list[float]:
        """Compute SO trigger prices from the entry price."""
        prices = []
        p = entry_price
        for i in range(MAX_LAYERS):
            dev = SO_DEV * (SO_STEP_MULT ** i)
            p = p * (1 - dev)
            prices.append(p)
        return prices

    def get_so_size(layer_idx: int) -> float:
        """Get dollar size for safety order at layer_idx (0-indexed from first SO).
        First SO is same size as BO, then scales by SO_VOL_MULT."""
        # SO base = remaining capital / estimated total SO weight
        # This ensures capital is allocated proportionally across layers
        base_so = bo_size * 0.5  # First SO = half of BO
        return base_so * (SO_VOL_MULT ** layer_idx)

    def open_deal(price: float, ts: int):
        nonlocal in_position, layers, entries, total_qty, total_cost
        nonlocal avg_entry, tp_price, so_prices, deal_start_ms, cash

        order_cost = min(bo_size, cash)
        if order_cost < 1.0:
            return False

        fee = order_cost * TAKER_FEE
        qty = (order_cost - fee) / price

        entries = [(price, qty, order_cost)]
        total_qty = qty
        total_cost = order_cost
        avg_entry = total_cost / total_qty
        tp_price = avg_entry * (1 + TP_PCT)
        so_prices = compute_so_grid(price)
        layers = 1
        deal_start_ms = ts
        cash -= order_cost
        in_position = True
        return True

    def add_so(layer_idx: int, price: float):
        """Add safety order at given layer. Returns False if no cash."""
        nonlocal layers, total_qty, total_cost, avg_entry, tp_price, cash

        so_cost = get_so_size(layer_idx)
        so_cost = min(so_cost, cash)
        if so_cost < 1.0:
            return False

        fee = so_cost * TAKER_FEE
        qty = (so_cost - fee) / price

        entries.append((price, qty, so_cost))
        total_qty += qty
        total_cost += so_cost
        avg_entry = total_cost / total_qty
        tp_price = avg_entry * (1 + TP_PCT)
        layers += 1
        cash -= so_cost
        return True

    def close_deal(exit_price: float, ts: int):
        nonlocal in_position, cash, cumulative_pnl, total_qty, total_cost

        gross = total_qty * exit_price
        fee = gross * TAKER_FEE
        net = gross - fee
        pnl = net - total_cost
        duration_h = max((ts - deal_start_ms) / 3_600_000, 1.0)

        deals_pnl.append(pnl)
        deals_hours.append(duration_h)
        cumulative_pnl += pnl
        cash += net
        in_position = False
        total_qty = 0.0
        total_cost = 0.0

    # Main loop
    for i, (ts, o, h, l, c, vol) in enumerate(candles):
        if not in_position:
            if not open_deal(o, ts):
                # No cash - shouldn't happen after a close, but handle it
                continue

        # Check TP first (optimistic: if high >= tp, we got filled)
        if h >= tp_price:
            close_deal(tp_price, ts)
            # Track equity after close
            equity = cash
            if equity > peak_equity:
                peak_equity = equity
            dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
            if dd > max_dd:
                max_dd = dd
            continue

        # Check safety orders (low might trigger one or more)
        so_added = True
        while so_added and layers <= MAX_LAYERS:
            so_idx = layers - 1  # 0-indexed SO number
            if so_idx >= len(so_prices):
                break
            if l <= so_prices[so_idx]:
                so_added = add_so(so_idx, so_prices[so_idx])
            else:
                break

        # After adding SOs, check if TP was hit this candle (price bounced)
        if in_position and h >= tp_price:
            close_deal(tp_price, ts)
            equity = cash
            if equity > peak_equity:
                peak_equity = equity
            dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
            if dd > max_dd:
                max_dd = dd
            continue

        # Track drawdown with open position valued at close
        if in_position:
            position_value = total_qty * c
            equity = cash + position_value
        else:
            equity = cash
        if equity > peak_equity:
            peak_equity = equity
        dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
        if dd > max_dd:
            max_dd = dd

    # Compute results
    total_hours = (candles[-1][0] - candles[0][0]) / 3_600_000 if len(candles) > 1 else 1
    total_weeks = max(total_hours / 168, 0.01)
    n_deals = len(deals_pnl)

    result["deals_completed"] = n_deals
    result["realized_pnl"] = round(sum(deals_pnl), 2)
    result["max_drawdown_pct"] = round(max_dd * 100, 2)

    if n_deals > 0:
        result["deals_per_week"] = round(n_deals / total_weeks, 1)
        result["avg_cycle_hours"] = round(sum(deals_hours) / n_deals, 1)
        result["avg_pnl_per_deal"] = round(result["realized_pnl"] / n_deals, 2)
        winners = sum(1 for p in deals_pnl if p > 0)
        result["win_rate"] = round(winners / n_deals * 100, 1)

    result["open_layers"] = layers if in_position else 0

    # Unrealized P&L
    if in_position:
        last_close = candles[-1][4]
        gross = total_qty * last_close
        fee = gross * TAKER_FEE
        result["unrealized_pnl"] = round(gross - fee - total_cost, 2)

    # Net return
    total_pnl = result["realized_pnl"] + result["unrealized_pnl"]
    result["net_return_pct"] = round(total_pnl / alloc * 100, 2)

    # Capital freedom
    result["capital_freedom"] = round(1 - (result["open_layers"] / 24), 4)

    # DCA Score
    result["dca_score"] = round(
        result["realized_pnl"] * (1 - max_dd) * result["capital_freedom"] / 100,
        2
    )

    return result


def get_window_range(window: str, now_ms: int) -> tuple[int, int]:
    """Get (start_ms, end_ms) for a named window."""
    if window == "7d":
        return now_ms - 7 * 24 * 3600 * 1000, now_ms
    elif window == "14d":
        return now_ms - 14 * 24 * 3600 * 1000, now_ms
    elif window == "30d":
        return now_ms - 30 * 24 * 3600 * 1000, now_ms
    elif window == "bear":
        bear_start = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
        return bear_start, now_ms
    else:
        raise ValueError(f"Unknown window: {window}")


def _resolve_symbol(conn: sqlite3.Connection, symbol: str) -> tuple[str, int]:
    """Try the given symbol, then flip USDT↔USDC. Returns (resolved_symbol, candle_count)."""
    for sym in [symbol, _alt_quote(symbol)]:
        row = conn.execute(
            "SELECT COUNT(*) FROM candles WHERE symbol = ? AND timeframe = '1h'", (sym,)
        ).fetchone()
        if row[0] > 0:
            return sym, row[0]
    return symbol, 0


def _alt_quote(symbol: str) -> str:
    """Flip USDT↔USDC in a symbol."""
    if '/USDT' in symbol:
        return symbol.replace('/USDT', '/USDC')
    elif '/USDC' in symbol:
        return symbol.replace('/USDC', '/USDT')
    return symbol


def _history_months(conn: sqlite3.Connection, symbol: str) -> float:
    """Return months of 1h candle history for a symbol."""
    row = conn.execute(
        "SELECT MIN(timestamp), MAX(timestamp) FROM candles "
        "WHERE symbol = ? AND timeframe = '1h'", (symbol,)
    ).fetchone()
    if row[0] is None:
        return 0.0
    return (row[1] - row[0]) / (1000 * 60 * 60 * 24 * 30.44)


def scan_all(coins: list[str], windows: list[str], top_n: Optional[int] = None, as_of_ms: Optional[int] = None) -> dict:
    """Run full scan across all coins and windows."""
    now_ms = as_of_ms or int(datetime.now(timezone.utc).timestamp() * 1000)

    conn = sqlite3.connect(str(DB_PATH))

    results: dict[str, list[dict]] = {w: [] for w in windows}
    immature_results: dict[str, list[dict]] = {w: [] for w in windows}
    coins_scanned = 0
    coins_immature = 0

    for symbol in coins:
        resolved, count = _resolve_symbol(conn, symbol)
        if count == 0:
            logger.warning(f"No candle data for {symbol}, skipping")
            continue

        coins_scanned += 1
        short_name = resolved.split("/")[0]
        months = _history_months(conn, resolved)
        mature = months >= MIN_HISTORY_MONTHS

        if not mature:
            coins_immature += 1
            logger.info(f"Scanning {short_name}... ({months:.1f}mo — immature, will track internally)")
        else:
            logger.info(f"Scanning {short_name}... ({months:.1f}mo)")

        symbol = resolved  # use the resolved symbol from here

        for window in windows:
            start_ms, end_ms = get_window_range(window, now_ms)
            candles = load_candles(conn, symbol, start_ms, end_ms)

            if len(candles) < 10:
                logger.warning(f"  {window}: only {len(candles)} candles for {short_name}, skipping")
                continue

            sim = run_dca_sim(candles, symbol, window)
            sim["mature"] = mature
            sim["history_months"] = round(months, 1)
            if mature:
                results[window].append(sim)
            else:
                immature_results[window].append(sim)
            logger.debug(
                f"  {window}: {sim['deals_completed']} deals, "
                f"${sim['realized_pnl']:+.0f}, DD {sim['max_drawdown_pct']:.1f}%, "
                f"Score {sim['dca_score']:.1f}"
            )

    conn.close()

    # Sort each window by dca_score descending
    for w in windows:
        results[w].sort(key=lambda r: r["dca_score"], reverse=True)
        immature_results[w].sort(key=lambda r: r["dca_score"], reverse=True)

    # Build output
    output = {
        "generated_at": datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).isoformat(),
        "windows": {},
        "coins_scanned": coins_scanned,
        "coins_mature": coins_scanned - coins_immature,
        "coins_immature": coins_immature,
        "min_history_months": MIN_HISTORY_MONTHS,
        "top_picks": {},
    }

    best_window = "bear" if "bear" in windows else windows[-1]
    all_results = results.get(best_window, [])

    if all_results:
        output["top_picks"] = {
            "fastest_cycler": max(all_results, key=lambda r: r["deals_per_week"])["coin"],
            "best_score": all_results[0]["coin"],
            "lowest_dd": min(all_results, key=lambda r: r["max_drawdown_pct"])["coin"],
            "most_capital_free": max(all_results, key=lambda r: r["capital_freedom"])["coin"],
        }

    for w in windows:
        # Published rankings = mature coins only
        rankings = results[w]
        if top_n:
            rankings = rankings[:top_n]

        window_data = {
            "rankings": [
                {**r, "rank": i + 1}
                for i, r in enumerate(rankings)
            ]
        }

        # Immature coins tracked but flagged separately
        if immature_results[w]:
            window_data["immature"] = [
                {**r, "rank": i + 1}
                for i, r in enumerate(immature_results[w])
            ]

        if w == "bear":
            window_data["start_date"] = "2026-01-01"
        output["windows"][w] = window_data

    return output


def print_table(output: dict, window: str, top_n: Optional[int] = None):
    """Print a formatted ranking table for a window."""
    if window not in output["windows"]:
        print(f"No data for window: {window}")
        return

    rankings = output["windows"][window]["rankings"]
    if top_n:
        rankings = rankings[:top_n]

    print(f"\n{'='*90}")
    print(f"  DCA Cycle Rankings — {window} window")
    print(f"{'='*90}")
    print(f"{'#':>3} {'Coin':<8} {'Deals':>5} {'D/Wk':>5} {'AvgHrs':>7} "
          f"{'Realized':>10} {'MaxDD%':>7} {'Layers':>6} {'CapFree':>7} {'Score':>8} {'WinR':>5}")
    print(f"{'-'*90}")

    for r in rankings:
        print(
            f"{r['rank']:>3} {r['coin']:<8} {r['deals_completed']:>5} "
            f"{r['deals_per_week']:>5.1f} {r['avg_cycle_hours']:>7.1f} "
            f"${r['realized_pnl']:>+9.0f} {r['max_drawdown_pct']:>6.1f}% "
            f"{r['open_layers']:>6} {r['capital_freedom']:>6.2f} "
            f"{r['dca_score']:>8.1f} {r['win_rate']:>4.0f}%"
        )

    print(f"{'-'*90}")

    # Show immature coins if any
    immature = output["windows"][window].get("immature", [])
    if immature:
        print(f"\n  Immature coins (< {output.get('min_history_months', MIN_HISTORY_MONTHS)}mo history — tracking only):")
        for r in immature:
            mo = r.get('history_months', '?')
            print(
                f"    {r['coin']:<8} {r['deals_completed']:>5} deals  "
                f"{r['deals_per_week']:>5.1f}/wk  "
                f"Score {r['dca_score']:>6.1f}  "
                f"({mo}mo data)"
            )
        print()


def append_score_history(output: dict):
    """Append current scan scores to the rolling history file.

    History format:
    {
        "snapshots": [
            {
                "timestamp": "2026-03-05T12:00:00+00:00",
                "scores": { "HBAR": 85.2, "SOL": 70.1, ... }
            },
            ...
        ]
    }

    Keeps up to 180 days (~6 months) of daily snapshots.
    """
    MAX_SNAPSHOTS = 180

    history = {"snapshots": []}
    if SCORE_HISTORY_PATH.exists():
        try:
            with open(SCORE_HISTORY_PATH, "r", encoding="utf-8") as f:
                history = json.load(f)
        except (json.JSONDecodeError, KeyError):
            logger.warning("Corrupt score_history.json, starting fresh")
            history = {"snapshots": []}

    # Use the "bear" window if available (longest backtest), else longest available
    best_window = "bear"
    if best_window not in output.get("windows", {}):
        available = list(output.get("windows", {}).keys())
        best_window = available[-1] if available else None

    if not best_window:
        return

    rankings = output["windows"][best_window].get("rankings", [])
    immature = output["windows"][best_window].get("immature", [])

    scores = {}
    for r in rankings + immature:
        coin = r.get("coin", r.get("symbol", "").split("/")[0])
        scores[coin] = {
            "dca_score": r.get("dca_score", 0.0),
            "deals_per_week": r.get("deals_per_week", 0.0),
            "max_drawdown_pct": r.get("max_drawdown_pct", 0.0),
            "realized_pnl": r.get("realized_pnl", 0.0),
            "capital_freedom": r.get("capital_freedom", 1.0),
            "mature": r.get("mature", False),
        }

    snapshot = {
        "timestamp": output.get("generated_at", datetime.now(timezone.utc).isoformat()),
        "window": best_window,
        "scores": scores,
    }

    # De-duplicate: if last snapshot is from the same calendar day, replace it
    today = snapshot["timestamp"][:10]
    if history["snapshots"]:
        last_day = history["snapshots"][-1]["timestamp"][:10]
        if last_day == today:
            history["snapshots"][-1] = snapshot
        else:
            history["snapshots"].append(snapshot)
    else:
        history["snapshots"].append(snapshot)

    # Trim to MAX_SNAPSHOTS
    if len(history["snapshots"]) > MAX_SNAPSHOTS:
        history["snapshots"] = history["snapshots"][-MAX_SNAPSHOTS:]

    SCORE_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SCORE_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    logger.info(f"Score history updated ({len(history['snapshots'])} snapshots) → {SCORE_HISTORY_PATH}")


def compute_trend_scores(history_path: Path = SCORE_HISTORY_PATH) -> dict:
    """Compute trend multipliers from score history.

    Returns:
        { "HBAR": { "trend_7d": 1.2, "trend_14d": 1.1, "trend_30d": 0.9,
                     "trend_multiplier": 1.15, "direction": "accelerating" }, ... }
    """
    if not history_path.exists():
        return {}

    with open(history_path, "r", encoding="utf-8") as f:
        history = json.load(f)

    snapshots = history.get("snapshots", [])
    if len(snapshots) < 3:
        logger.info(f"Need ≥3 snapshots for trend (have {len(snapshots)}), skipping trend calc")
        return {}

    # Build time series per coin: [(days_ago, score), ...]
    latest_ts = snapshots[-1]["timestamp"]
    latest_dt = datetime.fromisoformat(latest_ts)

    coin_series: dict[str, list[tuple[float, float]]] = {}
    for snap in snapshots:
        snap_dt = datetime.fromisoformat(snap["timestamp"])
        days_ago = (latest_dt - snap_dt).total_seconds() / 86400
        for coin, data in snap.get("scores", {}).items():
            score = data["dca_score"] if isinstance(data, dict) else data
            coin_series.setdefault(coin, []).append((days_ago, score))

    trends = {}
    for coin, series in coin_series.items():
        series.sort(key=lambda x: x[0], reverse=True)  # oldest first (highest days_ago)

        def slope_over_window(window_days: int) -> Optional[float]:
            points = [(d, s) for d, s in series if d <= window_days]
            if len(points) < 2:
                return None
            # Simple: (latest score - earliest score in window) / earliest score
            earliest = points[0][1]  # oldest in window
            latest = points[-1][1]   # most recent
            if abs(earliest) < 0.01:
                return 0.0
            return (latest - earliest) / abs(earliest)

        t7 = slope_over_window(7)
        t14 = slope_over_window(14)
        t30 = slope_over_window(30)

        # Composite trend multiplier: weighted average of available windows
        weights = []
        if t7 is not None:
            weights.append((t7, 0.5))   # 7d most recent, highest weight
        if t14 is not None:
            weights.append((t14, 0.3))
        if t30 is not None:
            weights.append((t30, 0.2))

        if not weights:
            continue

        weighted_change = sum(w * s for s, w in weights) / sum(w for _, w in weights)

        # Convert to multiplier: +20% change → 1.2x, -30% change → 0.7x
        # Clamp between 0.3 and 1.5 to avoid extreme swings
        multiplier = max(0.3, min(1.5, 1.0 + weighted_change))

        if weighted_change > 0.05:
            direction = "accelerating"
        elif weighted_change < -0.05:
            direction = "declining"
        else:
            direction = "stable"

        trends[coin] = {
            "trend_7d": round(t7, 3) if t7 is not None else None,
            "trend_14d": round(t14, 3) if t14 is not None else None,
            "trend_30d": round(t30, 3) if t30 is not None else None,
            "trend_multiplier": round(multiplier, 3),
            "direction": direction,
        }

    return trends


def send_telegram_summary(output: dict):
    """Send scan summary to Telegram via API."""
    token = os.environ.get("AIT_TG_TOKEN")
    chat_id = os.environ.get("AIT_TG_CHAT_ID")

    if not token or not chat_id:
        logger.info("Telegram env vars not set, skipping notification")
        return

    windows_available = list(output["windows"].keys())
    window_labels = "/".join(windows_available)

    # Use 30d window (matches dashboard default), fall back to bear then last available
    best_window = "30d" if "30d" in windows_available else ("bear" if "bear" in windows_available else windows_available[-1])
    rankings = output["windows"][best_window]["rankings"]

    # Apply trend multipliers to compute Trade Score (Base DCA Score × Trend Mult)
    trend_scores = output.get("trend_scores", {})
    scored_rankings = []
    for r in rankings:
        coin = r.get("coin", r.get("symbol", "").split("/")[0])
        dca_score = r.get("dca_score", 0.0)
        trend_data = trend_scores.get(coin, {})
        trend_mult = trend_data.get("trend_multiplier", 1.0)
        trade_score = dca_score * trend_mult
        scored_rankings.append({**r, "trend_mult": trend_mult, "trade_score": trade_score})

    # Sort by Trade Score (matches dashboard Opportunity Table)
    scored_rankings.sort(key=lambda x: x["trade_score"], reverse=True)
    top5 = scored_rankings[:5]

    lines = [f"\U0001f4ca [SCANNER] DCA Cycle Rankings ({window_labels})", ""]
    lines.append(f"Top 5 by Trade Score ({best_window}):")

    for i, r in enumerate(top5, 1):
        trend_arrow = "\u2197" if r["trend_mult"] > 1.0 else ("\u2198" if r["trend_mult"] < 1.0 else "\u2192")
        lines.append(
            f"{i}. {r['coin']} \u2014 {r['deals_per_week']:.1f} d/wk, "
            f"${r['realized_pnl']:+,.0f}, DD {r['max_drawdown_pct']:.0f}%, "
            f"Trade {r['trade_score']:.1f} (Base {r['dca_score']:.1f} \u00d7 {r['trend_mult']:.1f}x {trend_arrow})"
        )

    total_deals = sum(
        r["deals_completed"]
        for r in output["windows"][best_window]["rankings"]
    )
    lines.append("")
    lines.append(
        f"Capital velocity: {total_deals} deals across "
        f"{output['coins_scanned']} coins"
    )

    # Derive picks from the Trade Score-ranked list (same window, same ranking)
    if scored_rankings:
        best_trade = scored_rankings[0]["coin"]
        fastest = max(scored_rankings, key=lambda r: r.get("deals_per_week", 0))["coin"]
        safest = min(scored_rankings, key=lambda r: r.get("max_drawdown_pct", 100))["coin"]
        lines.append(f"\U0001f3c6 Best: {best_trade} | "
                     f"\u26a1 Fastest: {fastest} | "
                     f"\U0001f6e1\ufe0f Safest: {safest}")

    message = "\n".join(lines)

    try:
        import urllib.request
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = json.dumps({
            "chat_id": chat_id,
            "text": message,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                logger.info("Telegram notification sent")
            else:
                logger.warning(f"Telegram API returned {resp.status}")
    except Exception as e:
        logger.warning(f"Failed to send Telegram notification: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="V14 DCA Cycle Scanner \u2014 Bear Market Capital Velocity Optimizer"
    )
    parser.add_argument("--window", choices=["7d", "14d", "30d", "bear"],
                        help="Run only a single time window")
    parser.add_argument("--coin", type=str, help="Scan a single coin (e.g. HYPE)")
    parser.add_argument("--top", type=int, help="Show only top N results")
    parser.add_argument("--no-telegram", action="store_true", help="Skip Telegram notification")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--as-of", type=str, help="Run as if date is YYYY-MM-DD (for historical snapshots)")
    parser.add_argument("--backfill-history", type=int, metavar="DAYS",
                        help="Backfill N days of score history snapshots (runs scanner N times with past dates)")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.window:
        windows = [args.window]
    else:
        windows = ["7d", "14d", "30d", "bear"]

    if args.coin:
        coin_upper = args.coin.upper()
        matching = [c for c in COINS if c.startswith(coin_upper + "/")]
        if not matching:
            logger.error(f"Coin '{args.coin}' not found in universe. Available: {[c.split('/')[0] for c in COINS]}")
            sys.exit(1)
        coins = matching
    else:
        coins = COINS

    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        sys.exit(1)

    logger.info(f"V14 DCA Cycle Scanner \u2014 {len(coins)} coins, {len(windows)} windows")
    logger.info(f"Parameters: BO={BO_PCT:.0%}, SO_DEV={SO_DEV:.1%}, "
                f"SO_STEP_MULT={SO_STEP_MULT}, SO_VOL_MULT={SO_VOL_MULT}, "
                f"TP={TP_PCT:.1%}, MAX_LAYERS={MAX_LAYERS}")

    # Handle --backfill-history: run scanner for N past days to build trend history
    if args.backfill_history:
        days = args.backfill_history
        logger.info(f"Backfilling {days} days of score history...")
        for d in range(days, 0, -1):
            past_dt = datetime.now(timezone.utc) - timedelta(days=d)
            past_ms = int(past_dt.timestamp() * 1000)
            logger.info(f"  Backfill: scanning as-of {past_dt.strftime('%Y-%m-%d')}...")
            hist_output = scan_all(coins, ["30d"], as_of_ms=past_ms)
            append_score_history(hist_output)
        logger.info(f"Backfill complete. Running current scan now...")

    # Determine as-of timestamp
    as_of_ms = None
    if args.as_of:
        as_of_dt = datetime.strptime(args.as_of, "%Y-%m-%d").replace(
            hour=18, tzinfo=timezone.utc
        )
        as_of_ms = int(as_of_dt.timestamp() * 1000)
        logger.info(f"Running as-of {args.as_of} (ts={as_of_ms})")

    output = scan_all(coins, windows, top_n=args.top, as_of_ms=as_of_ms)

    for w in windows:
        print_table(output, w, top_n=args.top)

    if output.get("top_picks"):
        tp = output["top_picks"]
        print(f"\n\U0001f3c6 Top Picks:")
        print(f"  Best Score:     {tp.get('best_score', 'N/A')}")
        print(f"  Fastest Cycler: {tp.get('fastest_cycler', 'N/A')}")
        print(f"  Lowest DD:      {tp.get('lowest_dd', 'N/A')}")
        print(f"  Most Cap Free:  {tp.get('most_capital_free', 'N/A')}")

    # Save score history for trend analysis
    append_score_history(output)

    # Compute and display trend scores if history is available
    trends = compute_trend_scores()
    if trends:
        output["trend_scores"] = trends
        print(f"\n{'='*70}")
        print(f"  DCA Trend Scores (score momentum)")
        print(f"{'='*70}")
        print(f"{'Coin':<8} {'Direction':<14} {'7d':>8} {'14d':>8} {'30d':>8} {'Mult':>6}")
        print(f"{'-'*70}")
        for coin in sorted(trends.keys(), key=lambda c: trends[c]["trend_multiplier"], reverse=True):
            t = trends[coin]
            t7 = f"{t['trend_7d']:+.1%}" if t['trend_7d'] is not None else "—"
            t14 = f"{t['trend_14d']:+.1%}" if t['trend_14d'] is not None else "—"
            t30 = f"{t['trend_30d']:+.1%}" if t['trend_30d'] is not None else "—"
            print(f"{coin:<8} {t['direction']:<14} {t7:>8} {t14:>8} {t30:>8} {t['trend_multiplier']:>5.2f}x")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    logger.info(f"Results saved to {OUTPUT_PATH}")

    if not args.no_telegram:
        send_telegram_summary(output)


if __name__ == "__main__":
    main()
