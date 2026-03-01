#!/usr/bin/env python3
"""V12e Exit Improvements Runner - Simple Implementation

Uses monkey-patching to add CFGI >= 75 hard gate to existing V12 engine.
Price discovery mode is already implemented in the engine.
"""
import sys
import json
import os
import types
from pathlib import Path
from datetime import datetime

# Set up import path
workspace_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(workspace_dir))

import pandas as pd
from trading.spot.backtest_engine_v12 import SpotBacktestEngineV12, DailyScorerConductor

# Configuration
PYTHON = r"C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe"
WORKSPACE = Path(__file__).resolve().parent

COINS = {
    "btc": {"symbol": "BTC/USDT", "data": "binance_BTC_1h.csv", "ath": 109000},
    "eth": {"symbol": "ETH/USDT", "data": "binance_ETH_1h.csv", "ath": 4878},
    "sol": {"symbol": "SOL/USDT", "data": "binance_SOL_1h.csv", "ath": 260}
}

PROFILES = ["low", "medium", "high"]
RESULTS_DIR = WORKSPACE / "backtest_results" / "v12e_exit_improvements"

def add_cfgi_hard_gate():
    """Add CFGI >= 75 hard gate to DailyScorerConductor via monkey-patching"""
    
    def cfgi_allows_exit(self, ts_1h_ms: int) -> bool:
        """Check if CFGI >= 75 allows EXIT transition.
        
        Returns True if CFGI >= 75 or no CFGI data available.
        Returns False if CFGI < 75 (veto the exit).
        """
        if not self._cfgi_history:
            return True  # No CFGI data available, don't block
            
        # Convert timestamp to date string for CFGI lookup
        dt = pd.Timestamp(ts_1h_ms, unit='ms', tz='UTC').normalize()
        date_str = dt.strftime("%Y-%m-%d")
        
        if date_str not in self._cfgi_history:
            return True  # No CFGI data for this date, don't block
            
        cfgi_score = self._cfgi_history[date_str]
        
        if cfgi_score < 75:
            print(f"  🚫 CFGI HARD GATE: EXIT vetoed — CFGI={cfgi_score:.0f} < 75 on {date_str}")
            return False
            
        return True
    
    # Add the method to DailyScorerConductor
    DailyScorerConductor.cfgi_allows_exit = cfgi_allows_exit
    
    # Now monkey-patch the engine to use the CFGI gate
    original_transition_to_exit = SpotBacktestEngineV12._transition_to_exit
    
    def cfgi_gated_transition_to_exit(self, price: float, ts: str, ts_ms: int, daily_score: float):
        """Wrapper that checks CFGI before allowing exit transition"""
        if self._conductor.cfgi_allows_exit(ts_ms):
            return original_transition_to_exit(self, price, ts, ts_ms, daily_score)
        else:
            # CFGI vetoed - stay in current phase
            print(f"  EXIT transition vetoed by CFGI hard gate at {ts}")
            return
    
    # Replace the method
    SpotBacktestEngineV12._transition_to_exit = cfgi_gated_transition_to_exit
    
    print("✅ CFGI >= 75 hard gate added to V12 engine")

def get_profile_params(profile: str) -> dict:
    """Get profile-specific parameters matching existing V12e"""
    if profile == "low":
        return {
            "dist_exit_threshold": 50,
            "spring_deploy_tiers": [25, 50, 75],
            "spring_score_thresholds": [60, 75, 90],
            "dist_threshold_floor": 30,
            "v12_weekly_dist_veto": False,
            "exit_mcap_ath_pct": 0.25
        }
    elif profile == "medium":
        return {
            "dist_exit_threshold": 45,
            "spring_deploy_tiers": [30, 60, 80],
            "spring_score_thresholds": [65, 80, 90],
            "dist_threshold_floor": 25,
            "v12_weekly_dist_veto": False,
            "exit_mcap_ath_pct": 0.30
        }
    else:  # high
        return {
            "dist_exit_threshold": 40,
            "spring_deploy_tiers": [35, 65, 85],
            "spring_score_thresholds": [70, 85, 95],
            "dist_threshold_floor": 20,
            "v12_weekly_dist_veto": False,
            "exit_mcap_ath_pct": 0.35
        }

def run_single_backtest(coin_key: str, coin_config: dict, profile: str) -> dict:
    """Run a single backtest configuration"""
    
    print(f"\n{'='*60}")
    print(f"RUNNING: {coin_key.upper()} {profile.upper()}")
    print(f"{'='*60}")
    
    try:
        # Load price data
        data_file = WORKSPACE / "data" / coin_config["data"]
        if not data_file.exists():
            return {"error": f"Data file not found: {data_file}"}
        
        df = pd.read_csv(data_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        print(f"Loaded {len(df):,} candles from {data_file.name}")
        print(f"Period: {df.index[0]} to {df.index[-1]}")
        
        # Get profile parameters
        profile_params = get_profile_params(profile)
        
        # Fixed parameters for exit improvements test
        params = {
            "initial_capital": 10000,
            "compound_gains": True,
            "compound_threshold_usd": 500,
            "v12_slippage_pct": 0.0005,  # 0.05% slippage
            "exchange": "aster",  # 0% maker, 0.04% taker
            "symbol": coin_config["symbol"],
            "timeframe": "1h",
            **profile_params
        }
        
        # Create engine with known ATH for price discovery mode
        engine = SpotBacktestEngineV12(**params)
        engine._conductor._known_historical_ath = coin_config["ath"]
        engine._conductor._symbol = coin_config["symbol"]
        
        print(f"Running V12e Exit Improvements: {coin_config['symbol']} {profile.upper()}")
        print(f"Known ATH: ${coin_config['ath']:,.0f}")
        print(f"Exit improvements: Price Discovery + CFGI >= 75 Hard Gate")
        
        # Run backtest
        result = engine.run(df)
        
        # Analyze results
        exit_phases = len([t for t in result.trade_log if "EXIT" in str(t.reason)])
        short_trades = [t for t in result.trade_log if "short" in str(t.reason).lower()]
        short_pnl = sum(t.pnl for t in short_trades) if short_trades else 0
        
        result_data = {
            "symbol": coin_config["symbol"],
            "profile": profile,
            "known_ath": coin_config["ath"],
            "period_start": df.index[0].isoformat(),
            "period_end": df.index[-1].isoformat(),
            "total_pnl_pct": result.total_pnl_pct,
            "max_drawdown_pct": result.max_drawdown_pct,
            "sharpe_ratio": result.sharpe_ratio,
            "total_trades": result.total_trades,
            "win_rate": result.win_rate_pct,
            "avg_trade_pct": result.avg_trade_pct,
            "exit_phases": exit_phases,
            "short_pnl": short_pnl,
            "short_trades": len(short_trades),
            "parameters": params
        }
        
        # Save individual results
        output_file = RESULTS_DIR / f"{coin_key}_{profile}_improved.json"
        with open(output_file, 'w') as f:
            json.dump(result_data, f, indent=2)
        
        print(f"✅ Results: ROI={result.total_pnl_pct:.1f}% | DD={result.max_drawdown_pct:.1f}% | Sharpe={result.sharpe_ratio:.2f}")
        print(f"   Exit Phases: {exit_phases} | Short P&L: ${short_pnl:,.0f}")
        print(f"   Saved: {output_file}")
        
        return result_data
        
    except Exception as e:
        error_msg = f"Error running {coin_key} {profile}: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg, "total_pnl_pct": 0, "max_drawdown_pct": 0}

def load_baseline_results() -> dict:
    """Load baseline V12e results for comparison"""
    baseline_dir = WORKSPACE / "backtest_results" / "v12_lifecycle"
    baseline_results = {}
    
    for coin in ["btc", "eth", "sol"]:
        for profile in ["low", "medium", "high"]:
            baseline_file = baseline_dir / f"{coin}_1h_v12e_{profile}.json"
            if baseline_file.exists():
                try:
                    data = json.loads(baseline_file.read_text())
                    baseline_results[f"{coin}_{profile}"] = data
                except Exception:
                    pass
    
    return baseline_results

def get_baseline_roi(baseline_results: dict, coin: str, profile: str) -> float:
    """Get baseline ROI for comparison"""
    key = f"{coin}_{profile}"
    if key in baseline_results:
        return baseline_results[key].get("total_pnl_pct")
    
    # Fallback to hardcoded values from requirements
    baseline_values = {
        "eth_low": 181.3, "eth_medium": 237.3, "eth_high": 314.2,
        "btc_low": 233.0, "btc_medium": 185.0, "btc_high": 463.0,
        "sol_low": 132.1, "sol_medium": 191.9, "sol_high": 184.4
    }
    
    return baseline_values.get(key)

def generate_results_report(all_results: dict):
    """Generate comprehensive results report"""
    baseline_results = load_baseline_results()
    
    report_content = f"""# V12e Exit Improvements Backtest Results
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Configuration
- **Price Discovery Mode**: ✅ Enabled (requires weekly confirmation when price > KNOWN_ATH)
- **CFGI Hard Gate**: ✅ Enabled (EXIT requires CFGI >= 75, vetoes if CFGI < 75)
- **Capital**: $10,000
- **Compounding**: True  
- **Slippage**: 0.05% (0.0005)
- **Exchange**: Aster (0% maker / 0.04% taker fees)
- **Period**: Oct 2020 → Feb 2026 (all available 1h data)

## Known ATH Values
- **BTC**: $109,000
- **ETH**: $4,878
- **SOL**: $260

## Results Summary

| Coin | Profile | Improved ROI | Improved DD | Improved Sharpe | Exit Phases | Short PnL | Baseline ROI* | ROI Change |
|------|---------|-------------|-------------|----------------|-------------|-----------|---------------|------------|
"""
    
    # Add results rows
    for coin in ["btc", "eth", "sol"]:
        for profile in ["low", "medium", "high"]:
            key = f"{coin}_{profile}"
            
            if key in all_results and "error" not in all_results[key]:
                r = all_results[key]
                baseline_roi = get_baseline_roi(baseline_results, coin, profile)
                roi_change = ""
                if baseline_roi is not None and r.get("total_pnl_pct"):
                    change = r.get("total_pnl_pct", 0) - baseline_roi
                    roi_change = f"{change:+.1f}%"
                
                report_content += f"| {coin.upper()} | {profile} | {r.get('total_pnl_pct', 0):.1f}% | {r.get('max_drawdown_pct', 0):.1f}% | {r.get('sharpe_ratio', 0):.2f} | {r.get('exit_phases', 0)} | ${r.get('short_pnl', 0):,.0f} | {baseline_roi or 'N/A'} | {roi_change} |\n"
            else:
                error = all_results.get(key, {}).get("error", "Not run")
                report_content += f"| {coin.upper()} | {profile} | ERROR | ERROR | ERROR | - | - | - | {error} |\n"
    
    report_content += """
*Baseline ROI from V12e results without fees/slippage

## Impact Analysis

### Price Discovery Mode Impact
When price > KNOWN_ATH (price discovery mode):
- ATH proximity gate becomes meaningless (price IS the ATH)
- Weekly bearish structure confirmation required before EXIT
- More conservative exits during genuine price discovery periods

### CFGI Hard Gate Impact
EXIT transitions require CFGI >= 75:
- Prevents exits during fear/panic periods (CFGI < 75)
- Only allows exits when greed is elevated
- Falls back gracefully when CFGI data unavailable

## Detailed Results

"""
    
    # Add detailed results for each coin
    for coin in ["btc", "eth", "sol"]:
        report_content += f"### {coin.upper()} Results\n\n"
        
        for profile in ["low", "medium", "high"]:
            key = f"{coin}_{profile}"
            if key in all_results and "error" not in all_results[key]:
                r = all_results[key]
                report_content += f"""**{profile.upper()} Profile**
- ROI: {r.get('total_pnl_pct', 0):.1f}%
- Max Drawdown: {r.get('max_drawdown_pct', 0):.1f}%
- Sharpe Ratio: {r.get('sharpe_ratio', 0):.2f}
- Total Trades: {r.get('total_trades', 0)}
- Win Rate: {r.get('win_rate', 0):.1f}%
- Exit Phases: {r.get('exit_phases', 0)}
- Short P&L: ${r.get('short_pnl', 0):,.0f} ({r.get('short_trades', 0)} trades)

"""
            else:
                error = all_results.get(key, {}).get("error", "Not run")
                report_content += f"**{profile.upper()} Profile**: ❌ {error}\n\n"
        
        report_content += "\n"
    
    # Save report
    report_file = RESULTS_DIR / "RESULTS.md"
    report_file.write_text(report_content)
    
    # Also save raw results
    raw_results_file = RESULTS_DIR / "raw_results.json"
    with open(raw_results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n📊 Results report saved to: {report_file}")
    print(f"📊 Raw results saved to: {raw_results_file}")

def main():
    print(f"""
{'='*80}
V12e EXIT IMPROVEMENTS BACKTEST SUITE
Price Discovery Mode + CFGI >= 75 Hard Gate
{'='*80}

Running 9 backtests: 3 coins × 3 profiles
Output: {RESULTS_DIR}
""")
    
    # Create results directory
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Add CFGI hard gate to the engine
    add_cfgi_hard_gate()
    
    # Store all results
    all_results = {}
    
    # Run all combinations
    for coin_key, coin_config in COINS.items():
        for profile in PROFILES:
            run_key = f"{coin_key}_{profile}"
            result = run_single_backtest(coin_key, coin_config, profile)
            all_results[run_key] = result
    
    # Generate comparison report
    generate_results_report(all_results)
    
    print(f"\n{'='*80}")
    print("✅ BACKTEST SUITE COMPLETE")
    print(f"📁 Results saved to: {RESULTS_DIR}")
    print(f"📊 View RESULTS.md for detailed comparison")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()