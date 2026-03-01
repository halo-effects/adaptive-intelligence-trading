"""V13 Full Lifecycle Test: Baseline vs Enhanced DCA (1h grinder).

Runs the complete V13 phase engine for each coin, then replaces DCA-phase
P&L with 1h DCA grinder results using winning per-coin configs.

Purpose: Compare total lifecycle ROI (all phases) between:
  A) V13 baseline (daily DCA ticks)
  B) V13 + 1h DCA grinder (per-coin optimized configs)

This lets us validate against the live paper bot dashboard numbers.
"""
import sqlite3
import sys
import copy
import numpy as np
import pandas as pd
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack
from dca_long_sweep import SweepParams, LongDCAEngine, load_candles, add_regime

DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'

# Paper bot coins + config
COINS = ['ETH/USDC', 'BTC/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
CAPITAL = 2500  # per coin (paper bot = $10K / 4 coins, but we test 5)
PROFILE = 'high'
START = '2023-01-01'
END = '2026-02-27'

# Winning DCA configs per coin (from dca_tf_compare.py results)
DCA_CONFIGS = {
    'ETH/USDC': SweepParams(tp_pct=0.015, dev_pct=0.025, so_mult=2.0, max_layers=8,
                             base_pct=0.05, adaptive=False),
    'BTC/USDC': None,  # Skip DCA grinding for BTC (negative on all configs)
    'SOL/USDC': SweepParams(tp_pct=0.020, dev_pct=0.030, so_mult=2.0, max_layers=8,
                             base_pct=0.05, adaptive=False),
    'LINK/USDC': SweepParams(tp_pct=0.010, dev_pct=0.020, so_mult=2.0, max_layers=8,
                              base_pct=0.05, adaptive=False),
    'XRP/USDC': SweepParams(tp_pct=0.008, dev_pct=0.012, so_mult=2.5, max_layers=5,
                             base_pct=0.05, adaptive=True),
}


def get_v13_config(coin, capital):
    """Create V13Config matching paper bot settings."""
    cfg = V13Config()
    cfg.COIN = coin
    cfg.CAPITAL = capital
    cfg.PROFILE = PROFILE
    cfg.START_DATE = START
    cfg.END_DATE = END

    # High profile settings (match paper bot)
    cfg.TIER1_PCT = 0.60
    cfg.TIER2_PCT = 0.20
    cfg.TIER3_PCT = 0.10
    cfg.SHORT_TIER1_PCT = 0.60
    cfg.SHORT_TIER2_PCT = 0.20
    cfg.SHORT_TIER3_PCT = 0.10
    cfg.SHORTS_ENABLED = True

    return cfg


def extract_dca_windows(phase_log):
    """Extract DCA windows from V13 phase log."""
    windows = []
    dca_start = None

    for entry in phase_log:
        if entry['to'] == Phase.DCA:
            dca_start = entry['date']
        elif dca_start is not None and entry.get('from') == Phase.DCA:
            exit_phase = entry['to']
            windows.append({
                'start': str(dca_start.date()),
                'end': str(entry['date'].date()),
                'exit_to': exit_phase.name if hasattr(exit_phase, 'name') else str(exit_phase),
            })
            dca_start = None

    # Handle still-in-DCA at end
    if dca_start is not None:
        windows.append({
            'start': str(dca_start.date()),
            'end': END,
            'exit_to': 'OPEN',
        })

    return windows


def run_1h_dca_on_windows(coin, windows, params, capital):
    """Run 1h DCA grinder on given windows, return total PnL."""
    if params is None:
        return 0.0, 0, 0.0  # BTC: skip DCA

    engine = LongDCAEngine(params, capital)
    total_candles = 0

    for w in windows:
        df = load_candles(coin, '1h', w['start'], w['end'])
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

    return engine.total_pnl, engine.total_lots_closed, engine.win_rate


def main():
    print("=" * 120)
    print("V13 FULL LIFECYCLE TEST: BASELINE vs ENHANCED DCA (1h grinder)")
    print(f"Coins: {', '.join(c.split('/')[0] for c in COINS)} | Capital: ${CAPITAL}/coin | Profile: {PROFILE}")
    print(f"Period: {START} to {END} | DCA timeframe: 1h | Phase transitions: daily")
    print("=" * 120)

    results = []

    for coin in COINS:
        short = coin.split('/')[0]
        print(f"\n{'='*120}")
        print(f"  {coin}")
        print(f"{'='*120}")

        # --- Run V13 baseline ---
        try:
            cfg = get_v13_config(coin, CAPITAL)
            pack = V13SignalPack(coin, db_path=str(DB_PATH))
            engine = V13BacktestV8(pack, cfg)
            baseline_result = engine.run()
        except Exception as e:
            print(f"  FAILED to run V13 baseline: {e}")
            continue

        if baseline_result is None:
            print(f"  No result from V13 baseline")
            continue

        # Extract baseline metrics
        baseline_roi = baseline_result.get('roi', 0)
        baseline_equity = baseline_result.get('final_equity', CAPITAL)
        baseline_pnl = baseline_equity - CAPITAL
        baseline_dca_pnl = baseline_result.get('dca_pnl', 0)
        baseline_dca_trades = baseline_result.get('dca_trades', 0)

        # Get phase log for DCA windows
        phase_log = engine.phase_log
        dca_windows = extract_dca_windows(phase_log)
        markup_windows = [w for w in dca_windows if w['exit_to'] == 'MARKUP']
        all_dca_days = sum(
            max(0, (datetime.strptime(w['end'], '%Y-%m-%d') -
                     datetime.strptime(w['start'], '%Y-%m-%d')).days)
            for w in dca_windows)

        print(f"\n  Phase Log:")
        for entry in phase_log:
            fr = entry.get('from', '-')
            to = entry.get('to', '-')
            if hasattr(fr, 'name'):
                fr = fr.name
            if hasattr(to, 'name'):
                to = to.name
            reason = entry.get('reason', '')
            eq = entry.get('equity', 0)
            print(f"    {str(entry['date'].date()):>12}  {str(fr):>10} -> {str(to):<10}  eq=${eq:>8.0f}  {reason}")

        print(f"\n  DCA Windows: {len(dca_windows)} total ({len(markup_windows)} exit to MARKUP), ~{all_dca_days} days")

        # --- Run 1h DCA grinder on ALL DCA windows ---
        dca_params = DCA_CONFIGS.get(coin)
        enhanced_dca_pnl, enhanced_dca_lots, enhanced_dca_wr = run_1h_dca_on_windows(
            coin, dca_windows, dca_params, CAPITAL)

        # Also run on MARKUP-exit only for comparison
        markup_dca_pnl, markup_dca_lots, markup_dca_wr = run_1h_dca_on_windows(
            coin, markup_windows, dca_params, CAPITAL)

        # Calculate enhanced total: baseline non-DCA P&L + 1h DCA P&L
        non_dca_pnl = baseline_pnl - baseline_dca_pnl
        enhanced_pnl = non_dca_pnl + enhanced_dca_pnl
        enhanced_roi = enhanced_pnl / CAPITAL * 100

        # Markup-only enhanced
        markup_enhanced_pnl = non_dca_pnl + markup_dca_pnl
        markup_enhanced_roi = markup_enhanced_pnl / CAPITAL * 100

        print(f"\n  --- BASELINE (V13 daily DCA) ---")
        print(f"    Total ROI:     {baseline_roi:>+8.1f}%  (${baseline_pnl:>+8.0f})")
        print(f"    DCA P&L:       ${baseline_dca_pnl:>+8.1f}  ({baseline_dca_trades} trades)")
        print(f"    Non-DCA P&L:   ${non_dca_pnl:>+8.0f}  (markup sells + shorts)")

        print(f"\n  --- ENHANCED (1h DCA grinder, ALL windows) ---")
        dca_label = DCA_CONFIGS[coin].label if DCA_CONFIGS[coin] else "SKIP"
        print(f"    DCA Config:    {dca_label}")
        print(f"    1h DCA P&L:    ${enhanced_dca_pnl:>+8.1f}  ({enhanced_dca_lots} lots, {enhanced_dca_wr:.0f}% WR)")
        print(f"    Total ROI:     {enhanced_roi:>+8.1f}%  (${enhanced_pnl:>+8.0f})")
        print(f"    Delta:         {enhanced_roi - baseline_roi:>+8.1f}%  (${enhanced_dca_pnl - baseline_dca_pnl:>+8.0f} from DCA)")

        print(f"\n  --- ENHANCED (1h DCA, MARKUP-exit windows only) ---")
        print(f"    1h DCA P&L:    ${markup_dca_pnl:>+8.1f}  ({markup_dca_lots} lots, {markup_dca_wr:.0f}% WR)")
        print(f"    Total ROI:     {markup_enhanced_roi:>+8.1f}%  (${markup_enhanced_pnl:>+8.0f})")
        print(f"    Delta:         {markup_enhanced_roi - baseline_roi:>+8.1f}%  (${markup_dca_pnl - baseline_dca_pnl:>+8.0f} from DCA)")

        results.append({
            'coin': short,
            'baseline_roi': baseline_roi,
            'baseline_pnl': baseline_pnl,
            'baseline_dca_pnl': baseline_dca_pnl,
            'non_dca_pnl': non_dca_pnl,
            'enhanced_roi': enhanced_roi,
            'enhanced_pnl': enhanced_pnl,
            'enhanced_dca_pnl': enhanced_dca_pnl,
            'markup_enhanced_roi': markup_enhanced_roi,
            'dca_windows': len(dca_windows),
            'markup_windows': len(markup_windows),
            'dca_days': all_dca_days,
        })

    # --- PORTFOLIO SUMMARY ---
    print(f"\n{'='*120}")
    print("PORTFOLIO SUMMARY")
    print(f"{'='*120}")

    total_capital = len(results) * CAPITAL
    print(f"\n  {'Coin':<6} {'Baseline':>10} {'Enhanced':>10} {'Mkup-Only':>10} {'Delta':>8} {'DCA Win':>8} {'DCA Days':>9}")
    print(f"  {'_'*6} {'_'*10} {'_'*10} {'_'*10} {'_'*8} {'_'*8} {'_'*9}")

    total_base = 0
    total_enh = 0
    total_mkup = 0

    for r in results:
        delta = r['enhanced_roi'] - r['baseline_roi']
        print(f"  {r['coin']:<6} {r['baseline_roi']:>+9.1f}% {r['enhanced_roi']:>+9.1f}% "
              f"{r['markup_enhanced_roi']:>+9.1f}% {delta:>+7.1f}% "
              f"{r['markup_windows']:>4}/{r['dca_windows']:<3} {r['dca_days']:>7}d")
        total_base += r['baseline_pnl']
        total_enh += r['enhanced_pnl']
        total_mkup += r['non_dca_pnl'] + (r['enhanced_dca_pnl'] if r['markup_windows'] > 0 else r['baseline_dca_pnl'])

    base_port_roi = total_base / total_capital * 100
    enh_port_roi = total_enh / total_capital * 100

    print(f"\n  Portfolio ({len(results)} coins, ${total_capital:,} capital):")
    print(f"    Baseline ROI:  {base_port_roi:>+8.1f}%  (${total_base:>+,.0f})")
    print(f"    Enhanced ROI:  {enh_port_roi:>+8.1f}%  (${total_enh:>+,.0f})")
    print(f"    Delta:         {enh_port_roi - base_port_roi:>+8.1f}%  (${total_enh - total_base:>+,.0f})")

    # Trade breakdown
    print(f"\n  P&L Breakdown:")
    print(f"    {'Coin':<6} {'Non-DCA':>10} {'Base DCA':>10} {'1h DCA':>10} {'DCA Lift':>10}")
    print(f"    {'_'*6} {'_'*10} {'_'*10} {'_'*10} {'_'*10}")
    for r in results:
        lift = r['enhanced_dca_pnl'] - r['baseline_dca_pnl']
        print(f"    {r['coin']:<6} ${r['non_dca_pnl']:>+8.0f} ${r['baseline_dca_pnl']:>+8.1f} "
              f"${r['enhanced_dca_pnl']:>+8.1f} ${lift:>+8.1f}")

    print(f"\n{'='*120}")
    print("Done.")


if __name__ == '__main__':
    main()
