"""Quick verify signals are working after rebuild."""
from v13_signals import V13SignalPack
import pandas as pd

for coin in ['ETH', 'SOL', 'BTC']:
    pack = V13SignalPack(coin)
    d = pack.daily
    sym = d.attrs.get('symbol', '?')
    adx_v = d['adx'].notna().sum()
    k_dec = pack.stoch_2w.get_k_at(pd.Timestamp('2024-12-22'))
    print(f"{coin}: {sym}  {len(d)} rows  {d.index[0].date()} to {d.index[-1].date()}  "
          f"ADX valid={adx_v}  2W_K@Dec22={k_dec:.1f}")
    
    # Check key market moments
    dates = ['2021-05-12', '2021-11-10', '2022-06-18', '2023-01-01', '2024-03-14', '2024-12-22']
    for dt_str in dates:
        dt = pd.Timestamp(dt_str)
        if dt > d.index[-1] or dt < d.index[0]:
            continue
        snap = pack.snapshot_at(dt)
        stoch = snap['stoch_2w_K']
        adx = snap['adx']
        bmsb = snap['bmsb']
        cfgi = snap['cfgi']
        hh = snap['hh_hl']
        ll = snap['lh_ll']
        stoch_str = f"{stoch:.1f}" if not pd.isna(stoch) else "NaN"
        adx_str = f"{adx:.1f}" if not pd.isna(adx) else "NaN"
        cfgi_str = f"{cfgi:.0f}" if not pd.isna(cfgi) else "NaN"
        print(f"    {dt_str}: 2W_K={stoch_str:>5s}  ADX={adx_str:>5s}  BMSB={bmsb:<8s}  "
              f"CFGI={cfgi_str:>4s}  HH_HL={hh}  LH_LL={ll}")
    print()
