"""
Backtest: OB93 arms the top signal, then wait for 2D divergence (or other confirmation)
to time the actual MARKUP exit. Keep OB85/failsafe/ranging as safety nets.

Pattern: OB93 fires -> armed=True -> wait for divergence -> THEN sell
If divergence never comes, fallback layers (OB85/failsafe/ranging) still catch it.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

import sqlite3, pandas as pd, numpy as np
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack

DB_PATH = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'

def compute_2d_signals(coin):
    """Return dict of date_str -> {divergence, steve_score, k_deflection}"""
    db = sqlite3.connect(DB_PATH)
    base = coin.split('/')[0]
    df = pd.read_sql(f"SELECT timestamp, open, high, low, close, volume FROM candles_daily WHERE symbol LIKE '{base}%' ORDER BY timestamp", db)
    db.close()
    if df.empty: return {}
    
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('date').sort_index()
    d2 = df.resample('2D').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna()
    
    period = 14
    delta = d2['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi_min = rsi.rolling(14).min()
    rsi_max = rsi.rolling(14).max()
    k = ((rsi - rsi_min) / (rsi_max - rsi_min)) * 100
    d_line = k.rolling(3).mean()
    
    # MFI
    tp = (d2['high'] + d2['low'] + d2['close']) / 3
    mf = tp * d2['volume']
    pos_mf = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
    neg_mf = mf.where(tp < tp.shift(1), 0).rolling(14).sum()
    mfi = 100 - (100 / (1 + pos_mf / neg_mf.replace(0, np.nan)))
    
    d2['rsi'] = rsi
    d2['k'] = k
    d2['d'] = d_line
    d2['mfi'] = mfi
    
    result = {}
    lookback = 30
    
    for i in range(lookback, len(d2)):
        dt = d2.index[i]
        cr = d2['rsi'].iloc[i]
        cp = d2['close'].iloc[i]
        
        # Divergence check
        has_div = False
        if pd.notna(cr) and cr >= 60:
            wp = d2['close'].iloc[i-lookback:i+1]
            wr = d2['rsi'].iloc[i-lookback:i+1]
            if cp >= wp.max() * 0.97:
                rp = wr.max()
                if rp >= 75 and rp - cr >= 8:
                    has_div = True
        
        # K deflection: K was > 80, now dropped > 10 from peak
        k_deflect = False
        if pd.notna(d2['k'].iloc[i]):
            recent_k = d2['k'].iloc[max(0,i-10):i+1].dropna()
            if len(recent_k) > 1:
                peak_recent_k = recent_k.max()
                if peak_recent_k >= 80 and d2['k'].iloc[i] <= peak_recent_k - 10:
                    k_deflect = True
        
        # RSI < 60 (momentum lost)
        rsi_weak = pd.notna(cr) and cr < 60
        
        # K < D cross
        k_below_d = False
        if i > 0 and pd.notna(d2['k'].iloc[i]) and pd.notna(d2['d'].iloc[i]):
            if pd.notna(d2['k'].iloc[i-1]) and pd.notna(d2['d'].iloc[i-1]):
                if d2['k'].iloc[i-1] >= d2['d'].iloc[i-1] and d2['k'].iloc[i] < d2['d'].iloc[i]:
                    k_below_d = True
        
        # MFI < 50 (money flowing out)
        mfi_weak = pd.notna(d2['mfi'].iloc[i]) and d2['mfi'].iloc[i] < 50
        
        for ds in [dt.strftime('%Y-%m-%d'), (dt + pd.Timedelta(days=1)).strftime('%Y-%m-%d')]:
            old = result.get(ds, {})
            result[ds] = {
                'divergence': has_div or old.get('divergence', False),
                'k_deflect': k_deflect or old.get('k_deflect', False),
                'rsi_weak': rsi_weak or old.get('rsi_weak', False),
                'k_below_d': k_below_d or old.get('k_below_d', False),
                'mfi_weak': mfi_weak or old.get('mfi_weak', False),
            }
    
    return result


class V13OB93Armed(V13BacktestV8):
    """OB93 arms, then waits for confirmation signal to time the exit."""
    
    def __init__(self, pack, config=None, signal_data=None, confirm_signal='divergence', max_wait_days=60):
        super().__init__(pack, config)
        self.signal_data = signal_data or {}
        self.confirm_signal = confirm_signal
        self.max_wait_days = max_wait_days
        self.ob93_armed = False
        self.ob93_armed_date = None
        self.ob93_armed_price = 0
    
    def _check_markup(self, date, price):
        if self.dca_coins > 0:
            self._dca_tick(date, price)
        
        k_2w = self.pack.stoch_2w.get_k_at(date)
        if not np.isnan(k_2w) and k_2w > self.peak_2w_k:
            self.peak_2w_k = k_2w
        
        # Layer 1: Early warning (unchanged)
        if self._signal_near(date, self.early_warnings_1w) and self.early_warning_date is None:
            self.early_warning_date = date
            self.trades.append({
                'date': date, 'action': f'EARLY_WARNING_1W_97 (2W_peak={self.peak_2w_k:.0f})',
                'price': price, 'amount': 0, 'coins': 0, 'phase': self.phase
            })
        
        # Layer 2: OB93 ARMS (doesn't sell immediately)
        if not self.ob93_armed and self._signal_near(date, self.ob_exits_2w):
            self.ob93_armed = True
            self.ob93_armed_date = date
            self.ob93_armed_price = price
            self.trades.append({
                'date': date, 'action': f'OB93_ARMED (waiting for {self.confirm_signal})',
                'price': price, 'amount': 0, 'coins': 0, 'phase': self.phase
            })
        
        # Layer 2 continued: Check confirmation after armed
        if self.ob93_armed:
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            sig = self.signal_data.get(date_str, {})
            days_armed = (date - self.ob93_armed_date).days if self.ob93_armed_date else 0
            
            confirmed = sig.get(self.confirm_signal, False)
            timeout = days_armed >= self.max_wait_days
            
            if confirmed or timeout:
                reason = self.confirm_signal if confirmed else f'TIMEOUT_{days_armed}d'
                pnl = self._sell_all(date, f'OB93+{reason.upper()}')
                if self.dca_coins > 0:
                    self._dca_close(date, 'TOP_EXIT')
                self._change_phase(date, Phase.FLAT,
                    f'OB93 armed -> {reason}, pnl={pnl:+.1f}%')
                self._reset_top_state()
                self.ob93_armed = False
                self.ob93_armed_date = None
                return
        
        # Layer 2b: OB85 fallback (only if NOT armed by OB93)
        if not self.ob93_armed:
            if self.peak_2w_k < self.cfg.OB_THRESHOLD_2W and self.early_warning_date:
                if self._signal_near(date, self.ob85_1w):
                    pnl = self._sell_all(date, f'FALLBACK_1W_OB85 (2W_peak={self.peak_2w_k:.0f})')
                    if self.dca_coins > 0:
                        self._dca_close(date, 'TOP_EXIT')
                    self._change_phase(date, Phase.FLAT,
                        f'1W OB85 fallback, pnl={pnl:+.1f}%')
                    self._reset_top_state()
                    return
        
        # Layer 3: Failsafe (unchanged, fires even if armed)
        if not self.ob93_armed:
            if self.early_warning_date and not self.failsafe_armed:
                if (date - self.early_warning_date).days >= self.cfg.FAILSAFE_WINDOW_WEEKS * 7:
                    self.failsafe_armed = True
            if self.failsafe_armed and self._signal_near(date, self.failsafe_1w):
                pnl = self._sell_all(date, 'FAILSAFE_1W_K50')
                if self.dca_coins > 0:
                    self._dca_close(date, 'TOP_EXIT')
                self._change_phase(date, Phase.FLAT, f'Failsafe 1W K<50')
                self._reset_top_state()
                return
        
        # Layer 4: Ranging (unchanged)
        days_in = (date - self.phase_start_date).days if self.phase_start_date else 0
        if days_in >= 14:
            adx = self._adx(date)
            if not np.isnan(adx) and adx < self.cfg.PHASE_ADX_RANGING:
                self.adx_below_20_streak += 1
                if self.adx_below_20_streak >= self.cfg.PHASE_ADX_SUSTAINED_DAYS:
                    pnl = self._sell_all(date, f'MARKUP_RANGING')
                    if self.dca_coins > 0:
                        self._dca_close(date, 'RANGING_EXIT')
                    self._change_phase(date, Phase.FLAT, f'Markup ranging')
                    self._reset_top_state()
                    self.ob93_armed = False
                    return
            else:
                self.adx_below_20_streak = 0
        
        # Layer 5: Markup failure (unchanged)
        if self.entry_price > 0:
            dd = (price - self.entry_price) / self.entry_price
            if dd < -self.cfg.MARKUP_FAIL_DD_PCT:
                adx = self._adx(date)
                if not np.isnan(adx) and adx > self.cfg.MARKUP_FAIL_ADX:
                    pnl = self._sell_all(date, f'MARKUP_FAIL')
                    if self.dca_coins > 0:
                        self._dca_close(date, 'MARKUP_FAIL')
                    self._change_phase(date, Phase.FLAT, f'Markup failed')
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

print("Computing 2D signals...")
all_signals = {}
for coin in coins:
    base = coin.split('/')[0]
    all_signals[base] = compute_2d_signals(coin)

# Baseline
baselines = {}
for coin in coins:
    base = coin.split('/')[0]
    pack = V13SignalPack(base)
    baselines[base] = V13BacktestV8(pack, V13Config()).run()['final_equity']
base_total = sum(baselines.values())

print(f"\nBaseline: ETH=${baselines['ETH']:,.0f} SOL=${baselines['SOL']:,.0f} LINK=${baselines['LINK']:,.0f} XRP=${baselines['XRP']:,.0f} = ${base_total:,.0f}")

# Test different confirmation signals and timeouts
print("\n" + "=" * 80)
print("OB93 ARMS -> CONFIRMATION SIGNAL -> SELL")
print("=" * 80)

confirm_signals = ['divergence', 'k_deflect', 'k_below_d', 'rsi_weak', 'mfi_weak']
timeouts = [30, 60, 90]

print(f"\n{'Signal':>12} {'Wait':>5} | {'ETH':>8} {'SOL':>8} {'LINK':>8} {'XRP':>8} | {'Total':>9} {'Delta':>9}")
print("-" * 85)

# Also test baseline (immediate OB93 sell = wait 0)
print(f"{'baseline':>12} {'0d':>5} | ${baselines['ETH']:>7,.0f} ${baselines['SOL']:>7,.0f} ${baselines['LINK']:>7,.0f} ${baselines['XRP']:>7,.0f} | ${base_total:>8,.0f} ${0:>+8,.0f}")

best_delta = -999999
best_config = ""

for sig in confirm_signals:
    for timeout in timeouts:
        results = {}
        for coin in coins:
            base = coin.split('/')[0]
            pack = V13SignalPack(base)
            bt = V13OB93Armed(pack, V13Config(), signal_data=all_signals[base],
                            confirm_signal=sig, max_wait_days=timeout)
            results[base] = bt.run()['final_equity']
        
        total = sum(results.values())
        delta = total - base_total
        marker = " ***" if delta > 0 else ""
        print(f"{sig:>12} {timeout:>3}d | ${results['ETH']:>7,.0f} ${results['SOL']:>7,.0f} ${results['LINK']:>7,.0f} ${results['XRP']:>7,.0f} | ${total:>8,.0f} ${delta:>+8,.0f}{marker}")
        
        if delta > best_delta:
            best_delta = delta
            best_config = f"{sig}/{timeout}d"

print(f"\nBest: {best_config} ({best_delta:+,.0f})")

# Detail for best configs
print("\n--- DETAIL FOR POSITIVE CONFIGS ---")
for sig in confirm_signals:
    for timeout in timeouts:
        results = {}
        detail_trades = {}
        for coin in coins:
            base = coin.split('/')[0]
            pack = V13SignalPack(base)
            bt = V13OB93Armed(pack, V13Config(), signal_data=all_signals[base],
                            confirm_signal=sig, max_wait_days=timeout)
            results[base] = bt.run()['final_equity']
            detail_trades[base] = [t for t in bt.trades if 'OB93' in str(t.get('action', '')) and t.get('amount', 0) != 0]
        
        total = sum(results.values())
        delta = total - base_total
        if delta > -2000:  # Show anything close to positive
            print(f"\n{sig}/{timeout}d (delta ${delta:+,.0f}):")
            for base in ['ETH', 'SOL', 'LINK', 'XRP']:
                armed = [t for t in detail_trades.get(base, []) if 'ARMED' not in str(t.get('action', ''))]
                print(f"  {base} (${results[base]:,.0f}):")
                all_t = []
                pack = V13SignalPack(base)
                bt = V13OB93Armed(pack, V13Config(), signal_data=all_signals[base],
                                confirm_signal=sig, max_wait_days=timeout)
                bt.run()
                for t in bt.trades:
                    if 'OB93' in str(t.get('action', '')):
                        print(f"    {t['date']} - {t['action']} @ ${t['price']:.2f}")
