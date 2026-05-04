"""Backtest 4 trailing stop configs + fixed TP against actual candle data."""
import sqlite3, sys
import numpy as np

DB_PATH = r"C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db"
conn = sqlite3.connect(DB_PATH)

CONFIGS = [
    {"name": "Fixed TP (1.5%)", "act": None, "cb": None},
    {"name": "Current (1.5%/0.5%)", "act": 0.015, "cb": 0.005},
    {"name": "Opt1 (1.5%/0.25%)", "act": 0.015, "cb": 0.0025},
    {"name": "Opt2 (2.0%/0.5%)", "act": 0.020, "cb": 0.005},
    {"name": "Opt3 (1.75%/0.25%)", "act": 0.0175, "cb": 0.0025},
]

COINS = ["TAO/USDT", "ZEC/USDT", "FET/USDT", "JTO/USDT", "HYPE/USDT"]
CAPITAL = 50000
PER_COIN = CAPITAL / len(COINS)
BO_PCT = 0.30
TP_PCT = 0.015
SO_DEV = 0.025
SO_MULT = 1.5
MAX_LAYERS = 12
TAKER_FEE = 0.00035
MAKER_FEE = 0.00025


def get_candles(symbol):
    rows = conn.execute(
        "SELECT timestamp, open, high, low, close FROM candles "
        "WHERE symbol=? AND timeframe='1h' ORDER BY timestamp",
        (symbol,)
    ).fetchall()
    # Last 365 days worth
    if len(rows) > 365 * 24:
        rows = rows[-365*24:]
    return rows


def simulate(candles, config):
    capital = PER_COIN
    total_pnl = 0.0
    trades = 0
    wins = 0
    trade_pnls = []

    coins_held = 0.0
    avg_entry = 0.0
    layers = 0
    cost = 0.0

    trail_active = False
    trail_peak = 0.0

    is_fixed = config["act"] is None

    for ts, o, h, l, c in candles:
        if c <= 0 or np.isnan(c):
            continue

        # --- Check TP ---
        if coins_held > 0:
            tp = avg_entry * (1 + TP_PCT)
            fill = None
            taker = False

            if is_fixed:
                if h >= tp:
                    fill = tp
            else:
                activation = avg_entry * (1 + config["act"])
                if trail_active:
                    trail_peak = max(trail_peak, h)
                    trigger = trail_peak * (1 - config["cb"])
                    if l <= trigger:
                        fill = trigger
                        taker = True
                elif h >= activation:
                    trail_active = True
                    trail_peak = h
                    trigger = trail_peak * (1 - config["cb"])
                    if l <= trigger:
                        fill = trigger
                        taker = True

            if fill is not None:
                proceeds = coins_held * fill
                fee = proceeds * (TAKER_FEE if taker else MAKER_FEE)
                pnl = proceeds - cost - fee
                total_pnl += pnl
                capital += proceeds - fee
                trades += 1
                if pnl > 0:
                    wins += 1
                pnl_pct = (pnl / cost * 100) if cost > 0 else 0
                trade_pnls.append(pnl_pct)
                coins_held = 0; avg_entry = 0; layers = 0; cost = 0
                trail_active = False; trail_peak = 0
                continue

        # --- DCA entry ---
        if layers >= MAX_LAYERS:
            continue

        buy = False
        if layers == 0:
            buy = True
        else:
            so_trigger = avg_entry * (1 - SO_DEV)
            if c <= so_trigger:
                buy = True

        if buy and capital > 1:
            if layers == 0:
                order = min(PER_COIN * BO_PCT, capital)
            else:
                order = min(PER_COIN * BO_PCT * (SO_MULT ** layers), capital)

            fee = order * TAKER_FEE
            capital -= (order + fee)
            nc = order / c
            old_val = coins_held * avg_entry
            coins_held += nc
            avg_entry = (old_val + order) / coins_held
            cost += order + fee
            layers += 1
            trail_active = False; trail_peak = 0

    # Close remainder
    if coins_held > 0 and len(candles) > 0:
        last_c = candles[-1][4]
        proceeds = coins_held * last_c
        fee = proceeds * TAKER_FEE
        pnl = proceeds - cost - fee
        total_pnl += pnl
        trades += 1
        if pnl > 0: wins += 1
        trade_pnls.append((pnl / cost * 100) if cost > 0 else 0)

    avg_pnl_pct = np.mean(trade_pnls) if trade_pnls else 0
    med_pnl_pct = np.median(trade_pnls) if trade_pnls else 0
    return {
        "pnl": total_pnl, "trades": trades, "wins": wins,
        "avg_pnl_pct": avg_pnl_pct, "med_pnl_pct": med_pnl_pct,
        "trade_pnls": trade_pnls,
    }


# Run
print("TRAILING STOP BACKTEST — ACTUAL CANDLE DATA")
print(f"Coins: {', '.join(c.replace('/USDT','') for c in COINS)}")
print(f"Capital: ${CAPITAL:,}, Per coin: ${PER_COIN:,.0f}, 365d window")
print("=" * 95)

all_results = {}
for cfg in CONFIGS:
    coin_results = {}
    total_pnl = 0; total_trades = 0; total_wins = 0; all_trade_pnls = []
    for coin in COINS:
        candles = get_candles(coin)
        if not candles:
            continue
        r = simulate(candles, cfg)
        coin_results[coin] = r
        total_pnl += r["pnl"]
        total_trades += r["trades"]
        total_wins += r["wins"]
        all_trade_pnls.extend(r["trade_pnls"])

    roi = total_pnl / CAPITAL * 100
    wr = total_wins / total_trades * 100 if total_trades > 0 else 0
    avg_t = np.mean(all_trade_pnls) if all_trade_pnls else 0
    med_t = np.median(all_trade_pnls) if all_trade_pnls else 0
    all_results[cfg["name"]] = {
        "pnl": total_pnl, "roi": roi, "trades": total_trades,
        "wins": total_wins, "wr": wr, "avg_t": avg_t, "med_t": med_t,
        "coins": coin_results, "all_pnls": all_trade_pnls,
    }

# Summary
print(f"\n{'Config':<24} {'PnL':>10} {'ROI':>7} {'Trades':>7} {'Win%':>6} {'Avg%':>7} {'Med%':>7} {'$/Trade':>9}")
print("-" * 85)
for name, r in all_results.items():
    avg_d = r["pnl"] / r["trades"] if r["trades"] > 0 else 0
    print(f"{name:<24} ${r['pnl']:>8,.0f} {r['roi']:>6.1f}% {r['trades']:>6} {r['wr']:>5.1f}% {r['avg_t']:>6.2f}% {r['med_t']:>6.2f}% ${avg_d:>8.2f}")

# vs Fixed
print(f"\n{'Config':<24} {'vs Fixed':>10} {'Improvement':>12}")
print("-" * 50)
fp = all_results["Fixed TP (1.5%)"]["pnl"]
for name, r in all_results.items():
    if "Fixed" in name: continue
    d = r["pnl"] - fp
    pct = d / abs(fp) * 100 if fp != 0 else 0
    print(f"{name:<24} ${d:>8,.0f}   {pct:>+9.1f}%")

# Per-coin
print(f"\nPer-coin PnL:")
print(f"{'Coin':<10}", end="")
for cfg in CONFIGS:
    print(f" {cfg['name'][:12]:>12}", end="")
print()
print("-" * 75)
for coin in COINS:
    base = coin.replace("/USDT","")
    print(f"{base:<10}", end="")
    for cfg in CONFIGS:
        r = all_results[cfg["name"]]["coins"].get(coin, {})
        pnl = r.get("pnl", 0)
        print(f" ${pnl:>10,.0f}", end="")
    print()

# Trade distribution
print(f"\nTrade PnL Distribution (% per trade):")
print(f"{'Config':<24} {'<0%':>6} {'0-1%':>6} {'1-1.5%':>7} {'1.5-2%':>7} {'2-3%':>6} {'3-5%':>6} {'>5%':>6}")
print("-" * 75)
for name, r in all_results.items():
    pnls = r["all_pnls"]
    if not pnls: continue
    n = len(pnls)
    bins = [
        sum(1 for p in pnls if p < 0),
        sum(1 for p in pnls if 0 <= p < 1),
        sum(1 for p in pnls if 1 <= p < 1.5),
        sum(1 for p in pnls if 1.5 <= p < 2),
        sum(1 for p in pnls if 2 <= p < 3),
        sum(1 for p in pnls if 3 <= p < 5),
        sum(1 for p in pnls if p >= 5),
    ]
    print(f"{name:<24}", end="")
    for b in bins:
        print(f" {b/n*100:>5.1f}%", end="")
    print()

conn.close()
