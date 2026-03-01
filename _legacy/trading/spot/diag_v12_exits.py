"""Diagnose why SOL/BTC get fewer exits. Trace daily scores at known peaks."""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

import logging
logging.basicConfig(stream=sys.stdout, level=logging.WARNING)

from trading.spot.run_v12_chained import run_chained, DEFAULT_V12_PARAMS
from trading.spot.macro_indicators import load_historical_fear_greed
from trading.spot import backtest_engine_v12 as eng

fg = load_historical_fear_greed()

# Trace all phase transitions
transitions = []
orig_exit = eng.SpotBacktestEngineV12._transition_to_exit
def traced_exit(self, price, ts, ts_ms, daily_score):
    transitions.append(('EXIT', price, ts, daily_score))
    orig_exit(self, price, ts, ts_ms, daily_score)
eng.SpotBacktestEngineV12._transition_to_exit = traced_exit

orig_md = eng.SpotBacktestEngineV12._transition_to_markdown
def traced_md(self, price, ts):
    transitions.append(('MARKDOWN', price, ts, 0))
    orig_md(self, price, ts)
eng.SpotBacktestEngineV12._transition_to_markdown = traced_md

orig_sp = eng.SpotBacktestEngineV12._transition_to_spring
def traced_sp(self, price, ts):
    transitions.append(('SPRING', price, ts, 0))
    orig_sp(self, price, ts)
eng.SpotBacktestEngineV12._transition_to_spring = traced_sp

orig_mu = eng.SpotBacktestEngineV12._transition_to_markup
def traced_mu(self, price, ts):
    transitions.append(('MARKUP', price, ts, 0))
    orig_mu(self, price, ts)
eng.SpotBacktestEngineV12._transition_to_markup = traced_mu

orig_dca = eng.SpotBacktestEngineV12._transition_to_dca
def traced_dca(self, price, ts):
    transitions.append(('DCA', price, ts, 0))
    orig_dca(self, price, ts)
eng.SpotBacktestEngineV12._transition_to_dca = traced_dca

for coin, symbol in [('BTC', 'BTC/USDT')]:
    transitions.clear()
    params = dict(DEFAULT_V12_PARAMS)
    try:
        result, info = run_chained(symbol, '1h', '2020-10-01', '2025-02-20', 10000, fg, params)
        print("\n=== %s: PnL=%+.1f%% ===" % (coin, result.total_return_pct))
        from datetime import datetime
        for phase, price, ts, score in transitions:
            try:
                dt = datetime.fromtimestamp(float(ts)/1000).strftime('%Y-%m-%d')
            except:
                dt = str(ts)[:10]
            extra = " score=%.1f" % score if score else ""
            print("  %s -> %s at $%.0f%s" % (dt, phase, price, extra))
    except Exception as e:
        print("%s: ERROR %s" % (coin, e))
        import traceback
        traceback.print_exc()
