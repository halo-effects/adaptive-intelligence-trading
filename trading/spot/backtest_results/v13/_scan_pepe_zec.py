"""Quick price scan for PEPE and ZEC to identify ground truth transitions."""
import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "candles.db"
db = sqlite3.connect(str(DB_PATH))

for symbol in ['NEAR/USDT', 'LINK/USDT']:
    df = pd.read_sql(
        "SELECT date, close, high, low, volume, adx, rsi14, sma50, sma200 FROM candles_daily WHERE symbol=? ORDER BY date",
        db, params=(symbol,))
    print(f"\n{'='*80}")
    print(f"  {symbol} — {len(df)} days, {df['date'].iloc[0]} to {df['date'].iloc[-1]}")
    print(f"{'='*80}")
    
    # Monthly summary: open, close, high, low, direction
    df['month'] = df['date'].str[:7]
    monthly = df.groupby('month').agg(
        open=('close', 'first'),
        close=('close', 'last'),
        high=('high', 'max'),
        low=('low', 'min'),
        avg_adx=('adx', 'mean'),
        avg_rsi=('rsi14', 'mean'),
    )
    monthly['change_pct'] = (monthly['close'] - monthly['open']) / monthly['open'] * 100
    monthly['direction'] = monthly['change_pct'].apply(lambda x: 'UP' if x > 5 else ('DOWN' if x < -5 else 'FLAT'))
    
    print(f"\n  {'Month':<10} {'Open':>12} {'Close':>12} {'Change':>8} {'Dir':>5} {'ADX':>5} {'RSI':>5}")
    print(f"  {'─'*65}")
    for idx, row in monthly.iterrows():
        print(f"  {idx:<10} {row['open']:>12.6f} {row['close']:>12.6f} {row['change_pct']:>7.1f}% {row['direction']:>5} {row['avg_adx']:>5.1f} {row['avg_rsi']:>5.1f}")

db.close()
