"""
FULL V2 FINAL BACKTEST: Bottom conviction + Top detection (OB93+divergence 35d)
Both systems integrated into ROUTER v2 engine.

Bottom: 3D death cross -> 2W K>=5 -> score>=3/4 -> close shorts, flip MARKUP
Top: OB93 arms -> wait for 2D divergence (35d timeout) -> sell MARKUP, enter ROUTER
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

import sqlite3, pandas as pd, numpy as np
from v13_router_engine_v2 import V13RouterV2, V13Config, Phase, V13SignalPack
from v13_router_engine_v2 import HybridDetector2D

DB_PATH = r'C:\Users\Never\.openclaw\workspace\trading\spot\data\candles.db'

def compute_2d_divergence_dates(coin):
    db = sqlite3.connect(DB_PATH)
    base = coin.split('/')[0] if '/' in coin else coin
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


class V13RouterV2Final(V13RouterV2):
    """V2 with OB93+divergence top timing. Bottom conviction inherited from V2."""
    
    def __init__(self, pack, config=None, conviction_enabled=True, min_score=3,
                 exhaustion_tf='2W', exhaustion_k_min=5.0, exhaustion_mode='k_lift',
                 div_dates=None, top_timing_enabled=True, max_wait_days=35):
        super().__init__(pack, config, conviction_enabled=conviction_enabled,
                        min_score=min_score, exhaustion_tf=exhaustion_tf,
                        exhaustion_k_min=exhaustion_k_min, exhaustion_mode=exhaustion_mode)
        self.div_dates = div_dates or set()
        self.top_timing_enabled = top_timing_enabled
        self.max_wait_days = max_wait_days
        self._ob93_armed = False
        self._ob93_armed_date = None
    
    def _router_check_markup(self, date, price, signals):
        """Override: OB93 arms then waits for divergence. All other layers unchanged."""
        if not self.top_timing_enabled:
            # Pass through to parent (v2 -> v1 -> v8 behavior)
            super()._router_check_markup(date, price, signals)
            return
        
        # DCA ticks
        if self.dca_coins > 0:
            self._dca_tick(date, price)
        
        # Track peak 2W K
        k_2w = self.pack.stoch_2w.get_k_at(date)
        if not np.isnan(k_2w) and k_2w > self.peak_2w_k:
            self.peak_2w_k = k_2w
        
        # Layer 1: Early warning
        if signals['early_warning_1w'] and self.early_warning_date is None:
            self.early_warning_date = date
            self.trades.append({
                'date': date, 'action': f'EARLY_WARNING_1W_97 (2W_peak={self.peak_2w_k:.0f})',
                'price': price, 'amount': 0, 'coins': 0, 'phase': self.phase
            })
        
        # Layer 2: OB93 ARMS (doesn't sell immediately)
        if not self._ob93_armed and signals['ob_2w_93']:
            self._ob93_armed = True
            self._ob93_armed_date = date
            self.trades.append({
                'date': date, 'action': f'OB93_ARMED (waiting for divergence, {self.max_wait_days}d timeout)',
                'price': price, 'amount': 0, 'coins': 0, 'phase': self.phase
            })
        
        # Layer 2 continued: check confirmation
        if self._ob93_armed:
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            days_armed = (date - self._ob93_armed_date).days if self._ob93_armed_date else 0
            has_div = date_str in self.div_dates
            timeout = days_armed >= self.max_wait_days
            
            if has_div or timeout:
                reason = 'DIVERGENCE' if has_div else f'TIMEOUT_{days_armed}d'
                old_phase = self.phase
                pnl = self._sell_all(date, f'OB93+{reason}')
                if self.dca_coins > 0:
                    self._dca_close(date, 'TOP_EXIT')
                self._change_phase(date, Phase.ROUTER, f'OB93 armed -> {reason}, pnl={pnl:+.1f}%')
                self._reset_top_state()
                self._ob93_armed = False
                self._ob93_armed_date = None
                # Trigger conviction gate (top detected)
                if self.conviction_enabled:
                    self._top_detected = True
                    self._conviction_fired = False
                    self._no_reshort = False
                return
        
        # Layer 2b: OB85 fallback (only if NOT armed)
        if not self._ob93_armed:
            if self.peak_2w_k < self.cfg.OB_THRESHOLD_2W and self.early_warning_date:
                if signals['ob_1w_85']:
                    old_phase = self.phase
                    pnl = self._sell_all(date, f'FALLBACK_1W_OB85 (2W_peak={self.peak_2w_k:.0f})')
                    if self.dca_coins > 0:
                        self._dca_close(date, 'TOP_EXIT')
                    self._change_phase(date, Phase.ROUTER, f'1W OB85 fallback, pnl={pnl:+.1f}%')
                    self._reset_top_state()
                    # Also trigger conviction gate
                    if self.conviction_enabled:
                        self._top_detected = True
                        self._conviction_fired = False
                        self._no_reshort = False
                    return
        
        # Layer 3: Failsafe (only if NOT armed)
        if not self._ob93_armed:
            if self.early_warning_date and not self.failsafe_armed:
                if (date - self.early_warning_date).days >= self.cfg.FAILSAFE_WINDOW_WEEKS * 7:
                    self.failsafe_armed = True
            if self.failsafe_armed and signals['failsafe_1w']:
                old_phase = self.phase
                pnl = self._sell_all(date, 'FAILSAFE_1W_K50')
                if self.dca_coins > 0:
                    self._dca_close(date, 'TOP_EXIT')
                self._change_phase(date, Phase.ROUTER, f'Failsafe 1W K<50')
                self._reset_top_state()
                if self.conviction_enabled:
                    self._top_detected = True
                    self._conviction_fired = False
                    self._no_reshort = False
                return
        
        # Layer 4: Ranging
        days_in = signals['days_in_phase']
        if days_in >= 14:
            adx = signals['adx']
            if not np.isnan(adx) and adx < self.cfg.PHASE_ADX_RANGING:
                self.adx_below_20_streak += 1
                if self.adx_below_20_streak >= self.cfg.PHASE_ADX_SUSTAINED_DAYS:
                    pnl = self._sell_all(date, f'MARKUP_RANGING')
                    if self.dca_coins > 0:
                        self._dca_close(date, 'RANGING_EXIT')
                    self._change_phase(date, Phase.ROUTER, f'Markup ranging')
                    self._reset_top_state()
                    self._ob93_armed = False
                    return
            else:
                self.adx_below_20_streak = 0
        
        # Layer 5: Markup failure
        if self.entry_price > 0:
            dd = (price - self.entry_price) / self.entry_price
            if dd < -self.cfg.MARKUP_FAIL_DD_PCT:
                adx = signals['adx']
                if not np.isnan(adx) and adx > self.cfg.MARKUP_FAIL_ADX:
                    pnl = self._sell_all(date, f'MARKUP_FAIL')
                    if self.dca_coins > 0:
                        self._dca_close(date, 'MARKUP_FAIL')
                    self._change_phase(date, Phase.ROUTER, f'Markup failed')
                    self._reset_top_state()
                    self._ob93_armed = False
                    return
        
        # Tier adds
        self._router_check_markup_tiers(date, price, signals)
    
    def _change_phase(self, date, new_phase, reason=''):
        """Reset OB93 armed state on entering MARKUP."""
        # Don't call v2's _router_check_markup override since we handle top detection ourselves
        # Call grandparent directly
        V13RouterV2._change_phase(self, date, new_phase, reason)
        if new_phase == Phase.MARKUP:
            self._ob93_armed = False
            self._ob93_armed_date = None


# ============================================================================
# RUN FULL COMPARISON: v1 baseline vs v2+conviction vs v2+conviction+top_timing
# ============================================================================

coins = ['ETH/USDC', 'SOL/USDC', 'LINK/USDC', 'XRP/USDC']
capital = 10000
per_coin = capital / len(coins)

print("Computing 2D divergence dates...")
all_div = {}
for coin in coins:
    base = coin.split('/')[0]
    all_div[base] = compute_2d_divergence_dates(coin)
    print(f"  {base}: {len(all_div[base])} dates")

print(f"\n{'='*80}")
print("FULL V2 FINAL BACKTEST")
print(f"Bottom: 3D DX + 2W K>=5 + score>=3/4 + close shorts")
print(f"Top: OB93 arms + 2D divergence (35d timeout)")
print(f"Capital: ${capital:,} (${per_coin:,.0f}/coin)")
print(f"{'='*80}")

configs = {
    'v1_baseline': {'conviction': False, 'top_timing': False},
    'v2_conviction_only': {'conviction': True, 'top_timing': False},
    'v2_full': {'conviction': True, 'top_timing': True},
}

all_results = {}

for label, cfg in configs.items():
    results = {}
    for coin in coins:
        base = coin.split('/')[0]
        pack = V13SignalPack(base)
        
        if not cfg['top_timing']:
            # Use standard V2 (with or without conviction)
            eng = V13RouterV2(pack, V13Config(), conviction_enabled=cfg['conviction'],
                            min_score=3, exhaustion_tf='2W', exhaustion_mode='k_lift')
        else:
            # Use V2 Final with top timing
            eng = V13RouterV2Final(pack, V13Config(), conviction_enabled=cfg['conviction'],
                                  min_score=3, exhaustion_tf='2W', exhaustion_mode='k_lift',
                                  div_dates=all_div[base], top_timing_enabled=True, max_wait_days=35)
        
        eng.cfg.CAPITAL = per_coin
        r = eng.run()
        if r:
            results[coin] = r
    
    all_results[label] = results

# Summary table
print(f"\n{'='*80}")
print(f"{'Config':<25} | {'ETH':>8} {'SOL':>8} {'LINK':>8} {'XRP':>8} | {'Total':>9} {'ROI':>7}")
print(f"{'-'*80}")

for label in configs:
    results = all_results[label]
    eqs = {}
    for coin in coins:
        eqs[coin] = results[coin]['final_equity'] if coin in results else 0
    total = sum(eqs.values())
    roi = (total - capital) / capital * 100
    print(f"{label:<25} | ${eqs.get('ETH/USDC',0):>7,.0f} ${eqs.get('SOL/USDC',0):>7,.0f} ${eqs.get('LINK/USDC',0):>7,.0f} ${eqs.get('XRP/USDC',0):>7,.0f} | ${total:>8,.0f} {roi:>+6.1f}%")

# Delta rows
base_total = sum(all_results['v1_baseline'][c]['final_equity'] for c in coins)
for label in ['v2_conviction_only', 'v2_full']:
    total = sum(all_results[label][c]['final_equity'] for c in coins)
    delta = total - base_total
    print(f"  delta vs baseline: {label:<20} ${delta:>+8,.0f}")

# Detail: triggers and key exits for v2_full
print(f"\n{'='*80}")
print("DETAIL: v2_full (conviction + top timing)")
print(f"{'='*80}")

for coin in coins:
    base = coin.split('/')[0]
    r = all_results['v2_full'][coin]
    pack = V13SignalPack(base)
    eng = V13RouterV2Final(pack, V13Config(), conviction_enabled=True,
                          min_score=3, exhaustion_tf='2W', exhaustion_mode='k_lift',
                          div_dates=all_div[base], top_timing_enabled=True, max_wait_days=35)
    eng.cfg.CAPITAL = per_coin
    r2 = eng.run()
    
    print(f"\n{coin} (${r2['final_equity']:,.0f}, {r2['roi']:+.1f}%):")
    
    # Key exits
    for t in eng.trades:
        a = str(t.get('action', ''))
        if any(x in a for x in ['OB93', 'FALLBACK', 'FAILSAFE', 'RANGING', 'FAIL', 'CONVICTION', 'DIVERGENCE']):
            print(f"  {t['date'].strftime('%Y-%m-%d') if hasattr(t['date'], 'strftime') else t['date']} - {a} @ ${t['price']:.2f}")
    
    # Conviction triggers
    if r2.get('conviction_triggers'):
        print(f"  CONVICTION TRIGGERS:")
        for ct in r2['conviction_triggers']:
            d = ct['details']
            print(f"    {ct['date'].strftime('%Y-%m-%d')}: score={ct['score']}/4, short_pnl={ct['short_pnl_pct']:+.1f}%")
