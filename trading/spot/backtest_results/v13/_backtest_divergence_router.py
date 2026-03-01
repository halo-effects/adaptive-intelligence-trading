"""
Backtest: Replace OB93/OB85/failsafe top detection with 2D RSI bearish divergence.
Compare vs baseline v8 ($28,094).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

import sqlite3
import pandas as pd
import numpy as np
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack

DB_PATH = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'

def compute_2d_divergence_dates(coin):
    """Find all dates where 2D RSI bearish divergence fires."""
    db = sqlite3.connect(DB_PATH)
    base = coin.split('/')[0]
    df = pd.read_sql(f"SELECT timestamp, close FROM candles_daily WHERE symbol LIKE '{base}%' ORDER BY timestamp", db)
    db.close()
    if df.empty:
        return set()
    
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('date').sort_index()
    d2 = df.resample('2D').agg({'close': 'last'}).dropna()
    
    # RSI on 2D
    period = 14
    delta = d2['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    d2['rsi'] = rsi
    
    lookback = 30
    rsi_gap = 8
    price_pct = 0.03
    rsi_floor = 60
    rsi_peak_min = 75
    
    divergence_dates = set()
    
    for i in range(lookback, len(d2)):
        current_rsi = d2['rsi'].iloc[i]
        current_price = d2['close'].iloc[i]
        if pd.isna(current_rsi) or current_rsi < rsi_floor:
            continue
        
        window_prices = d2['close'].iloc[i-lookback:i+1]
        window_rsi = d2['rsi'].iloc[i-lookback:i+1]
        
        price_high = window_prices.max()
        if current_price < price_high * (1 - price_pct):
            continue
        
        rsi_peak = window_rsi.max()
        if rsi_peak < rsi_peak_min:
            continue
        
        if rsi_peak - current_rsi >= rsi_gap:
            div_date = d2.index[i]
            # Add the 2D candle date and next day to catch daily tick
            divergence_dates.add(div_date.strftime('%Y-%m-%d'))
            divergence_dates.add((div_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d'))
    
    return divergence_dates


class V13DivergenceTop(V13BacktestV8):
    """V13 engine with 2D divergence replacing OB93/OB85/failsafe for top detection."""
    
    def __init__(self, pack, config=None, divergence_dates=None):
        super().__init__(pack, config)
        self.divergence_dates = divergence_dates or set()
        self.divergence_fired = False
    
    def _check_markup(self, date, price):
        """Override: Replace OB93/OB85/failsafe with 2D divergence, keep ranging + failure."""
        if self.dca_coins > 0:
            self._dca_tick(date, price)
        
        k_2w = self.pack.stoch_2w.get_k_at(date)
        if not np.isnan(k_2w) and k_2w > self.peak_2w_k:
            self.peak_2w_k = k_2w
        
        # NEW: 2D RSI Bearish Divergence as primary top signal
        date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
        
        if date_str in self.divergence_dates and not self.divergence_fired:
            self.divergence_fired = True
            pnl = self._sell_all(date, 'DIVERGENCE_2D_TOP')
            if self.dca_coins > 0:
                self._dca_close(date, 'TOP_EXIT')
            self._change_phase(date, Phase.FLAT, f'2D RSI divergence top, pnl={pnl:+.1f}%')
            self._reset_top_state()
            return
        
        # Keep Layer 4: Ranging exit
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
        
        # Keep Layer 5: Markup failure
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
        """Reset divergence_fired when entering MARKUP."""
        super()._change_phase(date, new_phase, reason)
        if new_phase == Phase.MARKUP:
            self.divergence_fired = False


# Run comparison
coins = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
start = '2023-01-01'

print("=" * 70)
print("V13 TOP DETECTION: 2D DIVERGENCE vs BASELINE (OB93/OB85/failsafe)")
print("=" * 70)

baseline_total = 0
divergence_total = 0

for coin in coins:
    base = coin.split('/')[0]
    div_dates = compute_2d_divergence_dates(coin)
    print(f"\n{base}: {len(div_dates)} divergence dates found")
    
    # Baseline
    pack_b = V13SignalPack(base)
    cfg_b = V13Config()
    bt_b = V13BacktestV8(pack_b, cfg_b)
    res_b = bt_b.run()
    eq_b = res_b['final_equity']
    
    # Divergence
    pack_d = V13SignalPack(base)
    cfg_d = V13Config()
    bt_d = V13DivergenceTop(pack_d, cfg_d, divergence_dates=div_dates)
    res_d = bt_d.run()
    eq_d = res_d['final_equity']
    
    delta = eq_d - eq_b
    baseline_total += eq_b
    divergence_total += eq_d
    
    div_exits = [t for t in bt_d.trades if 'DIVERGENCE' in str(t.get('action', ''))]
    base_exits = [t for t in bt_b.trades if any(x in str(t.get('action', '')) for x in ['OB93', 'OB85', 'FAILSAFE', 'RANGING'])]
    
    print(f"  Baseline:    ${eq_b:,.0f}")
    print(f"  Divergence:  ${eq_d:,.0f}  (delta: ${delta:+,.0f})")
    print(f"  Divergence exits ({len(div_exits)}):")
    for t in div_exits:
        print(f"    {t['date']} @ ${t['price']:.2f} — {t['action']}")
    print(f"  Baseline exits ({len(base_exits)}):")
    for t in base_exits:
        print(f"    {t['date']} @ ${t['price']:.2f} — {t['action']}")

print(f"\n{'='*70}")
print(f"TOTAL BASELINE:    ${baseline_total:,.0f}")
print(f"TOTAL DIVERGENCE:  ${divergence_total:,.0f}")
print(f"DELTA:             ${divergence_total - baseline_total:+,.0f}")
print(f"{'='*70}")
