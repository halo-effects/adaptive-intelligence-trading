"""Compare pack loaded with db_path vs without."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_signals import V13SignalPack
import pandas as pd

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'

# With explicit db_path (standalone style)
pack1 = V13SignalPack('XRP/USDC', db_path=DB)
# Without (wrapper style)
pack2 = V13SignalPack('XRP/USDC')

# Compare daily data
print(f"Daily rows: pack1={len(pack1.daily)}, pack2={len(pack2.daily)}")
print(f"Daily start: pack1={pack1.daily.index[0]}, pack2={pack2.daily.index[0]}")
print(f"Daily end:   pack1={pack1.daily.index[-1]}, pack2={pack2.daily.index[-1]}")

# Compare exact values
if pack1.daily.equals(pack2.daily):
    print("Daily data: IDENTICAL")
else:
    diffs = (pack1.daily != pack2.daily).any(axis=1)
    print(f"Daily data: {diffs.sum()} rows differ")

# Compare CFGI
if pack1.cfgi_df is not None and pack2.cfgi_df is not None:
    print(f"\nCFGI rows: pack1={len(pack1.cfgi_df)}, pack2={len(pack2.cfgi_df)}")
    if pack1.cfgi_df.equals(pack2.cfgi_df):
        print("CFGI data: IDENTICAL")
    else:
        print("CFGI data: DIFFERENT")
else:
    print(f"CFGI: pack1={'OK' if pack1.cfgi_df is not None else 'None'}, pack2={'OK' if pack2.cfgi_df is not None else 'None'}")

# Check coin mapping
print(f"\nCoin: pack1={pack1.coin}, pack2={pack2.coin}")
