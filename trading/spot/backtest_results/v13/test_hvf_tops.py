"""Test HVF around cycle tops vs corrections vs markdown entries.
Question: Can HVF confirm the top is in or predict markdown spillover?"""
import sqlite3, pandas as pd, numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_hvf_daily import composite_hvf_score, detect_swing_points, hvf_harmonic_pattern

DB = Path(__file__).resolve().parent.parent.parent / "data" / "candles.db"

# Key dates for each coin
EVENTS = {
    'BTC/USDC': {
        'markup_peak': '2024-12-17',      # Local top / ATH push
        'correction_mid': '2025-01-13',   # Mid-correction (didn't become markdown yet)
        'markdown_entry': '2025-01-20',   # Confirmed markdown
        'correction_hold': '2024-10-25',  # Brief dip during markup - should hold through
    },
    'ETH/USDC': {
        'markup_peak': '2024-12-06',
        'correction_mid': '2024-12-20',
        'markdown_entry': '2025-01-07',
        'correction_hold': '2024-11-25',  # Dip during markup
    },
    'SOL/USDC': {
        'markup_peak': '2024-11-22',
        'correction_mid': '2024-12-20',
        'markdown_entry': '2025-01-10',
        'correction_hold': '2024-12-05',
    },
}

def get_hvf_timeline(df, center_date, window_days=44, offsets=None):
    """Get HVF scores around a date."""
    if offsets is None:
        offsets = [-30, -21, -14, -7, 0, 7, 14, 21]
    results = []
    for offset in offsets:
        d = center_date + pd.Timedelta(days=offset)
        idx = df.index.get_indexer([d], method='nearest')[0]
        if idx >= window_days:
            window = df.iloc[max(0, idx - window_days):idx + 1]
            comp, _, _, _ = composite_hvf_score(window)
            score = float(comp.iloc[-1]) if hasattr(comp, 'iloc') else float(comp)
            price = df.iloc[idx]['close']
            actual_date = df.index[idx]
            results.append((offset, score, price, actual_date))
    return results


def main():
    db = sqlite3.connect(str(DB))
    
    print("HVF at Cycle Tops vs Corrections vs Markdown")
    print("=" * 70)
    print("Question: Does HVF distinguish tops from corrections?")
    print("If HVF is HIGH at top = energy building for breakdown (confirms top)")
    print("If HVF is LOW at top = no compression, might just be a correction")
    print()
    
    for symbol, events in EVENTS.items():
        df = pd.read_sql(
            'SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp',
            db, params=(symbol,))
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('date', inplace=True)
        
        coin = symbol.split('/')[0]
        print(f"\n{'='*70}")
        print(f"  {coin}")
        print(f"{'='*70}")
        
        for event_name, date_str in events.items():
            center = pd.Timestamp(date_str)
            timeline = get_hvf_timeline(df, center, offsets=[-21, -14, -7, 0, 7, 14])
            
            print(f"\n  {event_name} ({date_str}):")
            for offset, score, price, actual_d in timeline:
                label = ">>>" if offset == 0 else f"{offset:+d}d"
                bar = "#" * int(score * 30)
                print(f"    {label:>5} {actual_d.date()} HVF={score:.3f} ${price:>10,.2f} |{bar}")
        
        # Also check: harmonic patterns near the top
        peak_date = pd.Timestamp(events['markup_peak'])
        md_date = pd.Timestamp(events['markdown_entry'])
        
        # Check for harmonic patterns in the top-to-markdown window
        idx_peak = df.index.get_indexer([peak_date], method='nearest')[0]
        idx_md = df.index.get_indexer([md_date], method='nearest')[0]
        
        if idx_peak >= 60:
            window = df.iloc[max(0, idx_peak - 60):min(len(df), idx_md + 30)]
            swings = detect_swing_points(window, lookback=5)
            patterns = hvf_harmonic_pattern(window, swings)
            
            if patterns:
                print(f"\n  Harmonic patterns (top→markdown window):")
                for p in patterns:
                    print(f"    {p['date'].date()} {p['direction']} score={p['score']:.3f} BC_ratio={p.get('bc_ratio', 0):.3f}")
            else:
                print(f"\n  No harmonic patterns in top→markdown window")
    
    db.close()
    
    print(f"\n{'='*70}")
    print("INTERPRETATION:")
    print("  HVF HIGH at peak → compression building, breakdown likely (CONFIRM top)")
    print("  HVF LOW at peak  → no compression, more likely a correction (DENY top)")
    print("  HVF HIGH at markdown entry → energy releasing into breakdown")
    print("  HVF LOW at correction_hold → no energy, just noise (hold through)")


if __name__ == '__main__':
    main()
