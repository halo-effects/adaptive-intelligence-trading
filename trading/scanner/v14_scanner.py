"""V14 Coin Scanner — Score and rank coins for V14 DCA engine."""

import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import numpy as np

# -- Path setup ---------------------------------------------------------------
_WORKSPACE = Path(__file__).resolve().parent.parent.parent
_V13_DIR = _WORKSPACE / 'trading' / 'spot' / 'backtest_results' / 'v13'
sys.path.insert(0, str(_V13_DIR))
sys.path.insert(0, str(_WORKSPACE))

from v13_signals import V13SignalPack
from v14_dca_engine import V14DCAEngine, V14Config

DB_PATH = _WORKSPACE / 'trading' / 'spot' / 'data' / 'candles.db'

# -- Constants ----------------------------------------------------------------

QUALIFIED_COINS = [
    'BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'BNB/USDT', 'SOL/USDT',
    'LINK/USDC', 'ADA/USDT', 'LTC/USDT', 'AVAX/USDT', 'DOT/USDT',
    'UNI/USDT', 'AAVE/USDT', 'NEAR/USDT', 'HBAR/USDT', 'ATOM/USDT',
]

ACTIVE_COINS = ['HBAR/USDT', 'ATOM/USDT', 'LINK/USDC', 'NEAR/USDT']

MIN_HISTORY_DAYS = 784  # StochRSI warmup requirement


# -- Helpers ------------------------------------------------------------------

def check_history(coin: str) -> int:
    """Count daily candles available in DB for a coin."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        # Check candles_daily table — return MAX across USDC/USDT
        base = coin.split('/')[0]
        best = 0
        for quote in ('USDC', 'USDT'):
            sym = f"{base}/{quote}"
            count = conn.execute(
                "SELECT COUNT(*) FROM candles_daily WHERE symbol = ?",
                (sym,)
            ).fetchone()[0]
            best = max(best, count)

        if best > 0:
            return best

        # Fallback: candles table with 1d timeframe
        for quote in ('USDC', 'USDT'):
            sym = f"{base}/{quote}"
            count = conn.execute(
                "SELECT COUNT(*) FROM candles WHERE symbol = ? AND timeframe = '1d'",
                (sym,)
            ).fetchone()[0]
            best = max(best, count)
        return best
    finally:
        conn.close()


def run_backtest(coin: str, capital: float = 2500) -> dict | None:
    """Run V14 DCA backtest with locked scanner config. Returns results dict or None."""
    pack = V13SignalPack(coin)

    cfg = V14Config()
    cfg.CAPITAL = capital
    cfg.START_DATE = '2024-10-01'
    cfg.END_DATE = datetime.now().strftime('%Y-%m-%d')
    cfg.DCA_ACCUMULATE = False       # Cycling mode
    cfg.DCA_BO_PCT = 0.40
    cfg.DCA_SO_DEVIATION = 0.02
    cfg.DCA_SO_MULTIPLIER = 1.5
    cfg.DCA_MAX_LAYERS = 10
    cfg.DCA_TP_PCT = 0.015
    cfg.OB_FALLBACK_1W = 99          # OB85 disabled
    cfg.DCA_CAPITAL_PCT = 0.90
    cfg.CONVICTION_MIN_SCORE = 3
    cfg.TOP_DIVERGENCE_TIMEOUT = 35

    engine = V14DCAEngine(pack, cfg)
    return engine.run()


def score_coin(coin: str, results: dict, history_days: int) -> dict:
    """Apply 5-factor scoring model. Returns score breakdown dict."""

    # -- Factor 1: Trade Cycling Rate (25 pts) --
    total_trades = results['total_long_trades'] + results['total_short_trades']
    phases = max(results['phase_changes'], 1)
    tpp = total_trades / phases  # trades per phase

    if tpp >= 30:
        cycling_rate = 25
    elif tpp >= 20:
        cycling_rate = 20
    elif tpp >= 15:
        cycling_rate = 15
    elif tpp >= 10:
        cycling_rate = 10
    else:
        cycling_rate = 5

    # -- Factor 2: Short PnL Dominance (25 pts) --
    total_pnl = results['long_pnl'] + results['short_pnl']
    if total_pnl > 0:
        short_pct = results['short_pnl'] / total_pnl * 100 if total_pnl != 0 else 0
    else:
        short_pct = 0

    if results['short_pnl'] <= 0:
        short_dom = 0
    elif short_pct > 50:
        short_dom = 25
    elif short_pct > 30:
        short_dom = 20
    elif short_pct > 10:
        short_dom = 15
    else:
        short_dom = 10

    # -- Factor 3: Max Drawdown (20 pts) --
    dd = results['max_drawdown']  # negative number
    if dd > -20:
        dd_score = 20
    elif dd > -30:
        dd_score = 17
    elif dd > -40:
        dd_score = 14
    elif dd > -50:
        dd_score = 10
    elif dd > -60:
        dd_score = 5
    else:
        dd_score = 0

    # -- Factor 4: Phase Count (15 pts) --
    pc = results['phase_changes']
    if pc in (2, 3):
        phase_score = 15
    elif pc == 4:
        phase_score = 12
    elif pc == 1:
        phase_score = 10
    elif pc >= 5:
        phase_score = 8
    else:
        phase_score = 0

    # -- Factor 5: History Depth (15 pts) --
    if history_days >= 2000:
        hist_score = 15
    elif history_days >= 1500:
        hist_score = 12
    elif history_days >= 1000:
        hist_score = 8
    elif history_days >= MIN_HISTORY_DAYS:
        hist_score = 5
    else:
        hist_score = 0  # disqualified

    composite = cycling_rate + short_dom + dd_score + phase_score + hist_score

    # Grade
    if composite >= 90:
        grade = 'A+'
    elif composite >= 80:
        grade = 'A'
    elif composite >= 70:
        grade = 'B+'
    elif composite >= 60:
        grade = 'B'
    elif composite >= 45:
        grade = 'C'
    elif composite >= 30:
        grade = 'D'
    else:
        grade = 'F'

    # Win rate
    total_wins = results['long_wins'] + results['short_wins']
    win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0

    return {
        'symbol': coin,
        'composite_score': composite,
        'grade': grade,
        'roi_pct': round(results['roi'], 1),
        'max_drawdown_pct': round(dd, 1),
        'total_trades': total_trades,
        'long_trades': results['total_long_trades'],
        'short_trades': results['total_short_trades'],
        'long_pnl': round(results['long_pnl'], 2),
        'short_pnl': round(results['short_pnl'], 2),
        'phase_changes': pc,
        'win_rate': round(win_rate, 1),
        'trades_per_phase': round(tpp, 1),
        'short_pnl_pct': round(short_pct, 1),
        'history_days': history_days,
        'scoring': {
            'cycling_rate': cycling_rate,
            'short_dominance': short_dom,
            'drawdown': dd_score,
            'phase_count': phase_score,
            'history': hist_score,
        },
        'is_active': coin in ACTIVE_COINS,
        'available_on': ['hyperliquid'],
    }


def scan_all(capital: float = 10000) -> dict:
    """Run scanner on all qualified coins. Returns full output dict."""
    per_coin = capital / len(QUALIFIED_COINS)
    rankings = []
    disqualified = []

    print(f"V14 Scanner — {len(QUALIFIED_COINS)} coins, ${capital:,.0f} total (${per_coin:,.0f}/coin)")
    print("=" * 60)

    for i, coin in enumerate(QUALIFIED_COINS, 1):
        print(f"[{i}/{len(QUALIFIED_COINS)}] {coin} ... ", end='', flush=True)

        # Check history
        try:
            days = check_history(coin)
        except Exception as e:
            print(f"DB ERROR: {e}")
            disqualified.append({'symbol': coin, 'reason': f'DB error: {e}'})
            continue

        if days < MIN_HISTORY_DAYS:
            print(f"DISQUALIFIED ({days} days, need {MIN_HISTORY_DAYS})")
            disqualified.append({
                'symbol': coin,
                'reason': f'Insufficient history ({days} days, need {MIN_HISTORY_DAYS})'
            })
            continue

        # Run backtest
        try:
            results = run_backtest(coin, capital=per_coin)
            if results is None:
                print("NO DATA")
                disqualified.append({'symbol': coin, 'reason': 'Backtest returned no data'})
                continue
        except Exception as e:
            print(f"BACKTEST ERROR: {e}")
            disqualified.append({'symbol': coin, 'reason': f'Backtest error: {e}'})
            continue

        # Score
        scored = score_coin(coin, results, days)
        rankings.append(scored)

        total_trades = scored['total_trades']
        print(f"score={scored['composite_score']} ({scored['grade']}) "
              f"ROI={scored['roi_pct']:.0f}% DD={scored['max_drawdown_pct']:.0f}% "
              f"trades={total_trades} phases={scored['phase_changes']}")

    # Sort by composite score descending
    rankings.sort(key=lambda x: x['composite_score'], reverse=True)

    output = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'engine': 'v14_dca',
        'profile': 'medium',
        'backtest_start': '2024-10-01',
        'coins_tested': len(QUALIFIED_COINS),
        'coins_qualified': len(rankings),
        'rankings': rankings,
        'active_coins': ACTIVE_COINS,
        'disqualified': disqualified,
    }

    print("=" * 60)
    print(f"Qualified: {len(rankings)}/{len(QUALIFIED_COINS)}")
    if rankings:
        print(f"Top: {rankings[0]['symbol']} ({rankings[0]['composite_score']} {rankings[0]['grade']})")
    return output


def save_json(data: dict, output_path: str):
    """Write scanner JSON for dashboard."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"Saved: {path} ({path.stat().st_size:,} bytes)")


# -- CLI ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='V14 Coin Scanner')
    parser.add_argument('--output', default=str(_WORKSPACE / 'docs' / 'data' / 'v14' / 'scanner.json'),
                        help='Output JSON path')
    parser.add_argument('--capital', type=float, default=10000, help='Total capital')
    args = parser.parse_args()

    data = scan_all(capital=args.capital)
    save_json(data, args.output)


if __name__ == '__main__':
    main()
