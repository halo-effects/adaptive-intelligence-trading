"""DCA Long-Only Sweep on CORRECTLY CLASSIFIED DCA Windows Only.

Only runs on DCA windows that exit to MARKUP (true accumulation).
Excludes windows that exit to MARKDOWN (misclassified distribution).
ETF era: Jan 2023+ only. 15m candles. Long-only.

This answers: "How much does 15m grinding add to properly-classified accumulation phases?"
"""
import sqlite3
import sys
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack
from dca_long_sweep import (
    SweepParams, LongDCAEngine, load_candles, add_regime, get_dca_windows
)

DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'candles.db'

COINS = ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']
CAPITAL = 2500
TF = '15m'
MIN_DATE = '2023-01-01'  # ETF era


def run_clean_sweep():
    print("=" * 110)
    print("DCA LONG-ONLY SWEEP — CORRECTLY CLASSIFIED WINDOWS ONLY (exit to MARKUP)")
    print(f"Capital: ${CAPITAL}/coin | Timeframe: {TF} | Period: Jan 2023+ | Long-only")
    print("=" * 110)

    # Get DCA windows with exit direction
    print("\n-- DCA Windows (ETF era, MARKUP exits only) --")
    all_windows = {}
    all_windows_full = {}  # Including MARKDOWN exits for comparison
    
    for coin in COINS:
        try:
            windows = get_dca_windows(coin, 'high')
            # Filter to ETF era + 15m data availability
            etf_windows = [w for w in windows if w['end'] >= '2023-03-12']
            markup_windows = [w for w in etf_windows if w['exit_to'] == 'MARKUP']
            markdown_windows = [w for w in etf_windows if w['exit_to'] == 'MARKDOWN']
            all_windows[coin] = markup_windows
            all_windows_full[coin] = etf_windows
            
            markup_days = sum(
                max(0, (datetime.strptime(w['end'], '%Y-%m-%d') -
                         datetime.strptime(max(w['start'], '2023-03-12'), '%Y-%m-%d')).days)
                for w in markup_windows)
            md_days = sum(
                max(0, (datetime.strptime(w['end'], '%Y-%m-%d') -
                         datetime.strptime(max(w['start'], '2023-03-12'), '%Y-%m-%d')).days)
                for w in markdown_windows)
            
            print(f"  {coin:12} MARKUP exits: {len(markup_windows)} windows, ~{markup_days}d | "
                  f"MARKDOWN exits: {len(markdown_windows)} windows, ~{md_days}d (excluded)")
        except Exception as e:
            print(f"  {coin:12} FAILED - {e}")

    # Parameter sweep — focused on what matters
    params_list = [
        # Baseline: V13 current (daily ticks, simulated as fixed on 15m)
        SweepParams(tp_pct=0.015, dev_pct=0.025, so_mult=2.0, max_layers=8,
                    base_pct=0.05, adaptive=False),
        # Tighter TP for more cycles
        SweepParams(tp_pct=0.010, dev_pct=0.020, so_mult=2.0, max_layers=8,
                    base_pct=0.05, adaptive=False),
        SweepParams(tp_pct=0.008, dev_pct=0.015, so_mult=2.0, max_layers=6,
                    base_pct=0.05, adaptive=False),
        SweepParams(tp_pct=0.008, dev_pct=0.012, so_mult=2.5, max_layers=5,
                    base_pct=0.05, adaptive=False),
        # Adaptive variants
        SweepParams(tp_pct=0.015, dev_pct=0.025, so_mult=2.0, max_layers=8,
                    base_pct=0.05, adaptive=True),
        SweepParams(tp_pct=0.010, dev_pct=0.020, so_mult=2.0, max_layers=8,
                    base_pct=0.05, adaptive=True),
        SweepParams(tp_pct=0.008, dev_pct=0.015, so_mult=2.0, max_layers=6,
                    base_pct=0.05, adaptive=True),
        SweepParams(tp_pct=0.008, dev_pct=0.012, so_mult=2.5, max_layers=5,
                    base_pct=0.05, adaptive=True),
        # Bigger base order
        SweepParams(tp_pct=0.010, dev_pct=0.020, so_mult=2.0, max_layers=8,
                    base_pct=0.10, adaptive=False),
        SweepParams(tp_pct=0.008, dev_pct=0.012, so_mult=2.5, max_layers=5,
                    base_pct=0.10, adaptive=False),
        # Scalper (very tight)
        SweepParams(tp_pct=0.006, dev_pct=0.010, so_mult=1.5, max_layers=5,
                    base_pct=0.05, adaptive=True),
        # Wide and safe
        SweepParams(tp_pct=0.020, dev_pct=0.030, so_mult=2.0, max_layers=8,
                    base_pct=0.05, adaptive=False),
    ]

    # Run on MARKUP-only windows
    print(f"\n{'=' * 110}")
    print("RESULTS: MARKUP-EXIT WINDOWS ONLY (correctly classified accumulation)")
    print(f"{'=' * 110}")

    results = {}  # coin -> [result dicts]
    
    for coin in COINS:
        if coin not in all_windows or not all_windows[coin]:
            print(f"\n  {coin}: No MARKUP-exit DCA windows")
            continue

        windows = all_windows[coin]
        results[coin] = []
        
        print(f"\n  {coin} ({TF}) — {len(windows)} accumulation windows")
        print(f"  {'Label':<45} {'ROI':>8} {'PnL':>9} {'Lots':>6} {'WR%':>6} {'DD%':>6}")
        print(f"  {'─'*45} {'─'*8} {'─'*9} {'─'*6} {'─'*6} {'─'*6}")

        for p in params_list:
            engine = LongDCAEngine(p, CAPITAL)
            total_candles = 0

            for w in windows:
                df = load_candles(coin, TF, w['start'], w['end'])
                if df.empty:
                    continue
                df = add_regime(df)
                for _, row in df.iterrows():
                    if pd.notna(row.get('atr_pct')):
                        engine.update_regime(row['regime'], row['atr_pct'])
                    engine.tick(row['close'], row['high'], row['low'], str(row['date']))
                    total_candles += 1
                # Force close at window end
                if len(df) > 0:
                    engine.force_close(df.iloc[-1]['close'], str(df.iloc[-1]['date']))

            r = {
                'label': p.label, 'roi': engine.roi, 'pnl': engine.total_pnl,
                'lots': engine.total_lots_closed, 'wr': engine.win_rate,
                'dd': engine._max_dd * 100, 'deals': engine.deals_completed,
            }
            results[coin].append(r)
            print(f"  {p.label:<45} {r['roi']:>+7.1f}% ${r['pnl']:>+8.1f} {r['lots']:>6} "
                  f"{r['wr']:>5.1f}% {r['dd']:>5.1f}%")

    # Also run on ALL windows (including MARKDOWN exits) for comparison
    print(f"\n{'=' * 110}")
    print("COMPARISON: ALL WINDOWS vs MARKUP-ONLY (best 3 params)")
    print(f"{'=' * 110}")

    # Pick top 3 params by average ROI across coins (MARKUP-only)
    param_avg = {}
    for i, p in enumerate(params_list):
        rois = []
        for coin in COINS:
            if coin in results and i < len(results[coin]):
                rois.append(results[coin][i]['roi'])
        if rois:
            param_avg[i] = np.mean(rois)
    
    top3_idx = sorted(param_avg.keys(), key=lambda x: param_avg[x], reverse=True)[:3]
    
    print(f"\n  {'Label':<45} {'Coin':>8} {'MARKUP ROI':>11} {'ALL ROI':>9} {'Delta':>8}")
    print(f"  {'─'*45} {'─'*8} {'─'*11} {'─'*9} {'─'*8}")

    for idx in top3_idx:
        p = params_list[idx]
        for coin in COINS:
            if coin not in all_windows_full:
                continue
            
            # MARKUP-only (already computed)
            markup_roi = results[coin][idx]['roi'] if coin in results and idx < len(results[coin]) else float('nan')
            
            # ALL windows
            engine_all = LongDCAEngine(p, CAPITAL)
            for w in all_windows_full.get(coin, []):
                df = load_candles(coin, TF, w['start'], w['end'])
                if df.empty:
                    continue
                df = add_regime(df)
                for _, row in df.iterrows():
                    if pd.notna(row.get('atr_pct')):
                        engine_all.update_regime(row['regime'], row['atr_pct'])
                    engine_all.tick(row['close'], row['high'], row['low'], str(row['date']))
                if len(df) > 0:
                    engine_all.force_close(df.iloc[-1]['close'], str(df.iloc[-1]['date']))
            all_roi = engine_all.roi
            
            delta = markup_roi - all_roi if not np.isnan(markup_roi) else float('nan')
            coin_short = coin.split('/')[0]
            print(f"  {p.label:<45} {coin_short:>8} {markup_roi:>+10.1f}% {all_roi:>+8.1f}% {delta:>+7.1f}%")

    # Per-window detail for best param on each coin
    print(f"\n{'=' * 110}")
    print("PER-WINDOW DETAIL (best param per coin, MARKUP-exit only)")
    print(f"{'=' * 110}")

    for coin in COINS:
        if coin not in results or not results[coin]:
            continue
        
        # Find best param for this coin
        best_idx = max(range(len(results[coin])), key=lambda i: results[coin][i]['roi'])
        best_p = params_list[best_idx]
        best_r = results[coin][best_idx]
        
        print(f"\n  {coin} — Best: {best_p.label} (ROI: {best_r['roi']:+.1f}%)")
        print(f"  {'Start':>12} {'End':>12} {'Days':>5} {'Candles':>8} {'ROI':>8} {'PnL':>9} {'Lots':>5} {'WR%':>6}")
        print(f"  {'-'*12} {'-'*12} {'-'*5} {'-'*8} {'-'*8} {'-'*9} {'-'*5} {'-'*6}")
        
        for w in all_windows[coin]:
            engine = LongDCAEngine(best_p, CAPITAL)
            df = load_candles(coin, TF, w['start'], w['end'])
            if df.empty:
                print(f"  {w['start']:>12} {w['end']:>12}  NO DATA")
                continue
            df = add_regime(df)
            for _, row in df.iterrows():
                if pd.notna(row.get('atr_pct')):
                    engine.update_regime(row['regime'], row['atr_pct'])
                engine.tick(row['close'], row['high'], row['low'], str(row['date']))
            if len(df) > 0:
                engine.force_close(df.iloc[-1]['close'], str(df.iloc[-1]['date']))
            
            days = (datetime.strptime(w['end'], '%Y-%m-%d') - datetime.strptime(w['start'], '%Y-%m-%d')).days
            print(f"  {w['start']:>12} {w['end']:>12} {days:>5} {len(df):>8} {engine.roi:>+7.1f}% "
                  f"${engine.total_pnl:>+8.1f} {engine.total_lots_closed:>5} {engine.win_rate:>5.1f}%")

    # Summary
    print(f"\n{'=' * 110}")
    print("CROSS-COIN SUMMARY (MARKUP-exit windows only)")
    print(f"{'=' * 110}")
    
    print(f"\n  {'Label':<45}", end='')
    for coin in COINS:
        print(f" {coin.split('/')[0]:>8}", end='')
    print(f" {'AVG':>8} {'TOTAL$':>9}")
    print(f"  {'─'*45}", end='')
    for _ in COINS:
        print(f" {'─'*8}", end='')
    print(f" {'─'*8} {'─'*9}")
    
    for i, p in enumerate(params_list):
        print(f"  {p.label:<45}", end='')
        rois = []
        total_pnl = 0
        for coin in COINS:
            if coin in results and i < len(results[coin]):
                r = results[coin][i]
                rois.append(r['roi'])
                total_pnl += r['pnl']
                print(f" {r['roi']:>+7.1f}%", end='')
            else:
                print(f" {'n/a':>8}", end='')
        avg = np.mean(rois) if rois else 0
        print(f" {avg:>+7.1f}% ${total_pnl:>+8.1f}")
    
    print(f"\n{'=' * 110}")
    print("Done.")


if __name__ == '__main__':
    run_clean_sweep()
