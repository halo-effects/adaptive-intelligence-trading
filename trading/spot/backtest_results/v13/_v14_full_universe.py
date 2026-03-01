"""V14 vs V13 across expanded coin universe."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v14_dca_engine import V14DCAEngine, V14Config
from v13_phase_backtest_v8 import V13BacktestV8, V13Config as V8Config
from v13_signals import V13SignalPack

# Full universe — use USDT for coins without USDC 1h data
COINS = [
    'BTC/USDT', 'ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC',
    'HBAR/USDT', 'AAVE/USDT', 'ADA/USDT', 'BNB/USDT', 'AVAX/USDT',
    'DOT/USDT', 'UNI/USDT', 'NEAR/USDT', 'LTC/USDT', 'ATOM/USDT',
]

CAPITAL = 2500  # Per coin

print("=" * 90)
print(f"V14 DCA ACCUMULATE vs V13 BASELINE — {len(COINS)} coins, ${CAPITAL}/coin, Oct 2024 start")
print("=" * 90)
print(f"{'Coin':<12} {'V13':>10} {'V13%':>8} {'V14':>10} {'V14%':>8} {'Delta':>10} {'V14 Phases':>10} {'Notes'}")
print("-" * 90)

v13_total = 0
v14_total = 0
v13_ok = 0
v14_ok = 0

for coin in COINS:
    base = coin.split('/')[0]
    v13_eq = None
    v14_eq = None
    v14_phases = 0
    notes = []

    # V13
    try:
        pack = V13SignalPack(coin)
        cfg = V8Config()
        cfg.CAPITAL = CAPITAL
        cfg.START_DATE = '2024-10-01'
        eng = V13BacktestV8(pack, cfg)
        r = eng.run()
        v13_eq = r['final_equity']
        v13_total += v13_eq
        v13_ok += 1
    except Exception as e:
        notes.append(f"V13:{str(e)[:30]}")

    # V14
    try:
        pack = V13SignalPack(coin)
        cfg = V14Config()
        cfg.CAPITAL = CAPITAL
        cfg.START_DATE = '2024-10-01'
        eng = V14DCAEngine(pack, cfg)
        r = eng.run()
        v14_eq = r['final_equity']
        v14_total += v14_eq
        v14_ok += 1
        v14_phases = r['phase_changes']
        
        # Note key events
        if r.get('top_triggers'):
            for t in r['top_triggers']:
                notes.append(f"TOP:{t['date'].strftime('%m/%d')}")
        if r.get('conviction_triggers'):
            for t in r['conviction_triggers']:
                notes.append(f"BOT:{t['date'].strftime('%m/%d')}")
        if r['max_drawdown'] < -50:
            notes.append(f"DD:{r['max_drawdown']:.0f}%")
    except Exception as e:
        notes.append(f"V14:{str(e)[:30]}")

    # Print row
    v13_str = f"${v13_eq:>8,.0f}" if v13_eq else "    ERROR"
    v14_str = f"${v14_eq:>8,.0f}" if v14_eq else "    ERROR"
    v13_pct = f"{(v13_eq-CAPITAL)/CAPITAL*100:>+7.1f}%" if v13_eq else "      N/A"
    v14_pct = f"{(v14_eq-CAPITAL)/CAPITAL*100:>+7.1f}%" if v14_eq else "      N/A"
    delta_str = f"${v14_eq-v13_eq:>+8,.0f}" if v13_eq and v14_eq else "      N/A"
    winner = "<" if v13_eq and v14_eq and v14_eq > v13_eq else ">" if v13_eq and v14_eq and v13_eq > v14_eq else "="
    
    print(f"  {coin:<10} {v13_str} {v13_pct} {v14_str} {v14_pct} {delta_str} {winner} {v14_phases:>5}ph  {' '.join(notes)}")

print("-" * 90)
v13_pct = (v13_total - CAPITAL*v13_ok) / (CAPITAL*v13_ok) * 100 if v13_ok else 0
v14_pct = (v14_total - CAPITAL*v14_ok) / (CAPITAL*v14_ok) * 100 if v14_ok else 0
print(f"  {'TOTAL':<10} ${v13_total:>8,.0f} {v13_pct:>+7.1f}% ${v14_total:>8,.0f} {v14_pct:>+7.1f}% ${v14_total-v13_total:>+8,.0f}")
print(f"\n  V14 wins on: ", end="")
# Recount
v14_wins = 0
v13_wins = 0
for coin in COINS:
    # Would need to rerun, just count from output
    pass
print(f"(see per-coin comparison above)")
