"""Check where Python actually loads the trading module from."""
import sys
import os

os.chdir(r'C:\Users\Never\.openclaw\workspace')
sys.path.insert(0, r'C:\Users\Never\.openclaw\workspace')

import trading.spot.run_v14_portfolio_live_aster as mod

print(f"Module file: {mod.__file__}")
print(f"Module cached: {getattr(mod, '__cached__', 'N/A')}")

# Check the actual _write_status code
cls = mod.V14PortfolioLiveAster
ws = cls._write_status
code = ws.__code__
str_consts = [c for c in code.co_consts if isinstance(c, str)]

print(f"\n_write_status at line {code.co_firstlineno}")
print(f"Has 'cash': {'cash' in str_consts}")
print(f"Has 'exchange_balance': {'exchange_balance' in str_consts}")

# Check if trading is an installed package
try:
    import importlib.metadata
    dist = importlib.metadata.distribution('trading')
    print(f"\nWARNING: trading is an installed package!")
    print(f"  Name: {dist.metadata['Name']}")
except Exception:
    print("\nNo installed 'trading' package (good)")

# Check all trading module paths
import trading
print(f"\ntrading.__file__: {trading.__file__}")
print(f"trading.__path__: {trading.__path__}")

# Check for .pth files or egg-links
site_packages = [p for p in sys.path if 'site-packages' in p]
print(f"\nSite packages dirs: {site_packages}")
for sp in site_packages:
    if os.path.exists(sp):
        pth_files = [f for f in os.listdir(sp) if f.endswith('.pth') or f.endswith('.egg-link')]
        if pth_files:
            print(f"  {sp}: {pth_files}")
