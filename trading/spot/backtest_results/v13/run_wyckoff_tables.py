"""
V13 v8 Wyckoff Page Backtest — ETH, SOL, BTC × Low/Medium/High
Period: Oct 2020 → Feb 2026 (present), $10,000 starting capital, 1h-equivalent daily candles.

Produces the data tables for the Wyckoff lifecycle page:
  Profile | Return | Final Equity | Monthly ROI | Daily ROI | CAGR | Win Rate

SOL note: Listed on Binance Aug 2020, so warm-up is short but the engine handles it.
"""
import sys
import json
import numpy as np
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))

from v13_phase_backtest_v8 import V13BacktestV8, V13Config, print_results
from v13_signals import V13SignalPack


CAPITAL = 10000
END_DATE = '2026-02-17'  # USDC data ends here (live collector stopped pushing USDC)

# Per-coin start dates based on available USDC 1h candle data
COIN_START = {
    'ETH': '2020-10-01',  # ETH/USDC 1h backfilled to Oct 2020
    'SOL': '2021-07-01',  # SOL/USDC 1h from Jul 2021 (Binance didn't have USDC pair earlier)
    'BTC': '2020-10-01',  # BTC/USDC 1h from Oct 2020 (full period)
}

# Profile configs matching risk-profiles-spec.md
PROFILES = {
    'low': {
        'DCA_BO_PCT': 0.03,
        'DCA_SO_DEVIATION': 0.03,
        'DCA_SO_MULTIPLIER': 2.0,
        'DCA_TP_PCT': 0.015,
        'DCA_MAX_LAYERS': 5,
        # Markup/short tiers: conservative
        'TIER1_PCT': 0.60,
        'TIER2_PCT': 0.20,
        'TIER3_PCT': 0.10,
        'SHORT_TIER1_PCT': 0.60,
        'SHORT_TIER2_PCT': 0.20,
        'SHORT_TIER3_PCT': 0.10,
    },
    'medium': {
        'DCA_BO_PCT': 0.04,
        'DCA_SO_DEVIATION': 0.025,
        'DCA_SO_MULTIPLIER': 2.0,
        'DCA_TP_PCT': 0.015,
        'DCA_MAX_LAYERS': 8,
        'TIER1_PCT': 0.60,
        'TIER2_PCT': 0.20,
        'TIER3_PCT': 0.10,
        'SHORT_TIER1_PCT': 0.60,
        'SHORT_TIER2_PCT': 0.20,
        'SHORT_TIER3_PCT': 0.10,
    },
    'high': {
        'DCA_BO_PCT': 0.05,
        'DCA_SO_DEVIATION': 0.02,
        'DCA_SO_MULTIPLIER': 2.0,
        'DCA_TP_PCT': 0.010,
        'DCA_MAX_LAYERS': 12,
        'TIER1_PCT': 0.60,
        'TIER2_PCT': 0.20,
        'TIER3_PCT': 0.10,
        'SHORT_TIER1_PCT': 0.60,
        'SHORT_TIER2_PCT': 0.20,
        'SHORT_TIER3_PCT': 0.10,
    },
}

COINS = ['ETH', 'SOL', 'BTC']


def make_config(profile_name, coin='BTC'):
    cfg = V13Config()
    cfg.CAPITAL = CAPITAL
    cfg.START_DATE = COIN_START.get(coin, '2020-10-01')
    cfg.END_DATE = END_DATE
    
    params = PROFILES[profile_name]
    for k, v in params.items():
        setattr(cfg, k, v)
    
    return cfg


def compute_table_metrics(result, capital):
    """Compute Wyckoff page table metrics from backtest result."""
    start = result['start']
    end = result['end']
    final_eq = result['final_equity']
    
    # Total return
    total_return = (final_eq - capital) / capital * 100
    
    # Days and months
    days = (end - start).days
    months = days / 30.44  # average month length
    years = days / 365.25
    
    # Monthly ROI (geometric)
    monthly_roi = ((final_eq / capital) ** (1 / months) - 1) * 100 if months > 0 else 0
    
    # Daily ROI (geometric)
    daily_roi = ((final_eq / capital) ** (1 / days) - 1) * 100 if days > 0 else 0
    
    # CAGR
    cagr = ((final_eq / capital) ** (1 / years) - 1) * 100 if years > 0 else 0
    
    # Win rate from closed trades (DCA + lifecycle)
    win_rate = result['win_rate']
    
    return {
        'return': total_return,
        'final_equity': final_eq,
        'monthly_roi': monthly_roi,
        'daily_roi': daily_roi,
        'cagr': cagr,
        'win_rate': win_rate,
    }


def main():
    print("=" * 90)
    print("  V13 v8 WYCKOFF PAGE BACKTEST")
    print(f"  Period: per-coin start -> {END_DATE}")
    print(f"  Capital: ${CAPITAL:,}")
    print(f"  Coins: {', '.join(COINS)}")
    print(f"  Profiles: Low, Medium, High")
    print("=" * 90)
    
    # Pre-load signal packs (expensive, do once per coin)
    packs = {}
    for coin in COINS:
        print(f"\n  Loading {coin} signal pack...")
        try:
            pack = V13SignalPack(coin)
            print(f"    Daily data: {pack.daily.index[0].date()} to {pack.daily.index[-1].date()} ({len(pack.daily)} rows)")
            if pack.cfgi_df is not None:
                print(f"    CFGI data: {pack.cfgi_df.index[0].date()} to {pack.cfgi_df.index[-1].date()} ({len(pack.cfgi_df)} rows)")
            else:
                print(f"    CFGI data: NONE (will run without sentiment gates)")
            packs[coin] = pack
        except Exception as e:
            print(f"    SKIP: {e}")
    
    all_results = {}  # {coin: {profile: result}}
    
    for coin in COINS:
        if coin not in packs:
            continue
        all_results[coin] = {}
        
        print(f"\n{'='*80}")
        print(f"  {coin}/USDT")
        print(f"{'='*80}")
        
        for profile_name in ['low', 'medium', 'high']:
            print(f"\n  --- {profile_name.upper()} Profile ---")
            cfg = make_config(profile_name, coin)
            
            print(f"  DCA: BO={cfg.DCA_BO_PCT:.0%}, dev={cfg.DCA_SO_DEVIATION:.1%}, "
                  f"mult={cfg.DCA_SO_MULTIPLIER}x, TP={cfg.DCA_TP_PCT:.1%}, layers={cfg.DCA_MAX_LAYERS}")
            
            bt = V13BacktestV8(packs[coin], cfg)
            result = bt.run()
            
            if result:
                print_results(result)
                metrics = compute_table_metrics(result, CAPITAL)
                all_results[coin][profile_name] = {
                    'result': result,
                    'metrics': metrics,
                }
                print(f"\n  TABLE ROW: Return={metrics['return']:+,.1f}%  "
                      f"Equity=${metrics['final_equity']:,.0f}  "
                      f"Monthly={metrics['monthly_roi']:.2f}%  "
                      f"Daily={metrics['daily_roi']:.3f}%  "
                      f"CAGR={metrics['cagr']:.1f}%  "
                      f"WinRate={metrics['win_rate']:.0f}%")
    
    # Print final tables
    print(f"\n\n{'='*90}")
    print(f"  WYCKOFF PAGE DATA TABLES — V13 v8")
    print(f"  Per-coin start -> {END_DATE}, ${CAPITAL:,} starting capital")
    print(f"{'='*90}")
    
    for coin in COINS:
        if coin not in all_results:
            continue
        print(f"\n  ### {coin}/USDT")
        print(f"  {'Profile':<10} {'Return':>12} {'Final Equity':>15} {'Monthly ROI':>13} {'Daily ROI':>11} {'CAGR':>8} {'Win Rate':>10}")
        print(f"  {'-'*79}")
        
        for profile_name in ['low', 'medium', 'high']:
            if profile_name not in all_results[coin]:
                continue
            m = all_results[coin][profile_name]['metrics']
            print(f"  {profile_name.capitalize():<10} {m['return']:>+11,.1f}% ${m['final_equity']:>13,.0f} "
                  f"{m['monthly_roi']:>12.2f}% {m['daily_roi']:>10.3f}% {m['cagr']:>7.1f}% {m['win_rate']:>9.0f}%")
    
    # Save results as JSON for dashboard update
    output = {}
    for coin in COINS:
        if coin not in all_results:
            continue
        output[coin] = {}
        for profile_name in ['low', 'medium', 'high']:
            if profile_name not in all_results[coin]:
                continue
            m = all_results[coin][profile_name]['metrics']
            r = all_results[coin][profile_name]['result']
            output[coin][profile_name] = {
                'return_pct': round(m['return'], 1),
                'final_equity': round(m['final_equity']),
                'monthly_roi': round(m['monthly_roi'], 2),
                'daily_roi': round(m['daily_roi'], 3),
                'cagr': round(m['cagr'], 1),
                'win_rate': round(m['win_rate'], 0),
                'closed_trades': r['closed_trades'],
                'wins': r['wins'],
                'losses': r['losses'],
                'dca_trades': r['dca_trades'],
                'markup_cycles': r['markup_cycles'],
                'max_drawdown': round(r['max_drawdown'], 1),
                'buy_hold_return': round(r['buy_hold_return'], 1),
            }
    
    out_path = Path(__file__).resolve().parent / 'wyckoff_v13_results.json'
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to: {out_path}")


if __name__ == '__main__':
    main()
