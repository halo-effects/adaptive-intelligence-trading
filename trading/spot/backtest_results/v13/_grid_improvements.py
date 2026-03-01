"""Test trailing TP and geometric grid spacing improvements for V14."""
import sys, copy
import pandas as pd
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
from v14_dca_engine import V14DCAEngine, V14Config, Phase

# We need to monkey-patch the engine to test these without modifying the original

class V14ConfigExtended(V14Config):
    """Extended config with new grid features."""
    DCA_TRAILING_TP = False       # Enable trailing TP
    DCA_TRAILING_CALLBACK = 0.005 # 0.5% callback from peak
    DCA_GEOMETRIC = False         # Geometric grid spacing
    DCA_GEO_RATIO = 1.3           # Each layer's deviation is ratio * previous
    OB_FALLBACK_1W = 99           # No OB85 (locked)


class V14DCAEngineV2(V14DCAEngine):
    """Extended engine with trailing TP and geometric spacing."""

    def __init__(self, pack, config=None, initial_phase='LONG_DCA'):
        super().__init__(pack, config or V14ConfigExtended(), initial_phase)
        self.long_peak_since_entry = 0.0
        self.short_trough_since_entry = float('inf')

    def _long_dca_tick(self, date, price):
        """Override with trailing TP and geometric grid."""
        if np.isnan(price):
            return
        available = self.capital * self.cfg.DCA_CAPITAL_PCT
        cfg = self.cfg

        # Track peak price since entry (for trailing TP)
        if self.long_coins > 0 and price > self.long_peak_since_entry:
            self.long_peak_since_entry = price

        # TRAILING TP: if price rose past TP level, then pulled back by callback%
        if (not cfg.DCA_ACCUMULATE and self.long_coins > 0 and
            hasattr(cfg, 'DCA_TRAILING_TP') and cfg.DCA_TRAILING_TP and
            self.long_tp > 0):
            if self.long_peak_since_entry >= self.long_tp:
                callback_price = self.long_peak_since_entry * (1 - cfg.DCA_TRAILING_CALLBACK)
                if price <= callback_price:
                    proceeds = self.long_coins * price
                    pnl = proceeds - self.long_cost
                    pnl_pct = pnl / self.long_cost * 100 if self.long_cost > 0 else 0
                    self.capital += proceeds
                    self.long_trades += 1
                    if pnl > 0: self.long_wins += 1
                    self.long_pnl += pnl
                    self.trades.append({
                        'date': date, 'action': f'LONG_DCA_TRAIL_TP ({self.long_layers}L, peak=${self.long_peak_since_entry:.2f})',
                        'price': price, 'amount': proceeds, 'coins': self.long_coins,
                        'phase': self.phase, 'pnl_pct': pnl_pct
                    })
                    self.long_coins = 0; self.long_avg_entry = 0; self.long_layers = 0
                    self.long_tp = 0; self.long_cost = 0; self.long_last_buy = None
                    self.long_peak_since_entry = 0
                    return
            # Don't fall through to fixed TP if trailing is active and peak is above TP
            if self.long_peak_since_entry >= self.long_tp:
                pass  # Let it trail, don't take fixed TP
            elif price >= self.long_tp:
                # Haven't peaked above TP yet, just crossed — start tracking
                self.long_peak_since_entry = price
                return  # Don't take fixed TP, start trailing

        # FIXED TP (original behavior, only if not trailing)
        elif (not cfg.DCA_ACCUMULATE and not getattr(cfg, 'DCA_TRAILING_TP', False) and
              self.long_coins > 0 and self.long_tp > 0 and price >= self.long_tp):
            proceeds = self.long_coins * price
            pnl = proceeds - self.long_cost
            pnl_pct = pnl / self.long_cost * 100 if self.long_cost > 0 else 0
            self.capital += proceeds
            self.long_trades += 1; self.long_wins += 1; self.long_pnl += pnl
            self.trades.append({
                'date': date, 'action': f'LONG_DCA_TP ({self.long_layers}L)',
                'price': price, 'amount': proceeds, 'coins': self.long_coins,
                'phase': self.phase, 'pnl_pct': pnl_pct
            })
            self.long_coins = 0; self.long_avg_entry = 0; self.long_layers = 0
            self.long_tp = 0; self.long_cost = 0; self.long_last_buy = None
            self.long_peak_since_entry = 0
            return

        if self.unwinding or self.long_layers >= cfg.DCA_MAX_LAYERS:
            return
        if self.long_last_buy and (date - self.long_last_buy).days < 1:
            return

        should_buy = False
        if self.long_layers == 0:
            should_buy = True
        elif self.long_avg_entry > 0:
            # GEOMETRIC: each layer needs ratio^layer * base_deviation drop
            if getattr(cfg, 'DCA_GEOMETRIC', False):
                cumulative_drop = 0
                for i in range(1, self.long_layers + 1):
                    cumulative_drop += cfg.DCA_SO_DEVIATION * (cfg.DCA_GEO_RATIO ** (i - 1))
                target_drop = cumulative_drop
            else:
                target_drop = cfg.DCA_SO_DEVIATION * self.long_layers
            current_drop = (self.long_avg_entry - price) / self.long_avg_entry
            if current_drop >= target_drop:
                should_buy = True

        if should_buy:
            if self.long_layers == 0:
                order = available * cfg.DCA_BO_PCT
            else:
                order = available * cfg.DCA_BO_PCT * (cfg.DCA_SO_MULTIPLIER ** min(self.long_layers, 4))
            order = min(order, self.capital * 0.3)
            if order < 10 or order > self.capital:
                return
            coins = order / price
            self.long_coins += coins; self.capital -= order; self.long_cost += order
            self.long_layers += 1; self.long_last_buy = date
            self.long_avg_entry = self.long_cost / self.long_coins
            self.long_tp = self.long_avg_entry * (1 + cfg.DCA_TP_PCT)
            self.long_peak_since_entry = price
            self.trades.append({
                'date': date, 'action': f'LONG_DCA_BUY_L{self.long_layers}',
                'price': price, 'amount': order, 'coins': coins, 'phase': self.phase
            })

    def _short_dca_tick(self, date, price):
        """Override with trailing TP and geometric grid for shorts."""
        if np.isnan(price):
            return
        available = self.capital * self.cfg.DCA_CAPITAL_PCT
        cfg = self.cfg

        # Track trough price since entry (for trailing TP)
        if self.short_coins > 0 and price < self.short_trough_since_entry:
            self.short_trough_since_entry = price

        # TRAILING TP for shorts
        if (not cfg.DCA_ACCUMULATE and self.short_coins > 0 and
            hasattr(cfg, 'DCA_TRAILING_TP') and cfg.DCA_TRAILING_TP and
            self.short_tp > 0):
            if self.short_trough_since_entry <= self.short_tp:
                callback_price = self.short_trough_since_entry * (1 + cfg.DCA_TRAILING_CALLBACK)
                if price >= callback_price:
                    buy_cost = self.short_coins * price
                    pnl = self.short_cost - buy_cost
                    pnl_pct = pnl / self.short_cost * 100 if self.short_cost > 0 else 0
                    self.capital += self.short_cost + pnl
                    self.short_trades += 1
                    if pnl > 0: self.short_wins += 1
                    self.short_pnl += pnl
                    self.trades.append({
                        'date': date, 'action': f'SHORT_DCA_TRAIL_TP ({self.short_layers}L, trough=${self.short_trough_since_entry:.2f})',
                        'price': price, 'amount': buy_cost, 'coins': self.short_coins,
                        'phase': self.phase, 'pnl_pct': pnl_pct
                    })
                    self.short_coins = 0; self.short_avg_entry = 0; self.short_layers = 0
                    self.short_tp = 0; self.short_cost = 0; self.short_last_sell = None
                    self.short_trough_since_entry = float('inf')
                    return
            if self.short_trough_since_entry <= self.short_tp:
                pass  # Let it trail
            elif price <= self.short_tp:
                self.short_trough_since_entry = price
                return

        # FIXED TP for shorts (original)
        elif (not cfg.DCA_ACCUMULATE and not getattr(cfg, 'DCA_TRAILING_TP', False) and
              self.short_coins > 0 and self.short_tp > 0 and price <= self.short_tp):
            buy_cost = self.short_coins * price
            pnl = self.short_cost - buy_cost
            pnl_pct = pnl / self.short_cost * 100 if self.short_cost > 0 else 0
            self.capital += self.short_cost + pnl
            self.short_trades += 1; self.short_wins += 1; self.short_pnl += pnl
            self.trades.append({
                'date': date, 'action': f'SHORT_DCA_TP ({self.short_layers}L)',
                'price': price, 'amount': buy_cost, 'coins': self.short_coins,
                'phase': self.phase, 'pnl_pct': pnl_pct
            })
            self.short_coins = 0; self.short_avg_entry = 0; self.short_layers = 0
            self.short_tp = 0; self.short_cost = 0; self.short_last_sell = None
            self.short_trough_since_entry = float('inf')
            return

        if self.unwinding or self.short_layers >= cfg.DCA_MAX_LAYERS:
            return
        if self.short_last_sell and (date - self.short_last_sell).days < 1:
            return

        should_sell = False
        if self.short_layers == 0:
            should_sell = True
        elif self.short_avg_entry > 0:
            if getattr(cfg, 'DCA_GEOMETRIC', False):
                cumulative_rise = 0
                for i in range(1, self.short_layers + 1):
                    cumulative_rise += cfg.DCA_SO_DEVIATION * (cfg.DCA_GEO_RATIO ** (i - 1))
                target_rise = cumulative_rise
            else:
                target_rise = cfg.DCA_SO_DEVIATION * self.short_layers
            current_rise = (price - self.short_avg_entry) / self.short_avg_entry
            if current_rise >= target_rise:
                should_sell = True

        if should_sell:
            if self.short_layers == 0:
                order = available * cfg.DCA_BO_PCT
            else:
                order = available * cfg.DCA_BO_PCT * (cfg.DCA_SO_MULTIPLIER ** min(self.short_layers, 4))
            order = min(order, self.capital * 0.3)
            if order < 10 or order > self.capital:
                return
            coins = order / price
            self.short_coins += coins; self.capital -= order; self.short_cost += order
            self.short_layers += 1; self.short_last_sell = date
            self.short_avg_entry = self.short_cost / self.short_coins
            self.short_tp = self.short_avg_entry * (1 - cfg.DCA_TP_PCT)
            self.short_trough_since_entry = price
            self.trades.append({
                'date': date, 'action': f'SHORT_DCA_SELL_L{self.short_layers}',
                'price': price, 'amount': order, 'coins': coins, 'phase': self.phase
            })


# ============================================================================
#  TEST HARNESS
# ============================================================================

coins_current = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
coins_best = ['HBAR/USDT', 'ADA/USDT', 'LINK/USDC', 'ATOM/USDT']
CAPITAL = 2500

def run_portfolio(label, coins, cfg_fn=None, engine_cls=V14DCAEngine):
    total = 0
    for coin in coins:
        pack = V13SignalPack(coin)
        cfg = V14ConfigExtended()
        cfg.CAPITAL = CAPITAL
        if cfg_fn:
            cfg_fn(cfg)
        eng = engine_cls(pack, cfg)
        r = eng.run()
        total += r['final_equity']
    roi = (total - 10000) / 10000 * 100
    print(f"  {label:<45} ${total:>9,.2f} ({roi:>+7.1f}%)")
    return total

print("GRID IMPROVEMENT TESTS")
print("=" * 70)

# ---- CURRENT COINS ----
print("\nCURRENT COINS (ETH/SOL/LINK/XRP):")
print("-" * 70)

# Baselines
run_portfolio("Accumulate (baseline)", coins_current)
run_portfolio("Cycling TP=1.5% (baseline)", coins_current,
              lambda c: setattr(c, 'DCA_ACCUMULATE', False))
run_portfolio("Cycling TP=2.5% (prev best)", coins_current,
              lambda c: [setattr(c, 'DCA_ACCUMULATE', False), setattr(c, 'DCA_TP_PCT', 0.025)])

# Trailing TP
for tp in [0.015, 0.02, 0.025]:
    for cb in [0.003, 0.005, 0.007, 0.01]:
        def mk(c, t=tp, b=cb):
            c.DCA_ACCUMULATE = False
            c.DCA_TRAILING_TP = True
            c.DCA_TP_PCT = t
            c.DCA_TRAILING_CALLBACK = b
        run_portfolio(f"Trailing TP={tp*100:.1f}% CB={cb*100:.1f}%", coins_current, mk, V14DCAEngineV2)

# Geometric grid
for ratio in [1.2, 1.3, 1.5]:
    def mk_geo(c, r=ratio):
        c.DCA_ACCUMULATE = False
        c.DCA_TP_PCT = 0.025
        c.DCA_GEOMETRIC = True
        c.DCA_GEO_RATIO = r
    run_portfolio(f"Geometric ratio={ratio} TP=2.5%", coins_current, mk_geo, V14DCAEngineV2)

# Geometric + Trailing combined
for ratio in [1.2, 1.3]:
    for tp in [0.02, 0.025]:
        for cb in [0.005, 0.007]:
            def mk_both(c, r=ratio, t=tp, b=cb):
                c.DCA_ACCUMULATE = False
                c.DCA_TRAILING_TP = True
                c.DCA_TP_PCT = t
                c.DCA_TRAILING_CALLBACK = b
                c.DCA_GEOMETRIC = True
                c.DCA_GEO_RATIO = r
            run_portfolio(f"Geo={ratio} Trail TP={tp*100:.1f}% CB={cb*100:.1f}%",
                         coins_current, mk_both, V14DCAEngineV2)

# ---- BEST COINS ----
print("\nBEST COINS (HBAR/ADA/LINK/ATOM):")
print("-" * 70)

run_portfolio("Accumulate (baseline)", coins_best)
run_portfolio("Cycling TP=1.5%", coins_best,
              lambda c: setattr(c, 'DCA_ACCUMULATE', False))

# Top trailing configs from current coins test
for tp in [0.02, 0.025]:
    for cb in [0.005, 0.007]:
        def mk(c, t=tp, b=cb):
            c.DCA_ACCUMULATE = False
            c.DCA_TRAILING_TP = True
            c.DCA_TP_PCT = t
            c.DCA_TRAILING_CALLBACK = b
        run_portfolio(f"Trailing TP={tp*100:.1f}% CB={cb*100:.1f}%", coins_best, mk, V14DCAEngineV2)

for ratio in [1.2, 1.3]:
    def mk_geo(c, r=ratio):
        c.DCA_ACCUMULATE = False
        c.DCA_TP_PCT = 0.025
        c.DCA_GEOMETRIC = True
        c.DCA_GEO_RATIO = r
    run_portfolio(f"Geometric ratio={ratio} TP=2.5%", coins_best, mk_geo, V14DCAEngineV2)
