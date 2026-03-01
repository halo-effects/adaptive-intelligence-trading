"""Find what differs between V13SignalPack('XRP') and V13SignalPack('XRP/USDC')."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
import pandas as pd

p1 = V13SignalPack('XRP')
p2 = V13SignalPack('XRP/USDC')

# Daily data
print(f"Daily identical: {p1.daily.equals(p2.daily)}")
print(f"Daily symbol attr: p1={p1.daily.attrs.get('symbol')}, p2={p2.daily.attrs.get('symbol')}")

# CFGI
print(f"CFGI: p1={p1.cfgi_df is not None}, p2={p2.cfgi_df is not None}")

# Check structure signals
print(f"\nStructure HH_HL comparison:")
for date in ['2024-10-05', '2024-10-06', '2024-10-07', '2025-04-04', '2025-04-05']:
    dt = pd.Timestamp(date)
    v1 = p1.structure.hh_hl_at(dt) if hasattr(p1.structure, 'hh_hl_at') else 'N/A'
    v2 = p2.structure.hh_hl_at(dt) if hasattr(p2.structure, 'hh_hl_at') else 'N/A'
    print(f"  {date}: p1={v1}, p2={v2}")

# Check all signal objects
for attr in ['stoch_1w', 'stoch_2w', 'stoch_3w', 'bmsb', 'structure', 'cfgi']:
    o1 = getattr(p1, attr)
    o2 = getattr(p2, attr)
    print(f"\n{attr}: type={type(o1).__name__}, same_type={type(o1)==type(o2)}")
    if hasattr(o1, 'data') and hasattr(o2, 'data'):
        if isinstance(o1.data, pd.DataFrame) and isinstance(o2.data, pd.DataFrame):
            print(f"  data identical: {o1.data.equals(o2.data)}")
