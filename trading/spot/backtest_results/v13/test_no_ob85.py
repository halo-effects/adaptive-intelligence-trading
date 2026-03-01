"""Test: Disable OB85 fallback, keep only 2W OB93 primary + 1W K<50 failsafe.
Compare against Run 4 baseline (with OB85)."""
from v13_phase_backtest_v8 import V13BacktestV8, V13Config
from v13_signals import V13SignalPack
from run_new_coins_profiles import make_config

baseline = {
    'ETH/USDC': {'low': 269, 'medium': 280, 'high': 284},
    'BTC/USDC': {'low': 186, 'medium': 211, 'high': 167},
    'SOL/USDC': {'low': 106, 'medium': 69, 'high': 54},
}

for coin in ['ETH/USDC', 'BTC/USDC', 'SOL/USDC']:
    print(f"\n{'='*60}")
    print(f"{coin}")
    print(f"{'='*60}")
    for profile in ['low', 'medium', 'high']:
        pack = V13SignalPack(coin)
        cfg = make_config(profile)
        
        # Disable OB85 fallback by setting threshold impossibly high
        cfg.STOCH_1W_OB = 100  # Never triggers
        
        bt = V13BacktestV8(pack, cfg)
        r = bt.run()
        roi = r.get('roi', 0)
        bh = r.get('buy_hold_return', 0)
        base = baseline[coin][profile]
        delta = roi - base
        
        print(f"  {profile:>6}: {roi:>+7.1f}% (was {base:>+4d}%, delta {delta:>+6.1f}%)  B&H: {bh:>+.0f}%  Cycles: {r['markup_cycles']}  Trades: {r['closed_trades']} ({r['wins']}W/{r['losses']}L)")
        
        # Show phase transitions for high profile
        if profile == 'high':
            for t in bt.phase_log:
                reason = t.get('reason', '')
                if 'OB' in reason or 'failsafe' in reason.lower() or 'MARKUP' in str(t.get('to', '')):
                    d = str(t.get('date', ''))[:10]
                    eq = t.get('equity', 0)
                    to = t.get('to', '')
                    print(f"         {d} ${eq:>8.0f} -> {to}: {reason}")
