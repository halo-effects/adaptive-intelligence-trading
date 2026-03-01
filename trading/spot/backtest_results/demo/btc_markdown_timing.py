"""Check exactly when BTC enters/exits markdown."""
import sys, os, sqlite3, pandas as pd
os.chdir(r"C:\Users\Never\.openclaw\workspace")
sys.path.insert(0, ".")
import logging; logging.basicConfig(level=logging.WARNING)
from trading.spot.backtest_engine_consolidated import SpotBacktestEngineV12, LifecyclePhase

orig_md = SpotBacktestEngineV12._transition_to_markdown
def traced_md(self, price, ts, *a, **kw):
    dt = pd.Timestamp(int(float(ts)), unit="ms")
    print(f"MARKDOWN entered: {dt}, price=${price:.0f}, exit_entry=${self._exit_entry_price:.0f}")
    return orig_md(self, price, ts, *a, **kw)
SpotBacktestEngineV12._transition_to_markdown = traced_md

orig_exit = SpotBacktestEngineV12._transition_to_exit
def traced_exit(self, price, ts, ts_ms, daily_score):
    dt = pd.Timestamp(int(float(ts)), unit="ms")
    print(f"EXIT entered: {dt}, price=${price:.0f}")
    return orig_exit(self, price, ts, ts_ms, daily_score)
SpotBacktestEngineV12._transition_to_exit = traced_exit

DB = "trading/spot/data/candles.db"
conn = sqlite3.connect(DB)
s = int(pd.Timestamp("2024-10-01").timestamp() * 1000)
e = int(pd.Timestamp("2025-03-01").timestamp() * 1000)
w = pd.read_sql_query("SELECT timestamp,open,high,low,close,volume FROM candles WHERE symbol='BTC/USDC' AND timestamp<? ORDER BY timestamp DESC LIMIT 2500", conn, params=(s,)).sort_values("timestamp")
f = pd.read_sql_query("SELECT timestamp,open,high,low,close,volume FROM candles WHERE symbol='BTC/USDC' AND timestamp>=? AND timestamp<=? ORDER BY timestamp", conn, params=(s, e))
df = pd.concat([w, f]).reset_index(drop=True)
for c in ["open","high","low","close","volume"]: df[c] = pd.to_numeric(df[c])
df["timestamp"] = df["timestamp"].astype(int)
conn.close()

eng = SpotBacktestEngineV12(symbol="BTC/USDC", timeframe="1h", capital=10000, profile="high",
    exchange="binance", v12f_gates=True, v12f_markdown_exit=True)
eng.run(df)
print(f"\nFinal phase: {eng._lifecycle_phase}")
print(f"Markdown entered ts: {eng._markdown_entered_ts}")
if eng._markdown_entered_ts:
    dt = pd.Timestamp(int(eng._markdown_entered_ts), unit="ms")
    print(f"Markdown entered date: {dt}")
