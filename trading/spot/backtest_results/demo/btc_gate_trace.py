"""Trace BTC gate checks with 5% floor."""
import sys, os, sqlite3, pandas as pd
os.chdir(r"C:\Users\Never\.openclaw\workspace")
sys.path.insert(0, ".")
import logging
logging.basicConfig(level=logging.WARNING)

from trading.spot.backtest_engine_consolidated import SpotBacktestEngineV12, LifecyclePhase

# Patch to trace gate checks
original_gates = SpotBacktestEngineV12._check_spring_gates
gate_attempts = []

def traced_gates(self, price, ts, ts_ms):
    result = original_gates(self, price, ts, ts_ms)
    if self._lifecycle_phase == LifecyclePhase.MARKDOWN:
        discount = 0
        if self._exit_entry_price > 0:
            discount = (self._exit_entry_price - price) / self._exit_entry_price * 100
        gate_attempts.append({
            'ts_ms': float(ts), 'price': price, 'discount': discount,
            'dwell_candles': getattr(self, '_markdown_candles_elapsed', -1),
            'result': result
        })
    return result
SpotBacktestEngineV12._check_spring_gates = traced_gates

DB = "trading/spot/data/candles.db"
conn = sqlite3.connect(DB)
start_ts = int(pd.Timestamp("2024-10-01").timestamp() * 1000)
end_ts = int(pd.Timestamp("2025-03-01").timestamp() * 1000)
warmup = pd.read_sql_query("SELECT timestamp,open,high,low,close,volume FROM candles WHERE symbol='BTC/USDC' AND timestamp<? ORDER BY timestamp DESC LIMIT 2500", conn, params=(start_ts,))
warmup = warmup.sort_values("timestamp")
fwd = pd.read_sql_query("SELECT timestamp,open,high,low,close,volume FROM candles WHERE symbol='BTC/USDC' AND timestamp>=? AND timestamp<=? ORDER BY timestamp", conn, params=(start_ts, end_ts))
df = pd.concat([warmup, fwd]).reset_index(drop=True)
for c in ["open","high","low","close","volume"]: df[c] = pd.to_numeric(df[c])
df["timestamp"] = df["timestamp"].astype(int)
conn.close()

engine = SpotBacktestEngineV12(symbol="BTC/USDC", timeframe="1h", capital=10000, profile="high",
    exchange="binance", v12f_gates=True, v12f_markdown_exit=True)
result = engine.run(df)

print(f"BTC: {result.total_return_pct:+.2f}%, Springs={engine.snapshot_state().get('v12_spring_phases',0)}")
print(f"Exit entry: ${engine._exit_entry_price:.0f}")
print(f"\nGate check attempts: {len(gate_attempts)}")
if gate_attempts:
    print("First 20:")
    for g in gate_attempts[:20]:
        dt = pd.Timestamp(int(g['ts_ms']), unit='ms').strftime('%Y-%m-%d %H:%M')
        print(f"  {dt}: price=${g['price']:.0f}, disc={g['discount']:.1f}%, dwell={g['dwell_candles']}h, passed={g['result']}")
else:
    print("NO gate checks attempted — floor never reached or markdown never entered fallback path")
    print(f"Phase at end: {engine._lifecycle_phase}")
    print(f"Markdown candles: {engine._markdown_candles_elapsed}")
    print(f"Exit entry price: {engine._exit_entry_price}")
