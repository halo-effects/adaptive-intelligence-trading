"""
V13 ROUTER Phase 2: Dynamic Tier Gates
Test signal-based T2/T3 confirmation vs fixed delays.

Gates tested:
  - OB proximity block (no T2 if OB signal within N days)
  - ADX trend strength (require ADX > threshold)
  - HH_HL / LH_LL structure continuation
  - Combined gates
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from copy import deepcopy
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack


class V13DynamicTiers(V13BacktestV8):
    """V13 with dynamic tier gates for testing."""

    def __init__(self, pack, cfg, gates=None):
        super().__init__(pack, cfg)
        # gates dict controls which gates are active
        self.gates = gates or {}
        self.blocked_tier_adds = []

    def _open_short(self, date, pct, tier):
        """Override to add dynamic gates for short tiers."""
        if tier >= 2 and not self._check_tier_gate(date, tier, 'short'):
            return
        super()._open_short(date, pct, tier)

    def _check_markup_tiers(self, date, price):
        """Override: replace fixed delay with signal-based confirmation."""
        if self.tier >= 3 or self.phase_start_date is None:
            return

        weeks_in = (date - self.phase_start_date).days / 7

        # T2 check
        if self.tier == 1:
            # Fixed delay minimum (can be reduced from 7 days)
            min_days = self.gates.get('t2_min_days', 7)
            days_in = (date - self.phase_start_date).days
            if days_in < min_days:
                return

            if not self._check_tier_gate(date, 2, 'long'):
                return

            self._buy(date, self.cfg.TIER2_PCT, 2)

        # T3 check
        elif self.tier == 2:
            min_days = self.gates.get('t3_min_days', 14)
            days_in = (date - self.phase_start_date).days
            if days_in < min_days:
                return

            if not self._check_tier_gate(date, 3, 'long'):
                return

            self._buy(date, self.cfg.TIER3_PCT, 3)

    def _check_tier_gate(self, date, tier, side):
        """Dynamic signal-based gate for tier adds."""
        passed = True
        reasons = []

        # Gate 1: OB proximity block
        ob_block_days = self.gates.get('ob_block_days', 0)
        if ob_block_days > 0 and side == 'long':
            for ob_set in [self.ob_exits_2w, self.ob85_1w]:
                for ob_date in ob_set:
                    gap = (date - ob_date).days
                    if 0 <= gap <= ob_block_days:
                        passed = False
                        reasons.append(f'OB_within_{gap}d')
                        break

        # Gate 2: ADX strength
        adx_min = self.gates.get('adx_min_t2', 0) if tier == 2 else self.gates.get('adx_min_t3', 0)
        if adx_min > 0:
            try:
                adx = self.pack.daily.loc[:date, 'adx'].iloc[-1]
                if not np.isnan(adx) and adx < adx_min:
                    passed = False
                    reasons.append(f'ADX={adx:.0f}<{adx_min}')
            except:
                pass

        # Gate 3: Structure continuation (HH_HL for longs, LH_LL for shorts)
        struct_min = self.gates.get('struct_min', 0)
        if struct_min > 0:
            if side == 'long':
                streak = self.pack.structure.hh_hl_streak(date, self.cfg.HH_HL_LOOKBACK)
                if streak < struct_min:
                    passed = False
                    reasons.append(f'HH_HL={streak}<{struct_min}')
            else:
                streak = self.pack.structure.lh_ll_streak(date, self.cfg.HH_HL_LOOKBACK)
                if streak < struct_min:
                    passed = False
                    reasons.append(f'LH_LL={streak}<{struct_min}')

        # Gate 4: No early warning signal active (for longs)
        if self.gates.get('no_early_warning', False) and side == 'long':
            for ew_date in self.early_warnings_1w:
                gap = (date - ew_date).days
                if 0 <= gap <= 7:
                    passed = False
                    reasons.append(f'EarlyWarning_within_{gap}d')
                    break

        if not passed:
            self.blocked_tier_adds.append({
                'date': date, 'tier': tier, 'side': side,
                'reasons': reasons
            })

        return passed


def run_variant(coins, gates, label):
    """Run backtest with specific gate configuration."""
    results = {}
    total_equity = 0
    total_blocked = 0

    for coin in coins:
        pack = V13SignalPack(coin)
        cfg = V13Config()
        cfg.START_DATE = '2023-01-01'
        cfg.END_DATE = '2026-02-25'
        cfg.CAPITAL = 2500

        bt = V13DynamicTiers(pack, cfg, gates=gates.copy())
        result = bt.run()
        if result is None:
            continue

        results[coin] = {
            'equity': result['final_equity'],
            'roi': result['roi'],
            'trades': result['total_trades'],
            'blocked': len(bt.blocked_tier_adds),
        }
        total_equity += result['final_equity']
        total_blocked += len(bt.blocked_tier_adds)

    return results, total_equity, total_blocked


def main():
    coins = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']

    # Define variants to test
    variants = [
        ('BASELINE (fixed 7d/14d)', {}),
        ('OB block 14d', {'ob_block_days': 14}),
        ('OB block 21d', {'ob_block_days': 21}),
        ('ADX > 20 for T2', {'adx_min_t2': 20}),
        ('ADX > 25 for T2', {'adx_min_t2': 25}),
        ('ADX > 25 for T2+T3', {'adx_min_t2': 25, 'adx_min_t3': 25}),
        ('Structure HH_HL >= 1', {'struct_min': 1}),
        ('Structure HH_HL >= 2', {'struct_min': 2}),
        ('No early warning', {'no_early_warning': True}),
        ('OB14d + ADX>25', {'ob_block_days': 14, 'adx_min_t2': 25}),
        ('OB14d + ADX>25 + Struct>=1', {'ob_block_days': 14, 'adx_min_t2': 25, 'struct_min': 1}),
        ('OB14d + ADX>20 + Struct>=1', {'ob_block_days': 14, 'adx_min_t2': 20, 'struct_min': 1}),
        ('OB21d + ADX>25 + Struct>=1', {'ob_block_days': 21, 'adx_min_t2': 25, 'struct_min': 1}),
        ('OB14d + ADX>25 + NoEW', {'ob_block_days': 14, 'adx_min_t2': 25, 'no_early_warning': True}),
        # Faster T2 with gates
        ('T2@3d + OB14d + ADX>25', {'t2_min_days': 3, 'ob_block_days': 14, 'adx_min_t2': 25}),
        ('T2@5d + OB14d + ADX>25', {'t2_min_days': 5, 'ob_block_days': 14, 'adx_min_t2': 25}),
        ('T2@3d + OB14d + ADX>25 + Struct>=1', {'t2_min_days': 3, 'ob_block_days': 14, 'adx_min_t2': 25, 'struct_min': 1}),
    ]

    print("=" * 100)
    print("  V13 DYNAMIC TIER GATES — Phase 2 Sweep")
    print("=" * 100)

    baseline_equity = None
    all_results = []

    for label, gates in variants:
        results, total_eq, blocked = run_variant(coins, gates, label)
        if baseline_equity is None:
            baseline_equity = total_eq

        delta = total_eq - baseline_equity
        all_results.append((label, results, total_eq, delta, blocked))

    # Print results
    print(f"\n{'Variant':<45} {'Total$':>10} {'Delta':>10} {'Blocked':>8}  ", end="")
    for c in coins:
        print(f" {c:>7}", end="")
    print()
    print("-" * 120)

    for label, results, total_eq, delta, blocked in all_results:
        d_str = f"{delta:+,.0f}" if delta != 0 else "BASE"
        print(f"{label:<45} ${total_eq:>9,.0f} {d_str:>10} {blocked:>8}  ", end="")
        for c in coins:
            if c in results:
                coin_delta = results[c]['equity'] - all_results[0][1].get(c, {}).get('equity', 0)
                print(f" {coin_delta:>+7,.0f}", end="")
            else:
                print(f" {'N/A':>7}", end="")
        print()


if __name__ == '__main__':
    main()
