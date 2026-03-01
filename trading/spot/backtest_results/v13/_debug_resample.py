import sqlite3, pandas as pd, numpy as np
from pathlib import Path
from v13_signals import load_daily, resample_nweek_ohlc

for coin in ['LINK/USDC', 'XRP/USDC']:
    d = load_daily(coin)
    if d is None:
        print(f'{coin}: no data')
        continue
    sym = d.attrs.get('symbol', '?')
    print(f'{coin}: loaded {sym}, {len(d)} rows, {d.index[0]}..{d.index[-1]}')
    print(f'  Index dtype: {d.index.dtype}, has NaT: {d.index.isna().any()}')
    print(f'  First 3 timestamps: {list(d["timestamp"][:3])}')
    
    # Try resampling
    try:
        ohlc = resample_nweek_ohlc(d[['open','high','low','close','volume']], 2)
        print(f'  2W resample: {len(ohlc)} rows, OK')
    except Exception as e:
        print(f'  2W resample FAILED: {e}')
        # Debug: check what resample produces
        import traceback
        traceback.print_exc()
