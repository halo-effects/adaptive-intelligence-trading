"""
Portfolio-Level Grid Optimization Backtest

Models the REAL portfolio manager behavior:
  - 3 coin slots (equity-tiered at <$500 — matches live)
  - Capital rotation: when a deal closes, freed capital is available for new entries
  - Daily scanner rebalance: coins rotate based on score
  - Shared capital pool across all active deals

Tests same 7 configs but now captures the portfolio-level capital velocity effect
that a per-coin sim misses.

Key difference: with 4-layer cap, capital that would be trapped in deep layers
is instead available for new deals on other coins.
"""
import sqlite3
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

DB = "trading/spot/data/candles.db"
conn = sqlite3.connect(DB)

# Fixed params
BO_PCT = 0.40
TOTAL_CAPITAL = 50000  # Total portfolio capital
MAX_COIN_SLOTS = 3     # Matches live PM at <$500 tier (scaled up for sim)
TAKER_FEE = 0.00025
MAKER_FEE = 0.0002

# Scanner coins
COINS = [
    "GRASS/USDT", "TAO/USDT", "FET/USDT", "ZEC/USDT", "JTO/USDT",
    "HYPE/USDT", "PENDLE/USDT", "INJ/USDT", "TON/USDT", "ONDO/USDT"
]

cutoff_ms = int((datetime.now() - timedelta(days=90)).timestamp() * 1000)

CONFIGS = [
    # (label, tp_pct, so_dev, so_mult, max_layers)
    ("BASELINE (1.5% TP, 12L)",     1.5, 0.015, 1.5, 12),
    ("TP2.5, 12L",                   2.5, 0.015, 1.5, 12),
    ("TP2.5, 4L cap",               2.5, 0.015, 1.5,  4),
    ("TP2.5, 4L, 2.0x mult",        2.5, 0.015, 2.0,  4),
    ("TP2.5, 4L, 2% dev",           2.5, 0.020, 1.5,  4),
    ("TP3.0, 4L cap",               3.0, 0.015, 1.5,  4),
    ("TP3.0, 4L, 2.0x mult",        3.0, 0.015, 2.0,  4),
]


class DealState:
    """Tracks one open deal (position)."""
    def __init__(self, symbol: str, entry_price: float, entry_size: float,
                 entry_candle: int, tp_pct: float, so_dev: float,
                 so_mult: float, max_layers: int, allocation: float):
        self.symbol = symbol
        self.layers = 1
        self.total_coins = entry_size / entry_price
        self.raw_cost = entry_size
        self.total_cost = entry_size + entry_size * TAKER_FEE
        self.avg_entry = entry_price
        self.tp_price = entry_price * (1 + tp_pct / 100)
        self.entry_candle = entry_candle
        self.tp_pct = tp_pct
        self.so_dev = so_dev
        self.so_mult = so_mult
        self.max_layers = max_layers
        self.allocation = allocation  # total capital allocated to this deal
        self.cash_remaining = allocation - entry_size  # unspent allocation
        self.max_dd_pct = 0.0
        self.peak_value = self.total_coins * entry_price

    def check_tp(self, high: float) -> Optional[dict]:
        """Check if TP hit. Returns deal result dict or None."""
        if high >= self.tp_price:
            proceeds = self.total_coins * self.tp_price
            fee = proceeds * MAKER_FEE
            pnl = proceeds - self.total_cost - fee
            ret_pct = pnl / self.total_cost * 100 if self.total_cost > 0 else 0
            return {
                "pnl": pnl,
                "return_pct": ret_pct,
                "layers": self.layers,
                "invested": self.total_cost,
                "allocation_used": self.allocation,
                "cash_returned": proceeds - fee,  # actual cash back
                "unused_allocation": self.cash_remaining,
            }
        return None

    def check_so(self, low: float, candle_idx: int) -> bool:
        """Check if next safety order triggers. Returns True if filled."""
        if self.layers >= self.max_layers:
            return False

        so_trigger = self.avg_entry * (1 - self.so_dev * self.layers)
        if low <= so_trigger:
            # Calculate layer size
            base = self.allocation * BO_PCT * 0.9
            mult = self.so_mult ** min(self.layers, 4)
            size = base * mult
            size = min(size, self.allocation * 0.3)  # 30% cap
            size = min(size, self.cash_remaining)  # can't spend more than allocated
            if size < 1:
                return False

            fill_price = so_trigger
            coins = size / fill_price
            fee = size * TAKER_FEE
            self.total_coins += coins
            self.raw_cost += size
            self.total_cost += size + fee
            self.avg_entry = self.raw_cost / self.total_coins
            self.tp_price = self.avg_entry * (1 + self.tp_pct / 100)
            self.layers += 1
            self.cash_remaining -= size
            return True
        return False

    def update_dd(self, price: float):
        """Track drawdown."""
        current_value = self.total_coins * price
        self.peak_value = max(self.peak_value, current_value)
        if self.peak_value > 0:
            dd = (self.peak_value - current_value) / self.peak_value * 100
            self.max_dd_pct = max(self.max_dd_pct, dd)


def run_portfolio_sim(coin_candles: Dict[str, list], tp_pct: float,
                      so_dev: float, so_mult: float, max_layers: int,
                      total_capital: float, max_slots: int) -> dict:
    """
    Run full portfolio simulation with capital rotation.

    All coins share a common timeline (1h candles). At each hour:
    1. Check TPs on open deals (free capital)
    2. Check SOs on open deals (deploy more capital)
    3. If slots available, open new deals on idle coins

    Coin priority for new entries: round-robin across available coins
    (simplified vs real scanner scoring, but captures rotation effect).
    """
    # Align all candles to common timestamps
    all_timestamps = set()
    for sym, candles in coin_candles.items():
        for ts, o, h, l, c in candles:
            all_timestamps.add(ts)
    sorted_ts = sorted(all_timestamps)

    # Build price lookup: {timestamp: {symbol: (o, h, l, c)}}
    price_data = defaultdict(dict)
    for sym, candles in coin_candles.items():
        for ts, o, h, l, c in candles:
            price_data[ts][sym] = (o, h, l, c)

    # State
    available_capital = total_capital
    open_deals: Dict[str, DealState] = {}  # symbol -> DealState
    completed_deals = []
    coin_queue = list(coin_candles.keys())  # rotation order
    queue_idx = 0
    deals_opened_total = 0

    # Track capital over time for utilization
    capital_deployed_hours = 0
    total_hours = 0

    for candle_idx, ts in enumerate(sorted_ts):
        total_hours += 1
        prices = price_data[ts]

        # 1. Check TPs on open deals
        closed_symbols = []
        for sym, deal in open_deals.items():
            if sym not in prices:
                continue
            o, h, l, c = prices[sym]
            result = deal.check_tp(h)
            if result:
                result["symbol"] = sym
                result["duration_h"] = candle_idx - deal.entry_candle
                result["max_dd_pct"] = deal.max_dd_pct
                completed_deals.append(result)
                # Return capital: proceeds + unused allocation
                returned = result["cash_returned"] + deal.cash_remaining
                available_capital += returned
                closed_symbols.append(sym)

        for sym in closed_symbols:
            del open_deals[sym]

        # 2. Check SOs on open deals (uses already-allocated capital)
        for sym, deal in open_deals.items():
            if sym not in prices:
                continue
            o, h, l, c = prices[sym]
            deal.check_so(l, candle_idx)
            deal.update_dd(c)

        # 3. Open new deals if slots available
        if len(open_deals) < max_slots and available_capital > 100:
            # Try each coin in rotation order
            attempts = 0
            while (len(open_deals) < max_slots and
                   available_capital > 100 and
                   attempts < len(coin_candles)):
                sym = coin_queue[queue_idx % len(coin_queue)]
                queue_idx += 1
                attempts += 1

                if sym in open_deals:
                    continue
                if sym not in prices:
                    continue

                o, h, l, c = prices[sym]
                # Allocate equal share of available capital per remaining slot
                slots_to_fill = max_slots - len(open_deals)
                allocation = min(
                    available_capital / slots_to_fill,
                    available_capital * 0.5  # never put >50% in one deal
                )
                if allocation < 50:
                    continue

                entry_size = allocation * BO_PCT * 0.9
                if entry_size < 10:
                    continue

                deal = DealState(
                    symbol=sym, entry_price=c, entry_size=entry_size,
                    entry_candle=candle_idx, tp_pct=tp_pct, so_dev=so_dev,
                    so_mult=so_mult, max_layers=max_layers,
                    allocation=allocation
                )
                open_deals[sym] = deal
                available_capital -= allocation
                deals_opened_total += 1

        # Track utilization
        if open_deals:
            capital_deployed_hours += 1

    # Mark-to-market any remaining open deals (don't count as completed)
    open_positions_value = 0
    for sym, deal in open_deals.items():
        last_ts = sorted_ts[-1]
        if sym in price_data[last_ts]:
            _, _, _, c = price_data[last_ts][sym]
            open_positions_value += deal.total_coins * c + deal.cash_remaining

    if not completed_deals:
        return None

    # Aggregate metrics
    total_pnl = sum(d["pnl"] for d in completed_deals)
    n_deals = len(completed_deals)
    returns = [d["return_pct"] for d in completed_deals]
    durations = [d["duration_h"] for d in completed_deals]
    layer_counts = [d["layers"] for d in completed_deals]
    drawdowns = [d["max_dd_pct"] for d in completed_deals]
    invested_amounts = [d["invested"] for d in completed_deals]

    # Capital efficiency
    efficiencies = []
    for d in completed_deals:
        if d["duration_h"] > 0 and d["invested"] > 0:
            eff = d["pnl"] / d["invested"] / d["duration_h"] * 1000
            efficiencies.append(eff)

    utilization = capital_deployed_hours / total_hours * 100 if total_hours > 0 else 0

    # Capital velocity: total $ cycled through deals / total capital / days
    total_invested = sum(d["invested"] for d in completed_deals)
    days = total_hours / 24
    capital_velocity = total_invested / total_capital / days if days > 0 else 0

    # Portfolio ROI
    roi = total_pnl / total_capital * 100

    # Per-coin stats
    coin_stats = defaultdict(lambda: {"deals": 0, "pnl": 0, "layers": []})
    for d in completed_deals:
        s = d["symbol"]
        coin_stats[s]["deals"] += 1
        coin_stats[s]["pnl"] += d["pnl"]
        coin_stats[s]["layers"].append(d["layers"])

    return {
        "deals": n_deals,
        "total_pnl": total_pnl,
        "roi_pct": roi,
        "avg_ret": statistics.mean(returns),
        "med_ret": statistics.median(returns),
        "avg_dur": statistics.mean(durations),
        "med_dur": statistics.median(durations),
        "avg_layers": statistics.mean(layer_counts),
        "max_layers_used": max(layer_counts),
        "avg_dd": statistics.mean(drawdowns),
        "max_dd": max(drawdowns),
        "capital_eff": statistics.mean(efficiencies) if efficiencies else 0,
        "utilization": utilization,
        "capital_velocity": capital_velocity,
        "total_invested": total_invested,
        "open_deals": len(open_deals),
        "open_value": open_positions_value,
        "coin_stats": dict(coin_stats),
    }


# =========================================================================
# Load candle data
# =========================================================================
print("Loading candle data...")
coin_candles = {}
for sym in COINS:
    candles = conn.execute(
        "SELECT timestamp, open, high, low, close FROM candles "
        "WHERE symbol=? AND timeframe='1h' AND timestamp>=? ORDER BY timestamp",
        (sym, cutoff_ms)
    ).fetchall()
    if candles and len(candles) >= 200:
        coin_candles[sym] = candles
        print(f"  {sym}: {len(candles)} candles ({len(candles)/24:.0f} days)")

print(f"\n{len(coin_candles)} coins loaded.\n")

# =========================================================================
# Run all configs
# =========================================================================
print("=" * 120)
print("  PORTFOLIO-LEVEL GRID OPTIMIZATION — 3 COIN SLOTS, CAPITAL ROTATION")
print(f"  ${TOTAL_CAPITAL:,} capital, {MAX_COIN_SLOTS} slots, 10 scanner coins, 90 days")
print(f"  Real 1h candles, limit fills, Hyperliquid fees")
print("=" * 120)

results = {}
for label, tp, dev, mult, max_l in CONFIGS:
    r = run_portfolio_sim(coin_candles, tp, dev, mult, max_l, TOTAL_CAPITAL, MAX_COIN_SLOTS)
    if r:
        results[label] = r

# =========================================================================
# Summary table
# =========================================================================
print(f"\n{'='*120}")
print("  PORTFOLIO RESULTS — CAPITAL ROTATION MODEL")
print(f"{'='*120}")
header = (
    f"  {'Config':<28} {'Deals':>6} {'PnL':>10} {'ROI':>7} {'Avg Ret':>8} "
    f"{'Avg Dur':>8} {'Avg Lyr':>8} {'Cap Vel':>8} {'Util%':>6} {'$ Cycled':>12} {'vs Base':>8}"
)
print(header)
print(f"  {'-'*116}")

baseline_pnl = results[CONFIGS[0][0]]["total_pnl"] if CONFIGS[0][0] in results else 1

for label, _, _, _, _ in CONFIGS:
    if label not in results:
        continue
    r = results[label]
    vs_base = ((r["total_pnl"] / baseline_pnl) - 1) * 100 if baseline_pnl else 0
    print(
        f"  {label:<28} {r['deals']:>6} ${r['total_pnl']:>8.0f} "
        f"{r['roi_pct']:>6.2f}% {r['avg_ret']:>7.2f}% {r['avg_dur']:>7.1f}h "
        f"{r['avg_layers']:>7.2f} {r['capital_velocity']:>7.3f} "
        f"{r['utilization']:>5.1f}% ${r['total_invested']:>10,.0f} {vs_base:>+7.1f}%"
    )

# =========================================================================
# Deep comparison: Baseline vs best 4L config
# =========================================================================
print(f"\n{'='*120}")
print("  HEAD-TO-HEAD: BASELINE vs TOP 4-LAYER CONFIG")
print(f"{'='*120}")

bl = results.get(CONFIGS[0][0])
# Find best 4L config by PnL
best_4l_label = max(
    [label for label, _, _, _, ml in CONFIGS if ml == 4 and label in results],
    key=lambda l: results[l]["total_pnl"]
)
b4 = results[best_4l_label]

metrics = [
    ("Total PnL",          f"${bl['total_pnl']:,.0f}",        f"${b4['total_pnl']:,.0f}"),
    ("Portfolio ROI",      f"{bl['roi_pct']:.2f}%",            f"{b4['roi_pct']:.2f}%"),
    ("Completed Deals",    f"{bl['deals']}",                    f"{b4['deals']}"),
    ("Avg Return/Deal",    f"{bl['avg_ret']:.2f}%",            f"{b4['avg_ret']:.2f}%"),
    ("Avg Duration",       f"{bl['avg_dur']:.1f}h",            f"{b4['avg_dur']:.1f}h"),
    ("Avg Layers",         f"{bl['avg_layers']:.2f}",          f"{b4['avg_layers']:.2f}"),
    ("Max Layers Used",    f"{bl['max_layers_used']}",          f"{b4['max_layers_used']}"),
    ("Capital Velocity",   f"{bl['capital_velocity']:.3f}",    f"{b4['capital_velocity']:.3f}"),
    ("Utilization",        f"{bl['utilization']:.1f}%",        f"{b4['utilization']:.1f}%"),
    ("Total $ Cycled",     f"${bl['total_invested']:,.0f}",    f"${b4['total_invested']:,.0f}"),
    ("Capital Efficiency", f"{bl['capital_eff']:.3f}",         f"{b4['capital_eff']:.3f}"),
    ("Max Drawdown",       f"{bl['max_dd']:.1f}%",             f"{b4['max_dd']:.1f}%"),
    ("Open Deals (EOD)",   f"{bl['open_deals']}",              f"{b4['open_deals']}"),
]

print(f"\n  {'Metric':<22} {'BASELINE (1.5% 12L)':>22} {best_4l_label:>22}")
print(f"  {'-'*68}")
for name, v1, v2 in metrics:
    print(f"  {name:<22} {v1:>22} {v2:>22}")

# =========================================================================
# Per-coin breakdown for winning config
# =========================================================================
print(f"\n{'='*120}")
print(f"  PER-COIN BREAKDOWN — {best_4l_label}")
print(f"{'='*120}")
print(f"  {'Coin':<16} {'Deals':>6} {'PnL':>10} {'Avg Layers':>10}")
print(f"  {'-'*46}")
for sym in sorted(b4["coin_stats"].keys()):
    cs = b4["coin_stats"][sym]
    avg_l = statistics.mean(cs["layers"]) if cs["layers"] else 0
    print(f"  {sym:<16} {cs['deals']:>6} ${cs['pnl']:>8.0f} {avg_l:>10.2f}")

# =========================================================================
# Verdict
# =========================================================================
print(f"\n{'='*120}")
print("  VERDICT")
print(f"{'='*120}")

ranked = sorted(results.items(), key=lambda x: x[1]["total_pnl"], reverse=True)
winner_label, winner = ranked[0]
delta_pnl = winner["total_pnl"] - bl["total_pnl"]
delta_pct = (winner["total_pnl"] / bl["total_pnl"] - 1) * 100 if bl["total_pnl"] else 0

print(f"\n  Winner: {winner_label}")
print(f"  PnL: ${winner['total_pnl']:,.0f} ({delta_pct:+.1f}% vs baseline, ${delta_pnl:+,.0f})")
print(f"  ROI: {winner['roi_pct']:.2f}% over 90 days")
print(f"  Deals: {winner['deals']} | Avg Duration: {winner['avg_dur']:.1f}h | Avg Layers: {winner['avg_layers']:.2f}")
print(f"  Capital Velocity: {winner['capital_velocity']:.3f} ($ cycled / capital / day)")
print(f"  Total $ Cycled: ${winner['total_invested']:,.0f}")

# Annualized projection
ann_roi = winner['roi_pct'] / 90 * 365
print(f"\n  Annualized ROI (projected): {ann_roi:.1f}%")

if len(ranked) > 1:
    ru_label, ru = ranked[1]
    print(f"\n  Runner-up: {ru_label}")
    print(f"  PnL: ${ru['total_pnl']:,.0f} ({(ru['total_pnl']/bl['total_pnl']-1)*100:+.1f}% vs baseline)")

conn.close()
