"""Main entry point: fetch data, screen coins, backtest, optimize, generate report."""
import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

from .config import MartingaleConfig
from .data_fetcher import fetch_multiple_symbols, get_top_pairs
from .coin_screener import screen_coins
from .martingale_engine import MartingaleBot, BacktestResult
from .regime_detector import classify_regime
from .optimizer import optimize

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def run_backtest_suite(symbols: list = None, timeframes: list = None,
                       days_back: int = 90, top_coins: int = 5,
                       optimize_top: int = 3, quick_optimize: bool = True):
    """Full pipeline: screen → backtest → optimize → report."""
    cfg = MartingaleConfig()
    if timeframes is None:
        timeframes = cfg.timeframes

    # 1. Screen coins
    print("=" * 60)
    print("STEP 1: Screening coins")
    print("=" * 60)
    if symbols is None:
        symbols = get_top_pairs(15)
    rankings = screen_coins(symbols, "1h", days_back=min(days_back, 30))
    print("\nCoin Rankings:")
    print(rankings[["symbol", "total", "volume", "atr_pct", "hurst", "bbw"]].to_string())

    top_symbols = rankings.head(top_coins)["symbol"].tolist()
    print(f"\nTop {top_coins} for backtesting: {top_symbols}")

    # 2. Fetch data for all timeframes
    print("\n" + "=" * 60)
    print("STEP 2: Fetching data")
    print("=" * 60)
    all_data = {}  # {symbol: {timeframe: df}}
    for sym in top_symbols:
        all_data[sym] = {}
        for tf in timeframes:
            data = fetch_multiple_symbols([sym], tf, days_back)
            if sym in data:
                all_data[sym][tf] = data[sym]

    # 3. Run backtests with default params
    print("\n" + "=" * 60)
    print("STEP 3: Running backtests (default params)")
    print("=" * 60)
    backtest_results = []
    for sym in top_symbols:
        for tf in timeframes:
            if tf not in all_data.get(sym, {}):
                continue
            df = all_data[sym][tf]
            bot = MartingaleBot(cfg)
            res = bot.run(df, sym, tf)
            backtest_results.append(res)
            s = res.summary_dict()
            print(f"  {sym} {tf}: {s['total_trades']} trades, "
                  f"PnL={s['total_profit']:.2f} ({s['total_profit_pct']:.1f}%), "
                  f"WR={s['win_rate']:.0f}%, DD={s['max_drawdown_pct']:.1f}%")

    # 4. Optimize top combos
    print("\n" + "=" * 60)
    print("STEP 4: Optimizing top combos")
    print("=" * 60)
    # Sort by profit factor to pick top combos
    sorted_results = sorted(backtest_results, key=lambda r: r.profit_factor, reverse=True)
    opt_results = {}
    seen = set()
    for res in sorted_results[:optimize_top]:
        key = res.symbol
        if key in seen:
            continue
        seen.add(key)
        print(f"\n  Optimizing {key}...")
        opt_df = optimize(all_data[key], key, cfg, quick=quick_optimize)
        opt_results[key] = opt_df
        print(f"  Top result: {opt_df.iloc[0].to_dict()}" if len(opt_df) > 0 else "  No results")

    # 5. Generate report
    print("\n" + "=" * 60)
    print("STEP 5: Generating report")
    print("=" * 60)
    report_path = generate_report(backtest_results, rankings, opt_results, all_data)
    print(f"\nReport saved to: {report_path}")
    return report_path


def generate_report(results: list, rankings: pd.DataFrame,
                    opt_results: dict, all_data: dict) -> str:
    """Generate interactive HTML report."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    html_parts = ["""<!DOCTYPE html><html><head>
    <title>Martingale Backtester Report</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }
        h1, h2, h3 { color: #00d4ff; }
        table { border-collapse: collapse; width: 100%; margin: 10px 0; }
        th, td { border: 1px solid #333; padding: 8px; text-align: right; }
        th { background: #16213e; }
        tr:nth-child(even) { background: #0f3460; }
        .card { background: #16213e; padding: 15px; margin: 10px 0; border-radius: 8px; }
        .positive { color: #00ff88; } .negative { color: #ff4444; }
    </style></head><body>"""]

    html_parts.append(f"<h1>🎰 Martingale DCA Backtester Report</h1>")
    html_parts.append(f"<p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>")

    # Coin rankings table
    html_parts.append("<h2>📊 Coin Screening Rankings</h2><div class='card'>")
    html_parts.append(rankings[["symbol", "total", "volume", "atr_pct", "hurst", "bbw"]].to_html(
        index=False, classes="ranking-table"))
    html_parts.append("</div>")

    # Summary table
    html_parts.append("<h2>📈 Backtest Results Summary</h2><div class='card'>")
    summaries = [r.summary_dict() for r in results]
    sum_df = pd.DataFrame(summaries)
    html_parts.append(sum_df.to_html(index=False))
    html_parts.append("</div>")

    # Equity curves
    html_parts.append("<h2>💰 Equity Curves</h2>")
    for res in results:
        if len(res.equity_curve) == 0:
            continue
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=res.equity_curve["timestamp"],
            y=res.equity_curve["equity"],
            mode="lines", name="Equity",
            line=dict(color="#00d4ff")
        ))
        fig.update_layout(
            title=f"{res.symbol} {res.timeframe} — Equity Curve",
            template="plotly_dark", height=350,
            margin=dict(l=50, r=20, t=40, b=30)
        )
        html_parts.append(f"<div>{fig.to_html(full_html=False, include_plotlyjs=False)}</div>")

    # Regime overlay on price (for first result per symbol)
    html_parts.append("<h2>🎯 Price + Regime Detection</h2>")
    seen_sym = set()
    for res in results:
        if res.symbol in seen_sym:
            continue
        seen_sym.add(res.symbol)
        tf = res.timeframe
        sym = res.symbol
        if sym in all_data and tf in all_data[sym]:
            df = all_data[sym][tf]
            regimes = res.regimes
            colors = {"CHOPPY": "#00ff88", "RANGING": "#88ff00", "MILD_TREND": "#ffaa00",
                      "TRENDING": "#ff4444", "EXTREME": "#ff00ff"}
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df["timestamp"], open=df["open"], high=df["high"],
                low=df["low"], close=df["close"], name="Price"
            ))
            # Add regime background as colored markers at the bottom
            for regime, color in colors.items():
                mask = regimes == regime
                if mask.any():
                    fig.add_trace(go.Scatter(
                        x=df["timestamp"][mask], y=df["low"][mask] * 0.998,
                        mode="markers", marker=dict(size=3, color=color),
                        name=regime
                    ))
            fig.update_layout(
                title=f"{sym} {tf} — Regime Overlay",
                template="plotly_dark", height=450,
                xaxis_rangeslider_visible=False,
                margin=dict(l=50, r=20, t=40, b=30)
            )
            html_parts.append(f"<div>{fig.to_html(full_html=False, include_plotlyjs=False)}</div>")

    # Optimization results
    if opt_results:
        html_parts.append("<h2>⚡ Optimization Results (Top 20)</h2>")
        for sym, opt_df in opt_results.items():
            html_parts.append(f"<h3>{sym}</h3><div class='card'>")
            html_parts.append(opt_df.to_html(index=False))
            html_parts.append("</div>")

            # Heatmap: take_profit vs max_safety_orders colored by profit_factor
            if len(opt_df) > 2:
                fig = go.Figure(data=go.Scatter(
                    x=opt_df["take_profit_pct"], y=opt_df["max_safety_orders"],
                    mode="markers",
                    marker=dict(
                        size=12, color=opt_df["profit_factor"],
                        colorscale="Viridis", showscale=True,
                        colorbar=dict(title="Profit Factor")
                    ),
                    text=opt_df.apply(lambda r: f"PF={r['profit_factor']:.2f} DD={r['max_drawdown_pct']:.1f}%", axis=1),
                ))
                fig.update_layout(
                    title=f"{sym} — TP% vs Max SO (color=Profit Factor)",
                    xaxis_title="Take Profit %", yaxis_title="Max Safety Orders",
                    template="plotly_dark", height=350,
                )
                html_parts.append(f"<div>{fig.to_html(full_html=False, include_plotlyjs=False)}</div>")

    # Deal log for best result
    if results:
        best = max(results, key=lambda r: r.profit_factor if r.total_trades > 0 else 0)
        if best.closed_deals:
            html_parts.append(f"<h2>📋 Deal Log — {best.symbol} {best.timeframe}</h2><div class='card'>")
            deals_data = []
            for d in best.closed_deals[:100]:  # cap at 100
                deals_data.append({
                    "Entry": str(d.entry_time)[:19],
                    "Exit": str(d.close_time)[:19] if d.close_time else "",
                    "SOs": d.so_count,
                    "Avg Entry": f"{d.avg_entry:.2f}",
                    "Exit Price": f"{d.close_price:.2f}" if d.close_price else "",
                    "PnL $": f"{d.pnl:.2f}",
                    "PnL %": f"{d.pnl_pct:.2f}",
                    "Invested": f"{d.total_invested:.2f}",
                })
            html_parts.append(pd.DataFrame(deals_data).to_html(index=False))
            html_parts.append("</div>")

    html_parts.append("</body></html>")

    report_path = RESULTS_DIR / "report.html"
    report_path.write_text("\n".join(html_parts), encoding="utf-8")
    return str(report_path)


if __name__ == "__main__":
    run_backtest_suite(days_back=60, top_coins=5, optimize_top=2, quick_optimize=True)
