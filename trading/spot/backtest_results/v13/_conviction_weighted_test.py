"""
Conviction-Weighted Tier Deployment Backtest for V13 Trading Engine

This integrates the bottom/top signal stack into V13's existing phase and tier system.

**The Strategy (enhances V13 v8, doesn't replace it):**
- V13's phase system stays intact: DCA → MARKUP → ROUTER → MARKDOWN cycle
- The CHANGE is: when the bottom signal stack fires during ROUTER phase, deploy markup tiers IMMEDIATELY 
  based on conviction level (signal count), instead of waiting weeks for slow confirmation
- Same for top: when top signal fires during MARKUP phase, deploy short tiers immediately
- Remaining capital (not deployed to directional tiers) runs DCA as normal
- ALL existing risk management stays: markdown failure detector (>25% rise + ADX>25), markup failure detector, etc.

**Conviction → Tier Mapping:**
- 3/5 bottom signals → Deploy T1 only (60% of coin capital) to MARKUP immediately
- 4/5 bottom signals → Deploy T1 + T2 (80%) immediately
- 5/5 bottom signals → Deploy T1 + T2 + T3 (90%) immediately
- For TOP signals, same mapping but to MARKDOWN shorts

**Bottom Signal Stack (need Spring + N others):**
1. 2D death cross active (SMA50 < SMA200 on 2-day resampled candles)
2. Price below daily SMA200
3. CFGI < 35 (coin-specific, from cfgi_daily table)
4. Weekly RSI(7) < 30
5. Spring pattern (price breaks below 20-day support low, recovers above within 5 days)
Spring is ALWAYS required as structural confirmation.

**Top Signal (from V13's existing system):**
- 2W StochRSI K > 93 (primary)
- 1W StochRSI K > 85 (fallback)
- 1W StochRSI K < 50 (failsafe)
"""

import sys, os
import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path
from datetime import timedelta
from collections import defaultdict

# Import the base V13 backtest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v13_phase_backtest_v8 import V13BacktestV8, V13Config, Phase
from v13_signals import V13SignalPack, load_daily, load_cfgi

# Database path - resolve from script location
DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'


# ── Bottom Signal Stack Detector ──────────────────────────────────────────

class BottomStackDetector:
    """Detects bottom signal stack with conviction scoring."""
    
    def __init__(self, coin, db_path=None):
        self.coin = coin
        self.db_path = db_path or DB_PATH
        self.base_coin = coin.split('/')[0] if '/' in coin else coin
        
        # Load data
        self.daily = self._load_daily_data()
        self.cfgi = self._load_cfgi_data()
        
        if self.daily is None:
            print(f"  No daily data for {coin}")
            return
            
        # Compute indicators
        self._compute_indicators()
        
    def _load_daily_data(self):
        """Load daily candles for the coin."""
        try:
            db = sqlite3.connect(str(self.db_path))
            # Use LIKE query to find coin data in candles_daily table
            symbols = db.execute(
                "SELECT DISTINCT symbol FROM candles_daily WHERE symbol LIKE ?",
                (f'{self.base_coin}%',)
            ).fetchall()
            
            if not symbols:
                print(f"  No candles_daily data found for {self.base_coin}")
                db.close()
                return None
                
            # Pick first symbol found
            symbol = symbols[0][0]
            
            df = pd.read_sql(
                "SELECT * FROM candles_daily WHERE symbol=? ORDER BY timestamp",
                db, params=[symbol]
            )
            db.close()
            
            if len(df) == 0:
                return None
                
            # Convert timestamps (int64 epoch ms) to datetime
            df['dt'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('dt')
            
            # Deduplicate and remove NaT
            df = df[~df.index.duplicated(keep='last')]
            df = df[df.index.notna()]
            
            return df
            
        except Exception as e:
            print(f"  Error loading daily data for {self.coin}: {e}")
            return None
            
    def _load_cfgi_data(self):
        """Load CFGI data for the coin."""
        try:
            db = sqlite3.connect(str(self.db_path))
            # CFGI uses just the base coin symbol (e.g., 'BTC' not 'BTC/USDC')
            df = pd.read_sql(
                "SELECT * FROM cfgi_daily WHERE symbol = ? ORDER BY date",
                db, params=[self.base_coin]
            )
            db.close()
            
            if len(df) == 0:
                print(f"  No CFGI data for {self.base_coin}")
                return None
                
            # Handle mixed date formats
            df['dt'] = pd.to_datetime(df['date'], format='mixed')
            df = df.set_index('dt')
            df.index = df.index.normalize()  # Remove time component
            
            # Deduplicate
            df = df[~df.index.duplicated(keep='last')]
            
            return df
            
        except Exception as e:
            print(f"  Error loading CFGI data for {self.coin}: {e}")
            return None
            
    def _compute_indicators(self):
        """Compute all required indicators."""
        if self.daily is None:
            return
            
        # 1. Daily SMA200
        self.daily['sma200'] = self.daily['close'].rolling(200).mean()
        
        # 2. 2-day resampled candles for death cross
        self._compute_2d_death_cross()
        
        # 3. Weekly RSI(7)
        self._compute_weekly_rsi()
        
        # 4. 20-day support levels for Spring pattern
        self.daily['support_20d'] = self.daily['low'].rolling(20).min()
        
    def _compute_2d_death_cross(self):
        """Compute SMA50/SMA200 on 2-day resampled data."""
        try:
            # Resample daily to 2-day
            two_day = self.daily.resample('2D').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            
            # Compute SMAs
            two_day['sma50'] = two_day['close'].rolling(50).mean()
            two_day['sma200'] = two_day['close'].rolling(200).mean()
            two_day['death_cross'] = two_day['sma50'] < two_day['sma200']
            
            # Align with daily index
            self.death_cross_2d = two_day['death_cross'].reindex(
                self.daily.index, method='ffill'
            ).fillna(False)
            
        except Exception as e:
            print(f"  Error computing 2D death cross: {e}")
            self.death_cross_2d = pd.Series(False, index=self.daily.index)
            
    def _compute_weekly_rsi(self):
        """Compute RSI(7) on weekly data."""
        try:
            # Resample to weekly
            weekly = self.daily['close'].resample('W').last().dropna()
            
            # Compute RSI(7)
            delta = weekly.diff()
            gain = delta.clip(lower=0)
            loss = (-delta).clip(lower=0)
            avg_gain = gain.ewm(alpha=1/7, min_periods=7).mean()
            avg_loss = loss.ewm(alpha=1/7, min_periods=7).mean()
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            # Align with daily index
            self.weekly_rsi = rsi.reindex(self.daily.index, method='ffill')
            
        except Exception as e:
            print(f"  Error computing weekly RSI: {e}")
            self.weekly_rsi = pd.Series(np.nan, index=self.daily.index)
            
    def _detect_spring(self, date, lookback_days=5):
        """Detect Spring pattern: break below 20-day support, recover within 5 days."""
        try:
            if date not in self.daily.index:
                return False
                
            # Get 20-day support level at the date
            support = self.daily.loc[date, 'support_20d']
            if pd.isna(support):
                return False
                
            # Look back for break below support
            start_date = date - timedelta(days=lookback_days)
            window = self.daily[(self.daily.index >= start_date) & (self.daily.index <= date)]
            
            if len(window) == 0:
                return False
                
            # Check if price broke below support and then recovered above
            broke_below = (window['low'] < support).any()
            current_price = self.daily.loc[date, 'close']
            recovered_above = current_price > support
            
            return broke_below and recovered_above
            
        except Exception as e:
            print(f"  Error detecting Spring pattern: {e}")
            return False
            
    def get_conviction_score(self, date):
        """Get bottom signal conviction score (0-5) and signal details."""
        if self.daily is None:
            return 0, {}
            
        try:
            if date not in self.daily.index:
                return 0, {}
                
            signals = {}
            score = 0
            
            # Signal 1: 2D death cross active
            if hasattr(self, 'death_cross_2d') and date in self.death_cross_2d.index:
                signals['death_cross_2d'] = self.death_cross_2d.loc[date]
                if signals['death_cross_2d']:
                    score += 1
                    
            # Signal 2: Price below daily SMA200
            price = self.daily.loc[date, 'close']
            sma200 = self.daily.loc[date, 'sma200']
            signals['below_sma200'] = not pd.isna(sma200) and price < sma200
            if signals['below_sma200']:
                score += 1
                
            # Signal 3: CFGI < 35
            cfgi_val = np.nan
            if self.cfgi is not None:
                # Find CFGI value closest to date
                cfgi_dates = self.cfgi.index[self.cfgi.index <= date]
                if len(cfgi_dates) > 0:
                    cfgi_date = cfgi_dates[-1]
                    cfgi_val = self.cfgi.loc[cfgi_date, 'cfgi']
                    
            signals['cfgi_fear'] = not pd.isna(cfgi_val) and cfgi_val < 35
            if signals['cfgi_fear']:
                score += 1
                
            # Signal 4: Weekly RSI(7) < 30
            if hasattr(self, 'weekly_rsi') and date in self.weekly_rsi.index:
                weekly_rsi_val = self.weekly_rsi.loc[date]
                signals['weekly_rsi_os'] = not pd.isna(weekly_rsi_val) and weekly_rsi_val < 30
                if signals['weekly_rsi_os']:
                    score += 1
                    
            # Signal 5: Spring pattern (ALWAYS required)
            signals['spring'] = self._detect_spring(date)
            if signals['spring']:
                score += 1
                
            # Spring is ALWAYS required for any bottom signal
            if not signals['spring']:
                score = 0
                
            signals['conviction_score'] = score
            signals['price'] = price
            signals['cfgi'] = cfgi_val
            signals['weekly_rsi'] = weekly_rsi_val if hasattr(self, 'weekly_rsi') else np.nan
            
            return score, signals
            
        except Exception as e:
            print(f"  Error getting conviction score: {e}")
            return 0, {}


# ── Conviction-Weighted V13 Backtest ──────────────────────────────────────

class ConvictionWeightedV13(V13BacktestV8):
    """Extends V13BacktestV8 with conviction-weighted tier deployment."""
    
    def __init__(self, pack: V13SignalPack, config: V13Config = None, 
                 min_conviction=3, enable_conviction=True):
        super().__init__(pack, config)
        self.min_conviction = min_conviction  # Minimum conviction for immediate deployment
        self.enable_conviction = enable_conviction  # Can disable for baseline comparison
        self.bottom_detector = BottomStackDetector(pack.coin)
        self.conviction_triggers = []  # Track trigger events
        
    def _check_flat(self, date, price):
        """Override FLAT phase to add conviction-weighted bottom detection."""
        if not self.enable_conviction:
            return super()._check_flat(date, price)
            
        # Get conviction score
        conviction, signals = self.bottom_detector.get_conviction_score(date) if self.bottom_detector.daily is not None else (0, {})
        
        # If we have sufficient conviction, deploy immediately
        if conviction >= self.min_conviction:
            self._deploy_conviction_tiers(date, conviction, signals)
            return
            
        # Otherwise, use standard FLAT logic
        super()._check_flat(date, price)
        
    def _deploy_conviction_tiers(self, date, conviction, signals):
        """Deploy markup tiers immediately based on conviction level."""
        price = self._price(date)
        
        # Log the trigger
        trigger_info = {
            'date': date,
            'coin': self.coin,
            'conviction': conviction,
            'signals': signals,
            'price': price
        }
        self.conviction_triggers.append(trigger_info)
        
        # Determine tier deployment based on conviction
        if conviction >= 5:
            # 5/5 signals: Deploy T1 + T2 + T3 (90%)
            tiers = [1, 2, 3]
            tier_name = "T1+T2+T3"
        elif conviction >= 4:
            # 4/5 signals: Deploy T1 + T2 (80%)
            tiers = [1, 2]
            tier_name = "T1+T2"
        else:
            # 3/5 signals: Deploy T1 only (60%)
            tiers = [1]
            tier_name = "T1"
            
        # Change to MARKUP phase
        self._change_phase(date, Phase.MARKUP, 
                          f'CONVICTION {conviction}/5 -> {tier_name} immediate')
                          
        # Deploy the tiers
        for tier in tiers:
            if tier == 1:
                self._buy(date, self.cfg.TIER1_PCT, tier)
            elif tier == 2:
                self._buy(date, self.cfg.TIER2_PCT, tier)
            elif tier == 3:
                self._buy(date, self.cfg.TIER3_PCT, tier)
                
        # Reset state for top detection
        self.early_warning_date = None
        self.failsafe_armed = False
        self.peak_2w_k = 0


# ── Test Configuration and Execution ──────────────────────────────────────

def run_conviction_test():
    """Run conviction-weighted backtest variants."""
    
    # Test parameters
    coins = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']
    capital_per_coin = 2500  # $2,500 per coin ($12,500 total)
    
    # Test variants
    variants = [
        {'name': 'BASELINE', 'enable_conviction': False, 'min_conviction': 999},
        {'name': 'Conv >=3/5 -> T1', 'enable_conviction': True, 'min_conviction': 3},
        {'name': 'Conv >=4/5 -> T1+T2', 'enable_conviction': True, 'min_conviction': 4},
        {'name': 'Graduated (3->T1, 4->T1T2...)', 'enable_conviction': True, 'min_conviction': 3}
    ]
    
    # Results storage
    results = []
    all_triggers = []
    
    print("Conviction-Weighted Tier Deployment Backtest")
    print("=" * 80)
    
    for variant in variants:
        print(f"\nRunning {variant['name']}...")
        variant_results = {'name': variant['name'], 'coins': {}, 'triggers': 0}
        variant_triggers = []
        total_value = 0
        
        for coin in coins:
            try:
                print(f"  {coin}...", end='')
                
                # Load signal pack
                pack = V13SignalPack(coin)
                if pack.daily is None:
                    print(" no data")
                    continue
                    
                # Configure with higher profile (T1=60%, T2=20%, T3=10%)
                config = V13Config()
                config.CAPITAL = capital_per_coin
                config.TIER1_PCT = 0.60
                config.TIER2_PCT = 0.20
                config.TIER3_PCT = 0.10
                
                # Run backtest
                if variant['name'] == 'Graduated (3->T1, 4->T1T2...)':
                    # Special case: graduated deployment
                    bt = GraduatedConvictionV13(pack, config)
                else:
                    bt = ConvictionWeightedV13(
                        pack, config, 
                        min_conviction=variant['min_conviction'],
                        enable_conviction=variant['enable_conviction']
                    )
                    
                result = bt.run()
                
                if result:
                    final_value = result['final_equity']
                    variant_results['coins'][coin] = final_value
                    total_value += final_value
                else:
                    print(" no results")
                    variant_results['coins'][coin] = capital_per_coin  # No gain/loss
                    total_value += capital_per_coin
                    continue
                
                # Collect triggers
                if hasattr(bt, 'conviction_triggers'):
                    variant_triggers.extend(bt.conviction_triggers)
                    variant_results['triggers'] += len(bt.conviction_triggers)
                
                print(f" ${final_value:,.0f}")
                
            except Exception as e:
                print(f" error: {e}")
                variant_results['coins'][coin] = capital_per_coin  # No gain/loss
                total_value += capital_per_coin
                
        variant_results['total'] = total_value
        results.append(variant_results)
        all_triggers.extend(variant_triggers)
    
    # Print results
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    
    print(f"{'Variant':<35} {'Total$':<10} {'Delta':<8} {'Triggers':<8} {'ETH':<8} {'SOL':<8} {'BTC':<8} {'LINK':<8} {'XRP':<8}")
    print("-" * 100)
    
    baseline_total = None
    for result in results:
        if result['name'] == 'BASELINE':
            baseline_total = result['total']
            
        delta = ""
        if baseline_total and result['name'] != 'BASELINE':
            delta_val = result['total'] - baseline_total
            delta = f"+{delta_val:,.0f}" if delta_val >= 0 else f"{delta_val:,.0f}"
            
        print(f"{result['name']:<35} ${result['total']:>8,.0f} {delta:<8} {result['triggers']:<8}", end="")
        
        for coin in coins:
            coin_val = result['coins'].get(coin, capital_per_coin)
            print(f" ${coin_val:>6,.0f}", end="")
            
        print()
    
    # Print trigger details
    if all_triggers:
        print(f"\n{'TRIGGER EVENTS':<20} {'Date':<12} {'Coin':<6} {'Conv':<5} {'Tier':<10} {'Price':<10}")
        print("-" * 70)
        
        for trigger in all_triggers:
            signals = trigger['signals']
            tier_deployed = "T1"
            if signals['conviction_score'] >= 5:
                tier_deployed = "T1+T2+T3"
            elif signals['conviction_score'] >= 4:
                tier_deployed = "T1+T2"
                
            print(f"{'':<20} {trigger['date'].strftime('%Y-%m-%d')} {trigger['coin']:<6} "
                  f"{trigger['conviction']}/5   {tier_deployed:<10} ${trigger['price']:<9.2f}")


class GraduatedConvictionV13(ConvictionWeightedV13):
    """Graduated conviction deployment: 3->T1, 4->T1+T2, 5->T1+T2+T3."""
    
    def _check_flat(self, date, price):
        """Override to implement graduated deployment."""
        if not self.enable_conviction:
            return super()._check_flat(date, price)
            
        # Get conviction score
        conviction, signals = self.bottom_detector.get_conviction_score(date) if self.bottom_detector.daily is not None else (0, {})
        
        # Deploy based on conviction level (graduated)
        if conviction >= 3:
            self._deploy_conviction_tiers(date, conviction, signals)
            return
            
        # Otherwise, use standard FLAT logic
        super()._check_flat(date, price)


if __name__ == '__main__':
    run_conviction_test()