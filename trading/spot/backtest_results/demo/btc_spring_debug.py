"""Debug why BTC never reaches spring in gate-driven architecture."""
import sys, os, sqlite3, pandas as pd
from pathlib import Path

os.chdir(r"C:\Users\Never\.openclaw\workspace")
sys.path.insert(0, ".")

import logging
logging.basicConfig(level=logging.WARNING)

from trading.spot.backtest_engine_consolidated import SpotBacktestEngineV12, LifecyclePhase

# Patch _check_spring_gates to log details
original_gates = SpotBacktestEngineV12._check_spring_gates
gate_log = []

def traced_gates(self, price, ts, ts_ms):
    result = original_gates(self, price, ts, ts_ms)
    dwell_days = self._markdown_candles_elapsed / 24
    discount = 0
    if self._exit_entry_price > 0:
        discount = (self._exit_entry_price - price) / self._exit_entry_price * 100
    
    # Log every 24 candles while in MARKDOWN and past 10% floor
    if (self._lifecycle_phase == LifecyclePhase.MARKDOWN 
            and self._markdown_candles_elapsed % 24 == 0
            and discount >= 10.0):
        gate_log.append({
            'ts': ts, 'price': price, 'discount': discount,
            'dwell_days': dwell_days, 'result': result
        })
    return result

SpotBacktestEngineV12._check_spring_gates = traced_gates

# Track markdown entries
original_md = SpotBacktestEngineV12._transition_to_markdown
md_log = []
def traced_md(self, price, ts, *args, **kwargs):
    md_log.append({'ts': ts, 'price': price, 'exit_entry': self._exit_entry_price})
    return original_md(self, price, ts, *args, **kwargs)
SpotBacktestEngineV12._transition_to_markdown = traced_md

# Load BTC candles
DB = Path("trading/spot/data/candles.db")
conn = sqlite3.connect(str(DB))
start_ts = int(pd.Timestamp("2024-10-01").timestamp() * 1000)
end_ts = int(pd.Timestamp("2025-03-01").timestamp() * 1000)
warmup = pd.read_sql_query(
    "SELECT timestamp,open,high,low,close,volume FROM candles WHERE symbol=? AND timestamp<? ORDER BY timestamp DESC LIMIT 2500",
    conn, params=("BTC/USDC", start_ts))
warmup = warmup.sort_values("timestamp")
fwd = pd.read_sql_query(
    "SELECT timestamp,open,high,low,close,volume FROM candles WHERE symbol=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp",
    conn, params=("BTC/USDC", start_ts, end_ts))
df = pd.concat([warmup, fwd]).reset_index(drop=True)
for c in ["open","high","low","close","volume"]:
    df[c] = pd.to_numeric(df[c])
df["timestamp"] = df["timestamp"].astype(int)

# Get BTC CFGI data
cfgi_df = pd.read_sql_query(
    "SELECT date, cfgi as value FROM cfgi_daily WHERE symbol='BTC' AND date >= '2024-10-01' AND date <= '2025-03-01' ORDER BY date",
    conn)
conn.close()

# Run engine
engine = SpotBacktestEngineV12(
    symbol="BTC/USDC", timeframe="1h", capital=10000, profile="high",
    exchange="binance", v12f_gates=True, v12f_markdown_exit=True)
result = engine.run(df)

print("=== BTC MARKDOWN ENTRIES ===")
for m in md_log:
    exit_p = m['exit_entry']
    print(f"  Entered MARKDOWN: price=${m['price']:.0f}, exit_entry_price=${exit_p:.0f}")

print(f"\n=== GATE CHECKS (daily, past 10% floor) ===")
print(f"Total logged: {len(gate_log)}")
for g in gate_log[:40]:
    ts_str = pd.Timestamp(int(float(g['ts'])), unit='ms').strftime('%Y-%m-%d')
    print(f"  {ts_str}: price=${g['price']:.0f}, discount={g['discount']:.1f}%, "
          f"dwell={g['dwell_days']:.0f}d, passed={g['result']}")

print(f"\n=== BTC CFGI VALUES ===")
if len(cfgi_df) > 0:
    print(f"Records: {len(cfgi_df)}")
    print(f"Min: {cfgi_df['value'].min():.1f}, Max: {cfgi_df['value'].max():.1f}, Mean: {cfgi_df['value'].mean():.1f}")
    below_35 = cfgi_df[cfgi_df['value'] <= 35]
    print(f"Days with CFGI <= 35: {len(below_35)}")
    if len(below_35) > 0:
        for _, row in below_35.iterrows():
            print(f"  {row['date']}: CFGI={row['value']:.1f}")
    below_50 = cfgi_df[cfgi_df['value'] <= 50]
    print(f"Days with CFGI <= 50: {len(below_50)}")
else:
    print("NO CFGI DATA FOR BTC!")

print(f"\n=== RESULT ===")
print(f"Return: {result.total_return_pct:+.2f}%, MaxDD: {result.max_drawdown_pct:.2f}%")
state = engine.snapshot_state()
print(f"EXIT={state.get('v12_exit_phases', 0)}, MARKDOWN={state.get('v12_markdown_phases', 0)}, "
      f"SPRING={state.get('v12_spring_phases', 0)}")
print(f"Cooldown candles remaining: {engine._exit_cooldown_candles}")
print(f"Markdown candles elapsed: {engine._markdown_candles_elapsed}")
print(f"Current phase: {engine._lifecycle_phase}")
