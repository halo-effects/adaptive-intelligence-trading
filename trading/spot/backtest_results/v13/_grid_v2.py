"""Focused test: trailing TP and geometric grid for V14."""
import sys
import numpy as np
import pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13_signals import V13SignalPack
from v14_dca_engine import V14DCAEngine, V14Config, Phase

coins = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
CAPITAL = 2500

def run(label, coins, accumulate=False, tp=0.015, trailing=False, callback=0.005, geometric=False, geo_ratio=1.3):
    total = 0
    for coin in coins:
        pack = V13SignalPack(coin)
        cfg = V14Config()
        cfg.CAPITAL = CAPITAL
        cfg.OB_FALLBACK_1W = 99
        cfg.DCA_ACCUMULATE = accumulate
        cfg.DCA_TP_PCT = tp
        # We'll implement trailing/geometric inline via a modified engine
        eng = ModifiedEngine(pack, cfg, trailing=trailing, callback=callback,
                            geometric=geometric, geo_ratio=geo_ratio)
        r = eng.run()
        total += r['final_equity']
    roi = (total - 10000) / 10000 * 100
    print(f"  {label:<50} ${total:>9,.2f} ({roi:>+7.1f}%)")
    return total


class ModifiedEngine(V14DCAEngine):
    def __init__(self, pack, cfg, trailing=False, callback=0.005, geometric=False, geo_ratio=1.3):
        super().__init__(pack, cfg)
        self._trailing = trailing
        self._callback = callback
        self._geometric = geometric
        self._geo_ratio = geo_ratio
        self._long_peak = 0.0
        self._short_trough = float('inf')

    def _long_dca_tick(self, date, price):
        if np.isnan(price):
            return
        cfg = self.cfg
        available = self.capital * cfg.DCA_CAPITAL_PCT

        # Track peak
        if self.long_coins > 0 and price > self._long_peak:
            self._long_peak = price

        # TP check (cycling mode only)
        if not cfg.DCA_ACCUMULATE and self.long_coins > 0 and self.long_tp > 0:
            take_profit = False

            if self._trailing:
                # Trailing: wait for price to exceed TP, then take on callback
                if self._long_peak >= self.long_tp:
                    cb_price = self._long_peak * (1 - self._callback)
                    if price <= cb_price:
                        take_profit = True
            else:
                if price >= self.long_tp:
                    take_profit = True

            if take_profit:
                proceeds = self.long_coins * price
                pnl = proceeds - self.long_cost
                pnl_pct = pnl / self.long_cost * 100 if self.long_cost > 0 else 0
                self.capital += proceeds
                self.long_trades += 1
                if pnl > 0: self.long_wins += 1
                self.long_pnl += pnl
                self.trades.append({
                    'date': date, 'action': f'LONG_TP_{self.long_layers}L',
                    'price': price, 'amount': proceeds, 'coins': self.long_coins,
                    'phase': self.phase, 'pnl_pct': pnl_pct
                })
                self.long_coins = 0; self.long_avg_entry = 0; self.long_layers = 0
                self.long_tp = 0; self.long_cost = 0; self.long_last_buy = None
                self._long_peak = 0
                return

        if self.unwinding or self.long_layers >= cfg.DCA_MAX_LAYERS:
            return
        if self.long_last_buy and (date - self.long_last_buy).days < 1:
            return

        should_buy = False
        if self.long_layers == 0:
            should_buy = True
        elif self.long_avg_entry > 0:
            if self._geometric:
                cum = sum(cfg.DCA_SO_DEVIATION * (self._geo_ratio ** i) for i in range(self.long_layers))
                target = cum
            else:
                target = cfg.DCA_SO_DEVIATION * self.long_layers
            current = (self.long_avg_entry - price) / self.long_avg_entry
            if current >= target:
                should_buy = True

        if should_buy:
            if self.long_layers == 0:
                order = available * cfg.DCA_BO_PCT
            else:
                order = available * cfg.DCA_BO_PCT * (cfg.DCA_SO_MULTIPLIER ** min(self.long_layers, 4))
            order = min(order, self.capital * 0.3)
            if order < 10 or order > self.capital:
                return
            coins_bought = order / price
            self.long_coins += coins_bought; self.capital -= order; self.long_cost += order
            self.long_layers += 1; self.long_last_buy = date
            self.long_avg_entry = self.long_cost / self.long_coins
            self.long_tp = self.long_avg_entry * (1 + cfg.DCA_TP_PCT)
            self._long_peak = price
            self.trades.append({
                'date': date, 'action': f'LONG_BUY_L{self.long_layers}',
                'price': price, 'amount': order, 'coins': coins_bought, 'phase': self.phase
            })

    def _short_dca_tick(self, date, price):
        if np.isnan(price):
            return
        cfg = self.cfg
        available = self.capital * cfg.DCA_CAPITAL_PCT

        if self.short_coins > 0 and price < self._short_trough:
            self._short_trough = price

        if not cfg.DCA_ACCUMULATE and self.short_coins > 0 and self.short_tp > 0:
            take_profit = False

            if self._trailing:
                if self._short_trough <= self.short_tp:
                    cb_price = self._short_trough * (1 + self._callback)
                    if price >= cb_price:
                        take_profit = True
            else:
                if price <= self.short_tp:
                    take_profit = True

            if take_profit:
                buy_cost = self.short_coins * price
                pnl = self.short_cost - buy_cost
                pnl_pct = pnl / self.short_cost * 100 if self.short_cost > 0 else 0
                self.capital += self.short_cost + pnl
                self.short_trades += 1
                if pnl > 0: self.short_wins += 1
                self.short_pnl += pnl
                self.trades.append({
                    'date': date, 'action': f'SHORT_TP_{self.short_layers}L',
                    'price': price, 'amount': buy_cost, 'coins': self.short_coins,
                    'phase': self.phase, 'pnl_pct': pnl_pct
                })
                self.short_coins = 0; self.short_avg_entry = 0; self.short_layers = 0
                self.short_tp = 0; self.short_cost = 0; self.short_last_sell = None
                self._short_trough = float('inf')
                return

        if self.unwinding or self.short_layers >= cfg.DCA_MAX_LAYERS:
            return
        if self.short_last_sell and (date - self.short_last_sell).days < 1:
            return

        should_sell = False
        if self.short_layers == 0:
            should_sell = True
        elif self.short_avg_entry > 0:
            if self._geometric:
                cum = sum(cfg.DCA_SO_DEVIATION * (self._geo_ratio ** i) for i in range(self.short_layers))
                target = cum
            else:
                target = cfg.DCA_SO_DEVIATION * self.short_layers
            current = (price - self.short_avg_entry) / self.short_avg_entry
            if current >= target:
                should_sell = True

        if should_sell:
            if self.short_layers == 0:
                order = available * cfg.DCA_BO_PCT
            else:
                order = available * cfg.DCA_BO_PCT * (cfg.DCA_SO_MULTIPLIER ** min(self.short_layers, 4))
            order = min(order, self.capital * 0.3)
            if order < 10 or order > self.capital:
                return
            coins_sold = order / price
            self.short_coins += coins_sold; self.capital -= order; self.short_cost += order
            self.short_layers += 1; self.short_last_sell = date
            self.short_avg_entry = self.short_cost / self.short_coins
            self.short_tp = self.short_avg_entry * (1 - cfg.DCA_TP_PCT)
            self._short_trough = price
            self.trades.append({
                'date': date, 'action': f'SHORT_SELL_L{self.short_layers}',
                'price': price, 'amount': order, 'coins': coins_sold, 'phase': self.phase
            })


# ============================================================================
print("GRID IMPROVEMENT SWEEP", flush=True)
print("=" * 70, flush=True)

print("\nCURRENT COINS:", flush=True)
run("Accumulate (baseline)", coins, accumulate=True)
run("Cycling TP=1.5% (fixed)", coins, tp=0.015)
run("Cycling TP=2.0% (fixed)", coins, tp=0.02)
run("Cycling TP=2.5% (fixed)", coins, tp=0.025)

print("\nTrailing TP:", flush=True)
for tp in [0.015, 0.02, 0.025]:
    for cb in [0.005, 0.007, 0.01]:
        run(f"Trail TP={tp*100:.1f}% CB={cb*100:.1f}%", coins, tp=tp, trailing=True, callback=cb)

print("\nGeometric grid:", flush=True)
for ratio in [1.2, 1.3, 1.5]:
    run(f"Geo ratio={ratio} TP=2.5%", coins, tp=0.025, geometric=True, geo_ratio=ratio)

print("\nGeometric + Trailing:", flush=True)
for ratio in [1.2, 1.3]:
    for tp in [0.02, 0.025]:
        for cb in [0.005, 0.007]:
            run(f"Geo={ratio} Trail TP={tp*100:.1f}% CB={cb*100:.1f}%", coins,
                tp=tp, trailing=True, callback=cb, geometric=True, geo_ratio=ratio)

# Best coins
best = ['HBAR/USDT', 'ADA/USDT', 'LINK/USDC', 'ATOM/USDT']
print("\nBEST COINS:", flush=True)
run("Accumulate", best, accumulate=True)
run("Cycling TP=1.5%", best, tp=0.015)
run("Cycling TP=2.5%", best, tp=0.025)
for tp in [0.02, 0.025]:
    for cb in [0.005, 0.007]:
        run(f"Trail TP={tp*100:.1f}% CB={cb*100:.1f}%", best, tp=tp, trailing=True, callback=cb)
for ratio in [1.2, 1.3]:
    run(f"Geo={ratio} TP=2.5%", best, tp=0.025, geometric=True, geo_ratio=ratio)
