"""Trace V12 markup entry/exit to diagnose negative PnL."""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

import logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

from trading.spot.run_v12_chained import run_chained, DEFAULT_V12_PARAMS, PRESETS

p = PRESETS['eth'].copy()
params = dict(DEFAULT_V12_PARAMS)

# Monkey-patch to trace transitions
from trading.spot import backtest_engine_v12 as eng

orig_markup_trans = eng.SpotBacktestEngineV12._transition_to_markup
def traced_markup_trans(self, price, ts):
    print(f"\n*** MARKUP ENTRY: price=${price:.2f}, cash=${self.cash:.0f}, ts={ts}")
    orig_markup_trans(self, price, ts)
    print(f"*** MARKUP DEPLOYED: qty={self._markup_position_qty:.4f}, avg=${self._markup_avg_entry:.2f}, cash=${self.cash:.0f}")
eng.SpotBacktestEngineV12._transition_to_markup = traced_markup_trans

orig_markup_close = eng.SpotBacktestEngineV12._close_markup_position
def traced_markup_close(self, sell_price, ts, reason):
    print(f"\n*** MARKUP EXIT: sell_price=${sell_price:.2f}, reason={reason}, ts={ts}")
    print(f"*** MARKUP POS: qty={self._markup_position_qty:.4f}, avg_entry=${self._markup_avg_entry:.2f}")
    print(f"*** MARKUP PNL: (${sell_price:.2f} - ${self._markup_avg_entry:.2f}) * {self._markup_position_qty:.4f} = ${(sell_price - self._markup_avg_entry) * self._markup_position_qty:.2f}")
    orig_markup_close(self, sell_price, ts, reason)
    print(f"*** AFTER CLOSE: cash=${self.cash:.0f}, total_markup_pnl=${self._v12_markup_pnl:.2f}")
eng.SpotBacktestEngineV12._close_markup_position = traced_markup_close

# Also trace spring entries
orig_spring = eng.SpotBacktestEngineV12._run_spring_candle
call_count = [0]
def traced_spring(self, price, high, low, ts, regime, fg_value):
    call_count[0] += 1
    if call_count[0] % 500 == 1:
        print(f"  SPRING candle: price=${price:.0f}, cash=${self.cash:.0f}, deployed=${self._spring_deployed:.0f}, entries={len(self._spring_entries)}")
    orig_spring(self, price, high, low, ts, regime, fg_value)
eng.SpotBacktestEngineV12._run_spring_candle = traced_spring

# Also trace markdown entry
orig_md = eng.SpotBacktestEngineV12._transition_to_markdown
def traced_md(self, price, ts):
    print(f"\n*** MARKDOWN ENTRY: price=${price:.2f}, cash=${self.cash:.0f}, ts={ts}")
    orig_md(self, price, ts)
eng.SpotBacktestEngineV12._transition_to_markdown = traced_md

# Trace spring transition
orig_spring_trans = eng.SpotBacktestEngineV12._transition_to_spring
def traced_spring_trans(self, price, ts):
    print(f"\n*** SPRING ENTRY: price=${price:.2f}, cash=${self.cash:.0f}, exit_entry=${self._exit_entry_price:.2f}, ts={ts}")
    orig_spring_trans(self, price, ts)
eng.SpotBacktestEngineV12._transition_to_spring = traced_spring_trans

# Trace exit
orig_exit = eng.SpotBacktestEngineV12._transition_to_exit
def traced_exit(self, price, ts, ts_ms, daily_score):
    print(f"\n*** EXIT ENTRY: price=${price:.2f}, cash=${self.cash:.0f}, ts={ts}, score={daily_score}")
    orig_exit(self, price, ts, ts_ms, daily_score)
eng.SpotBacktestEngineV12._transition_to_exit = traced_exit

from trading.spot.macro_indicators import load_historical_fear_greed
fg = load_historical_fear_greed()
result, info = run_chained(p['symbol'], '1h', p['start'], p['end'], p['capital'], fg, params)
print(f"\nFINAL: pnl={result.total_return_pct:.2f}%, markup_pnl={result.extra.get('v12_markup_pnl',0):.2f}")
