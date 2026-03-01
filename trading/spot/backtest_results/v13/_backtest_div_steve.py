"""
Backtest: 2D divergence + Steve overbought context filter.
Divergence only fires when Steve score >= threshold.
Steve score: RSI>80 + StochK>80 + StochD>80 + MFI>80 (0-4 scale on 2D candles)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

import sqlite3, pandas as pd, numpy as np
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack

DB_PATH = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'

def compute_divergence_with_steve(coin):
    """Return dict: date_str -> {'divergence': bool, 'steve_score': int, 'steve_max_recent': int}"""
    db = sqlite3.connect(DB_PATH)
    base = coin.split('/')[0]
    df = pd.read_sql(f"SELECT timestamp, open, high, low, close, volume FROM candles_daily WHERE symbol LIKE '{base}%' ORDER BY timestamp", db)
    db.close()
    if df.empty: return {}
    
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('date').sort_index()
    d2 = df.resample('2D').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna()
    
    # RSI
    period = 14
    delta = d2['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # StochRSI
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
    
    # SMA200
    sma200 = d2['close'].rolling(200).mean()
    
    d2['rsi'] = rsi
    d2['k'] = k
    d2['d'] = d_line
    d2['mfi'] = mfi
    d2['sma200'] = sma200
    
    result = {}
    lookback = 30
    
    for i in range(lookback, len(d2)):
        dt = d2.index[i]
        cr = d2['rsi'].iloc[i]
        cp = d2['close'].iloc[i]
        
        # Steve score at this bar
        score = 0
        if pd.notna(cr) and cr > 80: score += 1
        if pd.notna(d2['k'].iloc[i]) and d2['k'].iloc[i] > 80: score += 1
        if pd.notna(d2['d'].iloc[i]) and d2['d'].iloc[i] > 80: score += 1
        if pd.notna(d2['mfi'].iloc[i]) and d2['mfi'].iloc[i] > 80: score += 1
        
        # Max Steve score in last 15 bars (30 days) — "were we recently overbought?"
        recent_scores = []
        for j in range(max(lookback, i-15), i+1):
            s = 0
            if pd.notna(d2['rsi'].iloc[j]) and d2['rsi'].iloc[j] > 80: s += 1
            if pd.notna(d2['k'].iloc[j]) and d2['k'].iloc[j] > 80: s += 1
            if pd.notna(d2['d'].iloc[j]) and d2['d'].iloc[j] > 80: s += 1
            if pd.notna(d2['mfi'].iloc[j]) and d2['mfi'].iloc[j] > 80: s += 1
            recent_scores.append(s)
        max_recent = max(recent_scores) if recent_scores else 0
        
        # Check divergence
        has_div = False
        if pd.notna(cr) and cr >= 60:
            wp = d2['close'].iloc[i-lookback:i+1]
            wr = d2['rsi'].iloc[i-lookback:i+1]
            if cp >= wp.max() * 0.97:
                rp = wr.max()
                if rp >= 75 and rp - cr >= 8:
                    has_div = True
        
        date_str = dt.strftime('%Y-%m-%d')
        next_str = (dt + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        for ds in [date_str, next_str]:
            result[ds] = {'divergence': has_div or result.get(ds, {}).get('divergence', False),
                          'steve_score': max(score, result.get(ds, {}).get('steve_score', 0)),
                          'steve_max_recent': max(max_recent, result.get(ds, {}).get('steve_max_recent', 0))}
    
    return result


class V13DivSteve(V13BacktestV8):
    """Divergence + Steve context filter replaces OB93."""
    
    def __init__(self, pack, config=None, signal_data=None, steve_threshold=2, use_recent=True):
        super().__init__(pack, config)
        self.signal_data = signal_data or {}
        self.steve_threshold = steve_threshold
        self.use_recent = use_recent
        self.divergence_fired = False
    
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
        
        # Layer 2: DIVERGENCE + STEVE CONTEXT (replaces OB93)
        date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
        sig = self.signal_data.get(date_str, {})
        
        if sig.get('divergence', False) and not self.divergence_fired:
            steve = sig.get('steve_max_recent' if self.use_recent else 'steve_score', 0)
            if steve >= self.steve_threshold:
                self.divergence_fired = True
                pnl = self._sell_all(date, f'DIV+STEVE{steve} (thresh={self.steve_threshold})')
                if self.dca_coins > 0:
                    self._dca_close(date, 'TOP_EXIT')
                self._change_phase(date, Phase.FLAT, f'2D div + Steve>={self.steve_threshold}, pnl={pnl:+.1f}%')
                self._reset_top_state()
                return
        
        # Layer 2b: OB85 fallback (unchanged)
        if self.peak_2w_k < self.cfg.OB_THRESHOLD_2W and self.early_warning_date:
            if self._signal_near(date, self.ob85_1w):
                pnl = self._sell_all(date, f'FALLBACK_1W_OB85 (2W_peak={self.peak_2w_k:.0f})')
                if self.dca_coins > 0:
                    self._dca_close(date, 'TOP_EXIT')
                self._change_phase(date, Phase.FLAT,
                    f'1W OB85 fallback (2W peak={self.peak_2w_k:.0f}<93), pnl={pnl:+.1f}%')
                self._reset_top_state()
                return
        
        # Layer 3: Failsafe (unchanged)
        if self.early_warning_date and not self.failsafe_armed:
            if (date - self.early_warning_date).days >= self.cfg.FAILSAFE_WINDOW_WEEKS * 7:
                self.failsafe_armed = True
        if self.failsafe_armed and self._signal_near(date, self.failsafe_1w):
            pnl = self._sell_all(date, 'FAILSAFE_1W_K50')
            if self.dca_coins > 0:
                self._dca_close(date, 'TOP_EXIT')
            self._change_phase(date, Phase.FLAT, f'Failsafe 1W K<50, pnl={pnl:+.1f}%')
            self._reset_top_state()
            return
        
        # Layer 4: Ranging (unchanged)
        days_in = (date - self.phase_start_date).days if self.phase_start_date else 0
        if days_in >= 14:
            adx = self._adx(date)
            if not np.isnan(adx) and adx < self.cfg.PHASE_ADX_RANGING:
                self.adx_below_20_streak += 1
                if self.adx_below_20_streak >= self.cfg.PHASE_ADX_SUSTAINED_DAYS:
                    pnl = self._sell_all(date, f'MARKUP_RANGING (ADX<{self.cfg.PHASE_ADX_RANGING} for {self.adx_below_20_streak}d)')
                    if self.dca_coins > 0:
                        self._dca_close(date, 'RANGING_EXIT')
                    self._change_phase(date, Phase.FLAT, f'Markup ranging')
                    self._reset_top_state()
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
                    return
        
        self._check_markup_tiers(date, price)
    
    def _change_phase(self, date, new_phase, reason=''):
        super()._change_phase(date, new_phase, reason)
        if new_phase == Phase.MARKUP:
            self.divergence_fired = False


coins = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']

# Pre-compute signals
print("Computing signals...")
all_signals = {}
for coin in coins:
    base = coin.split('/')[0]
    all_signals[base] = compute_divergence_with_steve(coin)
    div_count = sum(1 for v in all_signals[base].values() if v['divergence'])
    print(f"  {base}: {div_count} divergence dates, max steve at div: {max((v['steve_max_recent'] for v in all_signals[base].values() if v['divergence']), default=0)}")

# Test matrix
print("\n" + "=" * 80)
print("DIVERGENCE + STEVE CONTEXT: SWEEP")
print("=" * 80)

# Get baseline once
baselines = {}
for coin in coins:
    base = coin.split('/')[0]
    pack = V13SignalPack(base)
    bt = V13BacktestV8(pack, V13Config())
    baselines[base] = bt.run()['final_equity']

base_total = sum(baselines.values())
print(f"\nBaseline: ETH=${baselines['ETH']:,.0f} SOL=${baselines['SOL']:,.0f} LINK=${baselines['LINK']:,.0f} XRP=${baselines['XRP']:,.0f} = ${base_total:,.0f}")

for use_recent in [True, False]:
    label = "recent_max" if use_recent else "current"
    print(f"\n--- Steve mode: {label} ---")
    print(f"{'Thresh':>6} | {'ETH':>8} {'SOL':>8} {'LINK':>8} {'XRP':>8} | {'Total':>9} {'Delta':>9}")
    print("-" * 75)
    
    for thresh in [1, 2, 3, 4]:
        results = {}
        for coin in coins:
            base = coin.split('/')[0]
            pack = V13SignalPack(base)
            bt = V13DivSteve(pack, V13Config(), signal_data=all_signals[base],
                           steve_threshold=thresh, use_recent=use_recent)
            results[base] = bt.run()['final_equity']
        
        total = sum(results.values())
        delta = total - base_total
        print(f"  >={thresh:>3} | ${results['ETH']:>7,.0f} ${results['SOL']:>7,.0f} ${results['LINK']:>7,.0f} ${results['XRP']:>7,.0f} | ${total:>8,.0f} ${delta:>+8,.0f}")

# Detail for best config
print("\n\n--- DETAIL: Best configs ---")
for thresh, use_recent in [(2, True), (3, True), (2, False), (3, False)]:
    label = "recent" if use_recent else "current"
    print(f"\nSteve>={thresh} ({label}):")
    for coin in coins:
        base = coin.split('/')[0]
        pack = V13SignalPack(base)
        bt = V13DivSteve(pack, V13Config(), signal_data=all_signals[base],
                       steve_threshold=thresh, use_recent=use_recent)
        bt.run()
        div_exits = [t for t in bt.trades if 'DIV+STEVE' in str(t.get('action', ''))]
        print(f"  {base}: {len(div_exits)} div exits")
        for t in div_exits:
            print(f"    {t['date']} @ ${t['price']:.2f} - {t['action']}")
