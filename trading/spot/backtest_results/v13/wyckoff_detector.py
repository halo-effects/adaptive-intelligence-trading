"""
Wyckoff Pattern Detection Module for V13 Trading Engine

This module detects accumulation and distribution patterns using the Wyckoff Method
to help the ROUTER phase make better transition decisions.

Author: V13 Trading Engine
Date: 2026-02-27
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

# Database path (same as V13 signals)
DB_PATH = Path(__file__).resolve().parents[3] / 'spot' / 'data' / 'candles.db'


class WyckoffDetector:
    """
    Wyckoff Pattern Detector for daily OHLCV data.
    
    Detects accumulation and distribution patterns and classifies Wyckoff phases:
    - Phase A: Stopping the trend (PS → SC → AR → ST)
    - Phase B: Building the cause (range-bound testing)
    - Phase C: The test (Spring for accumulation, UTAD for distribution) 
    - Phase D: Markup/Markdown begins (SOS/SOW)
    - Phase E: Trend in progress
    """
    
    def __init__(self, daily_data: pd.DataFrame, symbol: str = ""):
        """
        Initialize Wyckoff detector with daily OHLCV data.
        
        Args:
            daily_data: DataFrame with datetime index and OHLCV columns
            symbol: Trading symbol for reference
        """
        self.data = daily_data.copy()
        self.symbol = symbol
        self.events = []
        
        # Ensure we have required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in self.data.columns for col in required_cols):
            raise ValueError(f"Missing required columns. Need: {required_cols}")
            
        # Calculate technical indicators
        self._calculate_indicators()
        
        # Pattern state tracking
        self.current_phase = None
        self.accumulation_zones = []
        self.distribution_zones = []
        
    def _calculate_indicators(self):
        """Calculate technical indicators used for pattern detection."""
        # ATR for significant price move detection
        high_low = self.data['high'] - self.data['low']
        high_close = np.abs(self.data['high'] - self.data['close'].shift())
        low_close = np.abs(self.data['low'] - self.data['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        self.data['atr'] = true_range.rolling(14).mean()
        
        # Volume indicators
        self.data['volume_sma20'] = self.data['volume'].rolling(20).mean()
        self.data['volume_ratio'] = self.data['volume'] / self.data['volume_sma20']
        
        # Price indicators
        self.data['sma20'] = self.data['close'].rolling(20).mean()
        self.data['sma50'] = self.data['close'].rolling(50).mean()
        
        # Support and resistance levels
        self._calculate_support_resistance()
        
    def _calculate_support_resistance(self, lookback_short: int = 20, lookback_long: int = 50):
        """Calculate dynamic support and resistance levels."""
        self.data['support'] = self.data['low'].rolling(lookback_short).min()
        self.data['resistance'] = self.data['high'].rolling(lookback_short).max()
        self.data['support_long'] = self.data['low'].rolling(lookback_long).min()
        self.data['resistance_long'] = self.data['high'].rolling(lookback_long).max()
        
    def _is_high_volume(self, idx: int, threshold: float = 1.5) -> bool:
        """Check if volume is high relative to average."""
        if idx < 20 or 'volume_ratio' not in self.data.columns:
            return False
        return self.data.iloc[idx]['volume_ratio'] > threshold
        
    def _is_low_volume(self, idx: int, threshold: float = 0.7) -> bool:
        """Check if volume is low relative to average."""
        if idx < 20 or 'volume_ratio' not in self.data.columns:
            return False
        return self.data.iloc[idx]['volume_ratio'] < threshold
        
    def _is_significant_move(self, idx: int, pct_threshold: float = 3.0, atr_threshold: float = 1.0) -> bool:
        """Check if price move is significant based on % and ATR."""
        if idx < 1:
            return False
        row = self.data.iloc[idx]
        prev_close = self.data.iloc[idx-1]['close']
        
        # Percentage move
        pct_move = abs(row['close'] - prev_close) / prev_close * 100
        
        # ATR move
        atr_move = abs(row['close'] - prev_close) / row['atr'] if row['atr'] > 0 else 0
        
        return pct_move > pct_threshold or atr_move > atr_threshold
        
    def _detect_preliminary_support(self, idx: int) -> Optional[Dict]:
        """Detect PS (Preliminary Support) - first significant buying after extended decline."""
        if idx < 50:
            return None
            
        row = self.data.iloc[idx]
        
        # Check for extended decline (price below SMA50 and declining)
        recent_closes = self.data.iloc[idx-20:idx]['close']
        if len(recent_closes) == 0:
            return None
            
        # Must be in a downtrend
        if row['close'] > row['sma50'] or recent_closes.iloc[-1] >= recent_closes.iloc[0]:
            return None
            
        # High volume bounce
        if not self._is_high_volume(idx, 1.3):
            return None
            
        # Significant bounce from low
        bounce_size = (row['close'] - row['low']) / row['low'] * 100
        if bounce_size < 2.0:  # At least 2% intraday bounce
            return None
            
        return {
            'date': row.name,
            'pattern_type': 'PS',
            'confidence': 0.6,
            'price': row['close'],
            'volume_ratio': row['volume_ratio'],
            'description': 'Preliminary Support - First significant buying after decline'
        }
        
    def _detect_selling_climax(self, idx: int) -> Optional[Dict]:
        """Detect SC (Selling Climax) - sharp drop on very high volume with quick recovery."""
        if idx < 10:
            return None
            
        row = self.data.iloc[idx]
        
        # Very high volume
        if not self._is_high_volume(idx, 2.0):
            return None
            
        # Sharp price drop
        drop_size = (row['close'] - row['open']) / row['open'] * 100
        if drop_size > -3.0:  # At least 3% drop
            return None
            
        # Quick recovery (close near high of day)
        recovery = (row['close'] - row['low']) / (row['high'] - row['low'])
        if recovery < 0.6:  # Close in upper 40% of range
            return None
            
        return {
            'date': row.name,
            'pattern_type': 'SC', 
            'confidence': 0.8,
            'price': row['close'],
            'volume_ratio': row['volume_ratio'],
            'description': 'Selling Climax - Sharp drop on high volume with recovery'
        }
        
    def _detect_automatic_rally(self, idx: int) -> Optional[Dict]:
        """Detect AR (Automatic Rally) - rally after SC on declining volume."""
        if idx < 20:
            return None
            
        row = self.data.iloc[idx]
        
        # Look for recent SC (within last 10 days)
        recent_sc = None
        for i in range(max(0, idx-10), idx):
            for event in self.events:
                if (event['pattern_type'] == 'SC' and 
                    abs((event['date'] - self.data.index[i]).days) <= 1):
                    recent_sc = event
                    break
        
        if not recent_sc:
            return None
            
        # Rally from SC low
        sc_price = recent_sc['price']
        if row['close'] <= sc_price * 1.03:  # At least 3% rally from SC
            return None
            
        # Declining volume compared to SC
        if row['volume_ratio'] >= recent_sc['volume_ratio'] * 0.8:
            return None
            
        return {
            'date': row.name,
            'pattern_type': 'AR',
            'confidence': 0.7,
            'price': row['close'], 
            'volume_ratio': row['volume_ratio'],
            'description': 'Automatic Rally - Rally after SC on declining volume'
        }
        
    def _detect_secondary_test(self, idx: int) -> Optional[Dict]:
        """Detect ST (Secondary Test) - retest of SC area on lower volume."""
        if idx < 30:
            return None
            
        row = self.data.iloc[idx]
        
        # Look for SC/AR sequence in recent history
        recent_events = [e for e in self.events if 
                        e['pattern_type'] in ['SC', 'AR'] and
                        abs((e['date'] - row.name).days) <= 20]
        
        if len(recent_events) < 2:
            return None
            
        # Find SC level
        sc_events = [e for e in recent_events if e['pattern_type'] == 'SC']
        if not sc_events:
            return None
            
        sc_price = sc_events[-1]['price']
        
        # Test of SC area (within 3% of SC price)
        if abs(row['close'] - sc_price) / sc_price > 0.03:
            return None
            
        # Lower volume than SC
        sc_volume = sc_events[-1]['volume_ratio']
        if row['volume_ratio'] >= sc_volume * 0.7:
            return None
            
        return {
            'date': row.name,
            'pattern_type': 'ST',
            'confidence': 0.7,
            'price': row['close'],
            'volume_ratio': row['volume_ratio'],
            'description': 'Secondary Test - Retest of SC area on low volume'
        }
        
    def _detect_spring(self, idx: int) -> Optional[Dict]:
        """Detect Spring - price breaks below support then quickly reverses (KEY accumulation signal)."""
        if idx < 5:
            return None
            
        # Check last 1-3 days for spring pattern
        for lookback in range(1, 4):
            if idx < lookback:
                continue
                
            current_row = self.data.iloc[idx]
            spring_row = self.data.iloc[idx - lookback]
            
            # Support level from recent lows
            support_level = spring_row['support']
            if pd.isna(support_level):
                continue
                
            # Price broke below support by > 0.5 ATR
            break_amount = support_level - spring_row['low']
            atr_break = break_amount / spring_row['atr'] if spring_row['atr'] > 0 else 0
            
            if atr_break < 0.5:
                continue
                
            # Quick reversal - close back above support
            if current_row['close'] <= support_level:
                continue
                
            # Volume confirmation (should be relatively high on break)
            if not self._is_high_volume(idx - lookback, 1.2):
                continue
                
            return {
                'date': current_row.name,
                'pattern_type': 'Spring',
                'confidence': 0.9,
                'price': current_row['close'],
                'volume_ratio': spring_row['volume_ratio'],
                'description': 'Spring - Key accumulation signal: break and reversal'
            }
            
        return None
        
    def _detect_sign_of_strength(self, idx: int) -> Optional[Dict]:
        """Detect SOS (Sign of Strength) - strong rally on increasing volume breaking resistance."""
        if idx < 20:
            return None
            
        row = self.data.iloc[idx]
        
        # Break above resistance
        resistance_level = row['resistance']
        if pd.isna(resistance_level) or row['close'] <= resistance_level:
            return None
            
        # Strong volume (> 1.5x average)
        if not self._is_high_volume(idx, 1.5):
            return None
            
        # Significant price move up
        if not self._is_significant_move(idx):
            return None
            
        # Look for recent accumulation signals
        recent_acc_signals = [e for e in self.events if 
                             e['pattern_type'] in ['Spring', 'ST', 'SC'] and
                             abs((e['date'] - row.name).days) <= 30]
        
        confidence = 0.8 if recent_acc_signals else 0.6
        
        return {
            'date': row.name,
            'pattern_type': 'SOS',
            'confidence': confidence,
            'price': row['close'],
            'volume_ratio': row['volume_ratio'],
            'description': 'Sign of Strength - Strong rally breaking resistance'
        }
        
    def _detect_last_point_of_support(self, idx: int) -> Optional[Dict]:
        """Detect LPS (Last Point of Support) - pullback after SOS on low volume."""
        if idx < 10:
            return None
            
        row = self.data.iloc[idx]
        
        # Look for recent SOS
        recent_sos = None
        for event in self.events:
            if (event['pattern_type'] == 'SOS' and 
                1 <= (row.name - event['date']).days <= 10):
                recent_sos = event
                break
                
        if not recent_sos:
            return None
            
        # Pullback from SOS high
        sos_price = recent_sos['price']
        if row['close'] >= sos_price * 0.95:  # At least 5% pullback
            return None
            
        # Low volume
        if not self._is_low_volume(idx, 0.8):
            return None
            
        return {
            'date': row.name,
            'pattern_type': 'LPS',
            'confidence': 0.7,
            'price': row['close'],
            'volume_ratio': row['volume_ratio'],
            'description': 'Last Point of Support - Low volume pullback after SOS'
        }
        
    def _detect_preliminary_supply(self, idx: int) -> Optional[Dict]:
        """Detect PSY (Preliminary Supply) - first significant selling after extended rally."""
        if idx < 50:
            return None
            
        row = self.data.iloc[idx]
        
        # Check for extended rally (price above SMA50 and rising)
        recent_closes = self.data.iloc[idx-20:idx]['close']
        if len(recent_closes) == 0:
            return None
            
        # Must be in uptrend
        if row['close'] < row['sma50'] or recent_closes.iloc[-1] <= recent_closes.iloc[0]:
            return None
            
        # High volume selling
        if not self._is_high_volume(idx, 1.3):
            return None
            
        # Significant drop from high
        drop_size = (row['high'] - row['close']) / row['high'] * 100
        if drop_size < 2.0:  # At least 2% intraday drop from high
            return None
            
        return {
            'date': row.name,
            'pattern_type': 'PSY',
            'confidence': 0.6,
            'price': row['close'],
            'volume_ratio': row['volume_ratio'],
            'description': 'Preliminary Supply - First significant selling after rally'
        }
        
    def _detect_buying_climax(self, idx: int) -> Optional[Dict]:
        """Detect BC (Buying Climax) - sharp spike on high volume then reversal."""
        if idx < 10:
            return None
            
        row = self.data.iloc[idx]
        
        # Very high volume
        if not self._is_high_volume(idx, 2.0):
            return None
            
        # Sharp price spike up then reversal
        spike_size = (row['high'] - row['open']) / row['open'] * 100
        if spike_size < 3.0:  # At least 3% spike
            return None
            
        # Reversal (close significantly below high)
        reversal = (row['high'] - row['close']) / (row['high'] - row['low'])
        if reversal < 0.4:  # Close in lower 60% of range
            return None
            
        return {
            'date': row.name,
            'pattern_type': 'BC',
            'confidence': 0.8,
            'price': row['close'],
            'volume_ratio': row['volume_ratio'],
            'description': 'Buying Climax - Sharp spike on high volume with reversal'
        }
        
    def _detect_upthrust_after_distribution(self, idx: int) -> Optional[Dict]:
        """Detect UTAD (Upthrust After Distribution) - break above resistance then failure."""
        if idx < 5:
            return None
            
        # Check last 1-3 days for UTAD pattern
        for lookback in range(1, 4):
            if idx < lookback:
                continue
                
            current_row = self.data.iloc[idx]
            utad_row = self.data.iloc[idx - lookback]
            
            # Resistance level
            resistance_level = utad_row['resistance']
            if pd.isna(resistance_level):
                continue
                
            # Price broke above resistance
            break_amount = utad_row['high'] - resistance_level
            if break_amount <= 0:
                continue
                
            # Failed and closed back below resistance
            if current_row['close'] >= resistance_level:
                continue
                
            # Look for recent distribution signals
            recent_dist_signals = [e for e in self.events if 
                                 e['pattern_type'] in ['BC', 'PSY'] and
                                 abs((e['date'] - current_row.name).days) <= 30]
            
            confidence = 0.9 if recent_dist_signals else 0.7
            
            return {
                'date': current_row.name,
                'pattern_type': 'UTAD',
                'confidence': confidence,
                'price': current_row['close'],
                'volume_ratio': utad_row['volume_ratio'],
                'description': 'UTAD - Key distribution signal: break above resistance then failure'
            }
            
        return None
        
    def _detect_sign_of_weakness(self, idx: int) -> Optional[Dict]:
        """Detect SOW (Sign of Weakness) - strong decline on increasing volume below support."""
        if idx < 20:
            return None
            
        row = self.data.iloc[idx]
        
        # Break below support
        support_level = row['support']
        if pd.isna(support_level) or row['close'] >= support_level:
            return None
            
        # Strong volume
        if not self._is_high_volume(idx, 1.5):
            return None
            
        # Significant price move down
        if row['close'] >= self.data.iloc[idx-1]['close'] * 0.97:  # At least 3% down
            return None
            
        # Look for recent distribution signals
        recent_dist_signals = [e for e in self.events if 
                              e['pattern_type'] in ['UTAD', 'BC', 'PSY'] and
                              abs((e['date'] - row.name).days) <= 30]
        
        confidence = 0.8 if recent_dist_signals else 0.6
        
        return {
            'date': row.name,
            'pattern_type': 'SOW',
            'confidence': confidence,
            'price': row['close'],
            'volume_ratio': row['volume_ratio'],
            'description': 'Sign of Weakness - Strong decline breaking support'
        }
        
    def _detect_last_point_of_supply(self, idx: int) -> Optional[Dict]:
        """Detect LPSY (Last Point of Supply) - rally after SOW on low volume."""
        if idx < 10:
            return None
            
        row = self.data.iloc[idx]
        
        # Look for recent SOW
        recent_sow = None
        for event in self.events:
            if (event['pattern_type'] == 'SOW' and 
                1 <= (row.name - event['date']).days <= 10):
                recent_sow = event
                break
                
        if not recent_sow:
            return None
            
        # Rally from SOW low
        sow_price = recent_sow['price']
        if row['close'] <= sow_price * 1.03:  # At least 3% rally from SOW
            return None
            
        # Low volume
        if not self._is_low_volume(idx, 0.8):
            return None
            
        return {
            'date': row.name,
            'pattern_type': 'LPSY',
            'confidence': 0.7,
            'price': row['close'],
            'volume_ratio': row['volume_ratio'],
            'description': 'Last Point of Supply - Low volume rally after SOW'
        }
        
    def detect_patterns(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """
        Detect all Wyckoff patterns in the specified date range.
        
        Args:
            start_date: Start date for detection (YYYY-MM-DD format)
            end_date: End date for detection (YYYY-MM-DD format)
            
        Returns:
            List of detected pattern events with metadata
        """
        # Filter date range
        data_slice = self.data.copy()
        if start_date:
            data_slice = data_slice[data_slice.index >= pd.Timestamp(start_date)]
        if end_date:
            data_slice = data_slice[data_slice.index <= pd.Timestamp(end_date)]
            
        # Reset events for fresh detection
        self.events = []
        
        # Pattern detection functions
        detection_functions = [
            self._detect_preliminary_support,
            self._detect_selling_climax,
            self._detect_automatic_rally,
            self._detect_secondary_test,
            self._detect_spring,
            self._detect_sign_of_strength,
            self._detect_last_point_of_support,
            self._detect_preliminary_supply,
            self._detect_buying_climax,
            self._detect_upthrust_after_distribution,
            self._detect_sign_of_weakness,
            self._detect_last_point_of_supply
        ]
        
        # Scan through data chronologically
        for i in range(len(data_slice)):
            # Get the actual index in the full dataset
            full_idx = self.data.index.get_loc(data_slice.index[i])
            
            # Apply all detection functions
            for detect_func in detection_functions:
                pattern = detect_func(full_idx)
                if pattern:
                    self.events.append(pattern)
                    
        # Sort events by date
        self.events.sort(key=lambda x: x['date'])
        
        return self.events
        
    def classify_phase(self, date: pd.Timestamp) -> Optional[str]:
        """
        Classify the current Wyckoff phase at a given date.
        
        Args:
            date: Date to classify phase for
            
        Returns:
            Phase classification ('A', 'B', 'C', 'D', 'E') or None
        """
        # Get events before this date
        prior_events = [e for e in self.events if e['date'] <= date]
        if not prior_events:
            return None
            
        # Look at recent events (last 60 days)
        lookback_date = date - pd.Timedelta(days=60)
        recent_events = [e for e in prior_events if e['date'] >= lookback_date]
        
        # Phase classification logic
        accumulation_signals = ['PS', 'SC', 'AR', 'ST', 'Spring', 'SOS', 'LPS']
        distribution_signals = ['PSY', 'BC', 'AR', 'ST', 'UTAD', 'SOW', 'LPSY']
        
        acc_count = sum(1 for e in recent_events if e['pattern_type'] in accumulation_signals)
        dist_count = sum(1 for e in recent_events if e['pattern_type'] in distribution_signals)
        
        if not recent_events:
            return None
            
        # Check for key signals
        has_spring = any(e['pattern_type'] == 'Spring' for e in recent_events)
        has_sos = any(e['pattern_type'] == 'SOS' for e in recent_events)
        has_utad = any(e['pattern_type'] == 'UTAD' for e in recent_events)
        has_sow = any(e['pattern_type'] == 'SOW' for e in recent_events)
        
        # Phase classification
        if has_spring and not has_sos:
            return 'C'  # Spring test phase
        elif has_sos:
            return 'D'  # Markup beginning
        elif has_utad and not has_sow:
            return 'C'  # UTAD test phase  
        elif has_sow:
            return 'D'  # Markdown beginning
        elif acc_count > dist_count and acc_count >= 2:
            return 'A' if any(e['pattern_type'] in ['PS', 'SC'] for e in recent_events) else 'B'
        elif dist_count > acc_count and dist_count >= 2:
            return 'A' if any(e['pattern_type'] in ['PSY', 'BC'] for e in recent_events) else 'B'
            
        return 'B'  # Default to building phase
        
    def get_phase_summary(self, start_date: str = "2023-01-01", end_date: str = "2026-02-25") -> Dict:
        """Get a summary of phases and key signals over time."""
        events = self.detect_patterns(start_date, end_date)
        
        # Group by pattern type
        pattern_counts = {}
        for event in events:
            ptype = event['pattern_type']
            pattern_counts[ptype] = pattern_counts.get(ptype, 0) + 1
            
        # Key signals for phase transitions
        springs = [e for e in events if e['pattern_type'] == 'Spring']
        sos_signals = [e for e in events if e['pattern_type'] == 'SOS']
        utads = [e for e in events if e['pattern_type'] == 'UTAD'] 
        sows = [e for e in events if e['pattern_type'] == 'SOW']
        
        return {
            'symbol': self.symbol,
            'total_events': len(events),
            'pattern_counts': pattern_counts,
            'key_accumulation_signals': len(springs) + len(sos_signals),
            'key_distribution_signals': len(utads) + len(sows),
            'springs': springs,
            'sos_signals': sos_signals, 
            'utads': utads,
            'sows': sows,
            'events': events
        }


def load_daily_data(symbol: str, db_path: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Load daily candle data for a symbol from the database.
    
    Args:
        symbol: Symbol to load (e.g., 'ETH', 'BTC')
        db_path: Optional path to database file
        
    Returns:
        DataFrame with daily OHLCV data or None if not found
    """
    db = sqlite3.connect(str(db_path or DB_PATH))
    
    try:
        # Search by base symbol with LIKE query (handles various quote currencies)
        base = symbol.split('/')[0] if '/' in symbol else symbol
        
        # Get available symbols
        symbols_query = """
        SELECT DISTINCT symbol FROM candles_daily 
        WHERE symbol LIKE ? AND symbol NOT LIKE '%1000%'
        ORDER BY symbol
        """
        available_symbols = pd.read_sql(symbols_query, db, params=[f'{base}%'])
        
        if len(available_symbols) == 0:
            return None
            
        # Pick the best symbol (prefer USDT, then USDC)
        symbol_options = available_symbols['symbol'].tolist()
        
        best_symbol = None
        for preferred in [f'{base}/USDT', f'{base}/USDC', f'{base}/USD']:
            if preferred in symbol_options:
                best_symbol = preferred
                break
                
        if not best_symbol:
            best_symbol = symbol_options[0]  # Take first available
            
        # Load the data
        query = """
        SELECT timestamp, open, high, low, close, volume
        FROM candles_daily 
        WHERE symbol = ?
        ORDER BY timestamp
        """
        
        df = pd.read_sql(query, db, params=[best_symbol])
        
        if len(df) == 0:
            return None
            
        # Convert timestamp and set as index
        df['dt'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('dt', inplace=True)
        df.drop('timestamp', axis=1, inplace=True)
        
        # Store symbol info
        df.attrs['symbol'] = best_symbol
        df.attrs['base_symbol'] = base
        
        return df
        
    finally:
        db.close()