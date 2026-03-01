"""DCA Timeframe Comparison: 15m vs 1h on all 5 paper bot coins.

MARKUP-exit windows only (true accumulation). ETF era (Jan 2023+).
Matches paper bot universe: ETH, BTC, SOL, LINK, XRP.
"""
import sqlite3
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dca_long_sweep import (
    SweepParams, LongDCAEngine, load_candles, add_regime, get_dca_windows
)

DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'

COINS = ['ETH/USDC', 'BTC/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
CAPITAL = 2500
MIN_DATE = '2023-01-01'

# Parameter grid — same configs on both timeframes
PARAMS = [
    SweepParams(tp_pct=0.015, dev_pct=0.025, so_mult=2.0, max_layers=8, base_pct=0.05, adaptive=False),
    SweepParams(tp_pct=0.010, dev_pct=0.020, so_mult=2.0, max_layers=8, base_pct=0.05, adaptive=False),
    SweepParams(tp_pct=0.008, dev_pct=0.015, so_mult=2.0, max_layers=6, base_pct=0.05, adaptive=False),
    SweepParams(tp_pct=0.008, dev_pct=0.012, so_mult=2.5, max_layers=5, base_pct=0.05, adaptive=False),
    SweepParams(tp_pct=0.008, dev_pct=0.012, so_mult=2.5, max_layers=10, base_pct=0.05, adaptive=False),
    SweepParams(tp_pct=0.015, dev_pct=0.025, so_mult=2.0, max_layers=8, base_pct=0.05, adaptive=True),
    SweepParams(tp_pct=0.010, dev_pct=0.020, so_mult=2.0, max_layers=8, base_pct=0.05, adaptive=True),
    SweepParams(tp_pct=0.008, dev_pct=0.015, so_mult=2.0, max_layers=6, base_pct=0.05, adaptive=True),
    SweepParams(tp_pct=0.008, dev_pct=0.012, so_mult=2.5, max_layers=5, base_pct=0.05, adaptive=True),
    SweepParams(tp_pct=0.006, dev_pct=0.010, so_mult=1.5, max_layers=5, base_pct=0.05, adaptive=True),
    SweepParams(tp_pct=0.020, dev_pct=0.030, so_mult=2.0, max_layers=8, base_pct=0.05, adaptive=False),
    SweepParams(tp_pct=0.020, dev_pct=0.030, so_mult=2.0, max_layers=8, base_pct=0.05, adaptive=True),
]


def run_on_windows(coin, tf, windows, params):
    """Run a single param config on given windows at given timeframe."""
    engine = LongDCAEngine(params, CAPITAL)
    total_candles = 0
    for w in windows:
        df = load_candles(coin, tf, w['start'], w['end'])
        if df.empty:
            continue
        df = add_regime(df)
        for _, row in df.iterrows():
            if pd.notna(row.get('atr_pct')):
                engine.update_regime(row['regime'], row['atr_pct'])
            engine.tick(row['close'], row['high'], row['low'], str(row['date']))
            total_candles += 1
        if len(df) > 0:
            engine.force_close(df.iloc[-1]['close'], str(df.iloc[-1]['date']))
    return {
        'roi': engine.roi, 'pnl': engine.total_pnl,
        'lots': engine.total_lots_closed, 'wr': engine.win_rate,
        'dd': engine._max_dd * 100, 'deals': engine.deals_completed,
        'candles': total_candles,
    }


def main():
    print("=" * 120)
    print("DCA TIMEFRAME COMPARISON: 15m vs 1h")
    print(f"Coins: {', '.join(c.split('/')[0] for c in COINS)} | Capital: ${CAPITAL}/coin | MARKUP-exit windows | ETF era")
    print("=" * 120)

    # Get windows for all coins
    coin_windows = {}
    for coin in COINS:
        try:
            windows = get_dca_windows(coin, 'high')
            etf = [w for w in windows if w['end'] >= '2023-03-12']
            markup = [w for w in etf if w['exit_to'] == 'MARKUP']
            coin_windows[coin] = markup
            days = sum(max(0, (datetime.strptime(w['end'], '%Y-%m-%d') -
                               datetime.strptime(max(w['start'], '2023-03-12'), '%Y-%m-%d')).days)
                       for w in markup)
            print(f"  {coin:12} {len(markup)} MARKUP windows, ~{days} days")
        except Exception as e:
            print(f"  {coin:12} FAILED: {e}")

    # Run sweep for each coin on both timeframes
    for coin in COINS:
        windows = coin_windows.get(coin, [])
        if not windows:
            print(f"\n  {coin}: No windows, skipping")
            continue

        short = coin.split('/')[0]
        print(f"\n{'='*120}")
        print(f"  {coin} — {len(windows)} MARKUP-exit windows")
        print(f"  {'Label':<45} {'15m ROI':>8} {'15m PnL':>9} {'15m Lots':>9} | {'1h ROI':>8} {'1h PnL':>9} {'1h Lots':>9} | {'Delta':>7}")
        print(f"  {'_'*45} {'_'*8} {'_'*9} {'_'*9}   {'_'*8} {'_'*9} {'_'*9}   {'_'*7}")

        for p in PARAMS:
            r15 = run_on_windows(coin, '15m', windows, p)
            r1h = run_on_windows(coin, '1h', windows, p)
            delta = r15['roi'] - r1h['roi']
            print(f"  {p.label:<45} {r15['roi']:>+7.1f}% ${r15['pnl']:>+7.1f} {r15['lots']:>9} | "
                  f"{r1h['roi']:>+7.1f}% ${r1h['pnl']:>+7.1f} {r1h['lots']:>9} | {delta:>+6.1f}%")

    # Cross-coin summary: best param per coin per timeframe
    print(f"\n{'='*120}")
    print("BEST CONFIG PER COIN PER TIMEFRAME")
    print(f"{'='*120}")
    print(f"  {'Coin':<8} {'TF':>4} {'Best Config':<45} {'ROI':>8} {'PnL':>9} {'Lots':>6} {'WR%':>6}")
    print(f"  {'_'*8} {'_'*4} {'_'*45} {'_'*8} {'_'*9} {'_'*6} {'_'*6}")

    for coin in COINS:
        windows = coin_windows.get(coin, [])
        if not windows:
            continue
        short = coin.split('/')[0]
        for tf in ['15m', '1h']:
            best_r = None
            best_p = None
            for p in PARAMS:
                r = run_on_windows(coin, tf, windows, p)
                if best_r is None or r['roi'] > best_r['roi']:
                    best_r = r
                    best_p = p
            print(f"  {short:<8} {tf:>4} {best_p.label:<45} {best_r['roi']:>+7.1f}% ${best_r['pnl']:>+7.1f} {best_r['lots']:>6} {best_r['wr']:>5.1f}%")

    print(f"\n{'='*120}")
    print("Done.")


if __name__ == '__main__':
    main()
