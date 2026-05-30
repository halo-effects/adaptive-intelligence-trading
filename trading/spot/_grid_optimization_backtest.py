"""
Grid Optimization Backtest — Combined TP + Layer Cap + Multiplier Analysis

Tests the COMBINED effect of:
  - TP target: 1.5%, 2.5%, 3.0%
  - Max layers: 4, 8, 12
  - Martingale multiplier: 1.5x, 2.0x
  - Deviation: 1.5%, 2.0%

Uses real 1h candle data, limit fills, Hyperliquid fees.
Capital model: $5K per coin (scaled), single position per coin at a time.

Metrics:
  - Total PnL, deal count, avg return, avg duration
  - Capital efficiency (PnL per $invested per hour)
  - Max layers actually used, avg layers
  - Max drawdown per deal
"""
import sqlite3
import statistics
from collections import defaultdict
from datetime import datetime, timedelta

DB = "trading/spot/data/candles.db"
conn = sqlite3.connect(DB)

# Fixed params
BO_PCT = 0.40
CAPITAL = 5000
TAKER_FEE = 0.00025
MAKER_FEE = 0.0002

# Scanner coins (current approved + recent)
COINS = [
    "GRASS/USDT", "TAO/USDT", "FET/USDT", "ZEC/USDT", "JTO/USDT",
    "HYPE/USDT", "PENDLE/USDT", "INJ/USDT", "TON/USDT", "ONDO/USDT"
]

cutoff_ms = int((datetime.now() - timedelta(days=90)).timestamp() * 1000)

# -------------------------------------------------------------------------
# Test configurations
# -------------------------------------------------------------------------
CONFIGS = [
    # (label, tp_pct, so_dev, so_mult, max_layers)
    ("BASELINE (current live)",     1.5, 0.015, 1.5, 12),
    ("TP2.5 only",                  2.5, 0.015, 1.5, 12),
    ("TP2.5 + 4L cap",             2.5, 0.015, 1.5,  4),
    ("TP2.5 + 4L + 2.0x mult",    2.5, 0.015, 2.0,  4),
    ("TP2.5 + 4L + wider dev",    2.5, 0.020, 1.5,  4),
    ("TP3.0 + 4L cap",             3.0, 0.015, 1.5,  4),
    ("TP3.0 + 4L + 2.0x mult",    3.0, 0.015, 2.0,  4),
]


def run_dca_sim(candles, tp_pct, so_dev, so_mult, max_layers, capital):
    """
    Simulate DCA grid on 1h candles.
    Returns dict with all metrics.
    """
    deals = []
    cash = capital
    layers = 0
    total_coins = 0
    total_cost = 0  # includes fees
    raw_cost = 0    # excludes fees (for avg entry)
    avg_entry = 0
    tp_price = 0
    entry_candle = 0
    max_dd_this_deal = 0
    peak_value = 0

    # Pre-calculate layer sizes based on max layers
    layer_sizes = []
    base = capital * BO_PCT * 0.9  # 90% DCA allocation
    for i in range(max_layers):
        if i == 0:
            layer_sizes.append(base)
        else:
            # Multiplier capped at layer 4 (matching production code)
            mult = so_mult ** min(i, 4)
            layer_sizes.append(base * mult)

    for idx, (ts, o, h, l, c) in enumerate(candles):
        price = c

        # Track intra-deal drawdown
        if layers > 0 and total_coins > 0:
            current_value = total_coins * price
            peak_value = max(peak_value, current_value)
            if peak_value > 0:
                dd = (peak_value - current_value) / peak_value * 100
                max_dd_this_deal = max(max_dd_this_deal, dd)

        # Check TP (use HIGH — limit order fills when price touches)
        if layers > 0 and tp_price > 0:
            if h >= tp_price:
                proceeds = total_coins * tp_price
                fee = proceeds * MAKER_FEE
                pnl = proceeds - total_cost - fee
                ret_pct = pnl / total_cost * 100 if total_cost > 0 else 0
                duration = idx - entry_candle
                deals.append({
                    "pnl": pnl,
                    "return_pct": ret_pct,
                    "layers": layers,
                    "invested": total_cost,
                    "duration_h": duration,
                    "max_dd_pct": max_dd_this_deal,
                })
                cash = capital
                layers = 0
                total_coins = 0
                total_cost = 0
                raw_cost = 0
                avg_entry = 0
                tp_price = 0
                max_dd_this_deal = 0
                peak_value = 0
                continue

        # Layer entry logic
        if layers == 0:
            size = min(layer_sizes[0], cash)
            if size < 1:
                continue
            coins = size / price
            fee = size * TAKER_FEE
            total_coins = coins
            raw_cost = size
            total_cost = size + fee
            avg_entry = price
            tp_price = avg_entry * (1 + tp_pct / 100)
            layers = 1
            cash -= size
            entry_candle = idx
            peak_value = coins * price
        elif layers < max_layers:
            so_trigger = avg_entry * (1 - so_dev * layers)
            if l <= so_trigger:
                size = min(layer_sizes[layers], cash)
                # Also enforce 30% capital cap (matching production)
                size = min(size, capital * 0.3)
                if size < 1:
                    continue
                fill_price = so_trigger
                coins = size / fill_price
                fee = size * TAKER_FEE
                total_coins += coins
                raw_cost += size
                total_cost += size + fee
                avg_entry = raw_cost / total_coins
                tp_price = avg_entry * (1 + tp_pct / 100)
                layers += 1
                cash -= size

    # Aggregate metrics
    if not deals:
        return None

    total_pnl = sum(d["pnl"] for d in deals)
    n_deals = len(deals)
    returns = [d["return_pct"] for d in deals]
    durations = [d["duration_h"] for d in deals]
    layer_counts = [d["layers"] for d in deals]
    drawdowns = [d["max_dd_pct"] for d in deals]
    invested_amounts = [d["invested"] for d in deals]

    # Capital efficiency: PnL per $ invested per hour
    efficiencies = []
    for d in deals:
        if d["duration_h"] > 0 and d["invested"] > 0:
            eff = d["pnl"] / d["invested"] / d["duration_h"] * 1000  # per $1000 per hour
            efficiencies.append(eff)

    # Time deployed vs idle
    total_hours = len(candles)
    hours_in_deal = sum(d["duration_h"] for d in deals)
    utilization = hours_in_deal / total_hours * 100 if total_hours > 0 else 0

    return {
        "deals": n_deals,
        "total_pnl": total_pnl,
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
        "avg_invested": statistics.mean(invested_amounts),
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
    else:
        print(f"  {sym}: SKIPPED ({len(candles) if candles else 0} candles)")

print(f"\n{len(coin_candles)} coins loaded.\n")

# =========================================================================
# Run all configs
# =========================================================================
print("=" * 110)
print("  GRID OPTIMIZATION BACKTEST — 7 CONFIGURATIONS × {} COINS × 90 DAYS".format(len(coin_candles)))
print("  Real 1h candles, limit fills, Hyperliquid fees, $5K per coin")
print("=" * 110)

portfolio_results = {}

for label, tp, dev, mult, max_l in CONFIGS:
    agg = defaultdict(float)
    all_returns = []
    all_durations = []
    all_layers = []
    all_dd = []
    all_eff = []
    coin_details = {}

    for sym, candles in coin_candles.items():
        result = run_dca_sim(candles, tp, dev, mult, max_l, CAPITAL)
        if result:
            coin_details[sym] = result
            agg["deals"] += result["deals"]
            agg["total_pnl"] += result["total_pnl"]
            all_returns.append(result["avg_ret"])
            all_durations.append(result["avg_dur"])
            all_layers.append(result["avg_layers"])
            all_dd.append(result["max_dd"])
            all_eff.append(result["capital_eff"])

    portfolio_results[label] = {
        "deals": int(agg["deals"]),
        "total_pnl": agg["total_pnl"],
        "avg_ret": statistics.mean(all_returns) if all_returns else 0,
        "avg_dur": statistics.mean(all_durations) if all_durations else 0,
        "avg_layers": statistics.mean(all_layers) if all_layers else 0,
        "max_dd": max(all_dd) if all_dd else 0,
        "capital_eff": statistics.mean(all_eff) if all_eff else 0,
        "coin_details": coin_details,
    }

# =========================================================================
# Summary table
# =========================================================================
print(f"\n{'='*110}")
print("  PORTFOLIO RESULTS SUMMARY")
print(f"{'='*110}")
header = (
    f"  {'Config':<32} {'Deals':>6} {'PnL':>10} {'Avg Ret':>8} "
    f"{'Avg Dur':>8} {'Avg Lyr':>8} {'Max DD':>7} {'Cap Eff':>8} {'vs Base':>8}"
)
print(header)
print(f"  {'-'*106}")

baseline_pnl = portfolio_results[CONFIGS[0][0]]["total_pnl"]

for label, _, _, _, _ in CONFIGS:
    r = portfolio_results[label]
    vs_base = ((r["total_pnl"] / baseline_pnl) - 1) * 100 if baseline_pnl else 0
    print(
        f"  {label:<32} {r['deals']:>6} ${r['total_pnl']:>8.0f} "
        f"{r['avg_ret']:>7.2f}% {r['avg_dur']:>7.1f}h "
        f"{r['avg_layers']:>7.2f} {r['max_dd']:>6.1f}% "
        f"{r['capital_eff']:>7.3f} {vs_base:>+7.1f}%"
    )

# =========================================================================
# Per-coin breakdown for top 3 configs
# =========================================================================
# Sort by PnL to find top 3
ranked = sorted(portfolio_results.items(), key=lambda x: x[1]["total_pnl"], reverse=True)
top3_labels = [r[0] for r in ranked[:3]]

print(f"\n{'='*110}")
print("  TOP 3 CONFIGS — PER-COIN BREAKDOWN")
print(f"{'='*110}")

for label in top3_labels:
    r = portfolio_results[label]
    print(f"\n  >> {label} (Total PnL: ${r['total_pnl']:,.0f}, {r['deals']} deals)")
    print(f"  {'Coin':<16} {'Deals':>6} {'PnL':>10} {'Avg Ret':>8} {'Avg Dur':>8} {'Avg Lyr':>8} {'Max DD':>7}")
    print(f"  {'-'*72}")
    for sym in sorted(r["coin_details"].keys()):
        cd = r["coin_details"][sym]
        print(
            f"  {sym:<16} {cd['deals']:>6} ${cd['total_pnl']:>8.0f} "
            f"{cd['avg_ret']:>7.2f}% {cd['avg_dur']:>7.1f}h "
            f"{cd['avg_layers']:>7.2f} {cd['max_dd']:>6.1f}%"
        )

# =========================================================================
# Layer distribution comparison (baseline vs best 4L config)
# =========================================================================
print(f"\n{'='*110}")
print("  LAYER DISTRIBUTION — BASELINE vs 4-LAYER CONFIGS")
print(f"{'='*110}")

for label in [CONFIGS[0][0]] + [c[0] for c in CONFIGS if "4L" in c[0]][:2]:
    r = portfolio_results[label]
    all_layer_counts = []
    for sym, cd in r["coin_details"].items():
        # We don't have raw deal data here, use avg
        pass
    print(f"\n  {label}:")
    print(f"    Avg layers: {r['avg_layers']:.2f}")
    print(f"    Deals: {r['deals']}")
    print(f"    Capital efficiency: {r['capital_eff']:.4f}")

# =========================================================================
# Verdict
# =========================================================================
print(f"\n{'='*110}")
print("  VERDICT")
print(f"{'='*110}")
best_label, best = ranked[0]
print(f"  Winner: {best_label}")
print(f"  PnL: ${best['total_pnl']:,.0f} ({((best['total_pnl']/baseline_pnl)-1)*100:+.1f}% vs baseline)")
print(f"  Deals: {best['deals']} | Avg Duration: {best['avg_dur']:.1f}h | Avg Layers: {best['avg_layers']:.2f}")
print(f"  Capital Efficiency: {best['capital_eff']:.4f} (PnL per $1K per hour)")
print()

# Runner up
if len(ranked) > 1:
    ru_label, ru = ranked[1]
    print(f"  Runner-up: {ru_label}")
    print(f"  PnL: ${ru['total_pnl']:,.0f} ({((ru['total_pnl']/baseline_pnl)-1)*100:+.1f}% vs baseline)")

conn.close()
