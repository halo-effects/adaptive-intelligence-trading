"""Trace daily tick-by-tick: standalone vs wrapper for ONE coin.
Find exactly where prices/phases/equity diverge."""
import sys, sqlite3
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

V13_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(V13_DIR))
TRADING_DIR = V13_DIR.parent.parent
sys.path.insert(0, str(TRADING_DIR))
sys.path.insert(0, str(TRADING_DIR / 'spot'))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack
from v13_lifecycle_engine_v2 import V13LifecycleEngineV2, V13Config as WrapperConfig

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'
COIN = 'XRP/USDC'  # Biggest gap
START = '2024-10-01'
END = '2026-02-27'

# ---- STANDALONE ----
cfg = V13Config()
cfg.CAPITAL = 2500
cfg.START_DATE = START
cfg.END_DATE = END
cfg.TIER1_PCT = 0.60; cfg.TIER2_PCT = 0.20; cfg.TIER3_PCT = 0.10
cfg.SHORT_TIER1_PCT = 0.60; cfg.SHORT_TIER2_PCT = 0.20; cfg.SHORT_TIER3_PCT = 0.10
cfg.SHORTS_ENABLED = True

pack = V13SignalPack(COIN, db_path=DB)
standalone = V13BacktestV8(pack, cfg)

# Monkey-patch standalone to log every daily tick
sa_ticks = []
original_run = standalone.run

def patched_run():
    start = pd.Timestamp(standalone.cfg.START_DATE)
    end = pd.Timestamp(standalone.cfg.END_DATE)
    data = standalone.daily[(standalone.daily.index >= start) & (standalone.daily.index <= end)]
    
    standalone.phase = Phase.DCA
    standalone.phase_start_date = data.index[0]
    standalone.phase_log.append({
        'date': data.index[0], 'from': None, 'to': Phase.DCA,
        'reason': 'START', 'equity': standalone.cfg.CAPITAL,
        'price': data['close'].iloc[0]
    })
    
    for date, row in data.iterrows():
        price = row['close']
        equity = standalone._total_equity(date)
        
        sa_ticks.append({
            'date': str(date)[:10],
            'price': price,
            'equity': equity,
            'phase': standalone.phase.name if hasattr(standalone.phase, 'name') else str(standalone.phase),
            'capital': standalone.capital,
            'pos_coins': standalone.position_coins,
            'short_coins': standalone.short_coins,
            'dca_coins': standalone.dca_coins,
            'trades': len(standalone.trades),
        })
        
        standalone.equity_curve.append({
            'date': date, 'equity': equity, 'price': price, 'phase': standalone.phase
        })
        
        if standalone.phase_start_date and (date - standalone.phase_start_date).days < standalone.cfg.MIN_PHASE_DAYS:
            if standalone.phase in (Phase.DCA, Phase.MARKUP) and standalone.dca_coins > 0:
                standalone._dca_tick(date, price)
            continue
        
        if standalone.phase == Phase.DCA:
            standalone._check_dca(date, price)
        elif standalone.phase == Phase.MARKUP:
            standalone._check_markup(date, price)
        elif standalone.phase == Phase.FLAT:
            standalone._check_flat(date, price)
        elif standalone.phase == Phase.MARKDOWN:
            standalone._check_markdown(date, price)
    
    # Close open positions
    if standalone.position_coins > 0:
        standalone._sell_all(data.index[-1], 'OPEN_END')
    if standalone.dca_coins > 0:
        standalone._dca_close(data.index[-1], 'OPEN_END')
    if standalone.short_coins > 0:
        standalone._close_short(data.index[-1], 'OPEN_END')
    
    return standalone._results()

result = patched_run()
print(f"STANDALONE: {len(sa_ticks)} daily ticks, final equity ${result['final_equity']:,.1f}")

# ---- WRAPPER ----
w_cfg = WrapperConfig.from_profile('high', capital=2500)
wrapper = V13LifecycleEngineV2(symbol=COIN, capital=2500, config=w_cfg)

# Load 1h candles
conn = sqlite3.connect(DB)
start_dt = datetime.strptime(START, "%Y-%m-%d").replace(tzinfo=timezone.utc)
start_ms = int(start_dt.timestamp() * 1000)
hourly = pd.read_sql_query(
    "SELECT timestamp as timestamp_ms, open, high, low, close, volume FROM candles "
    "WHERE symbol=? AND timeframe='1h' AND timestamp>=? ORDER BY timestamp",
    conn, params=('XRP/USDT', start_ms)
)
conn.close()
hourly.index = pd.to_datetime(hourly['timestamp_ms'], unit='ms', utc=True)

# Track wrapper daily ticks
wr_ticks = []
prev_date = None
for idx, row in hourly.iterrows():
    candle = {
        "timestamp": int(row["timestamp_ms"]),
        "open": float(row["open"]),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "close": float(row["close"]),
        "volume": float(row["volume"]),
    }
    
    current_date = idx.strftime('%Y-%m-%d')
    
    actions = wrapper.tick(candle, 2500)
    
    # Log on daily boundary (when wrapper would have ticked)
    if prev_date is not None and current_date != prev_date:
        eng = wrapper._engine
        # Get the price the wrapper used for this tick
        prev_ts = pd.Timestamp(prev_date)
        w_price = eng._price(prev_ts)
        if np.isnan(w_price):
            w_price = float(row['close'])
        
        last_price = float(row['close'])
        eq = eng.capital
        if eng.position_coins > 0:
            eq += eng.position_coins * last_price
        if eng.dca_coins > 0:
            eq += eng.dca_coins * last_price
        if eng.short_coins > 0:
            eq += eng.short_cost + (eng.short_entry - last_price) * eng.short_coins
        
        wr_ticks.append({
            'date': prev_date,
            'price': w_price,
            'equity': eq,
            'phase': eng.phase.name if hasattr(eng.phase, 'name') else str(eng.phase),
            'capital': eng.capital,
            'pos_coins': eng.position_coins,
            'short_coins': eng.short_coins,
            'dca_coins': eng.dca_coins,
            'trades': len(eng.trades),
        })
    
    prev_date = current_date

# Final state
eng = wrapper._engine
last_price = float(hourly['close'].iloc[-1])
eq = eng.capital
if eng.position_coins > 0: eq += eng.position_coins * last_price
if eng.dca_coins > 0: eq += eng.dca_coins * last_price
if eng.short_coins > 0: eq += eng.short_cost + (eng.short_entry - last_price) * eng.short_coins

print(f"WRAPPER:    {len(wr_ticks)} daily ticks, final equity ${eq:,.1f}")

# ---- COMPARE ----
print(f"\nDAILY TICK COMPARISON (showing divergences only):")
print(f"{'Date':>12} {'S_Price':>10} {'W_Price':>10} {'P_Diff':>8} {'S_Phase':>12} {'W_Phase':>12} {'S_Equity':>12} {'W_Equity':>12} {'E_Diff':>10} {'S_Trades':>8} {'W_Trades':>8}")
print("-" * 130)

# Build lookup by date
sa_by_date = {t['date']: t for t in sa_ticks}
wr_by_date = {t['date']: t for t in wr_ticks}

all_dates = sorted(set(list(sa_by_date.keys()) + list(wr_by_date.keys())))

divergence_count = 0
first_diverge = None
for d in all_dates:
    s = sa_by_date.get(d)
    w = wr_by_date.get(d)
    
    if not s or not w:
        if not s:
            print(f"{d:>12} {'---':>10} {w['price']:>10.4f} {'MISSING':>8} {'---':>12} {w['phase']:>12} {'---':>12} {w['equity']:>12,.1f}")
        else:
            print(f"{d:>12} {s['price']:>10.4f} {'---':>10} {'MISSING':>8} {s['phase']:>12} {'---':>12} {s['equity']:>12,.1f} {'---':>12}")
        divergence_count += 1
        continue
    
    price_diff = abs(s['price'] - w['price'])
    eq_diff = w['equity'] - s['equity']
    phase_match = s['phase'] == w['phase']
    
    # Show if price differs, phase differs, or equity diverges significantly
    if price_diff > 0.0001 or not phase_match or abs(eq_diff) > 1:
        flag = ''
        if price_diff > 0.0001: flag += 'P'
        if not phase_match: flag += 'PH'
        if abs(eq_diff) > 1: flag += 'E'
        
        print(f"{d:>12} {s['price']:>10.4f} {w['price']:>10.4f} {price_diff:>8.4f} {s['phase']:>12} {w['phase']:>12} {s['equity']:>12,.1f} {w['equity']:>12,.1f} {eq_diff:>+10.1f} {s['trades']:>8} {w['trades']:>8}  [{flag}]")
        divergence_count += 1
        if first_diverge is None:
            first_diverge = d

print(f"\nTotal divergent days: {divergence_count}")
print(f"First divergence: {first_diverge}")
print(f"\nFinal standalone equity: ${result['final_equity']:,.1f}")
print(f"Final wrapper equity:    ${eq:,.1f}")
print(f"Delta:                   ${eq - result['final_equity']:+,.1f}")
