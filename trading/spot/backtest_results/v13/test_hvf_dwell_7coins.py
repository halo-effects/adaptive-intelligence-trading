"""
Test HVF + Channel Dwell + Breakout on expanded 9-coin test set.
Adds PEPE, ZEC, NEAR, LINK to the original 5.
"""
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from channel_breakout import ChannelBreakout
from test_hvf_daily import composite_hvf_score, detect_swing_points
from test_hvf_dwell_breakout import DwellAwareBreakout

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "candles.db"

# Extended ground truth with PEPE and ZEC
GROUND_TRUTH_7 = {
    'BTC/USDC': [
        ('2024-10-15', 'MARKUP'),
        ('2025-01-20', 'MARKDOWN'),
    ],
    'ETH/USDC': [
        ('2024-11-05', 'MARKUP'),
        ('2025-01-10', 'MARKDOWN'),
    ],
    'SOL/USDC': [
        ('2024-10-15', 'MARKUP'),
        ('2025-01-20', 'MARKDOWN'),
    ],
    'BNB/USDT': [
        ('2024-11-10', 'MARKUP'),
        ('2025-02-01', 'MARKDOWN'),
    ],
    'XRP/USDT': [
        ('2024-11-10', 'MARKUP'),
        ('2025-01-20', 'MARKDOWN'),
    ],
    'PEPE/USDT': [
        ('2024-02-15', 'MARKUP'),      # 3x rally start
        ('2024-11-05', 'MARKUP'),      # Second leg up
        ('2025-01-15', 'MARKDOWN'),    # Topped, declining
    ],
    'ZEC/USDT': [
        ('2025-09-15', 'MARKUP'),      # Mega breakout from long suppression
        ('2026-01-10', 'MARKDOWN'),    # Topped ~$500
    ],
    'NEAR/USDT': [
        ('2023-10-20', 'MARKUP'),      # $1.13 -> $3.65
        ('2024-11-05', 'MARKUP'),      # $3.93 -> $7.01
        ('2025-01-15', 'MARKDOWN'),    # Downtrend since
    ],
    'LINK/USDT': [
        ('2023-09-20', 'MARKUP'),      # $5.94 -> $14.41
        ('2024-11-05', 'MARKUP'),      # $11.25 -> $25.17
        ('2025-02-01', 'MARKDOWN'),    # Downtrend since
    ],
}


def analyze_coin(symbol, db):
    """Analyze channel + HVF + dwell for a coin."""
    df = pd.read_sql(
        "SELECT * FROM candles_daily WHERE symbol=? ORDER BY date",
        db, params=(symbol,))
    if len(df) == 0:
        print(f"  {symbol}: NO DATA")
        return None
    
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    # Ensure required columns
    for col in ['bb_width', 'adx']:
        if col not in df.columns:
            df[col] = 20.0
    
    dab = DwellAwareBreakout(df)
    dwell_bos = dab.dwell_breakouts()
    hvf_composite, _, _, _ = composite_hvf_score(df, lookback=30)
    
    print(f"\n{'='*70}")
    print(f"  {symbol} -- {len(df)} daily candles")
    print(f"  Channels: {len(dab.channels)}, Breakouts: {len(dwell_bos)}")
    print(f"{'='*70}")
    
    # Show channels by dwell tier
    for tier in ['extended', 'long', 'moderate', 'short']:
        tier_bos = [bo for bo in dwell_bos if bo['dwell_tier'] == tier]
        if tier_bos:
            print(f"\n  [{tier.upper()}] dwell breakouts:")
            for bo in tier_bos:
                bo_date = bo['breakout_date']
                hvf_window = {d: v for d, v in hvf_composite.items() 
                              if (bo_date - pd.Timedelta(days=30)) <= d <= bo_date}
                max_hvf = max(hvf_window.values()) if hvf_window else 0
                
                status = "CONFIRMED" if bo['confirmed'] else ("INVALIDATED" if bo['invalidated'] else "UNCONFIRMED")
                
                print(f"    {bo['breakout_date'].date()} {bo['direction']} "
                      f"({bo['dwell_days']}d channel) "
                      f"HVF_max={max_hvf:.3f} "
                      f"[{status}]")
    
    # Check ground truth alignment
    if symbol in GROUND_TRUTH_7:
        print(f"\n  Ground truth transitions:")
        for gt_date, gt_dir in GROUND_TRUTH_7[symbol]:
            gt = pd.Timestamp(gt_date)
            # Find nearest breakout
            nearest = None
            nearest_dist = 999
            for bo in dwell_bos:
                dist = abs((bo['breakout_date'] - gt).days)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest = bo
            
            if nearest and nearest_dist <= 60:
                hvf_window = {d: v for d, v in hvf_composite.items() 
                              if (nearest['breakout_date'] - pd.Timedelta(days=30)) <= d <= nearest['breakout_date']}
                max_hvf = max(hvf_window.values()) if hvf_window else 0
                
                print(f"    {gt_date} {gt_dir} -> nearest BO: {nearest['breakout_date'].date()} "
                      f"({nearest['dwell_days']}d {nearest['dwell_tier']}) "
                      f"HVF={max_hvf:.3f} "
                      f"{'CONFIRMED' if nearest['confirmed'] else 'MISS'}")
            else:
                print(f"    {gt_date} {gt_dir} -> NO nearby breakout (nearest: {nearest_dist}d away)")
    
    return dab, hvf_composite, dwell_bos


def main():
    print("HVF + Dwell + Breakout -- 7-Coin Expanded Test")
    print("=" * 70)
    print("Focus: ZEC (long suppression -> breakout) and PEPE (meme volatility)")
    
    db = sqlite3.connect(str(DB_PATH))
    
    # Analyze each coin
    for symbol in ['ZEC/USDT', 'PEPE/USDT', 'NEAR/USDT', 'LINK/USDT',
                    'BNB/USDT', 'XRP/USDT', 'BTC/USDC', 'ETH/USDC', 'SOL/USDC']:
        analyze_coin(symbol, db)
    
    db.close()


if __name__ == '__main__':
    main()
