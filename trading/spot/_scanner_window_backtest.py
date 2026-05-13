"""
Scanner Window Optimization — Walk-Forward Analysis

Tests which scanner lookback window (7d, 10d, 14d, 21d, 24d, 30d) produces the
best coin selections for the V14PM portfolio manager.

Approach:
1. Step through 90 days of history, day by day
2. Each day, run the DCA scanner for each window size to score all coins
3. Pick top-3 coins per window (matching live tier cap)
4. Track: which coins get promoted, when, and how they perform

Uses CURRENT production grid params: TP=3.0%, Max=4 layers, Dev=1.5%, Mult=1.5x

Does NOT modify production code. Read-only analysis.
"""
import sqlite3
import json
import statistics
from collections import defaultdict, Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Scanner coin universe (from v14_cycle_scanner.py) ──
COINS = [
    'BTC/USDC', 'ETH/USDC', 'SOL/USDC', 'XRP/USDT', 'LINK/USDT',
    'DOGE/USDT', 'ADA/USDT', 'LTC/USDT', 'AVAX/USDT', 'DOT/USDT',
    'UNI/USDT', 'ATOM/USDT', 'NEAR/USDT', 'HBAR/USDT', 'INJ/USDT',
    'FIL/USDT', 'RUNE/USDT', 'CRV/USDT', 'SNX/USDT', 'COMP/USDT',
    'MKR/USDT', 'ENS/USDT', 'DYDX/USDT', 'LDO/USDT', 'ARB/USDT',
    'OP/USDT', 'STX/USDT', 'SEI/USDT', 'RENDER/USDT',
    'SUI/USDT', 'FET/USDT', 'TAO/USDT', 'TON/USDT', 'JUP/USDT',
    'KAS/USDT', 'PENDLE/USDT', 'PYTH/USDT', 'TIA/USDT', 'ONDO/USDT',
    'ENA/USDT', 'EIGEN/USDT', 'W/USDT', 'ZRO/USDT',
    'HYPE/USDC', 'AAVE/USDT',
]

# ── Grid params (CURRENT production: High profile post-2026-05-12) ──
BO_PCT = 0.40
SO_DEV = 0.015
SO_STEP_MULT = 1.5
SO_VOL_MULT = 1.5
MAX_LAYERS = 4        # Updated from 12
TP_PCT = 0.030        # Updated from 0.015
TAKER_FEE = 0.00025
CAPITAL = 10_000.0
DCA_ALLOC = 0.90
HURDLE_RATE = 5.0
TOP_N = 3

# ── Windows to test ──
WINDOWS = [7, 10, 14, 21, 24, 30]

# ── Paths ──
DB_PATH = Path(__file__).resolve().parent / "data" / "candles.db"


def load_candles(conn, symbol, start_ms, end_ms):
    """Load 1h candles for a symbol within a time range."""
    cursor = conn.execute(
        "SELECT timestamp, open, high, low, close, volume FROM candles "
        "WHERE symbol = ? AND timeframe = '1h' AND timestamp >= ? AND timestamp <= ? "
        "ORDER BY timestamp",
        (symbol, start_ms, end_ms)
    )
    return cursor.fetchall()


def run_dca_sim(candles, symbol):
    """
    Run DCA sim with CURRENT production params (4 layers, 3.0% TP).
    Returns dict with dca_score, realized_pnl, deals, etc.
    """
    if len(candles) < 24:  # need at least 1 day
        return None

    alloc = CAPITAL * DCA_ALLOC
    bo_size = alloc * BO_PCT

    deals_pnl = []
    deals_hours = []
    deals_layers = []

    in_position = False
    layers = 0
    total_qty = 0.0
    total_cost = 0.0
    avg_entry = 0.0
    tp_price = 0.0
    so_prices = []
    deal_start_ms = 0
    cash = alloc
    peak_equity = alloc
    max_dd = 0.0

    def compute_so_grid(entry_price):
        prices = []
        p = entry_price
        for i in range(MAX_LAYERS):
            dev = SO_DEV * (SO_STEP_MULT ** i)
            p = p * (1 - dev)
            prices.append(p)
        return prices

    def get_so_size(layer_idx):
        base_so = bo_size * 0.5
        return base_so * (SO_VOL_MULT ** layer_idx)

    for i, (ts, o, h, l, c, vol) in enumerate(candles):
        if not in_position:
            order_cost = min(bo_size, cash)
            if order_cost < 1.0:
                continue
            fee = order_cost * TAKER_FEE
            qty = (order_cost - fee) / o
            total_qty = qty
            total_cost = order_cost
            avg_entry = total_cost / total_qty
            tp_price = avg_entry * (1 + TP_PCT)
            so_prices = compute_so_grid(o)
            layers = 1
            deal_start_ms = ts
            cash -= order_cost
            in_position = True

        # Check TP
        if in_position and h >= tp_price:
            gross = total_qty * tp_price
            fee = gross * TAKER_FEE
            net = gross - fee
            pnl = net - total_cost
            duration_h = max((ts - deal_start_ms) / 3_600_000, 1.0)
            deals_pnl.append(pnl)
            deals_hours.append(duration_h)
            deals_layers.append(layers)
            cash += net
            in_position = False
            total_qty = 0.0
            total_cost = 0.0
            equity = cash
            if equity > peak_equity:
                peak_equity = equity
            dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
            if dd > max_dd:
                max_dd = dd
            continue

        # Check SOs
        if in_position:
            while layers < MAX_LAYERS:
                so_idx = layers - 1
                if so_idx >= len(so_prices):
                    break
                if l <= so_prices[so_idx]:
                    so_cost = get_so_size(so_idx)
                    so_cost = min(so_cost, cash)
                    if so_cost < 1.0:
                        break
                    fee = so_cost * TAKER_FEE
                    qty = (so_cost - fee) / so_prices[so_idx]
                    total_qty += qty
                    total_cost += so_cost
                    avg_entry = total_cost / total_qty
                    tp_price = avg_entry * (1 + TP_PCT)
                    layers += 1
                    cash -= so_cost
                else:
                    break

            # Check TP after SO (bounce)
            if in_position and h >= tp_price:
                gross = total_qty * tp_price
                fee = gross * TAKER_FEE
                net = gross - fee
                pnl = net - total_cost
                duration_h = max((ts - deal_start_ms) / 3_600_000, 1.0)
                deals_pnl.append(pnl)
                deals_hours.append(duration_h)
                deals_layers.append(layers)
                cash += net
                in_position = False
                total_qty = 0.0
                total_cost = 0.0

        # Track drawdown
        if in_position:
            equity = cash + total_qty * c
        else:
            equity = cash
        if equity > peak_equity:
            peak_equity = equity
        dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
        if dd > max_dd:
            max_dd = dd

    # Results
    total_hours = (candles[-1][0] - candles[0][0]) / 3_600_000 if len(candles) > 1 else 1
    total_weeks = max(total_hours / 168, 0.01)
    n_deals = len(deals_pnl)

    realized_pnl = sum(deals_pnl) if deals_pnl else 0
    capital_freedom = 1 - ((layers if in_position else 0) / 24)
    dca_score = realized_pnl * (1 - max_dd) * capital_freedom / 100

    return {
        "symbol": symbol,
        "coin": symbol.split("/")[0],
        "dca_score": round(dca_score, 2),
        "realized_pnl": round(realized_pnl, 2),
        "deals_completed": n_deals,
        "deals_per_week": round(n_deals / total_weeks, 1) if n_deals else 0,
        "avg_cycle_hours": round(sum(deals_hours) / n_deals, 1) if n_deals else 0,
        "max_drawdown_pct": round(max_dd * 100, 2),
        "capital_freedom": round(capital_freedom, 4),
        "avg_layers": round(sum(deals_layers) / n_deals, 2) if n_deals else 0,
        "trap_deals": sum(1 for h in deals_hours if h > 100),
        "deep_deals": sum(1 for l in deals_layers if l >= 3),
    }


def run_daily_scanner(conn, coins, window_days, as_of_ms):
    """Run scanner for all coins using a specific window, as of a specific date."""
    start_ms = as_of_ms - window_days * 24 * 3600 * 1000
    results = []

    for symbol in coins:
        candles = load_candles(conn, symbol, start_ms, as_of_ms)
        if len(candles) < 48:  # need at least 2 days
            continue
        sim = run_dca_sim(candles, symbol)
        if sim and sim["dca_score"] >= HURDLE_RATE:
            results.append(sim)

    results.sort(key=lambda r: r["dca_score"], reverse=True)
    return results[:TOP_N]


def main():
    conn = sqlite3.connect(str(DB_PATH))

    # Determine date range: last 90 days, stepping day by day
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    days_back = 60  # 60 days of walk-forward (need window days before that for data)
    day_ms = 24 * 3600 * 1000

    print("=" * 120)
    print("  SCANNER WINDOW OPTIMIZATION — WALK-FORWARD ANALYSIS")
    print(f"  {days_back} days of walk-forward, {len(COINS)} coins, {len(WINDOWS)} windows")
    print(f"  Grid: TP=3.0%, Max=4 layers, Dev=1.5%, Mult=1.5x (current production)")
    print(f"  Top-{TOP_N} selection, Hurdle >= {HURDLE_RATE}")
    print("=" * 120)

    # For each window, track daily top-3 selections
    window_daily_picks = {w: [] for w in WINDOWS}  # window -> list of (date, [top3 coins])
    window_all_scores = {w: defaultdict(list) for w in WINDOWS}  # window -> coin -> [daily scores]

    # Step through time
    for day_offset in range(days_back, 0, -1):
        eval_ms = now_ms - day_offset * day_ms
        eval_date = datetime.fromtimestamp(eval_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")

        for w in WINDOWS:
            top = run_daily_scanner(conn, COINS, w, eval_ms)
            top_coins = [r["coin"] for r in top]
            window_daily_picks[w].append((eval_date, top_coins, top))

            # Track all qualifying scores
            for r in top:
                window_all_scores[w][r["coin"]].append({
                    "date": eval_date,
                    "score": r["dca_score"],
                    "deals": r["deals_completed"],
                    "pnl": r["realized_pnl"],
                })

        if day_offset % 10 == 0:
            print(f"  Processing day -{day_offset}... ({eval_date})")

    print("\nScan complete.\n")

    # =========================================================================
    # ANALYSIS 1: Top-3 picks comparison over time
    # =========================================================================
    print("=" * 120)
    print("  ANALYSIS 1: TOP-3 COIN SELECTIONS BY WINDOW")
    print("=" * 120)

    for w in WINDOWS:
        coin_days = Counter()
        for date, coins, _ in window_daily_picks[w]:
            for c in coins:
                coin_days[c] += 1
        total_days = len(window_daily_picks[w])
        print(f"\n  {w}d window — coins that appeared in top-3:")
        for coin, days in coin_days.most_common(15):
            print(f"    {coin:10s}: {days:3d}/{total_days} days ({days/total_days*100:.0f}%)")

    # =========================================================================
    # ANALYSIS 2: Ranking stability (churn)
    # =========================================================================
    print(f"\n{'='*120}")
    print("  ANALYSIS 2: RANKING STABILITY (CHURN RATE)")
    print(f"{'='*120}")
    print(f"\n  {'Window':<10} {'Avg Daily Changes':<20} {'Total Unique Coins':<20} {'Churn Rate':<15}")
    print(f"  {'-'*65}")

    for w in WINDOWS:
        changes = 0
        prev_set = set()
        unique_coins = set()
        for date, coins, _ in window_daily_picks[w]:
            coin_set = set(coins)
            unique_coins.update(coin_set)
            if prev_set:
                changes += len(coin_set - prev_set)
            prev_set = coin_set
        total_days = max(len(window_daily_picks[w]) - 1, 1)
        avg_changes = changes / total_days
        churn = changes / (total_days * TOP_N) * 100
        print(f"  {w}d{'':<7} {avg_changes:<20.2f} {len(unique_coins):<20d} {churn:<14.1f}%")

    # =========================================================================
    # ANALYSIS 3: Time to promotion for key coins
    # =========================================================================
    print(f"\n{'='*120}")
    print("  ANALYSIS 3: TIME TO PROMOTION (KEY MOMENTUM COINS)")
    print(f"{'='*120}")

    key_coins = ["TON", "HYPE", "PENDLE", "INJ", "JUP", "TAO", "ONDO"]
    print(f"\n  First day each coin appeared in top-3 for each window:")
    print(f"  {'Coin':<10}", end="")
    for w in WINDOWS:
        print(f"  {w}d{'':<8}", end="")
    print()
    print(f"  {'-'*80}")

    for coin in key_coins:
        print(f"  {coin:<10}", end="")
        for w in WINDOWS:
            first_date = None
            for date, coins, _ in window_daily_picks[w]:
                if coin in coins:
                    first_date = date
                    break
            if first_date:
                print(f"  {first_date:<10}", end="")
            else:
                print(f"  {'never':<10}", end="")
        print()

    # =========================================================================
    # ANALYSIS 4: Aggregate DCA scores by window
    # =========================================================================
    print(f"\n{'='*120}")
    print("  ANALYSIS 4: AGGREGATE TOP-3 PERFORMANCE BY WINDOW")
    print(f"{'='*120}")

    print(f"\n  {'Window':<10} {'Avg Score':<12} {'Avg PnL':<12} {'Avg Deals':<12} {'Avg Cycle(h)':<14} {'Avg Layers':<12} {'Traps':<8} {'Deep(L3+)':<10}")
    print(f"  {'-'*90}")

    window_summaries = {}
    for w in WINDOWS:
        all_scores = []
        all_pnl = []
        all_deals = []
        all_cycle = []
        all_layers = []
        total_traps = 0
        total_deep = 0

        for date, coins, top_results in window_daily_picks[w]:
            for r in top_results:
                all_scores.append(r["dca_score"])
                all_pnl.append(r["realized_pnl"])
                all_deals.append(r["deals_completed"])
                if r["avg_cycle_hours"] > 0:
                    all_cycle.append(r["avg_cycle_hours"])
                if r["avg_layers"] > 0:
                    all_layers.append(r["avg_layers"])
                total_traps += r.get("trap_deals", 0)
                total_deep += r.get("deep_deals", 0)

        if all_scores:
            summary = {
                "avg_score": statistics.mean(all_scores),
                "avg_pnl": statistics.mean(all_pnl),
                "avg_deals": statistics.mean(all_deals),
                "avg_cycle": statistics.mean(all_cycle) if all_cycle else 0,
                "avg_layers": statistics.mean(all_layers) if all_layers else 0,
                "total_traps": total_traps,
                "total_deep": total_deep,
            }
            window_summaries[w] = summary
            print(
                f"  {w}d{'':<7} {summary['avg_score']:<12.1f} "
                f"${summary['avg_pnl']:<10.0f} {summary['avg_deals']:<12.0f} "
                f"{summary['avg_cycle']:<14.1f} {summary['avg_layers']:<12.2f} "
                f"{total_traps:<8d} {total_deep:<10d}"
            )

    # =========================================================================
    # ANALYSIS 5: False positive rate (coins in top-3 for <3 days then gone)
    # =========================================================================
    print(f"\n{'='*120}")
    print("  ANALYSIS 5: FALSE POSITIVES (COINS IN TOP-3 < 3 CONSECUTIVE DAYS)")
    print(f"{'='*120}")

    print(f"\n  {'Window':<10} {'False Positives':<18} {'Total Promotions':<20} {'FP Rate':<10}")
    print(f"  {'-'*58}")

    for w in WINDOWS:
        # Track consecutive days each coin is in top-3
        coin_streaks = defaultdict(int)
        coin_max_streak = defaultdict(int)
        prev_coins = set()

        for date, coins, _ in window_daily_picks[w]:
            coin_set = set(coins)
            for c in coin_set:
                if c in prev_coins:
                    coin_streaks[c] += 1
                else:
                    coin_streaks[c] = 1
                coin_max_streak[c] = max(coin_max_streak[c], coin_streaks[c])
            for c in prev_coins - coin_set:
                coin_streaks[c] = 0
            prev_coins = coin_set

        total_coins = len(coin_max_streak)
        false_pos = sum(1 for c, s in coin_max_streak.items() if s < 3)
        fp_rate = false_pos / total_coins * 100 if total_coins else 0
        print(f"  {w}d{'':<7} {false_pos:<18d} {total_coins:<20d} {fp_rate:<9.1f}%")

    # =========================================================================
    # ANALYSIS 6: Side-by-side daily comparison (last 14 days)
    # =========================================================================
    print(f"\n{'='*120}")
    print("  ANALYSIS 6: DAILY TOP-3 PICKS — LAST 14 DAYS (SIDE-BY-SIDE)")
    print(f"{'='*120}")

    # Get last 14 entries from each window
    header = f"\n  {'Date':<12}"
    for w in WINDOWS:
        header += f"  {w}d{'':<22}"
    print(header)
    print(f"  {'-'*(12 + 26 * len(WINDOWS))}")

    n_show = min(14, len(window_daily_picks[WINDOWS[0]]))
    for i in range(-n_show, 0):
        date = window_daily_picks[WINDOWS[0]][i][0]
        row = f"  {date:<12}"
        for w in WINDOWS:
            coins = window_daily_picks[w][i][1] if abs(i) <= len(window_daily_picks[w]) else []
            coins_str = ", ".join(coins[:3])
            row += f"  {coins_str:<24}"
        print(row)

    # =========================================================================
    # VERDICT
    # =========================================================================
    print(f"\n{'='*120}")
    print("  VERDICT")
    print(f"{'='*120}")

    if window_summaries:
        best_w = max(window_summaries.items(), key=lambda x: x[1]["avg_score"])
        base_30 = window_summaries.get(30, {})

        print(f"\n  Highest avg DCA score: {best_w[0]}d window (score={best_w[1]['avg_score']:.1f})")
        if base_30:
            print(f"  Current 30d window: score={base_30['avg_score']:.1f}")
            delta = (best_w[1]['avg_score'] / base_30['avg_score'] - 1) * 100 if base_30['avg_score'] else 0
            print(f"  Delta: {delta:+.1f}%")

    # Save results
    output = {
        "analysis_date": datetime.now(timezone.utc).isoformat(),
        "config": {
            "windows": WINDOWS,
            "grid": {"tp_pct": TP_PCT, "max_layers": MAX_LAYERS, "so_dev": SO_DEV},
            "top_n": TOP_N,
            "hurdle_rate": HURDLE_RATE,
            "days_analyzed": days_back,
        },
        "window_summaries": {str(w): s for w, s in window_summaries.items()},
    }
    out_path = Path(__file__).resolve().parent / "data" / "scanner_window_analysis.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to {out_path}")

    conn.close()


if __name__ == "__main__":
    main()
