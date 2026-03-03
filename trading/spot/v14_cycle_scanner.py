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
from dataclasses import dataclass, field, asdict
from typing import Optional

# Force UTF-8 stdout on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logger = logging.getLogger("v14_cycle_scanner")

# ─── DCA Parameters (V14 High Profile) ─────────────────────────────────────

BO_PCT = 0.40          # 40% base order of available cash
SO_DEV = 0.015         # 1.5% safety order deviation
SO_MULT = 1.5          # Volume scale multiplier per layer
MAX_LAYERS = 12
TP_PCT = 0.015         # 1.5% take profit
TAKER_FEE = 0.00025    # Hyperliquid taker fee
CAPITAL = 10_000.0     # Capital per coin
DCA_ALLOC = 0.90       # 90% allocated to DCA

# Coin universe
COINS = [
    'HYPE/USDC', 'INJ/USDT', 'ASTER/USDT', 'DOT/USDT', 'FIL/USDT',
    'CRV/USDT', 'HBAR/USDT', 'ATOM/USDT', 'AAVE/USDT', 'UNI/USDT',
    'NEAR/USDT', 'ADA/USDT', 'SUI/USDT', 'LINK/USDT', 'SOL/USDT',
    'ETH/USDT', 'XRP/USDT', 'BTC/USDT', 'DOGE/USDT', 'SEI/USDT',
    'AVAX/USDT', 'LTC/USDT', 'RUNE/USDT',
]

# ─── Data Paths ─────────────────────────────────────────────────────────────

WORKSPACE = Path(__file__).resolve().parent.parent.parent
DB_PATH = WORKSPACE / "trading" / "spot" / "data" / "candles.db"
OUTPUT_PATH = WORKSPACE / "docs" / "data" / "v14" / "cycle_scanner.json"


@dataclass
class DealResult:
    """Result of a single completed DCA deal."""
    entry_time_ms: int
    exit_time_ms: int
    layers: int
    invested: float
    pnl: float
    duration_hours: float


@dataclass
class SimResult:
    """Full simulation result for a coin on a time window."""
    symbol: str
    window: str
    deals_completed: int = 0
    deals_per_week: float = 0.0
    avg_cycle_hours: float = 0.0
    realized_pnl: float = 0.0
    avg_pnl_per_deal: float = 0.0
    max_drawdown_pct: float = 0.0
    open_layers: int = 0
    unrealized_pnl: float = 0.0
    net_return_pct: float = 0.0
    capital_freedom: float = 1.0
    dca_score: float = 0.0
    win_rate: float = 0.0
    candles_used: int = 0


def load_candles(conn: sqlite3.Connection, symbol: str, start_ms: int, end_ms: int) -> list[tuple]:
    """Load 1h candles for a symbol within a time range, sorted by timestamp."""
    cursor = conn.execute(
        "SELECT timestamp, open, high, low, close, volume FROM candles "
        "WHERE symbol = ? AND timeframe = '1h' AND timestamp >= ? AND timestamp <= ? "
        "ORDER BY timestamp",
        (symbol, start_ms, end_ms)
    )
    return cursor.fetchall()


def run_dca_sim(candles: list[tuple], symbol: str, window: str) -> SimResult:
    """
    Run DCA simulation on a series of 1h candles.

    Logic:
    1. Start with $10K capital, 90% DCA allocation
    2. Place base order (BO_PCT of cash) at first candle open
    3. Each candle: check TP hit (high >= tp), check SO hit (low <= next_so)
    4. On TP: close position, bank PnL, reset for next deal
    5. On SO: add layer if < MAX_LAYERS, recalculate avg entry + TP
    """
    result = SimResult(symbol=symbol, window=window, candles_used=len(candles))

    if len(candles) < 2:
        return result

    total_capital = CAPITAL * DCA_ALLOC  # $9,000 for DCA
    cash = total_capital
    deals: list[DealResult] = []

    # Position state
    in_position = False
    avg_entry = 0.0
    position_qty = 0.0
    position_cost = 0.0  # total $ invested in current deal
    layers = 0
    last_so_price = 0.0
    tp_price = 0.0
    deal_start_ms = 0
    peak_equity = total_capital
    max_dd = 0.0

    # Pre-calculate SO volume for each layer (geometric)
    # Layer 0 = base order, layer 1+ = safety orders
    def get_so_volume(layer_num: int) -> float:
        """Get the dollar amount for a safety order at given layer."""
        base_so = total_capital * BO_PCT * 0.5  # SO starts at half of BO
        return base_so * (SO_MULT ** (layer_num - 1))

    def open_base_order(price: float, ts: int):
        nonlocal in_position, avg_entry, position_qty, position_cost
        nonlocal layers, last_so_price, tp_price, deal_start_ms, cash

        order_size = min(cash, total_capital * BO_PCT)
        if order_size < 1.0:  # minimum viable order
            return False

        fee = order_size * TAKER_FEE
        net_size = order_size - fee
        qty = net_size / price

        cash -= order_size
        avg_entry = price
        position_qty = qty
        position_cost = order_size
        layers = 1
        last_so_price = price
        tp_price = avg_entry * (1 + TP_PCT)
        deal_start_ms = ts
        in_position = True
        return True

    def add_safety_order(price: float):
        nonlocal avg_entry, position_qty, position_cost, layers, last_so_price, tp_price, cash

        so_size = get_so_volume(layers)
        so_size = min(so_size, cash)  # can't spend more than we have
        if so_size < 1.0:
            return

        fee = so_size * TAKER_FEE
        net_size = so_size - fee
        qty = net_size / price

        position_cost += so_size
        position_qty += qty
        avg_entry = position_cost / position_qty  # weighted average (approx, ignoring fees for avg)
        # More precise: avg_entry based on total cost vs total qty
        # Actually let's use cost-basis approach
        avg_entry = position_cost / position_qty
        layers += 1
        last_so_price = price
        tp_price = avg_entry * (1 + TP_PCT)
        cash -= so_size

    def close_position(exit_price: float, ts: int):
        nonlocal in_position, cash, position_qty, position_cost, layers

        gross_value = position_qty * exit_price
        fee = gross_value * TAKER_FEE
        net_value = gross_value - fee
        pnl = net_value - position_cost
        duration_h = (ts - deal_start_ms) / 3_600_000

        deals.append(DealResult(
            entry_time_ms=deal_start_ms,
            exit_time_ms=ts,
            layers=layers,
            invested=position_cost,
            pnl=pnl,
            duration_hours=max(duration_h, 1.0),  # minimum 1h
        ))

        cash += net_value
        in_position = False
        position_qty = 0.0
        position_cost = 0.0
        layers = 0

    # Main simulation loop
    for i, (ts, o, h, l, c, vol) in enumerate(candles):
        if not in_position:
            # Open a new deal at this candle's open
            if not open_base_order(o, ts):
                continue  # no cash left
            # Still check this candle for TP/SO after opening

        # Check take profit (high >= tp_price)
        if in_position and h >= tp_price:
            close_position(tp_price, ts)
            # Can open new deal on same candle if price dropped and came back
            # But for simplicity, wait for next candle
            # Track equity
            equity = cash  # no position after close
            if equity > peak_equity:
                peak_equity = equity
            dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
            if dd > max_dd:
                max_dd = dd
            continue

        # Check safety order (low <= next_so_price)
        if in_position and layers < MAX_LAYERS:
            next_so = last_so_price * (1 - SO_DEV * (SO_MULT ** (layers - 1)))
            # Could hit multiple SOs in one candle if price drops fast
            while layers < MAX_LAYERS and l <= next_so:
                add_safety_order(next_so)
                if layers < MAX_LAYERS:
                    next_so = last_so_price * (1 - SO_DEV * (SO_MULT ** (layers - 1)))
                else:
                    break

            # After adding SOs, check if TP was also hit this candle
            # (price dropped to SO then bounced to TP)
            if in_position and h >= tp_price:
                close_position(tp_price, ts)
                equity = cash
                if equity > peak_equity:
                    peak_equity = equity
                dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
                if dd > max_dd:
                    max_dd = dd
                continue

        # Track drawdown with open position
        if in_position:
            unrealized_value = position_qty * c
            equity = cash + unrealized_value
        else:
            equity = cash

        if equity > peak_equity:
            peak_equity = equity
        dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
        if dd > max_dd:
            max_dd = dd

    # Calculate final metrics
    total_hours = (candles[-1][0] - candles[0][0]) / 3_600_000 if len(candles) > 1 else 1
    total_weeks = total_hours / 168  # 168 hours per week

    result.deals_completed = len(deals)
    result.realized_pnl = round(sum(d.pnl for d in deals), 2)
    result.max_drawdown_pct = round(max_dd * 100, 2)

    if deals:
        result.deals_per_week = round(len(deals) / max(total_weeks, 0.01), 1)
        result.avg_cycle_hours = round(sum(d.duration_hours for d in deals) / len(deals), 1)
        result.avg_pnl_per_deal = round(result.realized_pnl / len(deals), 2)
        winners = sum(1 for d in deals if d.pnl > 0)
        result.win_rate = round(winners / len(deals) * 100, 1)

    result.open_layers = layers if in_position else 0

    # Unrealized P&L
    if in_position:
        last_price = candles[-1][4]  # last close
        unrealized_value = position_qty * last_price
        fee = unrealized_value * TAKER_FEE
        result.unrealized_pnl = round(unrealized_value - fee - position_cost, 2)
    else:
        result.unrealized_pnl = 0.0

    # Net return
    total_pnl = result.realized_pnl + result.unrealized_pnl
    result.net_return_pct = round(total_pnl / total_capital * 100, 2)

    # Capital freedom: penalizes locked-up capital
    result.capital_freedom = round(1 - (result.open_layers / 24), 4)

    # DCA Score = realized_pnl * (1 - max_dd) * capital_freedom / 100
    result.dca_score = round(
        result.realized_pnl * (1 - max_dd) * result.capital_freedom / 100,
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
        # Jan 1, 2026 UTC
        bear_start = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
        return bear_start, now_ms
    else:
        raise ValueError(f"Unknown window: {window}")


def scan_all(coins: list[str], windows: list[str], top_n: Optional[int] = None) -> dict:
    """Run full scan across all coins and windows."""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = None

    results: dict[str, list[SimResult]] = {w: [] for w in windows}
    coins_scanned = 0

    for symbol in coins:
        # Check if coin exists in DB
        row = conn.execute(
            "SELECT COUNT(*) FROM candles WHERE symbol = ? AND timeframe = '1h'",
            (symbol,)
        ).fetchone()
        if row[0] == 0:
            logger.warning(f"No candle data for {symbol}, skipping")
            continue

        coins_scanned += 1
        short_name = symbol.split("/")[0]
        logger.info(f"Scanning {short_name}...")

        for window in windows:
            start_ms, end_ms = get_window_range(window, now_ms)
            candles = load_candles(conn, symbol, start_ms, end_ms)

            if len(candles) < 10:
                logger.warning(f"  {window}: only {len(candles)} candles for {short_name}, skipping")
                continue

            sim = run_dca_sim(candles, symbol, window)
            results[window].append(sim)
            logger.debug(
                f"  {window}: {sim.deals_completed} deals, "
                f"${sim.realized_pnl:+.0f}, DD {sim.max_drawdown_pct:.1f}%, "
                f"Score {sim.dca_score:.1f}"
            )

    conn.close()

    # Sort each window by dca_score descending
    for w in windows:
        results[w].sort(key=lambda r: r.dca_score, reverse=True)

    # Build output
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "windows": {},
        "coins_scanned": coins_scanned,
        "top_picks": {},
    }

    # Aggregate top picks from the longest available window
    best_window = "bear" if "bear" in windows else windows[-1]
    all_results = results.get(best_window, [])

    if all_results:
        output["top_picks"] = {
            "fastest_cycler": max(all_results, key=lambda r: r.deals_per_week).symbol.split("/")[0],
            "best_score": all_results[0].symbol.split("/")[0],
            "lowest_dd": min(all_results, key=lambda r: r.max_drawdown_pct).symbol.split("/")[0],
            "most_capital_free": max(all_results, key=lambda r: r.capital_freedom).symbol.split("/")[0],
        }

    for w in windows:
        rankings = results[w]
        if top_n:
            rankings = rankings[:top_n]

        window_data = {
            "rankings": [
                {
                    "rank": i + 1,
                    "symbol": r.symbol,
                    "coin": r.symbol.split("/")[0],
                    "deals_completed": r.deals_completed,
                    "deals_per_week": r.deals_per_week,
                    "avg_cycle_hours": r.avg_cycle_hours,
                    "realized_pnl": r.realized_pnl,
                    "avg_pnl_per_deal": r.avg_pnl_per_deal,
                    "max_drawdown_pct": r.max_drawdown_pct,
                    "open_layers": r.open_layers,
                    "unrealized_pnl": r.unrealized_pnl,
                    "net_return_pct": r.net_return_pct,
                    "capital_freedom": r.capital_freedom,
                    "dca_score": r.dca_score,
                    "win_rate": r.win_rate,
                    "candles_used": r.candles_used,
                }
                for i, r in enumerate(rankings)
            ]
        }
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

    print(f"\n{'='*85}")
    print(f"  DCA Cycle Rankings — {window} window")
    print(f"{'='*85}")
    print(f"{'#':>3} {'Coin':<8} {'Deals':>5} {'D/Wk':>5} {'AvgHrs':>7} "
          f"{'Realized':>10} {'MaxDD%':>7} {'Layers':>6} {'CapFree':>7} {'Score':>8}")
    print(f"{'-'*85}")

    for r in rankings:
        print(
            f"{r['rank']:>3} {r['coin']:<8} {r['deals_completed']:>5} "
            f"{r['deals_per_week']:>5.1f} {r['avg_cycle_hours']:>7.1f} "
            f"${r['realized_pnl']:>+9.0f} {r['max_drawdown_pct']:>6.1f}% "
            f"{r['open_layers']:>6} {r['capital_freedom']:>6.2f} "
            f"{r['dca_score']:>8.1f}"
        )

    print(f"{'-'*85}")


def send_telegram_summary(output: dict):
    """Send scan summary to Telegram via API."""
    token = os.environ.get("AIT_TG_TOKEN")
    chat_id = os.environ.get("AIT_TG_CHAT_ID")

    if not token or not chat_id:
        logger.info("Telegram env vars not set, skipping notification")
        return

    # Build message from the best available window
    windows_available = list(output["windows"].keys())
    window_labels = "/".join(windows_available)

    # Use the longest window for the summary
    best_window = windows_available[-1]
    rankings = output["windows"][best_window]["rankings"][:5]

    lines = [f"📊 [SCANNER] DCA Cycle Rankings ({window_labels})", ""]
    lines.append(f"Top 5 by DCA Score ({best_window}):")

    for r in rankings:
        lines.append(
            f"{r['rank']}. {r['coin']} — {r['deals_per_week']:.1f} d/wk, "
            f"${r['realized_pnl']:+,.0f}, DD {r['max_drawdown_pct']:.0f}%, "
            f"Score {r['dca_score']:.1f}"
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

    if output.get("top_picks"):
        tp = output["top_picks"]
        lines.append(f"🏆 Best: {tp.get('best_score', '?')} | "
                     f"⚡ Fastest: {tp.get('fastest_cycler', '?')} | "
                     f"🛡️ Safest: {tp.get('lowest_dd', '?')}")

    message = "\n".join(lines)

    try:
        import urllib.request
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = json.dumps({
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
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
        description="V14 DCA Cycle Scanner — Bear Market Capital Velocity Optimizer"
    )
    parser.add_argument("--window", choices=["7d", "14d", "30d", "bear"],
                        help="Run only a single time window")
    parser.add_argument("--coin", type=str, help="Scan a single coin (e.g. HYPE)")
    parser.add_argument("--top", type=int, help="Show only top N results")
    parser.add_argument("--no-telegram", action="store_true", help="Skip Telegram notification")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Determine windows
    if args.window:
        windows = [args.window]
    else:
        windows = ["7d", "14d", "30d", "bear"]

    # Determine coins
    if args.coin:
        coin_upper = args.coin.upper()
        # Find matching symbol
        matching = [c for c in COINS if c.startswith(coin_upper + "/")]
        if not matching:
            logger.error(f"Coin '{args.coin}' not found in universe. Available: {[c.split('/')[0] for c in COINS]}")
            sys.exit(1)
        coins = matching
    else:
        coins = COINS

    # Check DB exists
    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        sys.exit(1)

    logger.info(f"V14 DCA Cycle Scanner — {len(coins)} coins, {len(windows)} windows")
    logger.info(f"Parameters: BO={BO_PCT:.0%}, SO_DEV={SO_DEV:.1%}, "
                f"SO_MULT={SO_MULT}, TP={TP_PCT:.1%}, MAX_LAYERS={MAX_LAYERS}")

    # Run scan
    output = scan_all(coins, windows, top_n=args.top)

    # Print results
    for w in windows:
        print_table(output, w, top_n=args.top)

    # Print top picks
    if output.get("top_picks"):
        tp = output["top_picks"]
        print(f"\n🏆 Top Picks:")
        print(f"  Best Score:     {tp.get('best_score', 'N/A')}")
        print(f"  Fastest Cycler: {tp.get('fastest_cycler', 'N/A')}")
        print(f"  Lowest DD:      {tp.get('lowest_dd', 'N/A')}")
        print(f"  Most Cap Free:  {tp.get('most_capital_free', 'N/A')}")

    # Save JSON output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    logger.info(f"Results saved to {OUTPUT_PATH}")

    # Send Telegram notification
    if not args.no_telegram:
        send_telegram_summary(output)


if __name__ == "__main__":
    main()
