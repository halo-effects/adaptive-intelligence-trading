#!/usr/bin/env python3
"""Diagnostic: Run ReversalDetector on ETH and SOL 1h data around known peaks."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
from datetime import datetime, timezone
from trading.spot.reversal_detector import ReversalDetector, ReversalDetectorConfig


def ms_to_str(ts_ms):
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')


def load_csv(path):
    df = pd.read_csv(path)
    return df


def run_detector(label, csv_paths, ath, peak_windows):
    """Run detector on concatenated data and report triggers near peak windows.
    
    peak_windows: list of (name, start_ts_ms, end_ts_ms) to focus reporting on
    """
    # Load and concatenate
    frames = []
    for p in csv_paths:
        if Path(p).exists():
            frames.append(load_csv(p))
    if not frames:
        print(f"  No data files found for {label}")
        return []
    
    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values('timestamp').drop_duplicates(subset='timestamp').reset_index(drop=True)
    
    config = ReversalDetectorConfig(ath=ath)
    det = ReversalDetector(config)
    
    results = []
    
    print(f"\n{'='*70}")
    print(f"  {label}  |  ATH: ${ath:,.0f}  |  {len(df):,} candles")
    print(f"  Range: {ms_to_str(df.iloc[0]['timestamp'])} to {ms_to_str(df.iloc[-1]['timestamp'])}")
    print(f"{'='*70}")
    
    # Run detector on all candles, collect trigger events
    all_triggers = []
    for i, row in df.iterrows():
        sc = det.score(float(row['close']), float(row['timestamp']))
        if sc > 0:
            drop_pct = (det._rolling_high - row['close']) / det._rolling_high * 100
            all_triggers.append({
                'timestamp': row['timestamp'],
                'date': ms_to_str(row['timestamp']),
                'close': row['close'],
                'rolling_high': det._rolling_high,
                'drop_pct': drop_pct,
                'score': sc,
                'peak_date': ms_to_str(det._rolling_high_ts) if det._rolling_high_ts else 'N/A',
            })
    
    # Report around each peak window
    for window_name, win_start, win_end in peak_windows:
        window_triggers = [t for t in all_triggers if win_start <= t['timestamp'] <= win_end]
        
        print(f"\n  --- {window_name} ---")
        if not window_triggers:
            print(f"  No triggers in window")
            continue
        
        # First trigger
        first = window_triggers[0]
        print(f"  First trigger: {first['date']}")
        print(f"    Price: ${first['close']:,.2f}  |  Peak: ${first['rolling_high']:,.2f} ({first['peak_date']})")
        print(f"    Drop: {first['drop_pct']:.1f}%  |  Score: {first['score']}")
        
        # Max score trigger
        max_t = max(window_triggers, key=lambda t: t['score'])
        if max_t != first:
            print(f"  Max score trigger: {max_t['date']}")
            print(f"    Price: ${max_t['close']:,.2f}  |  Drop: {max_t['drop_pct']:.1f}%  |  Score: {max_t['score']}")
        
        print(f"  Total triggers in window: {len(window_triggers)}")
        
        # Show first 10 triggers
        print(f"\n  {'Date':<22} {'Price':>10} {'Peak':>10} {'Drop%':>7} {'Score':>6}")
        print(f"  {'-'*22} {'-'*10} {'-'*10} {'-'*7} {'-'*6}")
        for t in window_triggers[:15]:
            print(f"  {t['date']:<22} ${t['close']:>9,.2f} ${t['rolling_high']:>9,.2f} {t['drop_pct']:>6.1f}% {t['score']:>5}")
        
        results.append({
            'window': window_name,
            'first_trigger': first,
            'max_trigger': max_t,
            'total_triggers': len(window_triggers),
            'all_triggers': window_triggers,
        })
    
    return results


def ts(year, month, day):
    """Create ms timestamp from date."""
    return int(datetime(year, month, day, tzinfo=timezone.utc).timestamp() * 1000)


def main():
    data_dir = Path('trading/spot/data/dwell_cache')
    
    all_results = {}
    
    # ETH — Nov 2021 peak
    # ETH — Dec 2024 peak
    eth_files = sorted(data_dir.glob('ETH_USDT_1h_*.csv'))
    eth_results = run_detector(
        "ETH",
        [str(f) for f in eth_files],
        ath=4878,
        peak_windows=[
            ("ETH Nov 2021 ($4,878 peak)", ts(2021, 11, 1), ts(2022, 2, 28)),
            ("ETH Dec 2024 ($4,087 peak)", ts(2024, 11, 1), ts(2025, 2, 28)),
        ]
    )
    all_results['ETH'] = eth_results
    
    # SOL — Nov 2021 peak
    sol_files = sorted(data_dir.glob('SOL_USDT_1h_*.csv'))
    sol_results = run_detector(
        "SOL",
        [str(f) for f in sol_files],
        ath=260,
        peak_windows=[
            ("SOL Nov 2021 ($260 peak)", ts(2021, 10, 1), ts(2022, 2, 28)),
        ]
    )
    all_results['SOL'] = sol_results
    
    # Write markdown report
    report_path = Path('trading/spot/backtest_results/v12_lifecycle/reversal_detector_diagnostic.md')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    lines = ["# Reversal Detector Diagnostic\n"]
    lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")
    lines.append("## Parameters\n")
    lines.append("| Parameter | Value |")
    lines.append("|-----------|-------|")
    lines.append("| ATH Proximity | 25% |")
    lines.append("| ATH Lookback | 30 days |")
    lines.append("| Tier 1 | 10% drop → 20 pts |")
    lines.append("| Tier 2 | 15% drop → 30 pts |")
    lines.append("| Tier 3 | 20% drop → 40 pts |")
    lines.append("| F&G Bonus | >75 in last 14d → +10 pts |")
    lines.append("| Speed Bonus | Drop within 7d of peak → +5 pts |")
    lines.append("")
    
    for coin, results in all_results.items():
        for r in results:
            lines.append(f"## {r['window']}\n")
            f = r['first_trigger']
            lines.append(f"**First trigger:** {f['date']}")
            lines.append(f"- Price: ${f['close']:,.2f} | Peak: ${f['rolling_high']:,.2f} ({f['peak_date']})")
            lines.append(f"- Drop: {f['drop_pct']:.1f}% | Score: {f['score']}")
            lines.append(f"- Total triggers in window: {r['total_triggers']}\n")
            
            lines.append(f"| Date | Price | Peak | Drop% | Score |")
            lines.append(f"|------|-------|------|-------|-------|")
            for t in r['all_triggers'][:20]:
                lines.append(f"| {t['date']} | ${t['close']:,.2f} | ${t['rolling_high']:,.2f} | {t['drop_pct']:.1f}% | {t['score']} |")
            lines.append("")
    
    report_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f"\n\nReport written to: {report_path}")


if __name__ == '__main__':
    main()
