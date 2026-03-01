"""
Backtest v2: Replace ONLY OB93 with 2D divergence. Keep OB85 fallback, failsafe, ranging, failure.
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


class V13DivReplace93(V13BacktestV8):
    """Replace ONLY the OB93 primary exit with 2D divergence. Keep everything else."""
    
    def __init__(self, pack, config=None, divergence_dates=None):
        super().__init__(pack, config)
        self.divergence_dates = divergence_dates or set()
        self.divergence_fired = False
    
    def _check_markup(self, date, price):
        """Override: swap Layer 2 (OB93) with divergence, keep Layers 1,2b,3,4,5."""
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
        
        # Layer 2: REPLACED — 2D divergence instead of OB93
        date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
        if date_str in self.divergence_dates and not self.divergence_fired:
            self.divergence_fired = True
            pnl = self._sell_all(date, 'DIVERGENCE_2D_TOP')
            if self.dca_coins > 0:
                self._dca_close(date, 'TOP_EXIT')
            self._change_phase(date, Phase.FLAT, f'2D divergence exit, pnl={pnl:+.1f}%')
            self._reset_top_state()
            return
        
        # Layer 2b: OB85 fallback (unchanged — fires when 2W never reached OB)
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
                    self._change_phase(date, Phase.FLAT,
                        f'Markup ranging: ADX<{self.cfg.PHASE_ADX_RANGING} for {self.adx_below_20_streak}d')
                    self._reset_top_state()
                    return
            else:
                self.adx_below_20_streak = 0
        
        # Layer 5: Markup failure (unchanged)
        if self.entry_price > 0:
            dd_from_entry = (price - self.entry_price) / self.entry_price
            if dd_from_entry < -self.cfg.MARKUP_FAIL_DD_PCT:
                adx = self._adx(date)
                if not np.isnan(adx) and adx > self.cfg.MARKUP_FAIL_ADX:
                    pnl = self._sell_all(date, f'MARKUP_FAIL (dd={dd_from_entry*100:.0f}%, ADX={adx:.0f})')
                    if self.dca_coins > 0:
                        self._dca_close(date, 'MARKUP_FAIL')
                    self._change_phase(date, Phase.FLAT,
                        f'Markup failed: {dd_from_entry*100:.0f}% below entry')
                    self._reset_top_state()
                    return
        
        self._check_markup_tiers(date, price)
    
    def _change_phase(self, date, new_phase, reason=''):
        super()._change_phase(date, new_phase, reason)
        if new_phase == Phase.MARKUP:
            self.divergence_fired = False


coins = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']

print("=" * 70)
print("V13: 2D DIVERGENCE REPLACES OB93 ONLY (keep OB85/failsafe/ranging)")
print("=" * 70)

bt = 0; dt = 0

for coin in coins:
    base = coin.split('/')[0]
    div_dates = compute_2d_divergence_dates(coin)
    
    pack_b = V13SignalPack(base)
    bt_b = V13BacktestV8(pack_b, V13Config())
    eq_b = bt_b.run()['final_equity']
    
    pack_d = V13SignalPack(base)
    bt_d = V13DivReplace93(pack_d, V13Config(), divergence_dates=div_dates)
    eq_d = bt_d.run()['final_equity']
    
    delta = eq_d - eq_b
    bt += eq_b; dt += eq_d
    
    div_exits = [t for t in bt_d.trades if 'DIVERGENCE' in str(t.get('action', ''))]
    base_ob93 = [t for t in bt_b.trades if 'OB93' in str(t.get('action', ''))]
    
    print(f"\n{base}: ${eq_b:,.0f} -> ${eq_d:,.0f} (delta ${delta:+,.0f})")
    print(f"  Divergence exits: {len(div_exits)}")
    for t in div_exits:
        print(f"    {t['date']} @ ${t['price']:.2f}")
    print(f"  Baseline OB93 exits: {len(base_ob93)}")
    for t in base_ob93:
        print(f"    {t['date']} @ ${t['price']:.2f}")

print(f"\n{'='*70}")
print(f"BASELINE:    ${bt:,.0f}")
print(f"DIVERGENCE:  ${dt:,.0f}")
print(f"DELTA:       ${dt - bt:+,.0f}")
print(f"{'='*70}")
