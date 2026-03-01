"""Compare backtest signal data vs what live bot would see."""
import sys
sys.path.insert(0, '.')
from v13_signals import V13SignalPack
import pandas as pd
import sqlite3

# Load backtest signal pack (uses candles_daily)
pack = V13SignalPack('ETH')
d = pack.daily

print("=== BACKTEST SIGNAL DATA (from candles_daily) ===")
print(f"Source symbol: {d.attrs.get('symbol', 'unknown')}")
print(f"Date range: {d.index[0].date()} to {d.index[-1].date()}")
print(f"Rows: {len(d)}")
print()

# Check key dates around Oct 2024 markup entry
print("--- ETH Oct 2024 (live bot entered markup Oct 13) ---")
for date_str in ['2024-10-04','2024-10-05','2024-10-06','2024-10-07','2024-10-08',
                 '2024-10-09','2024-10-10','2024-10-11','2024-10-12','2024-10-13',
                 '2024-10-14','2024-10-15']:
    dt = pd.Timestamp(date_str)
    if dt not in d.index:
        print(f"  {date_str}: NOT IN INDEX")
        continue
    row = d.loc[dt]
    snap = pack.snapshot_at(dt)
    print(f"  {date_str}: close=${row['close']:.2f}  ADX={row['adx']:.1f}  "
          f"HH_HL={int(row['consec_hh_hl'])}  LH_LL={int(row['consec_lh_ll'])}  "
          f"BMSB={snap['bmsb']}  2W_K={snap['stoch_2w_K']:.1f}  "
          f"SMA50slope={row['sma50_slope']:.2f}%")

print()

# Now check what the LIVE daily_collector produces
# The live pipeline uses build_daily_candles.aggregate_daily + compute_indicators on 1h candles
db_path = '../../data/candles.db'
conn = sqlite3.connect(db_path)

# Check if we have 1h candles for ETH/USDT in the DB
row_count = conn.execute(
    "SELECT COUNT(*) FROM candles WHERE symbol='ETH/USDT' AND timeframe='1h'"
).fetchone()[0]
print(f"=== 1h CANDLES IN DB ===")
print(f"ETH/USDT 1h candles: {row_count}")

if row_count > 0:
    # Get date range
    minmax = conn.execute(
        "SELECT MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol='ETH/USDT' AND timeframe='1h'"
    ).fetchone()
    print(f"Range: {pd.Timestamp(minmax[0], unit='ms').date()} to {pd.Timestamp(minmax[1], unit='ms').date()}")

# Check ETH/USDC too
for sym in ['ETH/USDC', 'SOL/USDC', 'SOL/USDT', 'BTC/USDC', 'BTC/USDT']:
    count = conn.execute(
        "SELECT COUNT(*) FROM candles WHERE symbol=? AND timeframe='1h'", (sym,)
    ).fetchone()[0]
    if count > 0:
        minmax = conn.execute(
            "SELECT MIN(timestamp), MAX(timestamp) FROM candles WHERE symbol=? AND timeframe='1h'", (sym,)
        ).fetchone()
        print(f"  {sym}: {count} rows, {pd.Timestamp(minmax[0], unit='ms').date()} to {pd.Timestamp(minmax[1], unit='ms').date()}")
    else:
        print(f"  {sym}: NO 1h candles")

print()

# Compare: what does the live pipeline's candles_daily look like for ETH/USDC?
for sym in ['ETH/USDT', 'ETH/USDC']:
    rows = conn.execute(
        "SELECT date, close, adx, consec_hh_hl, sma50_slope FROM candles_daily "
        "WHERE symbol=? AND date BETWEEN '2024-10-04' AND '2024-10-15' ORDER BY date",
        (sym,)
    ).fetchall()
    if rows:
        print(f"--- candles_daily {sym} Oct 2024 ---")
        for r in rows:
            print(f"  {r[0]}: close={r[1]:.2f}  ADX={r[2]:.1f if r[2] else 'NULL'}  "
                  f"HH_HL={r[3] if r[3] is not None else 'NULL'}  "
                  f"SMA50slope={r[4]:.2f if r[4] else 'NULL'}%")

# Key question: does the live ETH/USDC daily data match the backtest ETH/USDT daily data?
print()
print("=== COMPARING ETH/USDT (backtest) vs ETH/USDC (live) for Oct 2024 ===")
usdt = conn.execute(
    "SELECT date, close, adx, consec_hh_hl FROM candles_daily "
    "WHERE symbol='ETH/USDT' AND date BETWEEN '2024-10-04' AND '2024-10-15' ORDER BY date"
).fetchall()
usdc = conn.execute(
    "SELECT date, close, adx, consec_hh_hl FROM candles_daily "
    "WHERE symbol='ETH/USDC' AND date BETWEEN '2024-10-04' AND '2024-10-15' ORDER BY date"
).fetchall()
print(f"ETH/USDT rows: {len(usdt)}")
print(f"ETH/USDC rows: {len(usdc)}")
for u, c in zip(usdt, usdc):
    adx_diff = abs((u[2] or 0) - (c[2] or 0))
    hh_diff = (u[3] or 0) != (c[3] or 0)
    flag = " <<<" if adx_diff > 2 or hh_diff else ""
    print(f"  {u[0]}: USDT close=${u[1]:.2f} ADX={u[2]:.1f if u[2] else 'NULL'} HH={u[3]}  |  "
          f"USDC close=${c[1]:.2f} ADX={c[2]:.1f if c[2] else 'NULL'} HH={c[3]}{flag}")

conn.close()
