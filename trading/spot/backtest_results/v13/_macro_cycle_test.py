"""
Macro Cycle Backtest for V13 Trading Engine
Simplified but powerful strategy: ALL IN LONG or ALL IN SHORT based on signals.

Strategy:
1. Start in CASH (waiting for signal)
2. BOTTOM SIGNAL STACK (≥4/5 + Spring required) → ALL IN LONG
3. TOP SIGNAL (2W StochRSI K>93, or 1W>85 fallback, or 1W K<50 failsafe) → ALL IN SHORT
4. BOTTOM SIGNAL again → ALL IN LONG
5. Repeat

Bottom signals (need ≥4/5 + Spring required):
- 2D death cross active
- Below SMA200 (daily)
- CFGI < 35
- Weekly RSI(7) < 30
- Spring pattern (break below 20-day support + recover within 5 days)

Top signals (first match wins):
- 2W StochRSI K > 93 (primary)
- 1W StochRSI K > 85 (fallback)
- 1W StochRSI K < 50 (failsafe)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from v13_signals import V13SignalPack
from _bottom_stack_test import BottomStackDetector

# Avoid Unicode issues
import locale
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'candles.db'


class MacroCycleBacktest:
    """Macro Cycle Strategy: Binary long/short position switching."""
    
    def __init__(self, coin, start_date='2023-01-01', end_date='2026-02-25', capital=2500):
        self.coin = coin
        self.start_date = pd.Timestamp(start_date)
        self.end_date = pd.Timestamp(end_date)
        self.capital = capital
        
        # Load signal components
        try:
            self.pack = V13SignalPack(coin)
            self.bottom_detector = BottomStackDetector(coin)
        except Exception as e:
            print(f"ERROR loading {coin}: {e}")
            self.pack = None
            self.bottom_detector = None
            return
        
        # Trade tracking
        self.position = 'CASH'  # CASH, LONG, SHORT
        self.shares = 0.0
        self.entry_price = 0.0
        self.entry_date = None
        self.cash = capital
        self.equity_curve = []
        self.trades = []
        
        print(f"Initialized {coin}: {start_date} to {end_date}, ${capital:,.0f} capital")
    
    def get_daily_data(self):
        """Get daily price data in backtest range."""
        if self.pack is None:
            return None
        
        daily = self.pack.daily.copy()
        daily = daily[(daily.index >= self.start_date) & (daily.index <= self.end_date)]
        daily = daily[~daily.index.duplicated(keep='last')]
        daily = daily[daily.index.notna()]
        return daily.sort_index()
    
    def check_bottom_signal(self, date, min_hold_days=7):
        """Check if bottom signal stack fires (≥4/5 with Spring required)."""
        if self.bottom_detector is None:
            return False, {}
        
        # Prevent whipsaw: minimum hold period for shorts
        if (self.position == 'SHORT' and self.entry_date is not None and 
            (date - self.entry_date).days < min_hold_days):
            return False, {}
        
        count, signals = self.bottom_detector.check_bottom_stack(
            date, min_dx_days=10, cfgi_thresh=35, rsi_thresh=30
        )
        
        # Require ≥4/5 signals AND Spring pattern
        stack_active = count >= 4 and signals.get('spring', False)
        return stack_active, signals
    
    def check_top_signal(self, date, min_hold_days=7):
        """Check if top signal fires (2W K>93, or 1W K>85, or 1W K<50 failsafe after 14+ days)."""
        if self.pack is None:
            return False, ""
        
        # Prevent whipsaw: minimum hold period
        if (self.position == 'LONG' and self.entry_date is not None and 
            (date - self.entry_date).days < min_hold_days):
            return False, "min_hold"
        
        try:
            # Primary: 2W StochRSI K > 93
            if hasattr(self.pack, 'stoch_2w'):
                k_2w = self.pack.stoch_2w.get_k_at(date)
                if not pd.isna(k_2w) and k_2w > 93:
                    return True, f"2W_OB93 (K={k_2w:.1f})"
            
            # Fallback: 1W StochRSI K > 85
            if hasattr(self.pack, 'stoch_1w'):
                k_1w = self.pack.stoch_1w.get_k_at(date)
                if not pd.isna(k_1w) and k_1w > 85:
                    return True, f"1W_OB85 (K={k_1w:.1f})"
                
                # Failsafe: 1W StochRSI K < 50 (only after 14+ days to avoid whipsaws)
                if (self.entry_date is not None and 
                    (date - self.entry_date).days >= 14 and
                    not pd.isna(k_1w) and k_1w < 50):
                    return True, f"1W_K50_failsafe (K={k_1w:.1f})"
            
        except Exception as e:
            print(f"  Warning: StochRSI error on {date}: {e}")
        
        return False, ""
    
    def execute_trade(self, date, action, price, signal_info):
        """Execute a trade: go ALL IN LONG, ALL IN SHORT, or close position."""
        current_equity = self.calculate_equity(date, price)
        
        if action == 'LONG':
            if self.position == 'SHORT':
                # Close short position
                # Short P&L = shares * (entry_price - current_price)
                pnl = self.shares * (self.entry_price - price)
                current_equity = self.cash + pnl  # Final equity after closing short
                
                # Record short trade
                hold_days = (date - self.entry_date).days
                pnl_pct = (self.entry_price - price) / self.entry_price * 100
                self.trades.append({
                    'entry_date': self.entry_date,
                    'exit_date': date,
                    'direction': 'SHORT',
                    'entry_price': self.entry_price,
                    'exit_price': price,
                    'pnl_pct': pnl_pct,
                    'hold_days': hold_days,
                    'exit_signal': signal_info
                })
            
            # Go ALL IN LONG
            self.shares = current_equity / price
            self.cash = 0
            self.position = 'LONG'
            self.entry_price = price
            self.entry_date = date
            
        elif action == 'SHORT':
            if self.position == 'LONG':
                # Close long position
                current_equity = self.shares * price
                
                # Record long trade
                hold_days = (date - self.entry_date).days
                pnl_pct = (price - self.entry_price) / self.entry_price * 100
                self.trades.append({
                    'entry_date': self.entry_date,
                    'exit_date': date,
                    'direction': 'LONG',
                    'entry_price': self.entry_price,
                    'exit_price': price,
                    'pnl_pct': pnl_pct,
                    'hold_days': hold_days,
                    'exit_signal': signal_info
                })
            
            # Go ALL IN SHORT
            # For shorts: we sell 'shares' amount at current price
            # shares represents the position size, cash represents our proceeds from the sale
            self.shares = current_equity / price  # Position size (shares we're short)
            self.cash = current_equity  # Cash proceeds from short sale
            self.position = 'SHORT'
            self.entry_price = price
            self.entry_date = date
        
        print(f"  {date.strftime('%Y-%m-%d')}: {action} at ${price:.2f} - {signal_info} (Equity: ${current_equity:,.0f})")
    
    def calculate_equity(self, date, price):
        """Calculate current portfolio equity."""
        if self.position == 'CASH':
            return self.cash
        elif self.position == 'LONG':
            return self.shares * price
        elif self.position == 'SHORT':
            # Short equity = cash proceeds from initial sale + unrealized P&L
            # P&L for short = shares * (entry_price - current_price)
            unrealized_pnl = self.shares * (self.entry_price - price)
            return self.cash + unrealized_pnl
        return 0
    
    def run(self):
        """Run the macro cycle backtest."""
        if self.pack is None or self.bottom_detector is None:
            return None
        
        daily_data = self.get_daily_data()
        if daily_data is None or len(daily_data) == 0:
            print(f"  No data for {self.coin}")
            return None
        
        print(f"\nRunning {self.coin} backtest...")
        
        for date in daily_data.index:
            price = daily_data.loc[date, 'close']
            if pd.isna(price):
                continue
            
            # Check for signals based on current position
            if self.position in ['CASH', 'SHORT']:
                # Look for bottom signal to go LONG
                bottom_active, bottom_signals = self.check_bottom_signal(date)
                if bottom_active:
                    signal_desc = (f"BOTTOM_STACK {bottom_signals['active_count']}/5 "
                                 f"(DX={bottom_signals['dx_days']}d, "
                                 f"CFGI={bottom_signals['cfgi']:.0f}, "
                                 f"WRSI={bottom_signals['wrsi']:.0f}, Spring=YES)")
                    self.execute_trade(date, 'LONG', price, signal_desc)
            
            elif self.position == 'LONG':
                # Look for top signal to go SHORT
                top_active, top_desc = self.check_top_signal(date)
                if top_active:
                    self.execute_trade(date, 'SHORT', price, f"TOP_SIGNAL {top_desc}")
            
            # Track equity
            equity = self.calculate_equity(date, price)
            self.equity_curve.append({
                'date': date,
                'price': price,
                'position': self.position,
                'equity': equity
            })
        
        # Calculate final results
        final_equity = self.equity_curve[-1]['equity'] if self.equity_curve else self.capital
        roi = (final_equity - self.capital) / self.capital * 100
        
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t['pnl_pct'] > 0])
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        avg_hold_days = np.mean([t['hold_days'] for t in self.trades]) if self.trades else 0
        
        return {
            'coin': self.coin,
            'final_equity': final_equity,
            'roi': roi,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_hold_days': avg_hold_days,
            'trades': self.trades
        }


def main():
    """Run macro cycle backtest for all coins."""
    coins = ['ETH', 'SOL', 'BTC', 'LINK', 'XRP']
    total_capital = 10000
    capital_per_coin = total_capital / len(coins)
    
    print("=" * 120)
    print("  MACRO CYCLE BACKTEST - V13 Trading Engine")
    print("  Binary Long/Short Strategy: 2023-01-01 to 2026-02-25")
    print(f"  Capital: ${total_capital:,.0f} total (${capital_per_coin:,.0f} per coin)")
    print("=" * 120)
    
    results = {}
    total_equity = 0
    all_trades = []
    
    for coin in coins:
        bt = MacroCycleBacktest(coin, start_date='2023-01-01', 
                               end_date='2026-02-25', capital=capital_per_coin)
        result = bt.run()
        
        if result:
            results[coin] = result
            total_equity += result['final_equity']
            all_trades.extend(result['trades'])
            
            print(f"\n{coin} Results:")
            print(f"  Final Equity: ${result['final_equity']:,.0f}")
            print(f"  ROI: {result['roi']:+.1f}%")
            print(f"  Total Trades: {result['total_trades']}")
            print(f"  Win Rate: {result['win_rate']:.1f}%")
            print(f"  Avg Hold: {result['avg_hold_days']:.0f} days")
            
            # Show individual trades
            if result['trades']:
                print(f"  Trades:")
                for trade in result['trades']:
                    print(f"    {trade['entry_date'].strftime('%Y-%m-%d')} to "
                          f"{trade['exit_date'].strftime('%Y-%m-%d')}: "
                          f"{trade['direction']} ${trade['entry_price']:.2f} -> "
                          f"${trade['exit_price']:.2f} = {trade['pnl_pct']:+.1f}% "
                          f"({trade['hold_days']}d)")
        else:
            print(f"\n{coin}: FAILED")
    
    # Summary
    total_roi = (total_equity - total_capital) / total_capital * 100
    total_trades = len(all_trades)
    winning_trades = len([t for t in all_trades if t['pnl_pct'] > 0])
    total_win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
    avg_hold_time = np.mean([t['hold_days'] for t in all_trades]) if all_trades else 0
    
    print("\n" + "=" * 120)
    print("  MACRO CYCLE SUMMARY")
    print("=" * 120)
    print(f"Total Equity:     ${total_equity:,.0f}")
    print(f"Total ROI:        {total_roi:+.1f}%")
    print(f"Total Trades:     {total_trades}")
    print(f"Win Rate:         {total_win_rate:.1f}%")
    print(f"Avg Hold Time:    {avg_hold_time:.0f} days")
    print("")
    print(f"V13 v8 Baseline:  $24,442 (same period/coins)")
    baseline_delta = total_equity - 24442
    print(f"Delta vs V13 v8:  {baseline_delta:+,.0f} ({baseline_delta/24442*100:+.1f}%)")
    
    # Per-coin breakdown
    print(f"\nPer-Coin Results:")
    print(f"{'Coin':<6} {'Equity':>10} {'ROI':>8} {'Trades':>7} {'WinRate':>8} {'AvgHold':>8}")
    print("-" * 65)
    for coin in coins:
        if coin in results:
            r = results[coin]
            print(f"{coin:<6} ${r['final_equity']:>9,.0f} {r['roi']:>7.1f}% "
                  f"{r['total_trades']:>7} {r['win_rate']:>7.1f}% "
                  f"{r['avg_hold_days']:>7.0f}d")
        else:
            print(f"{coin:<6} {'FAILED':>10}")


if __name__ == '__main__':
    main()