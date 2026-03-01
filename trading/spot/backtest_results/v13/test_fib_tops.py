"""
Test Fibonacci extensions as cycle top indicators.
Can Fib extension levels predict when price is in a "top zone"?
If so, DCA should pause/reduce allocation when price reaches these zones.
"""
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_hvf_daily import detect_swing_points

DB = Path(__file__).resolve().parent.parent.parent / "data" / "candles.db"

FIB_EXT = [1.0, 1.272, 1.618, 2.0, 2.618, 3.618]
FIB_RETRACE = [0.236, 0.382, 0.5, 0.618, 0.786]
TOLERANCE = 0.03  # 3% proximity


def find_fib_zone(price, levels):
    """Check if price is near any Fibonacci level. Returns (ratio, level, distance%) or None."""
    for ratio, level in levels.items():
        if level > 0:
            dist = abs(price - level) / level
            if dist < TOLERANCE:
                return ratio, level, dist * 100
    return None


def analyze_coin(symbol):
    """Analyze if Fibonacci extension levels predict cycle tops."""
    db = sqlite3.connect(str(DB))
    df = pd.read_sql(
        'SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp',
        db, params=(symbol,))
    db.close()

    if len(df) == 0:
        print(f"  No data for {symbol}")
        return

    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('date', inplace=True)

    print(f"\n{'='*70}")
    print(f"  {symbol}")
    print(f"{'='*70}")

    swings = detect_swing_points(df, lookback=10)
    swing_lows = [s for s in swings if s['type'] == 'low']
    swing_highs = [s for s in swings if s['type'] == 'high']

    # Find major swing low before the Nov 2024 rally
    pre_lows = [s for s in swing_lows
                if s['date'] > pd.Timestamp('2024-06-01')
                and s['date'] < pd.Timestamp('2024-11-01')]

    if not pre_lows:
        print("  No swing lows found in Jun-Oct 2024")
        return

    major_low = min(pre_lows, key=lambda s: s['price'])

    # Find the swing high before the major low (the A point)
    prior_highs = [s for s in swing_highs
                   if s['date'] < major_low['date']
                   and s['date'] > major_low['date'] - pd.Timedelta(days=180)]

    if not prior_highs:
        print("  No prior swing high found")
        return

    major_high = max(prior_highs, key=lambda s: s['price'])
    swing_range = major_high['price'] - major_low['price']

    print(f"  Swing High (A): ${major_high['price']:.2f} ({major_high['date'].date()})")
    print(f"  Swing Low (B):  ${major_low['price']:.2f} ({major_low['date'].date()})")
    print(f"  Range: ${abs(swing_range):.2f}")

    # Compute extension levels from the low
    ext_levels = {}
    for ratio in FIB_EXT:
        ext_levels[ratio] = major_low['price'] + abs(swing_range) * ratio
    
    # Also compute retracement levels from the subsequent rally high
    # Find the actual cycle top
    post_rally = df[df.index > major_low['date']]
    if len(post_rally) == 0:
        return
    
    actual_top_price = post_rally['high'].max()
    actual_top_date = post_rally['high'].idxmax()
    
    # Now compute retrace levels from the rally (top down)
    rally_range = actual_top_price - major_low['price']
    retrace_from_top = {}
    for ratio in FIB_RETRACE:
        retrace_from_top[ratio] = actual_top_price - rally_range * ratio

    print(f"\n  Actual Cycle Top: ${actual_top_price:.2f} ({actual_top_date.date()})")
    print(f"\n  Extension levels from swing low:")
    for ratio in FIB_EXT:
        level = ext_levels[ratio]
        if actual_top_price > 0:
            pct_of_top = (level / actual_top_price) * 100
            hit = " ◄ TOP ZONE" if abs(100 - pct_of_top) < 5 else ""
            above = " (above top)" if level > actual_top_price else ""
            print(f"    {ratio:.3f}x: ${level:.2f} ({pct_of_top:.1f}% of top){hit}{above}")

    # Track price approaching Fib extension zones during the rally
    print(f"\n  Price at Fib extension zones during rally:")
    rally = df[(df.index >= major_low['date']) & (df.index <= actual_top_date + pd.Timedelta(days=30))]
    
    last_zone = None
    for d, row in rally.iterrows():
        zone = find_fib_zone(row['close'], ext_levels)
        if zone and zone[0] != last_zone:
            ratio, level, dist = zone
            print(f"    {d.date()}: ${row['close']:.2f} near {ratio:.3f}x extension (${level:.2f}, {dist:.1f}% away)")
            last_zone = zone[0]
    
    # Key question: did the top occur near a Fibonacci extension?
    top_zone = find_fib_zone(actual_top_price, ext_levels)
    if top_zone:
        print(f"\n  ✅ CYCLE TOP at Fibonacci {top_zone[0]:.3f}x extension (${top_zone[1]:.2f}, {top_zone[2]:.1f}% off)")
    else:
        # Check which zone it was between
        below = [(r, l) for r, l in ext_levels.items() if l < actual_top_price]
        above = [(r, l) for r, l in ext_levels.items() if l > actual_top_price]
        if below and above:
            b_ratio, b_level = max(below, key=lambda x: x[1])
            a_ratio, a_level = min(above, key=lambda x: x[1])
            print(f"\n  ⚠️ Top between {b_ratio:.3f}x (${b_level:.2f}) and {a_ratio:.3f}x (${a_level:.2f})")
        else:
            print(f"\n  ❌ Top not near any Fib extension")

    # DCA implication: if we paused DCA when price reached 1.272x or higher extension,
    # would we have avoided buying at the top?
    print(f"\n  DCA TOP FILTER TEST:")
    print(f"  If DCA paused when price > 1.272x extension (${ext_levels.get(1.272, 0):.2f}):")
    dca_buys_above = rally[rally['close'] > ext_levels.get(1.272, float('inf'))]
    dca_buys_below = rally[rally['close'] <= ext_levels.get(1.272, float('inf'))]
    print(f"    Days above: {len(dca_buys_above)} ({len(dca_buys_above)/max(1,len(rally))*100:.0f}% of rally)")
    print(f"    Days below: {len(dca_buys_below)} ({len(dca_buys_below)/max(1,len(rally))*100:.0f}% of rally)")
    
    # What about 1.618x?
    print(f"  If DCA paused when price > 1.618x extension (${ext_levels.get(1.618, 0):.2f}):")
    dca_above_618 = rally[rally['close'] > ext_levels.get(1.618, float('inf'))]
    print(f"    Days above: {len(dca_above_618)} ({len(dca_above_618)/max(1,len(rally))*100:.0f}% of rally)")


def main():
    print("Fibonacci Extension as Cycle Top Indicator")
    print("Can we prevent DCA buying at the top?")
    
    for symbol in ['BTC/USDC', 'ETH/USDC', 'SOL/USDC', 'BNB/USDT', 'XRP/USDT']:
        analyze_coin(symbol)
    
    print(f"\n{'='*70}")
    print(f"  CONCLUSION")
    print(f"{'='*70}")
    print("""
  If Fibonacci extensions consistently predict top zones:
  → DCA should REDUCE or PAUSE allocation when price enters extension zone
  → This prevents the "buying at the top" problem without needing the 2W OB signal
  → Combined with HVF compression: if HVF is LOW (no compression) AND price is 
    at Fib extension = exhaustion zone, don't DCA.
    """)


if __name__ == '__main__':
    main()
