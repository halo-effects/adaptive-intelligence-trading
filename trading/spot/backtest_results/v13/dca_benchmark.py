"""DCA Benchmark Test — Paper Bot Configuration.

Exact match to V13 paper bot:
  Coins: ETH/USDC, SOL/USDC, LINK/USDC, XRP/USDC
  Capital: $10,000 ($2,500/coin)
  Profile: High
  Period: Sep 2024 → Feb 2026 (paper bot timeframe)
  
Tests the 15m long-only DCA grinder on correctly classified (MARKUP-exit) DCA windows.
Compares: V13 current daily DCA vs optimized 15m grinder.
"""
import sqlite3
import sys
import numpy as np
import pandas as pd
from dataclasses import dataclass
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

# Paper bot config
COINS = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
CAPITAL_PER_COIN = 2500
START_DATE = '2024-09-01'  # Paper bot period
TF = '15m'

# Best params from clean sweep
BEST_PARAMS = [
    SweepParams(tp_pct=0.008, dev_pct=0.012, so_mult=2.5, max_layers=5,
                base_pct=0.10, adaptive=False),   # Best overall from sweep
    SweepParams(tp_pct=0.008, dev_pct=0.012, so_mult=2.5, max_layers=5,
                base_pct=0.05, adaptive=False),   # Same but smaller base
    SweepParams(tp_pct=0.015, dev_pct=0.025, so_mult=2.0, max_layers=8,
                base_pct=0.05, adaptive=False),   # V13 current (baseline)
    SweepParams(tp_pct=0.010, dev_pct=0.020, so_mult=2.0, max_layers=8,
                base_pct=0.05, adaptive=False),   # Mid-range
    SweepParams(tp_pct=0.020, dev_pct=0.030, so_mult=2.0, max_layers=8,
                base_pct=0.05, adaptive=False),   # Wide (ETH's best)
]


def main():
    print("=" * 110)
    print("V13 PAPER BOT DCA BENCHMARK")
    print(f"Coins: {', '.join(c.split('/')[0] for c in COINS)}")
    print(f"Capital: ${CAPITAL_PER_COIN}/coin (${CAPITAL_PER_COIN * len(COINS)} total)")
    print(f"Period: {START_DATE} -> Feb 2026 | Timeframe: {TF} | Long-only")
    print(f"Windows: MARKUP-exit only (correctly classified accumulation)")
    print("=" * 110)

    # Get DCA windows for each coin
    print("\n-- DCA Windows (Sep 2024+) --")
    all_windows = {}  # coin -> {'markup': [...], 'all': [...]}
    
    for coin in COINS:
        try:
            windows = get_dca_windows(coin, 'high')
            etf = [w for w in windows if w['end'] >= START_DATE]
            markup = [w for w in etf if w['exit_to'] == 'MARKUP']
            markdown = [w for w in etf if w['exit_to'] == 'MARKDOWN']
            other = [w for w in etf if w['exit_to'] not in ('MARKUP', 'MARKDOWN')]
            all_windows[coin] = {'markup': markup, 'all': etf}
            
            markup_days = sum(
                max(0, (datetime.strptime(w['end'], '%Y-%m-%d') -
                         datetime.strptime(max(w['start'], START_DATE), '%Y-%m-%d')).days)
                for w in markup)
            
            print(f"  {coin:12} MARKUP: {len(markup)} ({markup_days}d) | MD: {len(markdown)} | Other: {len(other)}")
            for w in etf:
                days = (datetime.strptime(w['end'], '%Y-%m-%d') - datetime.strptime(w['start'], '%Y-%m-%d')).days
                tag = 'GRIND' if w['exit_to'] == 'MARKUP' else 'SKIP'
                print(f"    {w['start']}..{w['end']} ({days:>3}d) -> {w['exit_to']:<10} [{tag}]")
        except Exception as e:
            print(f"  {coin:12} FAILED - {e}")

    # Check 15m data availability
    print(f"\n-- 15m Data Coverage --")
    conn = sqlite3.connect(DB_PATH)
    for coin in COINS:
        for sym in [coin, coin.replace('/USDC', '/USDT')]:
            r = conn.execute(
                "SELECT COUNT(*) FROM candles WHERE symbol=? AND timeframe='15m' AND timestamp>=?",
                (sym, int(datetime(2024,9,1,tzinfo=timezone.utc).timestamp()*1000))).fetchone()
            if r[0] > 0:
                print(f"  {sym:15} {r[0]:>6} candles from Sep 2024")
                break
        else:
            print(f"  {coin:15} NO 15m DATA")
    conn.close()

    # Run benchmark
    print(f"\n{'=' * 110}")
    print("BENCHMARK RESULTS")
    print(f"{'=' * 110}")

    all_results = {}
    
    for coin in COINS:
        if coin not in all_windows:
            continue
        
        markup_windows = all_windows[coin]['markup']
        if not markup_windows:
            print(f"\n  {coin}: No MARKUP-exit windows in period — nothing to grind")
            continue

        all_results[coin] = []
        
        print(f"\n  {coin} — {len(markup_windows)} accumulation windows")
        print(f"  {'Params':<45} {'ROI':>8} {'PnL':>9} {'Lots':>6} {'WR%':>6} {'DD%':>6} {'Deals':>6}")
        print(f"  {'='*45} {'='*8} {'='*9} {'='*6} {'='*6} {'='*6} {'='*6}")

        for p in BEST_PARAMS:
            engine = LongDCAEngine(p, CAPITAL_PER_COIN)
            
            for w in markup_windows:
                df = load_candles(coin, TF, w['start'], w['end'])
                if df.empty:
                    continue
                df = add_regime(df)
                for _, row in df.iterrows():
                    if pd.notna(row.get('atr_pct')):
                        engine.update_regime(row['regime'], row['atr_pct'])
                    engine.tick(row['close'], row['high'], row['low'], str(row['date']))
                if len(df) > 0:
                    engine.force_close(df.iloc[-1]['close'], str(df.iloc[-1]['date']))

            r = {
                'label': p.label, 'roi': engine.roi, 'pnl': engine.total_pnl,
                'lots': engine.total_lots_closed, 'wr': engine.win_rate,
                'dd': engine._max_dd * 100, 'deals': engine.deals_completed,
            }
            all_results[coin].append(r)
            print(f"  {p.label:<45} {r['roi']:>+7.1f}% ${r['pnl']:>+8.1f} {r['lots']:>6} "
                  f"{r['wr']:>5.1f}% {r['dd']:>5.1f}% {r['deals']:>6}")

    # Portfolio summary
    print(f"\n{'=' * 110}")
    print("PORTFOLIO SUMMARY ($10,000 total)")
    print(f"{'=' * 110}")
    
    print(f"\n  {'Params':<45}", end='')
    for coin in COINS:
        print(f" {coin.split('/')[0]:>6}", end='')
    print(f" {'PORT$':>9} {'PORT%':>8}")
    print(f"  {'='*45}", end='')
    for _ in COINS:
        print(f" {'='*6}", end='')
    print(f" {'='*9} {'='*8}")

    for i, p in enumerate(BEST_PARAMS):
        print(f"  {p.label:<45}", end='')
        total_pnl = 0
        for coin in COINS:
            if coin in all_results and i < len(all_results[coin]):
                r = all_results[coin][i]
                print(f" {r['roi']:>+5.1f}%", end='')
                total_pnl += r['pnl']
            else:
                print(f" {'n/a':>6}", end='')
        port_pct = total_pnl / (CAPITAL_PER_COIN * len(COINS)) * 100
        print(f" ${total_pnl:>+8.1f} {port_pct:>+7.1f}%")

    # Per-window detail for best overall param
    if all_results:
        # Find best param by total portfolio P&L
        best_idx = 0
        best_pnl = -999999
        for i in range(len(BEST_PARAMS)):
            total = sum(all_results[c][i]['pnl'] for c in all_results if i < len(all_results[c]))
            if total > best_pnl:
                best_pnl = total
                best_idx = i
        
        best_p = BEST_PARAMS[best_idx]
        print(f"\n{'=' * 110}")
        print(f"BEST CONFIG: {best_p.label}")
        print(f"Portfolio P&L: ${best_pnl:+.1f} ({best_pnl/(CAPITAL_PER_COIN*len(COINS))*100:+.1f}%)")
        print(f"{'=' * 110}")
        
        for coin in COINS:
            if coin not in all_windows:
                continue
            markup_windows = all_windows[coin]['markup']
            if not markup_windows:
                print(f"\n  {coin}: no windows")
                continue
                
            print(f"\n  {coin}:")
            print(f"  {'Start':>12} {'End':>12} {'Days':>5} {'15m':>7} {'ROI':>8} {'PnL':>9} {'Lots':>5} {'WR%':>6}")
            print(f"  {'-'*12} {'-'*12} {'-'*5} {'-'*7} {'-'*8} {'-'*9} {'-'*5} {'-'*6}")
            
            for w in markup_windows:
                engine = LongDCAEngine(best_p, CAPITAL_PER_COIN)
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
                print(f"  {w['start']:>12} {w['end']:>12} {days:>5} {len(df):>7} {engine.roi:>+7.1f}% "
                      f"${engine.total_pnl:>+8.1f} {engine.total_lots_closed:>5} {engine.win_rate:>5.1f}%")

    print(f"\n{'=' * 110}")
    print("MILESTONE CHECK: Is portfolio P&L positive across all coins?")
    if all_results:
        all_positive = True
        for coin in COINS:
            if coin in all_results:
                best_r = all_results[coin][best_idx]
                status = 'PASS' if best_r['pnl'] >= 0 else 'FAIL'
                if best_r['pnl'] < 0:
                    all_positive = False
                print(f"  {coin}: ${best_r['pnl']:>+.1f} [{status}]")
        print(f"\n  {'>>> MILESTONE REACHED <<<' if all_positive else '>>> NOT YET — some coins negative <<<'}")
    print(f"{'=' * 110}")


if __name__ == '__main__':
    main()
