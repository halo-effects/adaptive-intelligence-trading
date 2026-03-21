"""Probe the running bot by importing the same module and checking bytecode."""
import sys, os, importlib, marshal, types

os.chdir(r'C:\Users\Never\.openclaw\workspace')
sys.path.insert(0, r'C:\Users\Never\.openclaw\workspace')

# Import the module fresh (this is what the running process would have done)
mod = importlib.import_module('trading.spot.run_v14_portfolio_live_aster')

# Find _write_status on the class
cls = mod.V14PortfolioLiveAster
method = cls._write_status
code = method.__code__

print("_write_status code object:")
print(f"  co_filename: {code.co_filename}")
print(f"  co_firstlineno: {code.co_firstlineno}")

str_consts = [c for c in code.co_consts if isinstance(c, str)]
print(f"  Has 'cash': {'cash' in str_consts}")
print(f"  Has 'exchange_balance': {'exchange_balance' in str_consts}")
print(f"  Has 'total_realized_pnl': {'total_realized_pnl' in str_consts}")
print(f"  Calls fetch_full_balance: {'fetch_full_balance' in code.co_names}")
print(f"  Calls fetch_balance: {'fetch_balance' in code.co_names}")
