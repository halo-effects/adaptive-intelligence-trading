"""
Fine-tune the OB93 arms -> divergence confirms timeout window.
Sweep 30-120d in 5d increments.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

import sqlite3, pandas as pd, numpy as np
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack

DB_PATH = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'

def compute_2d_divergence_dates(coin):
    db = sqlite3.connect(DB_PATH)
    base = coin.split('/')[0]
    df = pd.read_sql(f"SELECT timestamp, close FROM candles_daily WHERE symbol LIKE '{base}%' ORDER BY timestamp", db)
    db.close()
    if df.empty: return set()
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('date').sort_index()
    d2 = df.resample('2D').agg({'close': 'last'}).dropna()
    period = 14
    delta = d2['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    d2['rsi'] = rsi
    divergence_dates = set()
    lookback = 30
    for i in range(lookback, len(d2)):
        cr = d2['rsi'].iloc[i]
        cp = d2['close'].iloc[i]
        if pd.isna(cr) or cr < 60: continue
        wp = d2['close'].iloc[i-lookback:i+1]
        wr = d2['rsi'].iloc[i-lookback:i+1]
        if cp < wp.max() * 0.97: continue
        rp = wr.max()
        if rp < 75: continue
        if rp - cr >= 8:
            dt = d2.index[i]
            divergence_dates.add(dt.strftime('%Y-%m-%d'))
            divergence_dates.add((dt + pd.Timedelta(days=1)).strftime('%Y-%m-%d'))
    return divergence_dates


class V13OB93Armed(V13BacktestV8):
    def __init__(self, pack, config=None, div_dates=None, max_wait_days=60):
        super().__init__(pack, config)
        self.div_dates = div_dates or set()
        self.max_wait_days = max_wait_days
        self.ob93_armed = False
        self.ob93_armed_date = None
    
    def _check_markup(self, date, price):
        if self.dca_coins > 0:
            self._dca_tick(date, price)
        k_2w = self.pack.stoch_2w.get_k_at(date)
        if not np.isnan(k_2w) and k_2w > self.peak_2w_k:
            self.peak_2w_k = k_2w
        
        # Layer 1: Early warning
        if self._signal_near(date, self.early_warnings_1w) and self.early_warning_date is None:
            self.early_warning_date = date
            self.trades.append({'date': date, 'action': f'EARLY_WARNING_1W_97', 'price': price, 'amount': 0, 'coins': 0, 'phase': self.phase})
        
        # Layer 2: OB93 arms
        if not self.ob93_armed and self._signal_near(date, self.ob_exits_2w):
            self.ob93_armed = True
            self.ob93_armed_date = date
        
        # Layer 2 continued: wait for divergence or timeout
        if self.ob93_armed:
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            days_armed = (date - self.ob93_armed_date).days if self.ob93_armed_date else 0
            has_div = date_str in self.div_dates
            timeout = days_armed >= self.max_wait_days
            
            if has_div or timeout:
                reason = 'DIVERGENCE' if has_div else f'TIMEOUT_{days_armed}d'
                pnl = self._sell_all(date, f'OB93+{reason}')
                if self.dca_coins > 0:
                    self._dca_close(date, 'TOP_EXIT')
                self._change_phase(date, Phase.FLAT, f'OB93 armed -> {reason}')
                self._reset_top_state()
                self.ob93_armed = False
                self.ob93_armed_date = None
                return
        
        # Layer 2b: OB85 fallback (only if NOT armed)
        if not self.ob93_armed:
            if self.peak_2w_k < self.cfg.OB_THRESHOLD_2W and self.early_warning_date:
                if self._signal_near(date, self.ob85_1w):
                    pnl = self._sell_all(date, f'FALLBACK_1W_OB85')
                    if self.dca_coins > 0:
                        self._dca_close(date, 'TOP_EXIT')
                    self._change_phase(date, Phase.FLAT, f'1W OB85 fallback')
                    self._reset_top_state()
                    return
        
        # Layer 3: Failsafe
        if not self.ob93_armed:
            if self.early_warning_date and not self.failsafe_armed:
                if (date - self.early_warning_date).days >= self.cfg.FAILSAFE_WINDOW_WEEKS * 7:
                    self.failsafe_armed = True
            if self.failsafe_armed and self._signal_near(date, self.failsafe_1w):
                pnl = self._sell_all(date, 'FAILSAFE_1W_K50')
                if self.dca_coins > 0:
                    self._dca_close(date, 'TOP_EXIT')
                self._change_phase(date, Phase.FLAT, f'Failsafe')
                self._reset_top_state()
                return
        
        # Layer 4: Ranging
        days_in = (date - self.phase_start_date).days if self.phase_start_date else 0
        if days_in >= 14:
            adx = self._adx(date)
            if not np.isnan(adx) and adx < self.cfg.PHASE_ADX_RANGING:
                self.adx_below_20_streak += 1
                if self.adx_below_20_streak >= self.cfg.PHASE_ADX_SUSTAINED_DAYS:
                    pnl = self._sell_all(date, f'MARKUP_RANGING')
                    if self.dca_coins > 0:
                        self._dca_close(date, 'RANGING_EXIT')
                    self._change_phase(date, Phase.FLAT, f'Ranging')
                    self._reset_top_state()
                    self.ob93_armed = False
                    return
            else:
                self.adx_below_20_streak = 0
        
        # Layer 5: Markup failure
        if self.entry_price > 0:
            dd = (price - self.entry_price) / self.entry_price
            if dd < -self.cfg.MARKUP_FAIL_DD_PCT:
                adx = self._adx(date)
                if not np.isnan(adx) and adx > self.cfg.MARKUP_FAIL_ADX:
                    pnl = self._sell_all(date, f'MARKUP_FAIL')
                    if self.dca_coins > 0:
                        self._dca_close(date, 'MARKUP_FAIL')
                    self._change_phase(date, Phase.FLAT, f'Failed')
                    self._reset_top_state()
                    self.ob93_armed = False
                    return
        
        self._check_markup_tiers(date, price)
    
    def _change_phase(self, date, new_phase, reason=''):
        super()._change_phase(date, new_phase, reason)
        if new_phase == Phase.MARKUP:
            self.ob93_armed = False
            self.ob93_armed_date = None


coins = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']

print("Computing divergence dates...")
all_div = {}
for coin in coins:
    base = coin.split('/')[0]
    all_div[base] = compute_2d_divergence_dates(coin)

# Baseline
baselines = {}
for coin in coins:
    base = coin.split('/')[0]
    pack = V13SignalPack(base)
    baselines[base] = V13BacktestV8(pack, V13Config()).run()['final_equity']
base_total = sum(baselines.values())

print(f"Baseline: ${base_total:,.0f} (ETH=${baselines['ETH']:,.0f} SOL=${baselines['SOL']:,.0f} LINK=${baselines['LINK']:,.0f} XRP=${baselines['XRP']:,.0f})")

# Sweep
print(f"\n{'Wait':>5} | {'ETH':>8} {'SOL':>8} {'LINK':>8} {'XRP':>8} | {'Total':>9} {'Delta':>9} | {'ETH_d':>7} {'SOL_d':>7} {'LINK_d':>7} {'XRP_d':>7}")
print("-" * 110)

best_delta = -999999
best_wait = 0

for wait in range(0, 125, 5):
    results = {}
    for coin in coins:
        base = coin.split('/')[0]
        if wait == 0:
            # Baseline = immediate sell
            results[base] = baselines[base]
        else:
            pack = V13SignalPack(base)
            bt = V13OB93Armed(pack, V13Config(), div_dates=all_div[base], max_wait_days=wait)
            results[base] = bt.run()['final_equity']
    
    total = sum(results.values())
    delta = total - base_total
    deltas = {b: results[b] - baselines[b] for b in results}
    marker = " ***" if delta == max(best_delta, delta) and delta > 0 else ""
    if delta > best_delta:
        best_delta = delta
        best_wait = wait
    
    print(f"{wait:>3}d | ${results['ETH']:>7,.0f} ${results['SOL']:>7,.0f} ${results['LINK']:>7,.0f} ${results['XRP']:>7,.0f} | ${total:>8,.0f} ${delta:>+8,.0f} | ${deltas['ETH']:>+6,.0f} ${deltas['SOL']:>+6,.0f} ${deltas['LINK']:>+6,.0f} ${deltas['XRP']:>+6,.0f}{marker}")

print(f"\nBest: {best_wait}d timeout (delta ${best_delta:+,.0f})")

# Detail for best
print(f"\n--- DETAIL: {best_wait}d timeout ---")
for coin in coins:
    base = coin.split('/')[0]
    pack = V13SignalPack(base)
    bt = V13OB93Armed(pack, V13Config(), div_dates=all_div[base], max_wait_days=best_wait)
    bt.run()
    ob93_events = [t for t in bt.trades if 'OB93' in str(t.get('action', ''))]
    print(f"\n{base} (${bt.run()['final_equity']:,.0f}):")
    # rerun for clean trades
    pack2 = V13SignalPack(base)
    bt2 = V13OB93Armed(pack2, V13Config(), div_dates=all_div[base], max_wait_days=best_wait)
    bt2.run()
    for t in bt2.trades:
        a = str(t.get('action', ''))
        if 'OB93' in a or 'FALLBACK' in a or 'FAILSAFE' in a or 'RANGING' in a or 'FAIL' in a or 'DIVERGENCE' in a:
            print(f"  {t['date']} - {a} @ ${t['price']:.2f}")
