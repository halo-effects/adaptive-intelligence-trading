"""Reproduce paper bot +199% baseline using default V13 config."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack

DB = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'

coins = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
total_eq = 0
total_cap = 0

print(f"Default config: START={V13Config().START_DATE} END={V13Config().END_DATE}")
print()

for coin in coins:
    cfg = V13Config()
    cfg.START_DATE = '2024-10-01'  # Paper bot DEFAULT_START_DATE
    cfg.END_DATE = '2026-02-27'
    cfg.CAPITAL = 2500
    cfg.TIER1_PCT = 0.60
    cfg.TIER2_PCT = 0.20
    cfg.TIER3_PCT = 0.10
    cfg.SHORT_TIER1_PCT = 0.60
    cfg.SHORT_TIER2_PCT = 0.20
    cfg.SHORT_TIER3_PCT = 0.10
    cfg.SHORTS_ENABLED = True

    pack = V13SignalPack(coin, db_path=DB)
    e = V13BacktestV8(pack, cfg)
    r = e.run()
    if not r:
        short = coin.split('/')[0]
        print(f"{short}: FAILED")
        continue

    short = coin.split('/')[0]
    start = str(r['start'].date())
    end = str(r['end'].date())
    print(f"{short}: ROI={r['roi']:+.1f}%  eq=${r['final_equity']:.0f}  "
          f"closed={r['closed_roi']:+.1f}%  period={start} to {end}  "
          f"cycles={r['markup_cycles']}  dca=${e.dca_pnl:+.1f}")
    total_eq += r['final_equity']
    total_cap += 2500

port_roi = (total_eq - total_cap) / total_cap * 100
print(f"\nPortfolio: {port_roi:+.1f}%  (${total_eq:.0f} from ${total_cap})")
print(f"Paper bot reference: +200.1% ($30,011 from $10,000)")
