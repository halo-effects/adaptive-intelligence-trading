"""Build transition matrix for V14: every phase change, what triggered it, outcome."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from v14_dca_engine import V14DCAEngine, V14Config
from v13_signals import V13SignalPack
import pandas as pd

COINS = [
    'BTC/USDT', 'ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC',
    'HBAR/USDT', 'AAVE/USDT', 'ADA/USDT', 'BNB/USDT', 'AVAX/USDT',
    'DOT/USDT', 'UNI/USDT', 'NEAR/USDT', 'LTC/USDT', 'ATOM/USDT',
]

all_transitions = []
all_trades = []

for coin in COINS:
    base = coin.split('/')[0]
    try:
        pack = V13SignalPack(coin)
        cfg = V14Config()
        cfg.CAPITAL = 2500
        cfg.START_DATE = '2024-10-01'
        eng = V14DCAEngine(pack, cfg)
        r = eng.run()
    except Exception as e:
        continue

    phases = r['phases']
    trades = r['trades']
    eq_curve = r['equity_curve']

    # For each phase, compute: duration, PnL during phase, trade count
    for i, p in enumerate(phases):
        start_date = p['date']
        end_date = phases[i+1]['date'] if i+1 < len(phases) else eq_curve.iloc[-1]['date'] if len(eq_curve) > 0 else start_date
        duration = (end_date - start_date).days

        # Equity at phase start and end
        eq_at_start = eq_curve[eq_curve['date'] >= start_date]
        eq_at_end = eq_curve[eq_curve['date'] <= end_date]
        eq_start_val = eq_at_start.iloc[0]['equity'] if len(eq_at_start) > 0 else 2500
        eq_end_val = eq_at_end.iloc[-1]['equity'] if len(eq_at_end) > 0 else eq_start_val
        phase_pnl = eq_end_val - eq_start_val
        phase_pnl_pct = phase_pnl / eq_start_val * 100 if eq_start_val > 0 else 0

        # Max drawdown during phase
        phase_eq = eq_curve[(eq_curve['date'] >= start_date) & (eq_curve['date'] <= end_date)]
        if len(phase_eq) > 0:
            peak = phase_eq['equity'].cummax()
            dd = ((phase_eq['equity'] - peak) / peak * 100).min()
        else:
            dd = 0

        # Count trades during phase
        phase_trades = [t for t in trades if start_date <= t['date'] <= end_date]
        n_trades = len(phase_trades)

        # Classify transition type
        reason = p['reason']
        if 'OB93' in reason:
            trigger = 'OB93_armed'
        elif 'DIVERGENCE' in reason:
            trigger = 'OB93+divergence'
        elif 'TIMEOUT' in reason:
            trigger = 'OB93+timeout'
        elif 'OB85' in reason:
            trigger = 'OB85_fallback'
        elif 'failsafe' in reason.lower() or 'K<50' in reason:
            trigger = 'failsafe_K50'
        elif 'conviction' in reason.lower():
            trigger = 'bottom_conviction'
        elif 'failed' in reason.lower() or 'FAIL' in reason:
            trigger = 'safety_net_fail'
        elif 'bullish' in reason.lower():
            trigger = 'structure_bullish'
        elif 'bearish' in reason.lower():
            trigger = 'structure_bearish'
        elif 'timeout' in reason.lower():
            trigger = 'router_timeout'
        elif 'Ranging' in reason:
            trigger = 'ranging'
        else:
            trigger = 'other'

        all_transitions.append({
            'coin': base,
            'date': start_date.strftime('%Y-%m-%d'),
            'from': p['from'],
            'to': p['to'],
            'trigger': trigger,
            'reason': reason,
            'duration_days': duration,
            'phase_pnl': phase_pnl,
            'phase_pnl_pct': phase_pnl_pct,
            'max_dd_pct': dd,
            'n_trades': n_trades,
        })

    # Also capture the INITIAL phase (before first transition)
    if phases:
        first_date = eq_curve.iloc[0]['date'] if len(eq_curve) > 0 else None
        if first_date:
            end_first = phases[0]['date']
            dur = (end_first - first_date).days
            eq_init = eq_curve[(eq_curve['date'] >= first_date) & (eq_curve['date'] <= end_first)]
            if len(eq_init) > 0:
                pnl = eq_init.iloc[-1]['equity'] - eq_init.iloc[0]['equity']
                pnl_pct = pnl / eq_init.iloc[0]['equity'] * 100
            else:
                pnl = 0; pnl_pct = 0
            all_transitions.insert(len(all_transitions) - len(phases), {
                'coin': base,
                'date': first_date.strftime('%Y-%m-%d'),
                'from': 'START',
                'to': 'LONG_DCA',
                'trigger': 'initial',
                'reason': 'Initial phase',
                'duration_days': dur,
                'phase_pnl': pnl,
                'phase_pnl_pct': pnl_pct,
                'max_dd_pct': 0,
                'n_trades': 0,
            })

df = pd.DataFrame(all_transitions)

# ===== ANALYSIS =====

print("=" * 100)
print("V14 TRANSITION MATRIX — All Coins, Oct 2024 Start")
print("=" * 100)

# 1. All transitions detail
print(f"\n{'Coin':<6} {'Date':<11} {'From':>10} {'To':>10} {'Trigger':<20} {'Days':>5} {'PnL':>10} {'PnL%':>7} {'DD%':>7}")
print("-" * 100)
for _, row in df.sort_values(['coin', 'date']).iterrows():
    print(f"{row['coin']:<6} {row['date']:<11} {row['from']:>10} {row['to']:>10} {row['trigger']:<20} {row['duration_days']:>5} ${row['phase_pnl']:>+8,.0f} {row['phase_pnl_pct']:>+6.1f}% {row['max_dd_pct']:>6.1f}%")

# 2. Trigger type summary
print(f"\n\n{'=' * 80}")
print("TRIGGER TYPE SUMMARY")
print("=" * 80)
trigger_summary = df.groupby('trigger').agg(
    count=('trigger', 'size'),
    avg_pnl=('phase_pnl', 'mean'),
    total_pnl=('phase_pnl', 'sum'),
    avg_duration=('duration_days', 'mean'),
    avg_dd=('max_dd_pct', 'mean'),
    positive=('phase_pnl', lambda x: (x > 0).sum()),
).sort_values('total_pnl', ascending=False)

print(f"{'Trigger':<22} {'Count':>5} {'Win':>4} {'Loss':>4} {'Win%':>6} {'Avg PnL':>10} {'Total PnL':>12} {'Avg Days':>9} {'Avg DD':>8}")
print("-" * 80)
for trigger, row in trigger_summary.iterrows():
    losses = row['count'] - row['positive']
    win_pct = row['positive'] / row['count'] * 100 if row['count'] > 0 else 0
    print(f"{trigger:<22} {row['count']:>5} {row['positive']:>4} {losses:>4} {win_pct:>5.0f}% ${row['avg_pnl']:>+8,.0f} ${row['total_pnl']:>+10,.0f} {row['avg_duration']:>8.0f}d {row['avg_dd']:>7.1f}%")

# 3. Phase type summary (what phase was active)
print(f"\n\n{'=' * 80}")
print("PHASE PERFORMANCE SUMMARY")
print("=" * 80)
# The 'to' column tells us what phase started
phase_perf = df[df['from'] != 'START'].groupby('to').agg(
    count=('to', 'size'),
    avg_pnl=('phase_pnl', 'mean'),
    total_pnl=('phase_pnl', 'sum'),
    avg_duration=('duration_days', 'mean'),
    positive=('phase_pnl', lambda x: (x > 0).sum()),
)
print(f"{'Phase':<12} {'Count':>5} {'Win':>4} {'Loss':>4} {'Win%':>6} {'Avg PnL':>10} {'Total PnL':>12} {'Avg Days':>9}")
print("-" * 80)
for phase, row in phase_perf.iterrows():
    losses = row['count'] - row['positive']
    win_pct = row['positive'] / row['count'] * 100 if row['count'] > 0 else 0
    print(f"{phase:<12} {row['count']:>5} {row['positive']:>4} {losses:>4} {win_pct:>5.0f}% ${row['avg_pnl']:>+8,.0f} ${row['total_pnl']:>+10,.0f} {row['avg_duration']:>8.0f}d")

# 4. Failing transitions (negative PnL)
print(f"\n\n{'=' * 80}")
print("FAILING TRANSITIONS (PnL < 0)")
print("=" * 80)
failures = df[df['phase_pnl'] < 0].sort_values('phase_pnl')
print(f"{'Coin':<6} {'Date':<11} {'Phase':>10} {'Trigger':<20} {'Days':>5} {'PnL':>10} {'DD%':>7} {'Reason'}")
print("-" * 100)
for _, row in failures.iterrows():
    print(f"{row['coin']:<6} {row['date']:<11} {row['to']:>10} {row['trigger']:<20} {row['duration_days']:>5} ${row['phase_pnl']:>+8,.0f} {row['max_dd_pct']:>6.1f}% {row['reason'][:50]}")

# 5. Transition flow: what typically follows what
print(f"\n\n{'=' * 80}")
print("TRANSITION FLOW (from -> to counts)")
print("=" * 80)
flow = df.groupby(['from', 'to']).size().reset_index(name='count').sort_values('count', ascending=False)
for _, row in flow.iterrows():
    print(f"  {row['from']:>10} -> {row['to']:<10}: {row['count']}")
